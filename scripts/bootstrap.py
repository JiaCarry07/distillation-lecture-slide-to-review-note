#!/usr/bin/env python3
"""Copy the reusable note pipeline into a new working directory."""

import argparse
import pathlib
import shutil


def copy_if_absent(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        print(f"保留已有文件：{target}")
        return
    shutil.copy2(source, target)
    print(f"复制：{target}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("destination", help="新工程目录")
    ap.add_argument("--example", action="store_true", help="同时复制自编示例章节")
    args = ap.parse_args()
    root = pathlib.Path(__file__).resolve().parent.parent
    dest = pathlib.Path(args.destination).resolve()
    for name in ("src", "qa", "build/parts", "build/assets", "build/tools"):
        (dest / name).mkdir(parents=True, exist_ok=True)
    for source in (root / "scripts").glob("*.py"):
        copy_if_absent(source, dest / "build" / source.name)
    copy_if_absent(root / "assets" / "note.css", dest / "build/assets/note.css")
    copy_if_absent(root / "references" / "SPEC.md", dest / "build/tools/SPEC.md")
    copy_if_absent(root / "examples" / "cover.html", dest / "build/parts/cover.html")
    if args.example:
        copy_if_absent(root / "examples" / "ch01.html", dest / "build/parts/ch01.html")
    print(f"工程已准备：{dest}")


if __name__ == "__main__":
    main()
