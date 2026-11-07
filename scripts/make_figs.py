#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把课件 PDF 逐页渲染，自动裁出「图形区」，生成可嵌入笔记的 PNG 配图。

处理链路：
  PowerPoint 导出的 PDF（矢量保真）
    → 按 DPI 渲染整页
    → 依据页眉文字判断并去掉标题带 / 页脚
    → 非白像素投影求内容外接框，自动裁掉白边
    → 保存 assets/figs/<id>_p<nn>.png

同时产出：
  src/fig_index.json        每页配图的元数据
  src/figs_ch<N>.md         按「笔记章」归组的可读配图清单（给撰写单元用）
  thumbs/ch<N>_s<k>.png     配图联系表（便于人工/多模态核验）
"""
import json
import pathlib
import re
import sys

import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFont
from chapter_map import load_chapter_map

BUILD = pathlib.Path(__file__).resolve().parents[1]
PDF = BUILD / 'pdf'
FIGS = BUILD / 'assets' / 'figs'
THUMBS = BUILD / 'thumbs'
SRC = BUILD / 'src'
FIGS.mkdir(parents=True, exist_ok=True)
THUMBS.mkdir(parents=True, exist_ok=True)

DPI = 150
SCALE = DPI / 72.0
HEADER_CUT_PT = 66.0      # 标准课件标题带高度
FOOTER_CUT_PT = 534.0
PAD = 14                  # 裁图四周留白(px)
INK_THRESH = 236          # 低于此灰度算作内容

CHAPTER_MAP, CHAPTER_TITLE = load_chapter_map(SRC / 'chapter_map.json')


def header_present(page):
    """页眉是否有大字号标题文字（决定要不要裁掉顶部标题带）。"""
    try:
        d = page.get_text('dict')
    except Exception:
        return False
    best = 0.0
    for b in d['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                if s['bbox'][1] < 80 and s['text'].strip():
                    best = max(best, s['size'])
    return best >= 15.5


def visual_stats(page):
    try:
        nd = len(page.get_drawings())
    except Exception:
        nd = 0
    try:
        ni = len(page.get_image_info())
    except Exception:
        ni = 0
    return nd, ni


def crop_page(page, has_header):
    pix = page.get_pixmap(dpi=DPI, alpha=False)
    img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
    gray = np.asarray(img.convert('L'))
    mask = gray < INK_THRESH
    h, w = mask.shape

    y0 = int(HEADER_CUT_PT * SCALE) if has_header else 0
    y1 = min(h, int(FOOTER_CUT_PT * SCALE))
    mask[:y0, :] = False
    mask[y1:, :] = False

    # 行列投影：忽略孤立噪点和细装饰线
    rows = mask.sum(axis=1)
    cols = mask.sum(axis=0)
    ys = np.where(rows > 3)[0]
    xs = np.where(cols > 3)[0]
    if len(ys) == 0 or len(xs) == 0:
        return None

    # 去掉极端离群（如右下角校徽、页码残留）
    def robust(v):
        lo = np.percentile(v, 0.4)
        hi = np.percentile(v, 99.6)
        return int(lo), int(hi)

    ya, yb = robust(ys)
    xa, xb = robust(xs)
    xa = max(0, xa - PAD); ya = max(y0, ya - PAD)
    xb = min(w, xb + PAD); yb = min(y1, yb + PAD)
    if yb - ya < 42 or xb - xa < 70:
        return None
    return img.crop((xa, ya, xb, yb))


def main():
    idx = {r['id']: r for r in json.loads((SRC / '_index.json').read_text(encoding='utf-8'))}
    records = []
    index_only = '--index-only' in sys.argv
    if index_only:
        records = json.loads((SRC / 'fig_index.json').read_text(encoding='utf-8'))
        print('仅重建清单与联系表：%d 条记录' % len(records))
    for fid in ([] if index_only else sorted(idx)):
        pdf = PDF / (fid + '.pdf')
        if not pdf.exists():
            print('MISSING', pdf.name)
            continue
        doc = pymupdf.open(pdf)
        out = []
        for pno in range(doc.page_count):
            page = doc[pno]
            hdr = header_present(page)
            nd, ni = visual_stats(page)
            name = '%s_p%02d.png' % (fid, pno + 1)
            rec = {'id': fid, 'page': pno + 1, 'file': 'assets/figs/' + name,
                   'header': hdr, 'drawings': nd, 'images': ni}
            # 纯文字页不生成配图；其余一律生成，保证「不漏图」
            if nd >= 6 or ni >= 1:
                try:
                    im = crop_page(page, hdr)
                except Exception as e:
                    im = None
                    rec['error'] = repr(e)
                if im is not None:
                    im.save(FIGS / name, optimize=True)
                    rec['ok'] = True
                    rec['w'], rec['h'] = im.size
            out.append(rec)
        doc.close()
        records.extend(out)
        ok = sum(1 for r in out if r.get('ok'))
        print('%-4s pages=%3d figs=%3d' % (fid, len(out), ok), flush=True)

    (SRC / 'fig_index.json').write_text(
        json.dumps(records, ensure_ascii=False, indent=1), encoding='utf-8')

    # 文字摘要（取每页前 60 字，去掉重复的页眉）
    texts = {}
    for fid in idx:
        t = (SRC / (fid + '.txt')).read_text(encoding='utf-8')
        parts = re.split(r'<<<SLIDE (\d+)>>>', t)
        for i in range(1, len(parts), 2):
            n = int(parts[i])
            lines = [x.strip() for x in parts[i + 1].strip().splitlines() if x.strip()]
            texts[(fid, n)] = ' / '.join(lines[:3])[:78]

    by_key = {(r['id'], r['page']): r for r in records}

    # 每章一份配图清单 + 联系表
    for ch in sorted(CHAPTER_MAP):
        lines = ['# 第 %d 章 %s · 可用配图清单' % (ch, CHAPTER_TITLE[ch]), '',
                 '路径均相对于 build/note_full.html；图来自原课件 PDF 高保真裁切。', '']
        pics = []
        for entry in CHAPTER_MAP[ch]:
            fid, desc = entry[0], entry[1]
            rng = entry[2] if len(entry) > 2 else None
            lines.append('## %s —— %s%s' % (
                fid, desc, ('（只用第 %d–%d 页）' % rng) if rng else ''))
            lines.append('')
            for (f, n), r in sorted(by_key.items()):
                if f != fid or not r.get('ok'):
                    continue
                if rng and not (rng[0] <= n <= rng[1]):
                    continue
                tag = texts.get((fid, n), '')
                lines.append('- `%s`  |  %s p%-2d  |  %s' % (r['file'], fid, n, tag))
                pics.append((r['file'], '%s p%d' % (fid, n), tag))
            lines.append('')
        (SRC / ('figs_ch%d.md' % ch)).write_text('\n'.join(lines), encoding='utf-8')

        # 联系表：4 列，每格 250×190
        if not pics:
            continue
        font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 14)
        cw, chh, cols = 250, 200, 4
        per = 24
        for s in range(0, len(pics), per):
            batch = pics[s:s + per]
            rows = (len(batch) + cols - 1) // cols
            sheet = Image.new('RGB', (cols * cw, rows * chh), '#ffffff')
            dr = ImageDraw.Draw(sheet)
            for k, (path, label, tag) in enumerate(batch):
                cx, cy = (k % cols) * cw, (k // cols) * chh
                im = Image.open(BUILD / path).convert('RGB')
                im.thumbnail((cw - 12, chh - 48))
                sheet.paste(im, (cx + (cw - im.width) // 2, cy + 4))
                dr.text((cx + 6, cy + chh - 40), label, fill='#1a5a9e', font=font)
                dr.text((cx + 6, cy + chh - 22), tag[:20], fill='#555555', font=font)
                dr.rectangle([cx, cy, cx + cw - 1, cy + chh - 1], outline='#dde5ee')
            sheet.save(THUMBS / ('ch%d_s%d.png' % (ch, s // per + 1)))
        print('ch%d 清单 %d 图, 联系表 %d 张' % (ch, len(pics), (len(pics) + per - 1) // per))

    print('配图总数：', sum(1 for r in records if r.get('ok')))


if __name__ == '__main__':
    main()
