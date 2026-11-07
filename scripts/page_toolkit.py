#!/usr/bin/env python3
"""Toolkit for reading slide-deck PDFs whose text layer is unusable.

Some CJK decks (typically dvipdfmx / LaTeX + KaiTi subsets) embed fonts with a
broken or missing ToUnicode CMap: `page.get_text()` returns glyph indices dressed
up as Latin-1, so all Chinese comes out as mojibake that no encode/decode
round-trip can recover. PDFium gives the same garbage, so switching engines does
not help.

The workaround is to stop reading text and start reading pixels: render pages and
look at them. This module provides the four tricks that make that practical.

    keys    cluster consecutive near-identical pages ("progressive build" slides)
            and emit the LAST page of each run — the one carrying all the content.
            On a real 579-page corpus this cut the reading load by 41%.
    sheets  tile selected pages into 2x3 contact sheets. 140 dpi is still fully
            legible for slides, so six pages cost one Read call.
    bands   crop the title band off every page and stack them into a single
            "outline map" image. One glance gives the whole section structure.
    zoom    render chosen pages large, cropped to the text bounding box. Use this
            to confirm example statements before transcribing a formula.
    check   post-export audit: leftover LaTeX source, stray '$', KaTeX error
            markers, and near-blank pages.

Usage:
    python page_toolkit.py keys   <pdf> [--thr 3.0] [--json out.json]
    python page_toolkit.py sheets <pdf> <outdir> <prefix> [--keys 1,2,3] [--dpi 140]
    python page_toolkit.py bands  <pdf> <out.png> [--cols 3]
    python page_toolkit.py zoom   <pdf> <out.png> <page> [<page> ...] [--dpi 400]
    python page_toolkit.py check  <pdf>

Requires: pymupdf, Pillow, numpy
"""

import argparse
import io
import json
import math
import os
import re
import sys

try:
    import pymupdf
    from PIL import Image, ImageDraw
    import numpy as np
except ImportError as exc:  # noqa: BLE001
    sys.exit("ERROR: needs pymupdf, Pillow and numpy (%s)" % exc)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _pil(page, dpi, gray=False):
    pm = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY if gray else pymupdf.csRGB)
    return Image.open(io.BytesIO(pm.tobytes("png")))


def _grid(items, cols, out, label_prefix="p", pad=6, caption_h=16):
    """Tile (label, PIL image) pairs into a grid and save."""
    if not items:
        raise SystemExit("ERROR: nothing to render")
    w = max(im.width for _, im in items)
    h = max(im.height for _, im in items)
    rows = math.ceil(len(items) / cols)
    canvas = Image.new(
        "RGB", (w * cols + pad * (cols + 1), (h + caption_h) * rows + pad), (225, 225, 225)
    )
    draw = ImageDraw.Draw(canvas)
    for k, (label, im) in enumerate(items):
        r, c = divmod(k, cols)
        x = pad + c * (w + pad)
        y = pad + r * (h + caption_h)
        draw.text((x + 3, y + 3), "%s%s" % (label_prefix, label), fill=(190, 0, 0))
        canvas.paste(im, (x, y + caption_h))
    canvas.save(out)
    return canvas.size


def _content_bbox(page, top=26.0, bottom=238.0):
    """Vertical extent of the real content, skipping a running header/footer.

    Coordinates are in PDF points. Defaults suit a 4:3 slide; scale the two
    cut-offs to the page height if the deck differs.
    """
    ymin, ymax = 1e9, 0.0
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            y0, y1 = line["bbox"][1], line["bbox"][3]
            if y0 < top or y0 > bottom:
                continue
            ymin = min(ymin, y0)
            ymax = max(ymax, y1)
    if ymin > ymax:
        return None
    return max(top, ymin - 8), min(bottom, ymax + 8)


# --------------------------------------------------------------------------- #
# subcommands
# --------------------------------------------------------------------------- #

def cmd_keys(args):
    doc = pymupdf.open(args.pdf)
    sigs = []
    for page in doc:
        sigs.append(np.asarray(_pil(page, 45, gray=True).resize((48, 48)), dtype=np.float32))

    groups, cur = [], [0]
    for i in range(1, len(sigs)):
        diff = float(np.abs(sigs[i] - sigs[i - 1]).mean())
        if diff > args.thr:
            groups.append(cur)
            cur = [i]
        else:
            cur.append(i)
    groups.append(cur)

    keys = [g[-1] + 1 for g in groups]
    payload = {"pages": doc.page_count, "groups": len(groups), "keys": keys}
    print(
        "%s: %d pages -> %d groups, %d key pages (threshold %.1f)"
        % (os.path.basename(args.pdf), doc.page_count, len(groups), len(keys), args.thr)
    )
    if args.json:
        old = {}
        if os.path.exists(args.json):
            with open(args.json, encoding="utf-8") as fh:
                old = json.load(fh)
        old[os.path.basename(args.pdf)] = payload
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(old, fh, ensure_ascii=False, indent=1)
        print("-> %s" % args.json)


def cmd_sheets(args):
    doc = pymupdf.open(args.pdf)
    if args.keys:
        keys = [int(x) for x in args.keys.split(",") if x.strip()]
    else:
        # recompute on the fly
        ns = argparse.Namespace(pdf=args.pdf, thr=args.thr, json=None)
        sigs = [np.asarray(_pil(p, 45, gray=True).resize((48, 48)), dtype=np.float32) for p in doc]
        groups, cur = [], [0]
        for i in range(1, len(sigs)):
            if float(np.abs(sigs[i] - sigs[i - 1]).mean()) > args.thr:
                groups.append(cur)
                cur = [i]
            else:
                cur.append(i)
        groups.append(cur)
        keys = [g[-1] + 1 for g in groups]

    os.makedirs(args.outdir, exist_ok=True)
    per = args.cols * args.rows
    made = []
    for start in range(0, len(keys), per):
        chunk = keys[start:start + per]
        items = [(str(k), _pil(doc[k - 1], args.dpi)) for k in chunk]
        out = os.path.join(args.outdir, "%s_%02d.png" % (args.prefix, start // per + 1))
        size = _grid(items, args.cols, out)
        made.append((out, chunk, size))
        print("%s -> %s" % (out, chunk))
    print("total %d key pages in %d sheets" % (len(keys), len(made)))


def cmd_bands(args):
    doc = pymupdf.open(args.pdf)
    items = []
    for i, page in enumerate(doc):
        im = _pil(page, 110)
        band = im.crop((0, 0, im.width, int(im.height * 0.13)))
        items.append((str(i + 1), band))
    size = _grid(items, args.cols, args.out, caption_h=0)
    print("%s  %s  (%d pages)" % (args.out, size, len(items)))


def cmd_zoom(args):
    doc = pymupdf.open(args.pdf)
    items = []
    for n in args.pages:
        page = doc[n - 1]
        box = _content_bbox(page)
        clip = pymupdf.Rect(0, box[0], page.rect.width, box[1]) if box else None
        pm = page.get_pixmap(dpi=args.dpi, clip=clip)
        items.append((str(n), Image.open(io.BytesIO(pm.tobytes("png")))))
    size = _grid(items, args.cols, args.out)
    print("%s  %s" % (args.out, size))


def cmd_check(args):
    doc = pymupdf.open(args.pdf)
    bad_cmd = bad_dollar = bad_err = blank = 0
    for i, page in enumerate(doc):
        text = page.get_text()
        cmds = set(re.findall(r"\\[a-zA-Z]+", text))
        if cmds:
            bad_cmd += 1
            print("  p%d leftover LaTeX: %s" % (i + 1, sorted(cmds)[:6]))
        if "$" in text:
            bad_dollar += 1
            print("  p%d stray '$' x%d" % (i + 1, text.count("$")))
        err = text.count("KaTeX") + text.count("ParseError")
        if err:
            bad_err += 1
            print("  p%d KaTeX error markers: %d" % (i + 1, err))
        gray = np.asarray(_pil(page, 50, gray=True).resize((60, 60)), dtype=np.float32)
        if float((gray < 235).mean()) < 0.012:
            blank += 1
            print("  p%d looks blank" % (i + 1))
    print(
        "pages: %d | leftover latex: %d | with $: %d | katex errors: %d | blank: %d"
        % (doc.page_count, bad_cmd, bad_dollar, bad_err, blank)
    )
    return 0 if not (bad_cmd or bad_dollar or bad_err or blank) else 1


# --------------------------------------------------------------------------- #

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("keys", help="cluster near-identical pages, emit key pages")
    p.add_argument("pdf")
    p.add_argument("--thr", type=float, default=3.0)
    p.add_argument("--json")
    p.set_defaults(func=cmd_keys)

    p = sub.add_parser("sheets", help="tile key pages into contact sheets")
    p.add_argument("pdf")
    p.add_argument("outdir")
    p.add_argument("prefix")
    p.add_argument("--keys", default="")
    p.add_argument("--thr", type=float, default=3.0)
    p.add_argument("--cols", type=int, default=2)
    p.add_argument("--rows", type=int, default=3)
    p.add_argument("--dpi", type=int, default=140)
    p.set_defaults(func=cmd_sheets)

    p = sub.add_parser("bands", help="stack every page's title band into an outline map")
    p.add_argument("pdf")
    p.add_argument("out")
    p.add_argument("--cols", type=int, default=3)
    p.set_defaults(func=cmd_bands)

    p = sub.add_parser("zoom", help="high-res crop of page content, for checking formulas")
    p.add_argument("pdf")
    p.add_argument("out")
    p.add_argument("pages", nargs="+", type=int)
    p.add_argument("--dpi", type=int, default=400)
    p.add_argument("--cols", type=int, default=2)
    p.set_defaults(func=cmd_zoom)

    p = sub.add_parser("check", help="audit an exported PDF")
    p.add_argument("pdf")
    p.set_defaults(func=cmd_check)

    args = ap.parse_args()
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
