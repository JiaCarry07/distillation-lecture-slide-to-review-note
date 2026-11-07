#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""独立复核用户三条硬要求：知识点覆盖 / 例题配图 / 图号引用。

不依赖各章撰写单元的汇报，直接从课件原文与成品 HTML 交叉比对。
输出 tools/coverage_report.txt。
"""
import html as htmllib
import pathlib
import re
import sys
from collections import OrderedDict

from lxml import html as lh

BUILD = pathlib.Path(__file__).resolve().parents[1]
SRC = BUILD / 'src'
PARTS = BUILD / 'parts'
sys.path.insert(0, str(BUILD / 'tools'))
from chapter_map import load_chapter_map
from project_parts import chapter_sources

CHAPTER_MAP, CHAPTER_TITLE = load_chapter_map(SRC / 'chapter_map.json')

PREFIX = re.compile(r'^(?:[一二三四五六七八九十]+[、.]|\d+(?:\.\d+)+[、.\s]?|§\s*\d+(?:\.\d+)*|'
                    r'\d+[-–]\d+\s*)')
NOISE = re.compile(r'(谢谢|再见|本讲主要内容|本节主要内容|本章主要内容|思考题|'
                   r'本讲要点|目录|例题|举例|续)')


def note_text(n):
    paths = {number: path for number, path, _ in chapter_sources(PARTS)}
    s = paths[n].read_text(encoding='utf-8')
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'\s+', '', htmllib.unescape(s)), paths[n].read_text(encoding='utf-8')


def course_sections(ch):
    """抽取本章课件里出现过的所有小节标题（去重，保留顺序）。"""
    out = OrderedDict()
    for entry in CHAPTER_MAP[ch]:
        fid, desc, rng = entry[0], entry[1], (entry[2] if len(entry) > 2 else None)
        txt = (SRC / (fid + '.txt')).read_text(encoding='utf-8')
        for mm in re.finditer(r'<<<SLIDE (\d+)>>>(.*?)(?=<<<SLIDE \d+>>>|$)', txt, re.S):
            pno = int(mm.group(1))
            if rng and not (rng[0] <= pno <= rng[1]):
                continue
            for line in mm.group(2).splitlines():
                line = line.strip()
                if not (3 <= len(line) <= 34):
                    continue
                if NOISE.search(line):
                    continue
                m = PREFIX.match(line)
                if not m:
                    continue
                core = re.sub(r'[\s:：（）()]+', '', line[m.end():])
                core = re.sub(r'[（(].*', '', core)
                if len(core) < 3 or core.isdigit():
                    continue
                out.setdefault(core, (fid, pno, line))
    return out


def check_examples(ch, raw):
    """每道 .ex 例题是否自带或紧邻配图。"""
    doc = lh.fromstring('<div id="root">' + raw + '</div>')
    exs = doc.xpath('//div[contains(concat(" ", normalize-space(@class), " "), " ex ")]')
    bad = []
    for ex in exs:
        title = ''.join(ex.xpath('.//div[contains(@class,"ex-hd")]//text()')).strip()
        title = re.sub(r'\s+', ' ', title)[:46]
        if ex.xpath('.//img'):
            continue
        nxt, found = ex.getnext(), False
        for _ in range(2):
            if nxt is None:
                break
            if nxt.xpath('.//img'):
                found = True
                break
            nxt = nxt.getnext()
        if not found:
            bad.append(title)
    return len(exs), bad


def check_figrefs(ch, raw):
    """正文里引用的「图 N-M」是否都有对应图注。"""
    text = re.sub(r'<[^>]+>', '', raw)
    caps = set(re.findall(r'<figcaption>\s*图\s*(\d+-\d+)', raw))
    refs = set(re.findall(r'图\s*(\d+-\d+)', text)) - caps
    return caps, sorted(refs - caps)


def main():
    lines = ['课件复习笔记 · 章节、例题配图与图号核对', '=' * 66, '']
    tot_sec = tot_hit = tot_ex = tot_bad_ex = 0
    for ch in sorted(CHAPTER_MAP):
        ntext, raw = note_text(ch)
        secs = course_sections(ch)
        hits, miss = [], []
        for core, (fid, pno, orig) in secs.items():
            key = core[:4] if len(core) >= 4 else core
            (hits if key in ntext else miss).append((core, fid, pno, orig))
        nex, bad_ex = check_examples(ch, raw)
        caps, dangling = check_figrefs(ch, raw)
        lines += [
            '─' * 66,
            '第 %d 章 %s' % (ch, CHAPTER_TITLE[ch]),
            '  课件小节 %3d 条 → 笔记命中 %3d 条 (%.0f%%)' % (
                len(secs), len(hits), 100 * len(hits) / max(1, len(secs))),
            '  例题 %3d 道，缺配图 %d 道' % (nex, len(bad_ex)),
            '  图注 %3d 个，正文引用但无图注 %d 个' % (len(caps), len(dangling)),
        ]
        if miss:
            lines.append('  【未命中的课件小节】')
            for core, fid, pno, orig in miss[:22]:
                lines.append('    %s p%-3d  %s' % (fid, pno, orig[:40]))
            if len(miss) > 22:
                lines.append('    … 另有 %d 条' % (len(miss) - 22))
        if bad_ex:
            lines.append('  【缺配图例题】')
            for t in bad_ex[:14]:
                lines.append('    ' + t)
        if dangling:
            lines.extend(['  【悬空图号引用】', '    ' + ', '.join(dangling[:18])])
        tot_sec += len(secs); tot_hit += len(hits)
        tot_ex += nex; tot_bad_ex += len(bad_ex)
    lines += ['=' * 66,
              '合计：课件小节 %d / 命中 %d (%.1f%%)；例题 %d / 缺配图 %d' % (
                  tot_sec, tot_hit, 100 * tot_hit / max(1, tot_sec), tot_ex, tot_bad_ex), '']
    (BUILD / 'tools' / 'coverage_report.txt').write_text('\n'.join(lines), encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
