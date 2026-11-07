#!/usr/bin/env python3
"""Create an editable note project without overwriting existing work."""

import argparse
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent.parent
CORE = {"assemble.py", "render.py", "finalize.py"}


def copy_new(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        print(f"保留已有文件：{target}")
    else:
        shutil.copy2(source, target)
        print(f"复制：{target}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", help="工程目录；源课件和最终 PDF 放这里")
    parser.add_argument("--example", action="store_true", help="添加可独立渲染的示例章节")
    args = parser.parse_args()
    project = Path(args.destination).resolve()
    stage = project / ".courseware-note-studio"
    build = stage / "build"
    for name in ("parts", "assets/figs", "src", "pdf", "thumbs", "tools", "references"):
        (build / name).mkdir(parents=True, exist_ok=True)
    for source in sorted((ROOT / "scripts").glob("*.py")):
        if source.name == "bootstrap.py":
            continue
        target = build / source.name if source.name in CORE else build / "tools" / source.name
        copy_new(source, target)
    copy_new(ROOT / "assets" / "note.css", build / "assets" / "note.css")
    for source in sorted((ROOT / "references").glob("*.md")):
        copy_new(source, build / "references" / source.name)
    copy_new(ROOT / "examples" / "cover.html", build / "parts" / "cover.html")
    if args.example:
        for example in sorted((ROOT / "examples").glob("ch[0-9]*.html")):
            copy_new(example, build / "parts" / example.name)
    print(f"工程已准备：{project}")


if __name__ == "__main__":
    main()
