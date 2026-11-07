#!/usr/bin/env python3
"""Check PDF page geometry, obvious formula leftovers and blank pages."""
import argparse
import re
import sys
import pymupdf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf')
    args = parser.parse_args()
    issues = []
    with pymupdf.open(args.pdf) as doc:
        if not doc.page_count:
            issues.append('PDF 没有页面')
        for i, page in enumerate(doc):
            text = page.get_text()
            if abs(page.rect.width - 594.96) > 1 or abs(page.rect.height - 841.9) > 1:
                issues.append(f'第 {i+1} 页不是 A4')
            if re.search(r'\$[^$\n]{1,240}\$', text) or re.search(r'\\(?:frac|dfrac|sqrt)\b', text):
                issues.append(f'第 {i+1} 页可能有公式源码')
            pix = page.get_pixmap(dpi=36, colorspace=pymupdf.csGRAY, alpha=False)
            if sum(v < 235 for v in pix.samples) / len(pix.samples) < 0.002:
                issues.append(f'第 {i+1} 页疑似空白')
        print(f'检查 {doc.page_count} 页；问题 {len(issues)} 项')
    for issue in issues:
        print(issue)
    return 1 if issues else 0


if __name__ == '__main__':
    sys.exit(main())
