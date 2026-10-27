#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 build/parts/*.html 片段拼装成一份完整 HTML。

章节片段命名约定：
  cover.html        封面 + 目录（可选，放在最前）
  ch01.html / ch02.html …  各章正文，按数字后缀自然排序

用法：
  python assemble.py                       # 拼到 build/note.html
  python assemble.py --out note_full.html
  python assemble.py --only ch01,ch02     # 只拼指定章（逗号分隔，不加 .html）
"""
import argparse, pathlib, re, sys

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

# 网格吸附 + KaTeX 渲染 + 溢出缩放。
# 三个要点（都是踩坑经验）：
#  1) 每个块级元素顶边吸附到 24pt 网格、高度补齐到 24pt 整数倍，
#     这样 PyMuPDF 逐页画的横线才能与文字基线严格对齐，跨页不走形。
#  2) KaTeX 配 $$ / \\[ \\] / $ 三种定界符；渲染必须发生在 </body> 前。
#  3) 任何超出栏宽的不可断行元素（宽表格/超长公式）会触发 Chrome 整文档
#     fit-to-page 缩放（字号被压到约 0.854×），用 zoom 等比缩小其布局足迹消除。
SNAP_JS = """
<script>
(function(){
  var PT = 96/72, H = 24*PT;   /* 32px = 24pt */
  function snap(){
    var body = document.body;
    var kids = Array.prototype.slice.call(body.children);
    kids.forEach(function(el){
      if (el.tagName === 'SCRIPT') return;
      el.style.marginTop = '0px';
      el.style.marginBottom = '0px';
    });
    for (var i=0; i<kids.length; i++){
      var el = kids[i];
      if (el.tagName === 'SCRIPT') continue;
      if (el.classList.contains('cover')) continue;
      if (el.classList.contains('pb')) continue;
      var top = el.getBoundingClientRect().top - body.getBoundingClientRect().top;
      var rem = top % H;
      if (rem > 0.35 && rem < H-0.35){
        el.style.marginTop = (H - rem).toFixed(2) + 'px';
      }
    }
    document.documentElement.setAttribute('data-snapped','1');
  }
  function fitOverflow(){
    var nodes = document.body.getElementsByTagName('*');
    for (var pass=0; pass<2; pass++){
      for (var i=0; i<nodes.length; i++){
        var el = nodes[i];
        if (el.nodeType !== 1) continue;
        var tag = el.tagName.toLowerCase();
        if (tag === 'body' || tag === 'html') continue;
        var cw = el.clientWidth;
        var sw = el.scrollWidth;
        if (cw > 0 && sw > cw + 1){
          var k = cw / sw;
          if (k > 0.2 && k < 1){
            el.style.zoom = k.toFixed(4);
          }
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
    snap();
    if (document.fonts && document.fonts.ready){
      document.fonts.ready.then(function(){ fitOverflow(); snap(); });
    }
  });
})();
</script>
"""

TAIL = """
</body>
</html>
"""

CH_RE = re.compile(r'ch(\d+)', re.IGNORECASE)


def natural_order(files):
    """cover 最前，其余按 ch 后的数字排序。"""
    out = []
    cover = None
    chs = []
    for f in files:
        if f.stem.lower() == 'cover':
            cover = f
        else:
            m = CH_RE.fullmatch(f.stem)
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
    ap.add_argument('--only', default=None,
                    help='只拼某几章，逗号分隔，如 ch01,ch02')
    args = ap.parse_args()

    root = pathlib.Path(__file__).resolve().parent
    parts_dir = root / args.parts

    all_files = [p for p in parts_dir.glob('*.html')
                 if p.stem.lower() == 'cover' or CH_RE.fullmatch(p.stem)]
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

    html = HEAD + '\n'.join(chunks) + SNAP_JS + TAIL
    out = root / args.out
    out.write_text(html, encoding='utf-8')
    print('-> %s  (%d chars, %d parts)' % (out, len(html), len(files)))


if __name__ == '__main__':
    main()
