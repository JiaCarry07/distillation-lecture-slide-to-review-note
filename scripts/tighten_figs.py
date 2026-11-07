#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把「整页裁图」升级为「紧凑纯图」，文件名保持不变，HTML 无需改动。

v2（像素级，安全）：
  1. 渲染整页；
  2. 抹掉固定页眉（校徽/水印/大标题）与页脚；
  3. 抹掉「宽且长」的说明段落文字块（短标注、尺寸数字一律保留）；
  4. 把连续的大片空白行压缩成窄间隔（只动垂直方向，保持三视图的长对正）；
  5. 自动裁白边。

这样不丢任何图形元素（矢量线、位图、图内标注都在），只去掉文字与空白。
默认输出到 assets/figs_v2/ 供比对；加 --apply 覆盖 assets/figs/。
"""
import json
import pathlib
import sys

import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFont

BUILD = pathlib.Path(__file__).resolve().parents[1]
PDF = BUILD / 'pdf'
OLDFIG = BUILD / 'assets' / 'figs'
OUTFIG = BUILD / 'assets' / 'figs_v2'
THUMBS = BUILD / 'thumbs'
OUTFIG.mkdir(parents=True, exist_ok=True)

DPI = 165
S = DPI / 72.0
HEADER_PT = 80          # 页眉带（含校徽、水印、大标题）
FOOTER_FRAC = 0.935
GAP_TRIGGER = 34        # 超过这么多连续空白像素才压缩
GAP_KEEP = 12
INK_THRESH = 236


def build(page):
    W, H = page.rect.width, page.rect.height
    pix = page.get_pixmap(dpi=DPI, alpha=False)
    arr = np.asarray(Image.frombytes('RGB', (pix.width, pix.height), pix.samples)).copy()
    h, w = arr.shape[:2]
    mask = arr.mean(axis=2) < INK_THRESH

    def white(y0, y1, x0, x1):
        y0, y1 = max(0, int(y0)), min(h, int(y1))
        x0, x1 = max(0, int(x0)), min(w, int(x1))
        if y1 > y0 and x1 > x0:
            arr[y0:y1, x0:x1] = 255
            mask[y0:y1, x0:x1] = False

    # 页眉 / 页脚
    white(0, HEADER_PT * S, 0, w)
    white(FOOTER_FRAC * H * S, h, 0, w)

    # 长段落说明文字：又宽又长才算，图内短标注不动
    try:
        blocks = page.get_text('blocks')
    except Exception:
        blocks = []
    nblank = 0
    for blk in blocks:
        if blk[6] != 0:
            continue
        t = blk[4].strip()
        if len(t) <= 24:
            continue
        b = pymupdf.Rect(blk[:4])
        if b.width < 0.34 * W:        # 窄块多为图内多行标注，保留
            continue
        white(b.y0 * S - 2, b.y1 * S + 2, b.x0 * S - 2, b.x1 * S + 2)
        nblank += 1

    # 垂直空白压缩（水平方向不动，保证长对正 / 高平齐关系不被打乱）
    row = mask.sum(axis=1)
    keep = []
    i = 0
    while i < h:
        if row[i] > 2:
            keep.append(i)
            i += 1
            continue
        j = i
        while j < h and row[j] <= 2:
            j += 1
        gap = j - i
        if gap > GAP_TRIGGER:
            st = i + (gap - GAP_KEEP) // 2
            keep.extend(range(st, st + GAP_KEEP))
        else:
            keep.extend(range(i, j))
        i = j
    if not keep:
        return None, nblank
    out = arr[np.array(keep, dtype=np.int32)]
    im = Image.fromarray(out)

    # 四边白边裁剪
    g = np.asarray(im.convert('L'))
    m = g < INK_THRESH
    rs, cs = m.sum(axis=1), m.sum(axis=0)
    ys, xs = np.where(rs > 3)[0], np.where(cs > 3)[0]
    if len(ys) == 0 or len(xs) == 0:
        return None, nblank
    box = (int(np.percentile(xs, .3)), int(np.percentile(ys, .3)),
           int(np.percentile(xs, 99.7)) + 1, int(np.percentile(ys, 99.7)) + 1)
    im = im.crop(box)
    if im.width < 70 or im.height < 42:
        return None, nblank
    return im, nblank


def main():
    apply = '--apply' in sys.argv
    dest = OLDFIG if apply else OUTFIG
    idx = json.loads((BUILD / 'src' / 'fig_index.json').read_text(encoding='utf-8'))
    targets = [r for r in idx if r.get('ok')]
    stat, docs = [], {}
    for r in targets:
        fid = r['id']
        if fid not in docs:
            docs[fid] = pymupdf.open(PDF / (fid + '.pdf'))
        d = docs[fid]
        pno = r['page'] - 1
        name = pathlib.Path(r['file']).name
        src = OLDFIG / name
        out = dest / name
        if pno >= d.page_count or not src.exists():
            continue
        old = Image.open(src)
        oi = int((np.asarray(old.convert('L')) < INK_THRESH).sum())
        try:
            im, nb = build(d[pno])
        except Exception:
            im, nb = None, -1
        if im is None:
            if not apply:
                out.write_bytes(src.read_bytes())
            stat.append((name, 'fallback', 0, 0, 0, 0, nb))
            continue
        # 安全网：某些课件用大文本框罩住整页，抹文字会连图一起抹掉。
        # 墨迹骤降(<35%)或宽度骤减(<72%)说明削到了图形，直接回退原整页裁图。
        ni = int((np.asarray(im.convert('L')) < INK_THRESH).sum())
        if ni / max(1, oi) < 0.35 or im.width / max(1, old.width) < 0.72:
            if not apply:
                out.write_bytes(src.read_bytes())
            stat.append((name, 'rollback', 0, 0, 0, 0, nb))
            continue
        im.save(out, optimize=True)
        stat.append((name, 'tight', old.width, old.height, im.width, im.height, nb))
    for d in docs.values():
        d.close()

    done = [s for s in stat if s[1] == 'tight']
    print('处理 %d 张 | 紧凑成功 %d | 安全回退 %d（削图保护 %d / 无内容 %d）' % (
        len(stat), len(done), len(stat) - len(done),
        sum(1 for s in stat if s[1] == 'rollback'),
        sum(1 for s in stat if s[1] == 'fallback')))
    if done:
        print('平均尺寸 原 %.0fx%.0f -> 新 %.0fx%.0f' % (
            np.mean([s[2] for s in done]), np.mean([s[3] for s in done]),
            np.mean([s[4] for s in done]), np.mean([s[5] for s in done])))
        print('平均高度比 %.2f | 面积比 %.2f | 高宽比中位数 原 %.2f -> 新 %.2f' % (
            np.mean([s[5] / max(1, s[3]) for s in done]),
            np.mean([s[4] * s[5] / max(1, s[2] * s[3]) for s in done]),
            np.median([s[3] / max(1, s[2]) for s in done]),
            np.median([s[5] / max(1, s[4]) for s in done])))
    print('输出 ->', dest)

    # 对比联系表
    picks = [s[0] for s in done[::max(1, len(done) // 12)]][:12]
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 15)
    cw, rh = 330, 250
    sheet = Image.new('RGB', (cw * 2, rh * max(1, len(picks))), '#ffffff')
    dr = ImageDraw.Draw(sheet)
    for k, name in enumerate(picks):
        for j, folder in enumerate([OLDFIG, dest]):
            p = folder / name
            if not p.exists():
                continue
            im = Image.open(p).convert('RGB')
            im.thumbnail((cw - 16, rh - 30))
            sheet.paste(im, (j * cw + (cw - im.width) // 2, k * rh + 24))
        dr.text((6, k * rh + 4), '%s   左:整页裁图   右:紧凑纯图' % name,
                fill='#1a5a9e', font=font)
        dr.line([(cw, k * rh), (cw, (k + 1) * rh)], fill='#d3dfec')
        dr.line([(0, (k + 1) * rh - 1), (cw * 2, (k + 1) * rh - 1)], fill='#e8eff7')
    sheet.save(THUMBS / 'compare_v2.png')
    for i, (a, b) in enumerate([(0, 4), (4, 8), (8, 12)]):
        if a * rh < sheet.height:
            sheet.crop((0, a * rh, cw * 2, min(sheet.height, b * rh))).save(
                THUMBS / ('cmp_v2_%d.png' % (i + 1)))
    print('对比图 -> thumbs/compare_v2.png 及 3 张分段图')


if __name__ == '__main__':
    main()
