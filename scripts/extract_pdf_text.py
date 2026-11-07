#!/usr/bin/env python3
"""Dump a PDF to a text file with explicit page markers, one block per page.

Slide decks are easier to digest when page boundaries are visible, because a
single slide is usually one self-contained concept.

Usage:
    python extract_pdf_text.py <input.pdf> <output.txt>

Requires: pymupdf  (pip install pymupdf)
"""

import sys
from pathlib import Path

try:
    import pymupdf
except ImportError:
    sys.exit("ERROR: pymupdf is required (pip install pymupdf)")


def main() -> int:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])

    doc = pymupdf.open(src)
    blocks = []
    for index, page in enumerate(doc):
        blocks.append("===== PAGE %d =====" % (index + 1))
        blocks.append(page.get_text().strip())
    dst.write_text("\n".join(blocks), encoding="utf-8")
    print("%s -> %s  (%d pages, %d chars)" % (src, dst, doc.page_count, sum(map(len, blocks))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
