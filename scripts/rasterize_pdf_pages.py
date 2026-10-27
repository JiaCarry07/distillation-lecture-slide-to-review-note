#!/usr/bin/env python3
"""Render selected PDF pages for visual reading when their text layer is broken."""

import argparse
import pathlib
import re
import sys

import pymupdf


def parse_pages(spec, count):
    if not spec:
        return list(range(1, count + 1))
    selected = set()
    for token in spec.split(","):
        token = token.strip()
        if not re.fullmatch(r"\d+(?:-\d+)?", token):
            raise ValueError(f"无效页码范围：{token!r}")
        bounds = [int(value) for value in token.split("-")]
        start, end = (bounds[0], bounds[0]) if len(bounds) == 1 else bounds
        if start < 1 or end > count or start > end:
            raise ValueError(f"页码超出 1–{count} 或范围倒置：{token}")
        selected.update(range(start, end + 1))
    return sorted(selected)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("output_dir")
    ap.add_argument("--pages", help="例如 1,3-5；省略则输出全部页")
    ap.add_argument("--dpi", type=int, default=150)
    args = ap.parse_args()
    if not 72 <= args.dpi <= 300:
        ap.error("--dpi 应在 72–300 之间")
    source = pathlib.Path(args.pdf)
    output = pathlib.Path(args.output_dir)
    if not source.is_file():
        ap.error(f"PDF 不存在：{source}")
    output.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(source) as doc:
        pages = parse_pages(args.pages, doc.page_count)
        for number in pages:
            target = output / f"page-{number:04d}.png"
            doc[number - 1].get_pixmap(dpi=args.dpi).save(target)
            print(target)
    print(f"已渲染 {len(pages)} 页；请逐页核对并整理内容，脚本不执行 OCR。")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, pymupdf.FileDataError) as exc:
        sys.exit(f"错误：{exc}")
