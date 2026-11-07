#!/usr/bin/env python3
"""Load the project-specific PPTX source-to-chapter mapping."""

import json
from pathlib import Path


def load_chapter_map(path: Path):
    if not path.is_file():
        raise RuntimeError(
            f"缺少 {path}；先按 README 的格式核对课件并建立章节映射"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    chapters = data.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        raise ValueError("chapter_map.json 需要非空 chapters 列表")
    mapping, titles = {}, {}
    for chapter in chapters:
        number = chapter.get("number")
        title = chapter.get("title")
        sources = chapter.get("sources")
        if not isinstance(number, int) or number < 0 or number in mapping:
            raise ValueError(f"章号无效或重复：{number!r}")
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"第 {number} 章缺少标题")
        if not isinstance(sources, list) or not sources:
            raise ValueError(f"第 {number} 章缺少 sources")
        entries = []
        for source in sources:
            fid = source.get("id")
            desc = source.get("description", "")
            pages = source.get("pages")
            if not isinstance(fid, str) or not fid.startswith("f") or not fid[1:].isdigit():
                raise ValueError(f"第 {number} 章的课件 id 无效：{fid!r}")
            if pages is not None and (
                not isinstance(pages, list) or len(pages) != 2
                or not all(isinstance(v, int) and v > 0 for v in pages)
                or pages[0] > pages[1]
            ):
                raise ValueError(f"第 {number} 章的页范围无效：{pages!r}")
            entries.append((fid, str(desc), tuple(pages) if pages else None))
        mapping[number] = entries
        titles[number] = title.strip()
    return mapping, titles
