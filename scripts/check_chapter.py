#!/usr/bin/env python3
"""Check common chapter-fragment mistakes before browser rendering."""

import argparse
import pathlib
import re
import sys


def inspect(source, expected_number=None):
    errors = []
    heading = re.search(
        r'<h1 class="chap">\s*<span class="cn">CHAPTER\s+(\d+)</span>', source,
        re.IGNORECASE,
    )
    if not heading:
        errors.append("缺少标准的 CHAPTER N 章标题")
    elif expected_number is not None and int(heading.group(1)) != expected_number:
        errors.append("章标题数字与文件名不一致")
    if re.search(r"<(?:html|head|body|style)\b", source, re.IGNORECASE):
        errors.append("章节只能是 HTML 内容片段，不能包含 html/head/body/style 标签")
    if source.count("$") % 2:
        errors.append("$ 定界符数量为奇数")
    for match in re.finditer(r"(?<!\$)\$(?!\$)([^$\n]+)(?<!\$)\$(?!\$)", source):
        formula = match.group(1)
        if re.search(r"\\(?:d?frac|begin|int|sum)\b", formula):
            errors.append("行内公式含会撑高行盒的命令：" + formula[:60])
        if "<" in formula or ">" in formula:
            errors.append("公式内的 < 或 > 未转义：" + formula[:60])
    figures = len(re.findall(r"<figure\b", source))
    captions = re.findall(r"<figcaption>\s*图\s+(\d+-\d+)", source)
    if figures != len(captions):
        errors.append(f"figure 有 {figures} 个，带图号的 figcaption 有 {len(captions)} 个")
    if len(captions) != len(set(captions)):
        errors.append("图号重复")
    ids = re.findall(r'\bid="([^"]+)"', source)
    if len(ids) != len(set(ids)):
        errors.append("HTML/SVG id 重复")
    return errors, figures, len(re.findall(r'class="ex"', source))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chapter", type=pathlib.Path)
    args = ap.parse_args()
    if not args.chapter.is_file():
        ap.error(f"文件不存在：{args.chapter}")
    number_match = re.fullmatch(r"ch(\d+)", args.chapter.stem)
    number = int(number_match.group(1)) if number_match else None
    source = args.chapter.read_text(encoding="utf-8")
    errors, figures, examples = inspect(source, number)
    print(f"{args.chapter}: {len(source)} 字符，{figures} 幅图，{examples} 道例题")
    if errors:
        for error in errors:
            print("错误：" + error, file=sys.stderr)
        return 1
    print("章节结构检查通过；仍需核对内容与最终 PDF 视觉效果。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
