#!/usr/bin/env python3
"""Assemble chapters, stabilize the table of contents, and render the final PDF."""

import argparse
import html
import os
import pathlib
import re
import subprocess
import sys

import pymupdf

ROOT = pathlib.Path(__file__).resolve().parent.parent
PARTS = ROOT / "build" / "parts"
COVER = PARTS / "cover.html"
BUILD = ROOT / "build"
PY = sys.executable
CHAPTER_RE = re.compile(r"C\s*H\s*A\s*P\s*T\s*E\s*R\s*((?:\s*\d)+)")


def discover_chapters():
    chapters = []
    for path in PARTS.glob("ch*.html"):
        match = re.fullmatch(r"ch(\d+)", path.stem)
        if not match:
            continue
        number = int(match.group(1))
        source = path.read_text(encoding="utf-8")
        heading = re.search(
            r'<h1 class="chap">\s*<span class="cn">CHAPTER\s+(\d+)</span>(.*?)</h1>',
            source, re.IGNORECASE | re.DOTALL,
        )
        if not heading or int(heading.group(1)) != number:
            raise RuntimeError(f"{path.name} 的 CHAPTER 章号与文件名不一致")
        title = html.unescape(re.sub(r"<[^>]+>", "", heading.group(2))).strip()
        if not title:
            raise RuntimeError(f"{path.name} 缺少章节标题")
        chapters.append((number, title, path))
    chapters.sort(key=lambda item: item[0])
    if not chapters or len({item[0] for item in chapters}) != len(chapters):
        raise RuntimeError("需要至少一份且章号唯一的 build/parts/chNN.html")
    if not COVER.is_file():
        raise RuntimeError("缺少 build/parts/cover.html；先复制 examples/cover.html")
    return chapters


def replace_text(source, attribute, value):
    pattern = re.compile(r'(<[^>]+\b' + attribute + r'[^>]*>)[^<]*(</[^>]+>)')
    result, count = pattern.subn(lambda m: m.group(1) + html.escape(str(value)) + m.group(2), source)
    if count != 1:
        raise RuntimeError(f"封面锚点 {attribute} 命中 {count} 处，应为 1")
    return result


def patch_cover(chapters, pages, total, title):
    source = COVER.read_text(encoding="utf-8")
    source = replace_text(source, r'data-title="[^"]*"', title)
    source = replace_text(source, r'data-pg="total"', total)
    figures = sum(p.read_text(encoding="utf-8").count("<figure") for _, _, p in chapters)
    examples = sum(p.read_text(encoding="utf-8").count('class="ex"') for _, _, p in chapters)
    chips = f"{len(chapters)} 章　{figures} 幅插图　{examples} 道例题　A4 横线纸"
    source = replace_text(source, r'data-pg="chips"', chips)
    rows = []
    for number, name, _ in chapters:
        rows.append(
            f'<tr><td>第 {number} 章</td><td>{html.escape(name)}</td>'
            f'<td data-pg="{number}">{pages.get(number, 0)}</td></tr>'
        )
    pattern = re.compile(r'(<tbody data-toc>).*?(</tbody>)', re.DOTALL)
    source, count = pattern.subn(lambda m: m.group(1) + "\n" + "\n".join(rows) + "\n" + m.group(2), source)
    if count != 1:
        raise RuntimeError(f"封面目录锚点 data-toc 命中 {count} 处，应为 1")
    COVER.write_text(source, encoding="utf-8")


def run(*args):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run([PY, *map(str, args)], cwd=ROOT, capture_output=True, env=env)
    if result.returncode:
        stdout = result.stdout.decode("utf-8", errors="replace")[-1500:]
        stderr = result.stderr.decode("utf-8", errors="replace")[-2500:]
        raise RuntimeError(f"命令失败：{' '.join(map(str, args))}\n{stdout}\n{stderr}")
    return result.stdout.decode("utf-8", errors="replace")


def build(pdf, skip_first, footer_left, browser=None, preview=False):
    run("build/assemble.py", "--out", "note_full.html")
    command = ["build/render.py", "build/note_full.html", pdf,
               "--skip-first", skip_first, "--footer-left", footer_left]
    if browser:
        command.extend(["--browser", browser])
    if preview:
        command.append("--no-rules")
    run(*command)


def extract_pages(pdf, chapters):
    wanted = {number for number, _, _ in chapters}
    pages = {}
    with pymupdf.open(pdf) as doc:
        total = doc.page_count
        for i, page in enumerate(doc):
            match = CHAPTER_RE.search(page.get_text())
            if match:
                number = int(re.sub(r"\s+", "", match.group(1)))
                if number in wanted and number not in pages:
                    pages[number] = i + 1
    missing = wanted - pages.keys()
    if missing:
        raise RuntimeError(f"未在 PDF 中找到章标题：{sorted(missing)}")
    return pages, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="课程复习笔记", help="封面标题")
    ap.add_argument("--out", default="复习笔记_A4横线纸.pdf", help="最终 PDF 路径")
    ap.add_argument("--footer-left", default="复习笔记", help="正文页左侧页脚")
    ap.add_argument("--browser", help="Edge/Chrome 程序路径")
    ap.add_argument("--max-passes", type=int, default=5)
    args = ap.parse_args()
    if args.max_passes < 2:
        ap.error("--max-passes 至少为 2")
    chapters = discover_chapters()
    BUILD.mkdir(parents=True, exist_ok=True)
    preview = BUILD / "_pass.pdf"
    candidate = BUILD / "_final.pdf"
    output = pathlib.Path(args.out)
    if not output.is_absolute():
        output = ROOT / output
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    patch_cover(chapters, {}, 0, args.title)
    previous = None
    try:
        for attempt in range(1, args.max_passes + 1):
            print(f"第 {attempt} 轮：渲染并核对目录页码", flush=True)
            build(preview, 0, "", args.browser, preview=True)
            current = extract_pages(preview, chapters)
            patch_cover(chapters, *current, args.title)
            if current == previous:
                break
            previous = current
        else:
            raise RuntimeError("目录页码未在限定轮数内稳定，未生成最终 PDF")

        pages, _ = current
        skip_first = min(pages.values()) - 1
        build(candidate, skip_first, args.footer_left, args.browser)
        if extract_pages(candidate, chapters) != current:
            raise RuntimeError("最终 PDF 的章首页与目录不一致，未替换目标文件")
        os.replace(candidate, output)
        print(f"完成：{output}（{current[1]} 页，前 {skip_first} 页无横线）")
    finally:
        preview.unlink(missing_ok=True)
        candidate.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, pymupdf.FileDataError) as exc:
        sys.exit(f"错误：{exc}")
