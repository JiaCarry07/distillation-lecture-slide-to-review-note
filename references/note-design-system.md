# 复习笔记 HTML 设计规范（已验证）

把课件内容写成一份 A4 排版的 HTML，再用无头浏览器打印成 PDF。下面这套 CSS 与组件结构已实际产出过
26 页、含 9 幅 SVG 图与大量 KaTeX 公式的中文复习笔记，可直接复用。

---

## 1. 页面骨架

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>…</title>
<link rel="stylesheet" href="package/dist/katex.min.css">
<script src="package/dist/katex.min.js"></script>
<script src="package/dist/contrib/auto-render.min.js"></script>
<style>/* 见第 3 节 */</style>
</head>
<body>
  <section class="cover">…</section>          <!-- 封面，page-break-after: always -->
  <h1 class="sec"><span class="no">1.1</span>小节标题</h1>
  …
<script>
renderMathInElement(document.body, {
  delimiters: [
    {left: "$$", right: "$$", display: true},
    {left: "$",  right: "$",  display: false}
  ],
  throwOnError: false,
  ignoredTags: ["script","noscript","style","textarea","pre","option"]
});
</script>
</body>
</html>
```

`package/dist/` 由 `scripts/ensure_katex.py` 准备，放在 HTML 同级目录，用相对路径引用即可。

---

## 2. 关键 CSS 变量（浅色主题）

```css
:root{
  --ink:#16202f; --ink2:#3b4a63; --ink3:#6a7a94;
  --line:#d9e2ee; --line2:#eef3f9;
  --blue:#1b5fa8; --blue-d:#12447c; --blue-s:#eaf2fb;
  --teal:#0c6f77; --teal-s:#e4f4f5;
  --amber:#a35a06; --amber-s:#fdf3e3;
  --red:#b02020; --red-s:#fdeceb;
  --green:#2a7048; --green-s:#e9f6ee;
  --violet:#5b3fa8; --violet-s:#f0ecfb;
}
@page{ size:A4; margin:16mm 15mm 17mm; }
html{ -webkit-print-color-adjust:exact; print-color-adjust:exact; }
body{
  margin:0; color:var(--ink);
  font-family:"Microsoft YaHei","微软雅黑","PingFang SC","Hiragino Sans GB",sans-serif;
  font-size:10.8pt; line-height:1.78; letter-spacing:.01em; background:#fff;
}
```

- **正文 10.8pt / 行高 1.78**：中文长文阅读的舒适区间；再小（<10pt）会明显吃力，再大页数膨胀。
- `print-color-adjust:exact` 必加，否则打印/导出时背景色会被丢弃。
- 深色主题只需把 `--ink` 系列翻转为浅色、各 `-s` 底色换成深色变体；不要在浅色主题里用深色面板。

---

## 3. 组件类

| 类名 | 用途 | 要点 |
|---|---|---|
| `.cover` | 封面 | `height:247mm` + `flex` 居中 + `page-break-after:always` |
| `h1.sec` | 一级节标题 | 深蓝渐变底、白字、圆角；`<span class="no">1.1</span>` 做编号列 |
| `h2.sub` | 二级标题 | 左侧 5px 青色竖条 |
| `h3.mini` | 三级标题 | 前面加 `▍` 符号 |
| `.card` / `.card.tint` | 内容卡片 | 圆角边框；`.tint` 是浅灰蓝底 |
| `.lbl.b/.t/.a/.r/.g/.v` | 卡片内标签 | 六种配色，分别对应蓝/青/橙/红/绿/紫语义 |
| `.callout.warn/.tip/.key/.ok` | 提示框 | 红=易错、橙=提示、青=重点结论、绿=结论 |
| `.fx` | **公式框** | 左边 4px 蓝条 + 居中；`.tag` 是框内左上角的说明文字 |
| `.steps` | 有序步骤 | CSS 计数器画成蓝色圆形数字 |
| `ul.dot` / `ul.chk` | 要点 / 自测 | `◆` / `✓` 伪元素 |
| `.navgrid` | 2 列卡片网格 | 适合"易错点清单" |
| `.two` | 2 列并排 | 适合左右对照（关联/非关联、两种方法） |
| `.footnote` | 脚注 | 灰色小字 + 虚线上边框 |
| `.pb` / `.avoid` | 强制分页 / 禁止跨页 | 见第 5 节 |

公式框的写法：

```html
<div class="fx">
<span class="tag">适用条件说明</span>
$$u_{ab}=\frac{\mathrm{d}w_{ab}}{\mathrm{d}q}\qquad \text{单位：伏特（V）}$$
</div>
```

---

## 4. 公式排版约定（KaTeX）

- 行内用 `$…$`，独立成行用 `$$…$$`（`.fx` 框内自动居中）。
- 微分符号用 `\mathrm{d}`，得到正体 **d**，比斜体 `d` 规范。
- 物理量带下标用 `u_{ab}`、`p_{\text{吸}}`（中文下标必须包在 `\text{}` 里）。
- 单位用 `\ \mathrm{V}` 或直接 `\text{单位：伏特（V）}`。
- 分段函数用 `\begin{cases} … \end{cases}`。
- **不要**在同一行混用 `\displaystyle` 与非 displaystyle 的 `\sum`：会让基线不齐、表格单元格内换行错乱。
  需要求和号变大时，整段都用 `$$…$$` 独立成行。

---

## 5. 分页控制（最容易踩坑的地方）

```css
/* 表格：允许跨页，但行不能断 */
table{ width:100%; border-collapse:collapse; }
thead{ display:table-header-group; }   /* 跨页时重复表头 */
tr{ break-inside:avoid; page-break-inside:avoid; }

/* 这些整体不能断 */
.card, .callout, .fx, figure{ break-inside:avoid; page-break-inside:avoid; }

/* 标题不要孤零零留在页底 */
h1.sec, h2.sub, h3.mini{ break-after:avoid; page-break-after:avoid; }
```

- ⚠️ **绝对不要给 `table` 加 `break-inside:avoid`**。长表格一旦超过一页就会整块被推到下一页，
  产生大片空白，实测能把 20 页的内容撑到 26 页。用 `tr` + `thead` 的组合代替。
- 分页后会出现的页底空白属于正常现象，不必强行消除。

---

## 6. 内嵌 SVG 图

课件里的电路图通常是位图截图，重绘成 SVG 后清晰度与一致性都好得多。

```html
<figure>
<svg viewBox="0 0 680 200" xmlns="http://www.w3.org/2000/svg"> … </svg>
<figcaption>图 1-4　说明文字（可用 $…$ 写公式）</figcaption>
</figure>
```

- **viewBox 宽度统一用 680**，`figure svg{ max-width:100% }`，这样能撑满正文宽度且比例一致。
- 文字必须显式给 `font-family`（用 `<text class="svgtxt">` + CSS `.svgtxt{font-family:"Microsoft YaHei",sans-serif}`），
  否则会退化成衬线体，与正文不搭。
- **颜色不要依赖 CSS 类**（`c-purple` 之类未实现），每个形状都写 inline `fill` / `stroke`。
- 箭头用 `<marker>` 定义，注意 `id` 在同一文档内不能重复。
- ⚠️ 文字宽度要按 `viewBox` 留足余量：中文按 1 字 ≈ 字号 px 估算。超出 viewBox 的部分会被**静默裁掉**，
  预览缩略图里看不出来，必须放大检查。
- 图例、标注尽量放在图形右侧或下方的空白区，别贴着 viewBox 边缘。

---

## 7. 页脚页码

浏览器 `--print-to-pdf` 的页眉页脚难以定制，改为导出后用 PyMuPDF 盖章（见 `scripts/html_to_pdf.py`）。

- 中文用 `fontname="china-s"`（内置 CJK 字体，无需外部字体文件）。
- ⚠️ **纯数字不要用 `china-s`**：它会把 ASCII 数字按全角渲染，`10 / 26` 会变成 `１ ０ / ２ ６`，字间带大空隙。
  数字部分改用 `fontname="helv"`。
- 封面页跳过，不盖页脚。

---

## 8. 内容组织建议

复习笔记按"导读 → 逐节 → 附录"三段式，实测好用：

1. **导读**：全章知识主线图（用 SVG 画分层流程图）+ 核心公式速查表 + 易错点清单。
   速查表列"主题 / 公式 / 适用条件与符号约定"，是整份笔记里最常被回看的一页。
2. **逐节**：每节固定顺序为「定义 → 公式（`.fx` 框）→ 符号规则 → 判据/分类表 → 例题 → 提示框」。
   课件里的例题全部保留，并把解题步骤编号写出来。
3. **附录**：符号规则总表、解题标准流程、自测清单（用 `ul.chk`，每条写成能答"是/否"的问句）。

课件原文的口语化表达要转写成书面语；课件里用图片表达的电路结构，尽量重绘为 SVG。
