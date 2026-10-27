#!/usr/bin/env python3
"""Download and extract the KaTeX distribution into a working directory.

Idempotent: exits immediately when the target already contains
package/dist/katex.min.css, katex.min.js and contrib/auto-render.min.js.

Usage:
    python ensure_katex.py <work_dir> [--version 0.16.11]

After it finishes, an HTML file placed in <work_dir> can reference the assets as:
    <link rel="stylesheet" href="package/dist/katex.min.css">
    <script src="package/dist/katex.min.js"></script>
    <script src="package/dist/contrib/auto-render.min.js"></script>
"""

import argparse
import base64
import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import sys
import tarfile
import urllib.request

DEFAULT_VERSION = "0.16.11"
MIRRORS = (
    "https://registry.npmmirror.com/katex/-/katex-{v}.tgz",
    "https://registry.npmjs.org/katex/-/katex-{v}.tgz",
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dest", help="working directory that will hold package/dist/")
    ap.add_argument("--version", default=DEFAULT_VERSION)
    args = ap.parse_args()
    if not re.fullmatch(r"\d+\.\d+\.\d+", args.version):
        ap.error("--version 应为固定的 x.y.z 版本号")

    dist = os.path.join(args.dest, "package", "dist")
    needed = (
        "katex.min.css",
        "katex.min.js",
        os.path.join("contrib", "auto-render.min.js"),
    )
    if all(os.path.exists(os.path.join(dist, n)) for n in needed):
        print("KaTeX already present: %s" % dist)
        return 0

    os.makedirs(args.dest, exist_ok=True)
    metadata_url = "https://registry.npmjs.org/katex/" + args.version
    try:
        with urllib.request.urlopen(metadata_url, timeout=30) as resp:
            metadata = json.load(resp)
        algorithm, encoded = metadata["dist"]["integrity"].split("-", 1)
        if algorithm != "sha512":
            raise ValueError("npm 元数据没有 SHA-512 完整性值")
        expected_digest = base64.b64decode(encoded, validate=True)
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: 无法取得 KaTeX 完整性信息：{exc}", file=sys.stderr)
        return 1

    blob = None
    for mirror in MIRRORS:
        url = mirror.format(v=args.version)
        try:
            print("downloading %s" % url)
            with urllib.request.urlopen(url, timeout=180) as resp:
                blob = resp.read(25 * 1024 * 1024 + 1)
            if len(blob) > 25 * 1024 * 1024:
                raise ValueError("KaTeX 压缩包超过 25 MiB 限额")
            if hashlib.sha512(blob).digest() != expected_digest:
                raise ValueError("下载内容与 npm SHA-512 完整性值不符")
            break
        except Exception as exc:  # noqa: BLE001 - report and try the next mirror
            blob = None
            print("mirror failed (%s): %s" % (url, exc), file=sys.stderr)

    if blob is None:
        print("ERROR: could not download KaTeX from any mirror", file=sys.stderr)
        return 1

    # Extract only regular files under package/dist; never follow archive links.
    root = pathlib.Path(args.dest).resolve()
    dist_root = (root / "package" / "dist").resolve()
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
        members = [m for m in tf if m.isfile() and m.name.startswith("package/dist/")]
        for member in members:
            target = (root / member.name).resolve()
            if dist_root not in target.parents:
                raise ValueError(f"压缩包路径越界：{member.name}")
        for member in members:
            target = (root / member.name).resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            source = tf.extractfile(member)
            if source is None:
                raise ValueError(f"无法读取压缩包成员：{member.name}")
            with source, target.open("wb") as output:
                shutil.copyfileobj(source, output)

    missing = [n for n in needed if not os.path.exists(os.path.join(dist, n))]
    if missing:
        print("ERROR: archive incomplete, missing %s" % missing, file=sys.stderr)
        return 1

    print("KaTeX ready: %s" % dist)
    return 0


if __name__ == "__main__":
    sys.exit(main())
