#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""抽取课件 PDF 的全文文本，按页插入 <<<PAGE n>>> 标记，便于逐页阅读与还原散落公式。

用法：
  python extract_pdf_text.py "<课件.pdf>" "<工作目录>/src/<章名>.txt"

文字层快检只提供线索。命中 0 次时应抽样比对原 PDF，不能单凭该值
断定文字层损坏；必要时用 rasterize_pdf_pages.py 读图。
"""
import pathlib, sys
import pymupdf


def main():
    if len(sys.argv) != 3:
        sys.exit('用法: extract_pdf_text.py <课件.pdf> <输出.txt>')
    src = pathlib.Path(sys.argv[1])
    out = pathlib.Path(sys.argv[2])
    out.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() != '.pdf':
        sys.exit('输入应为 PDF')
    if not src.is_file():
        sys.exit(f'文件不存在：{src}')

    parts = []
    with pymupdf.open(src) as d:
        page_count = d.page_count
        for i in range(page_count):
            parts.append('\n<<<PAGE %d>>>\n' % (i + 1))
            parts.append(d[i].get_text())
    out.write_text(''.join(parts), encoding='utf-8')

    # 文字层可用性快检
    txt = ''.join(parts)
    probe = '的一是在有为与函数复数点线面积分电路电压电流电阻功率'
    hit = sum(txt.count(c) for c in probe)
    print('已写出 %s（%d 页，%d 字符）' % (out, page_count, len(txt)))
    print('文字层快检：高频中文字命中 %d 次（0 时请与原 PDF 抽样比对）' % hit)


if __name__ == '__main__':
    main()
