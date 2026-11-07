#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""给正文里的「图 N-M」引用加 PDF 内部跳转，点击直达对应图注。

要点：
  - 不能用 page.search_for("图 2-5")：那是子串匹配，会误命中「图 2-50/2-51…」。
    改用 rawdict 逐字符 bbox + 正则 `(?!\\d)` 精确边界。
  - 图注字号 8.8pt、正文 11pt，用字号区分两者。
  - 保留已有链接；已有链接占用引用位置时跳过。
运行顺序：finalize.py → postprocess_pdf.py → enhance_navigation.py → link_figures.py
"""
import argparse
import pathlib
import re
import sys

import pymupdf

BUILD = pathlib.Path(__file__).resolve().parents[1]
ROOT = BUILD.parent.parent
REF = re.compile(r'图\s*(\d+-\d+)(?!\d)')
CAP_SIZE_MAX = 9.3          # 图注 8.8pt；表格 9.8pt、正文 11pt


def scan(doc):
    caps, refs = {}, []
    for i in range(doc.page_count):
        for b in doc[i].get_text('rawdict')['blocks']:
            for line in b.get('lines', []):
                for sp in line['spans']:
                    chars = sp.get('chars', [])
                    if not chars:
                        continue
                    text = ''.join(c['c'] for c in chars)
                    size = sp.get('size', 11.0)
                    for m in REF.finditer(text):
                        r = pymupdf.Rect(chars[m.start()]['bbox'])
                        for k in range(m.start() + 1, m.end()):
                            r |= pymupdf.Rect(chars[k]['bbox'])
                        key = m.group(1)
                        if size <= CAP_SIZE_MAX:
                            caps.setdefault(key, (i + 1, r.y0))
                        else:
                            refs.append((key, i + 1, r))
    return caps, refs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=pathlib.Path)
    args = parser.parse_args()
    doc = pymupdf.open(args.pdf.resolve())
    caps, refs = scan(doc)
    print('图注 %d 个 | 正文引用 %d 处' % (len(caps), len(refs)), flush=True)

    # Preserve existing links. Repeated runs skip occupied reference rectangles.
    existing = {i: [pymupdf.Rect(link['from']) for link in doc[i].get_links()
                    if link.get('from')] for i in range(doc.page_count)}

    added = skipped_same = missing = 0
    for key, page_no, rect in refs:
        target = caps.get(key)
        if not target:
            missing += 1
            continue
        if any(rect.intersects(old) for old in existing[page_no - 1]):
            continue
        tp, ty = target
        doc[page_no - 1].insert_link({
            'kind': pymupdf.LINK_GOTO,
            'from': rect,
            'page': tp - 1,
            'to': pymupdf.Point(0, max(0, ty - 28)),
        })
        added += 1
        existing[page_no - 1].append(rect)
        if tp == page_no:
            skipped_same += 1
    doc.saveIncr()
    print('插入跳转 %d 个（其中同页 %d）| 无对应图注 %d 处' % (
        added, skipped_same, missing), flush=True)
    print('总链接数 %d' % sum(len(doc[i].get_links()) for i in range(doc.page_count)))
    doc.close()


if __name__ == '__main__':
    main()
