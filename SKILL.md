---
name: distillation-lecture-slide-to-review-note
description: 将 PDF 课件或由 PPT 导出的 PDF 整理成可打印的 A4 横线纸复习笔记。适用于需要中文正文、KaTeX 数学公式、内嵌 SVG 图示和自动目录页码的笔记制作；不负责把课件内容自动改写成准确笔记。
---

# distillation-lecture-slide-to-review-note

这套工作流把**已核对的章节内容**排成 HTML，再由 Edge/Chrome 打印成 A4 PDF；PyMuPDF 在正文页的文字基线下画横线并盖页码。课件文字抽取、公式还原、图示重绘和事实核对需要执行者完成，脚本只负责确定性的排版步骤。

## 使用前

- 输入课件需为 PDF；PPT/PPTX 先由用户可用的工具导出 PDF。
- Windows 环境需可运行的 Python、PyMuPDF 和 Edge/Chrome。首次构建 KaTeX 需联网；离线时可预先把 `package/dist/` 放入工程根目录。依赖和运行命令见 [README.md](README.md)。
- 先读 [references/SPEC.md](references/SPEC.md) 的排版与公式约束。需要看标记写法时读自编短例 [examples/ch01.html](examples/ch01.html)；它是**功能样例**，不规定实际笔记的篇幅或学科内容。

## 制作流程

1. 用 `scripts/bootstrap.py` 建工程。它只复制不存在的文件，不覆盖已经写好的章节。

   ```powershell
   python scripts/bootstrap.py .\_note
   cd .\_note
   python build\ensure_katex.py .
   ```

2. 逐份抽取课件文字，并与原 PDF 抽样比对。高频中文命中 0 次只是警报，不能单凭它认定文字层损坏。

   ```powershell
   python build\extract_pdf_text.py .\src\chapter1.pdf .\src\chapter1.txt
   ```

   如果文字层确实错乱，按 [references/broken-text-layer.md](references/broken-text-layer.md) 把相关页渲染为图后逐页整理；本包不声称提供 OCR。

3. 先写一章，确定解释深度、公式和图示风格，再写其余章节。每章是 `build/parts/chNN.html` 内容片段，以 `<h1 class="chap"><span class="cn">CHAPTER N</span>章节标题</h1>` 开头；文件名和章号必须相符。准确性优先于页数，例题页码以原课件核对。需要分章协作且已获授权时，可参考 [agents/dispatch_prompt.md](agents/dispatch_prompt.md)。

4. KaTeX 资产必须在渲染前准备好。`finalize.py` 自动发现 `chNN.html`，由章节标题生成目录，多次渲染直到页码稳定，并把最终 PDF 输出到工程根目录。

   ```powershell
   python build\finalize.py --title "课程复习笔记" --out "复习笔记_A4横线纸.pdf"
   ```

   只验证单章、不需要封面和目录时：

   ```powershell
   python build\assemble.py --only ch01 --out note_full.html
   python build\render.py build\note_full.html note.pdf --skip-first 0
   ```

5. 逐页检查最终 PDF：公式没有 `$...$` 源码、正文约 11 pt、横线贴近正文基线、图示未裁切、页码与目录一致。用 PyMuPDF 抽查文本字号并渲染页面为 PNG，再目视核对。不要只凭文件存在或大小宣布完成。

## 排版不变量

- [assets/note.css](assets/note.css) 的 `@page` 与 [scripts/render.py](scripts/render.py) 的 A4 边距、24 pt 网格、首线位置必须一起维护；改其一就要重新做打印校准。
- 行内公式不用高分式或复杂矩阵；放到独立 `.fx` 公式框。HTML 内的数学比较符 `<`、`>` 写作 `&lt;`、`&gt;`。
- 超宽表格和公式可能触发浏览器整页缩放；先拆行、换行或重排，再检查输出字号。`assemble.py` 的溢出处理只是兜底。
- SVG 应内嵌并给图形明确的描边、填充和可见范围；教材图只能按核对后的含义重绘，不能凭记忆补画。

## 交付

说明覆盖的课件章节、未能确认的内容、公式与图的处理方式，以及 PDF 的页数和逐页检查结果。保留课件原件与可编辑 HTML。公开示例仅使用本包自编的短章节；实际课程材料的公开范围由材料权利人确认。
