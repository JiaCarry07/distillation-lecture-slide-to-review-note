#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 PPTX 抽取逐页文字 + 形状统计，生成索引与文本源文件。

输出：
  src/_index.json            文件清单（id / 路径 / 页数 / 章）
  src/<id>.txt               逐页文字，<<<SLIDE n>>> 分隔
"""
import json
import pathlib
import re
import sys

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

ROOT = pathlib.Path(__file__).resolve().parents[3]          # 工作区根
BUILD = pathlib.Path(__file__).resolve().parents[1]
SRC = BUILD / 'src'
SRC.mkdir(parents=True, exist_ok=True)


def shape_text(sh, out):
    if sh.shape_type == MSO_SHAPE_TYPE.GROUP:
        for sub in sh.shapes:
            shape_text(sub, out)
        return
    if getattr(sh, 'has_table', False):
        for row in sh.table.rows:
            cells = [c.text.strip().replace('\n', ' ') for c in row.cells]
            line = ' | '.join(x for x in cells if x)
            if line:
                out.append(line)
        return
    if getattr(sh, 'has_text_frame', False):
        for para in sh.text_frame.paragraphs:
            t = ''.join(run.text for run in para.runs).strip()
            if t:
                out.append(t)
        return


def count_shapes(shapes):
    n_pic = n_draw = 0
    for sh in shapes:
        if sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
            n_pic += 1
        elif sh.shape_type == MSO_SHAPE_TYPE.GROUP:
            a, b = count_shapes(sh.shapes)
            n_pic += a
            n_draw += b
        elif sh.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE or sh.shape_type == MSO_SHAPE_TYPE.FREEFORM:
            n_draw += 1
    return n_pic, n_draw


def chapter_of(rel: str):
    m = re.match(r'第(\d+)章', rel)
    return int(m.group(1)) if m else 0


def main():
    files = sorted(p for p in ROOT.rglob('*.pptx') if '.courseware-note-studio' not in p.parts)
    index = []
    for i, p in enumerate(files, 1):
        fid = 'f%02d' % i
        rel = p.relative_to(ROOT).as_posix()
        rec = {'id': fid, 'path': str(p), 'rel': rel,
               'chapter': chapter_of(rel), 'name': p.stem}
        try:
            prs = Presentation(str(p))
            pages = []
            texts = []
            for n, slide in enumerate(prs.slides, 1):
                out = []
                for sh in slide.shapes:
                    shape_text(sh, out)
                npic, ndraw = count_shapes(slide.shapes)
                # 去重相邻重复行
                ded = []
                for line in out:
                    if not ded or ded[-1] != line:
                        ded.append(line)
                body = '\n'.join(ded)
                texts.append('<<<SLIDE %d>>>\n%s' % (n, body))
                pages.append({'n': n, 'chars': len(body), 'pics': npic, 'draws': ndraw,
                              'head': ded[0] if ded else ''})
            rec['slides'] = len(pages)
            rec['pages'] = pages
            (SRC / (fid + '.txt')).write_text('\n\n'.join(texts), encoding='utf-8')
            print('%-4s %3d slides  %s' % (fid, len(pages), rel))
        except Exception as e:
            rec['slides'] = 0
            rec['pages'] = []
            rec['error'] = repr(e)
            print('%-4s ERROR %s : %s' % (fid, rel, e), file=sys.stderr)
        index.append(rec)
    (SRC / '_index.json').write_text(json.dumps(index, ensure_ascii=False, indent=1),
                                     encoding='utf-8')
    print('总幻灯片：', sum(r['slides'] for r in index))


if __name__ == '__main__':
    main()
