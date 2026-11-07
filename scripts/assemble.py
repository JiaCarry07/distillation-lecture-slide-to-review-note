#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 parts/*.html 片段拼装成一份完整 HTML（A4 无横线自然流式）。

章节片段命名：cover.html（封面+目录，可选）、ch01.html / ch02.html …（按数字后缀自然排序）。
用法：
  python assemble.py                       # -> note.html
  python assemble.py --out note_full.html
  python assemble.py --only ch01,ch02
"""
import argparse
import pathlib
import re
import sys

HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>复习笔记</title>
<link rel="stylesheet" href="assets/note.css">
<link rel="stylesheet" href="../package/dist/katex.min.css">
<script src="../package/dist/katex.min.js"></script>
<script src="../package/dist/contrib/auto-render.min.js"></script>
</head>
<body>
"""

# 只做两件事：KaTeX 渲染 + 溢出缩放。
#  1) KaTeX 配 $$ / \[ \] / $ 三种定界符，渲染必须发生在 </body> 前；
#  2) 任何超出栏宽的不可断行元素（宽表格/超长公式）会触发 Chrome 整文档
#     fit-to-page 缩放（字号被压到约 0.854×），用 zoom 等比缩小其布局足迹消除。
# 只做溢出缩放与公式渲染，不做任何网格吸附。
BOOTSTRAP_JS = """
<script>
(function(){
  function fitOverflow(){
    var nodes = document.body.getElementsByTagName('*');
    for (var pass=0; pass<2; pass++){
      for (var i=0; i<nodes.length; i++){
        var el = nodes[i];
        if (el.nodeType !== 1) continue;
        var tag = el.tagName.toLowerCase();
        if (tag === 'body' || tag === 'html') continue;
        var cw = el.clientWidth, sw = el.scrollWidth;
        if (cw > 0 && sw > cw + 1){
          var k = cw / sw;
          if (k > 0.2 && k < 1) el.style.zoom = k.toFixed(4);
        }
      }
    }
  }
  function renderKatex(){
    if (!window.renderMathInElement) return;
    try{
      renderMathInElement(document.body, {
        delimiters: [
          {left: "$$", right: "$$", display: true},
          {left: "\\[", right: "\\]", display: true},
          {left: "$",  right: "$",  display: false}
        ],
        throwOnError: false,
        ignoredTags: ["script","noscript","style","textarea","pre","option"]
      });
    }catch(e){ console.error('katex', e); }
  }
  window.addEventListener('load', function(){
    renderKatex();
    fitOverflow();
    if (document.fonts && document.fonts.ready){
      document.fonts.ready.then(function(){ fitOverflow(); });
    }
  });
})();
</script>
"""

TAIL = """
</body>
</html>
"""

CH_RE = re.compile(r'ch(\d+)')


def natural_order(files):
    out, chs, cover = [], [], None
    for f in files:
        if f.stem.lower() == 'cover':
            cover = f
        else:
            m = CH_RE.search(f.stem)
            chs.append((int(m.group(1)) if m else 9999, f))
    chs.sort(key=lambda x: x[0])
    if cover:
        out.append(cover)
    out += [f for _, f in chs]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--parts', default='parts')
    ap.add_argument('--out', default='note.html')
    ap.add_argument('--only', default=None)
    args = ap.parse_args()

    root = pathlib.Path(__file__).resolve().parent
    parts_dir = root / args.parts
    all_files = [p for p in parts_dir.glob('*.html')
                 if p.stem == 'cover' or CH_RE.fullmatch(p.stem)]
    files = natural_order(all_files)
    if args.only:
        want = set(args.only.split(','))
        files = [f for f in files if f.stem in want]
    if not files:
        sys.exit('no parts found in %s' % parts_dir)

    chunks = []
    for f in files:
        txt = f.read_text(encoding='utf-8').replace('<!--MORE-->', '')
        chunks.append('<!-- ===== %s ===== -->\n' % f.stem + txt)
        print('  + %-14s %7d chars' % (f.name, len(txt)))

    html = HEAD + '\n'.join(chunks) + BOOTSTRAP_JS + TAIL
    out = root / args.out
    out.write_text(html, encoding='utf-8')
    print('-> %s  (%d chars, %d parts)' % (out, len(html), len(files)))


if __name__ == '__main__':
    main()
