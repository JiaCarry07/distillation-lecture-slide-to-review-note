#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""导航增强：三级书签（章/节/小标题）+ 目录可点击跳转 + 按章拆分单册 PDF。

用法：python tools/enhance_navigation.py <final.pdf> [--split-dir <新目录>]
更新书签和目录链接；分章文件若已存在则停止。
"""
import argparse
import html
import pathlib
import re

import pymupdf
from project_parts import chapter_sources

BUILD = pathlib.Path(__file__).resolve().parents[1]
ROOT = BUILD.parent.parent
PARTS = BUILD / 'parts'


def plain(frag: str) -> str:
    s = re.sub(r'<[^>]+>', '', frag)
    s = html.unescape(s)
    return re.sub(r'\s+', '', s)


def clean(t: str) -> str:
    t = re.sub(r'（[^）]*(?:课件|f\d\d\s*p)[^）]*）', '', t)
    t = re.sub(r'\([^)]*(?:课件|f\d\d\s*p)[^)]*\)', '', t)
    return t.strip() or t


def norm(s: str) -> str:
    return re.sub(r'[\s\u3000▍]+', '', s)


def headings():
    """(level, 标题原文, 显示名, 章号) —— 按文档顺序。"""
    out = [[1, '封面', '封面', None], [1, '目录', '目录', None]]
    for n, f, title in chapter_sources(PARTS):
        s = f.read_text(encoding='utf-8')
        m = re.search(r'<h1 class="chap"[^>]*>(.*?)</h1>', s, re.S)
        if m:
            t = re.sub(r'^CHAPTER\d+', '', plain(m.group(1)))
            if t:
                title = t
        out.append([1, plain(m.group(1)) if m else title,
                    title if n == 0 else '第 %d 章　%s' % (n, title), n])
        # 按出现顺序收集 h2 / h3
        for mt in re.finditer(r'<(h2|h3)\s+class="(sub|mini)"[^>]*>(.*?)</\1>', s, re.S):
            t = plain(mt.group(3))
            if not t:
                continue
            lv = 2 if mt.group(1) == 'h2' else 3
            out.append([lv, t, clean(t), n])
    return out


def locate(doc, hs):
    """顺序定位每个标题所在页；返回 toc 与未命中清单。"""
    pn = [norm(doc[i].get_text()) for i in range(doc.page_count)]
    chapter_pages = chapter_starts(doc)
    toc, missed, cursor = [], [], 0
    for lv, raw, label, ch in hs:
        if label == '封面':
            toc.append([1, label, 1]); cursor = 1; continue
        if label == '目录':
            toc.append([1, label, 2]); cursor = 2; continue
        if lv == 1 and ch is not None:
            found = chapter_pages.get(ch)
            if found:
                toc.append([lv, label, found])
                cursor = found - 1
            else:
                missed.append((lv, label[:34]))
            continue
        key = norm(raw)
        found = None
        # 标题里含 $…$ 时，KaTeX 字形不进文本层，补一个「去掉公式」的候选
        cands = [key, key[:12], key[:7]]
        if '$' in key:
            cands.insert(1, re.sub(r'\$[^$]*\$', '', key))
            cands.insert(2, key.split('$')[0])
        # 完整 → 前 12 字 → 前 7 字；逐级放宽但始终从 cursor 往后找
        for k in dict.fromkeys(cands):
            if not k:
                continue
            for i in range(cursor, doc.page_count):
                if k in pn[i]:
                    found = i + 1
                    break
            if found:
                break
        if not found and lv == 1 and ch is not None:
            pat = re.compile(r'C\s*H\s*A\s*P\s*T\s*E\s*R\s*%d' % ch)
            for i in range(cursor, doc.page_count):
                if pat.search(doc[i].get_text()):
                    found = i + 1
                    break
        if found:
            toc.append([lv, label, found])
            cursor = max(cursor, found - 1)
        else:
            missed.append((lv, label[:34]))
    return toc, missed


def chapter_starts(doc):
    pat = re.compile(r'C[ \t]*H[ \t]*A[ \t]*P[ \t]*T[ \t]*E[ \t]*R[ \t]*((?:[ \t]*\d)+)')
    st = {}
    for i in range(doc.page_count):
        for m in pat.finditer(doc[i].get_text()):
            n = int(re.sub(r'\s+', '', m.group(1)))
            st.setdefault(n, i + 1)
    return dict(sorted(st.items()))


def add_toc_links(doc, starts):
    """目录页里每个章名做成可点击跳转，保留已有链接。"""
    if doc.page_count < 2:
        return 0
    page = doc[1]
    occupied = [pymupdf.Rect(old['from']) for old in page.get_links() if old.get('from')]
    n = 0
    for ch, p in starts.items():
        label = '绪论' if ch == 0 else '第 %d 章' % ch
        for r in page.search_for(label):
            if any(r.intersects(old) for old in occupied):
                continue
            page.insert_link({
                'kind': pymupdf.LINK_GOTO,
                'from': r,
                'page': p - 1,
                'to': pymupdf.Point(0, 0),
            })
            n += 1
            occupied.append(r)
    return n


def split_chapters(doc, toc, starts, split, names, pdf):
    split.mkdir(parents=True, exist_ok=True)
    bounds = list(starts.items())
    made = []
    for k, (ch, s) in enumerate(bounds):
        e = bounds[k + 1][1] - 1 if k + 1 < len(bounds) else doc.page_count
        sub = pymupdf.open()
        sub.insert_pdf(doc, from_page=s - 1, to_page=e - 1)
        sub_toc = [[lv, t, p - s + 1] for lv, t, p in toc if s <= p <= e]
        if sub_toc:
            sub.set_toc(sub_toc)
        sub.set_metadata({
            'title': '%s · 复习笔记（单章版）' % names.get(ch, str(ch)),
            'subject': '摘自《%s》第 %d–%d 页' % (pdf.name, s, e),
        })
        name = '%02d.pdf' % ch
        out = split / name
        if out.exists():
            raise FileExistsError(f'分章文件已存在：{out}；请选择新的输出目录')
        sub.save(out, garbage=3, deflate=True)
        sub.close()
        made.append((name, e - s + 1, len(sub_toc), out.stat().st_size / 1024 / 1024))
    return made


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=pathlib.Path)
    parser.add_argument('--split-dir', type=pathlib.Path, help='可选：输出单章 PDF 的新目录')
    args = parser.parse_args()
    pdf = args.pdf.resolve()
    doc = pymupdf.open(pdf)
    print('主 PDF:', doc.page_count, '页', flush=True)

    hs = headings()
    print('标题总数: %d（一级 %d / 二级 %d / 三级 %d）' % (
        len(hs), sum(1 for x in hs if x[0] == 1),
        sum(1 for x in hs if x[0] == 2), sum(1 for x in hs if x[0] == 3)), flush=True)

    toc, missed = locate(doc, hs)
    doc.set_toc(toc)
    starts = chapter_starts(doc)
    nlink = add_toc_links(doc, starts)
    doc.saveIncr()
    print('三级书签 %d 条 | 目录链接 %d 个 | 未定位 %d 条' % (len(toc), nlink, len(missed)))
    if missed:
        print('  未定位样例:', missed[:10])

    made = []
    if args.split_dir:
        names = {n: title for n, _, title in chapter_sources(PARTS)}
        made = split_chapters(doc, toc, starts, args.split_dir.resolve(), names, pdf)
    doc.close()
    if made:
        print('\n单章打印版 ->', args.split_dir.resolve())
    for name, pages, ntoc, mb in made:
        print('  %-28s %3d 页  %3d 书签  %5.1f MB' % (name, pages, ntoc, mb))
    print('  合计 %d 页' % sum(m[1] for m in made))


if __name__ == '__main__':
    main()
