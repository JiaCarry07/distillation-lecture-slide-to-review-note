# 章节撰写规范

每章为 `build/parts/chNN.html` 内容片段，首行格式如下，文件名数字和章号必须一致：

```html
<h1 class="chap"><span class="cn">CHAPTER 1</span>章节标题</h1>
```

根据课件内容组织章节；涵盖用户要求的范围，保留必要的来源页码、例题、公式和图示。图示数量由内容决定。源材料不清楚时标记并核对，不编造。PDF 讲义图可重绘为内嵌 SVG；PPTX 图可经检查后裁切。课件图片的公开使用须确认授权。

行内公式用 `$...$`，独立公式用 `<div class="fx">$$...$$</div>`；HTML 中的比较符用 `&lt;`、`&gt;`。需要可控换行时拆分长公式和宽表格。图使用 `<figure class="fig">` 和明确图注。段落、公式、图片和题解须核对原课件。

可用组件包括 `chapcore`、`sub`、`mini`、`fx`、`callout key/warn/tip/ok`、`ex`、`steps`、`table.t`、`fig`、`figrow`、`footnote`。题解可使用 `q`、`qh`、`qn`、`qt`、`qa`、`qb`、`step`。自编可运行样例见 `examples/ch01.html`。

最后运行 `verify_pdf.py` 并逐页视觉检查；图片检查与目录检查均需对照源材料。保持 HTML 结构完整，避免把本机路径放入最终成品。
