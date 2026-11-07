#!/usr/bin/env python3
"""Print an assembled note to A4 PDF and add page numbers."""

import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import pymupdf

PAGE_W, PAGE_H = 594.96, 841.90
M_LR = 45.0  # Keep in sync with assets/note.css @page.

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_browser(override=None):
    if override:
        if pathlib.Path(override).is_file():
            return str(pathlib.Path(override).resolve())
        raise RuntimeError(f"指定的浏览器程序不存在：{override}")
    candidates = EDGE_CANDIDATES[:]
    candidates += [shutil.which(name) for name in ("msedge", "chrome", "chromium")]
    for candidate in candidates:
        if candidate and pathlib.Path(candidate).is_file():
            return str(pathlib.Path(candidate).resolve())
    raise RuntimeError("未找到 Edge/Chrome；可用 --browser 指定浏览器程序路径")


def check_local_assets(html):
    """Fail early if an assembled note references missing local KaTeX files."""
    source = html.read_text(encoding="utf-8")
    refs = re.findall(r"(?:src|href)=[\"']([^\"']+)[\"']", source)
    missing = []
    for ref in refs:
        if "package/dist/" not in ref:
            continue
        if not (html.parent / ref).resolve().is_file():
            missing.append(ref)
    if missing:
        raise RuntimeError("KaTeX 文件缺失：%s；先运行 ensure_katex.py" % ", ".join(missing))


def html_to_pdf(html, pdf, browser, timeout=600):
    profile = pdf.parent / "browser-profile"
    cmd = [browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
           "--no-first-run", "--disable-extensions", f"--user-data-dir={profile}",
           "--run-all-compositor-stages-before-draw", "--virtual-time-budget=20000",
           "--disable-lcd-text", f"--print-to-pdf={pdf}", html.as_uri()]
    result = subprocess.run(cmd, capture_output=True, timeout=timeout)
    if result.returncode != 0 or not pdf.is_file() or pdf.stat().st_size == 0:
        detail = (result.stderr or result.stdout or b"").decode("utf-8", errors="replace")[-2500:]
        raise RuntimeError(f"浏览器打印失败（退出码 {result.returncode}）：{detail}")


def stamp_footer(doc, skip_first=0, left_text="", page_number_position="right"):
    for i in range(skip_first, doc.page_count):
        page = doc[i]
        y = PAGE_H - 30
        body_number = i - skip_first + 1
        number = str(body_number)
        width = pymupdf.get_text_length(number, fontname="helv", fontsize=8.6)
        side = page_number_position
        if side == "outer":
            side = "right" if body_number % 2 else "left"
        x = {"left": M_LR, "center": (PAGE_W - width) / 2,
             "right": PAGE_W - M_LR - width}[side]
        if left_text:
            if side == "left":
                remaining = page.insert_textbox(
                    pymupdf.Rect(PAGE_W / 2, y - 9, PAGE_W - M_LR, y + 4),
                    left_text, fontname="china-s", fontsize=7.8,
                    color=(0.42, 0.47, 0.55), align=2)
                if remaining < 0:
                    raise RuntimeError("页脚说明过长，无法与左侧页码并排；请缩短 --footer-left")
            else:
                page.insert_text((M_LR, y), left_text, fontname="china-s",
                                 fontsize=7.8, color=(0.42, 0.47, 0.55))
        page.insert_text((x, y), number, fontname="helv",
                         fontsize=8.6, color=(0.30, 0.36, 0.45))


def validate_printed_pdf(doc):
    if doc.page_count == 0:
        raise RuntimeError("浏览器生成了空 PDF")
    for i, page in enumerate(doc):
        if abs(page.rect.width - PAGE_W) > 1 or abs(page.rect.height - PAGE_H) > 1:
            raise RuntimeError(f"第 {i + 1} 页不是 A4")
        text = page.get_text()
        if re.search(r"\$[^$\n]{1,240}\$", text):
            raise RuntimeError(f"第 {i + 1} 页仍有 $...$ 公式源码；检查 KaTeX 和 HTML 公式")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("pdf")
    ap.add_argument("--browser", help="Edge/Chrome 程序路径；默认自动查找")
    ap.add_argument("--footer-left", default="")
    ap.add_argument("--page-number-position", choices=("right", "left", "center", "outer"),
                    default="right", help="页码位置：右、左、居中或书籍外侧（奇右偶左）")
    ap.add_argument("--skip-first", type=int, default=0,
                    help="前 N 页不盖页脚；下一页从正文第 1 页开始编号")
    args = ap.parse_args()

    html = pathlib.Path(args.html).resolve()
    pdf = pathlib.Path(args.pdf).resolve()
    if not html.is_file():
        ap.error(f"HTML 不存在：{html}")
    if args.skip_first < 0:
        ap.error("--skip-first 不能为负数")
    pdf.parent.mkdir(parents=True, exist_ok=True)
    check_local_assets(html)
    browser = find_browser(args.browser)

    # Build in a private directory so a failed print never reuses an old PDF.
    with tempfile.TemporaryDirectory(prefix="note-render-", dir=pdf.parent) as scratch:
        scratch = pathlib.Path(scratch)
        printed = scratch / "printed.pdf"
        finished = scratch / "finished.pdf"
        html_to_pdf(html, printed, browser)
        with pymupdf.open(printed) as doc:
            validate_printed_pdf(doc)
            if args.skip_first > doc.page_count:
                raise RuntimeError("--skip-first 超过 PDF 总页数")
            stamp_footer(doc, args.skip_first, args.footer_left, args.page_number_position)
            count = doc.page_count
            doc.save(finished, garbage=3, deflate=True)
        os.replace(finished, pdf)
    print(f"完成：{pdf}（{count} 页）")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired, pymupdf.FileDataError) as exc:
        sys.exit(f"错误：{exc}")
