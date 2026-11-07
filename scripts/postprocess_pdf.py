#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""定稿后处理：全本逐页体检 + 按章抽样渲染 + 写入 PDF 书签与元数据。

用法：python tools/postprocess_pdf.py <final.pdf>
会就地增量更新最终 PDF。
"""
import argparse
import html
import pathlib
import re
import sys

import pymupdf
from project_parts import chapter_sources

BUILD = pathlib.Path(__file__).resolve().parents[1]
PARTS = BUILD / 'parts'
AUDIT = BUILD / 'thumbs' / 'audit'
AUDIT.mkdir(parents=True, exist_ok=True)

def plain(fragment: str) -> str:
    """把标题片段还原成 PDF 文本层里可能出现的纯文本。"""
    s = re.sub(r'<[^>]+>', '', fragment)
    s = html.unescape(s)
    return re.sub(r'\s+', '', s)


def clean_label(title: str) -> str:
    """书签显示名：去掉子代理写在小节标题尾部的课件来源括注。"""
    t = re.sub(r'（[^）]*(?:课件|f\d\d\s*p)[^）]*）', '', title)
    t = re.sub(r'\([^)]*(?:课件|f\d\d\s*p)[^)]*\)', '', t)
    return t.strip() or title


def collect_headings():
    """返回 [(level, 标题, 章号 or None)]，按文档顺序。"""
    out = [(1, '封面', None), (1, '目录', None)]
    for n, f, title in chapter_sources(PARTS):
        s = f.read_text(encoding='utf-8')
        m = re.search(r'<h1 class="chap"[^>]*>(.*?)</h1>', s, re.S)
        if m:
            t = plain(m.group(1))
            t = re.sub(r'^CHAPTER\d+', '', t)
            if t:
                title = t
        out.append((1, title if n == 0 else '第 %d 章　%s' % (n, title), n))
        for h in re.findall(r'<h2 class="sub"[^>]*>(.*?)</h2>', s, re.S):
            t = plain(h)
            if t:
                out.append((2, t, n))
    return out


def norm(s: str) -> str:
    return re.sub(r'[\s\u3000]+', '', s)


def build_toc(doc, headings):
    """按顺序在页文本里定位每个标题，生成 PyMuPDF TOC。"""
    page_norm = [norm(doc[i].get_text()) for i in range(doc.page_count)]
    toc = []
    cursor = 0
    missed = []
    for level, title, ch in headings:
        if title == '封面':
            toc.append([1, title, 1]); cursor = 1; continue
        if title == '目录':
            toc.append([1, title, 2]); cursor = 2; continue
        key = norm(title)
        found = None
        # 完整匹配 → 退而求其次用前 10 字 → 再退用前 6 字
        for k in dict.fromkeys([key, key[:10], key[:6]]):
            if not k:
                continue
            for i in range(cursor, doc.page_count):
                if k in page_norm[i]:
                    found = i + 1
                    break
            if found:
                break
        if not found:
            # 章标题用 CHAPTER 锚点兜底
            if level == 1 and ch is not None:
                pat = re.compile(r'C\s*H\s*A\s*P\s*T\s*E\s*R\s*%d' % ch)
                for i in range(cursor, doc.page_count):
                    if pat.search(doc[i].get_text()):
                        found = i + 1
                        break
        if found:
            toc.append([level, clean_label(title) if level == 2 else title, found])
            cursor = max(cursor, found - 1)   # 同一页可命中多个标题
        else:
            missed.append(title)
    return toc, missed


def audit(doc):
    rows = []
    for i in range(doc.page_count):
        t = doc[i].get_text()
        nimg = len(doc[i].get_images(full=True))
        # 图片是否越出页边距
        overflow = 0
        for img in doc[i].get_images(full=True):
            for r in doc[i].get_image_rects(img[0]):
                if r.x0 < 20 or r.x1 > doc[i].rect.width - 20 or r.y1 > doc[i].rect.height - 12:
                    overflow += 1
        rows.append((i + 1, len(t.strip()), nimg, overflow))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=pathlib.Path)
    args = parser.parse_args()
    pdf = args.pdf.resolve()
    doc = pymupdf.open(pdf)
    print('打开:', pdf.name, '| 页数', doc.page_count, flush=True)

    # ---------- 1. 全本逐页体检 ----------
    rows = audit(doc)
    sparse = [p for p, n, im, ov in rows if n < 90 and im == 0]
    overflow = [(p, ov) for p, n, im, ov in rows if ov]
    nofig = [p for p, n, im, ov in rows if im == 0]
    total_img = sum(r[2] for r in rows)
    report = [
        pdf.name + ' · 全本逐页体检',
        '=' * 60,
        '总页数: %d' % doc.page_count,
        '嵌入图片总数: %d' % total_img,
        '无图页: %d 页 -> %s' % (len(nofig), nofig),
        '稀疏页(文字<90且无图): %s' % (sparse or '无'),
        '图片越界页: %s' % (overflow or '无'),
        '最少文字页 top10: %s' % sorted(rows, key=lambda r: r[1])[:10],
        '',
        '页号  文字数  图片数  越界',
    ]
    report += ['%4d %7d %6d %5d' % r for r in rows]
    (BUILD / 'tools' / 'audit_report.txt').write_text('\n'.join(report), encoding='utf-8')
    print('体检: 图片 %d, 稀疏页 %s, 越界页 %s' % (total_img, sparse or '无', overflow or '无'))

    # ---------- 2. 按章抽样渲染 ----------
    starts = {}
    pat = re.compile(r'C[ \t]*H[ \t]*A[ \t]*P[ \t]*T[ \t]*E[ \t]*R[ \t]*((?:[ \t]*\d)+)')
    for i in range(doc.page_count):
        for m in pat.finditer(doc[i].get_text()):
            n = int(re.sub(r'\s+', '', m.group(1)))
            starts.setdefault(n, i + 1)
    bounds = sorted(starts.items())
    picks = [1, 2]
    for k, (n, s) in enumerate(bounds):
        e = bounds[k + 1][1] - 1 if k + 1 < len(bounds) else doc.page_count
        picks += [s, s + min(3, (e - s) // 2), e]
    picks = sorted(set(p for p in picks if 1 <= p <= doc.page_count))
    for p in picks:
        doc[p - 1].get_pixmap(dpi=78).save(AUDIT / ('audit_p%03d.png' % p))
    print('抽样渲染 %d 页 -> thumbs/audit/' % len(picks))

    # ---------- 3. 书签与元数据 ----------
    headings = collect_headings()
    toc, missed = build_toc(doc, headings)
    doc.set_toc(toc)
    doc.set_metadata({
        'title': pdf.stem,
        'subject': '依据已核对课件整理的复习笔记',
        'keywords': '课件; 复习笔记',
        'creator': 'KaTeX + 无头 Edge 排版',
    })
    doc.saveIncr()
    print('书签写入: %d 条 (一级 %d / 二级 %d)' % (
        len(toc), sum(1 for t in toc if t[0] == 1), sum(1 for t in toc if t[0] == 2)))
    if missed:
        print('未定位标题 %d 条:' % len(missed), missed[:12])
    print('\n书签预览:')
    for lv, t, p in toc[:16]:
        print('  %s%s .... %s' % ('  ' * (lv - 1), t[:38], p))
    doc.close()


if __name__ == '__main__':
    main()
