#!/usr/bin/env python3
"""Discover chapter HTML files and their reader-facing titles."""

import html
from pathlib import Path
import re


CH_FILE = re.compile(r"ch(\d+)\.html$", re.IGNORECASE)
CH_HEAD = re.compile(
    r'<h1\s+class="chap"[^>]*>\s*<span\s+class="cn">\s*CHAPTER\s+(\d+)\s*</span>(.*?)</h1>',
    re.IGNORECASE | re.DOTALL,
)


def chapter_sources(parts: Path):
    result = []
    for path in parts.glob("ch*.html"):
        match = CH_FILE.fullmatch(path.name)
        if not match:
            continue
        number = int(match.group(1))
        source = path.read_text(encoding="utf-8")
        head = CH_HEAD.search(source)
        if not head or int(head.group(1)) != number:
            raise ValueError(f"{path.name} 的 CHAPTER 章号与文件名不一致")
        title = html.unescape(re.sub(r"<[^>]+>", "", head.group(2))).strip()
        if not title:
            raise ValueError(f"{path.name} 缺少章节标题")
        result.append((number, path, title))
    result.sort(key=lambda row: row[0])
    if not result:
        raise ValueError(f"{parts} 下没有 chNN.html")
    return result
