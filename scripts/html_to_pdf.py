#!/usr/bin/env python3
"""Render HTML through the project's checked A4 PDF pipeline."""
import argparse
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('html')
    parser.add_argument('out')
    parser.add_argument('--footer-left', default='')
    parser.add_argument('--skip-first-page', action='store_true')
    parser.add_argument('--browser')
    parser.add_argument('--page-number-position', choices=('right', 'left', 'center', 'outer'), default='right')
    args = parser.parse_args()
    renderer = Path(__file__).resolve().parents[1] / 'render.py'
    cmd = [sys.executable, str(renderer), args.html, args.out,
           '--footer-left', args.footer_left, '--skip-first', '1' if args.skip_first_page else '0',
           '--page-number-position', args.page_number_position]
    if args.browser:
        cmd += ['--browser', args.browser]
    return subprocess.call(cmd)


if __name__ == '__main__':
    sys.exit(main())
