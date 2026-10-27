# 分章协作提示模板

仅在当前任务允许分工、且确实有多份独立课件时使用。每个执行单元只负责一章；主控统一核对原课件、拼装和渲染最终 PDF。

```text
目标：把《<课程名>》第 <N> 章《<章名>》整理成 A4 横线纸复习笔记的一个 HTML 内容片段。

先读：
1. <工程目录>/build/tools/SPEC.md：页面网格、公式和 HTML 组件约束。
2. <skill目录>/examples/ch01.html：自编短例，只参考标记写法，不照搬学科内容或篇幅。
3. <工程目录>/src/<课件文本>.txt，并对照 <工程目录>/src/<原课件>.pdf 核对关键页。

只写：<工程目录>/build/parts/ch<N两位数字>.html。
文件以 <h1 class="chap"><span class="cn">CHAPTER N</span><章名></h1> 开头。
只写 HTML 内容片段，不写 html/head/body/style。不要修改共享 CSS、封面或其他章节。

本章应覆盖：<用户要求与原课件中的范围>。
重点解释：<3–5 个真正需要讲透的概念>。
例题、公式和图示必须与原课件或明确标为自编的内容一致；不确定之处列出，不要猜测。
引用课件例题时标原课件页码。需要读图时使用 build/rasterize_pdf_pages.py。

交付前在工程根目录运行：
python build/check_chapter.py build/parts/ch<N两位数字>.html

完成时简要报告：覆盖小节、图数、例题数、未解决的课件疑问和自检结果。
不要独立渲染最终 PDF；主控统一执行 finalize.py 和逐页检查。
```
