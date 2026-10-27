# A4 横线纸笔记 · 章节制作规范

这份规范记录了固定页面网格、HTML 组件和公式约束。电路图坐标与元件符号只是学科示例；处理其他学科时按原材料重绘相应图示。

---

## 1. 任务与产出

| 项 | 说明 |
|---|---|
| 输入 | 工程目录的 `src/<章名>.txt`（课件全文，已按 `<<<PAGE n>>>` 分页），并对照原 PDF |
| 产出 | `build/parts/chNN.html`（**只有内容片段**，不要 `<html>`/`<head>`/`<body>`） |
| 样式 | 已由 `build/assets/note.css` 统一提供，**不要自己写 `<style>`，不要改这个 css** |
| 范例 | skill 包内的 `examples/ch01.html` 是自编短例，演示标记写法，不规定正式章节篇幅 |
| 篇幅 | 由课件内容和用户要求决定；不要为了凑页数缩字号或添加未经核对的知识点 |

### 页面几何（决定了内容密度，务必记住）

- A4，正文 **11pt / 行高 24pt**，每页 **31 行**，内容宽约 44 个汉字。
- 所以：**一页大约 900–1100 字正文**（含公式和图会更少）。
- 每个 `<h2 class="sub">` 节标题占 1 行，`<h3 class="mini">` 占 1 行，`<p>` 每行 24pt。

---

## 2. 内容组织示例（电路课程）

```html
<h1 class="chap"><span class="cn">CHAPTER 2</span>电阻电路的等效变换</h1>
<div class="chapcore">核心：用「等效」把复杂网络化简成一眼能算出的形式。</div>

<h2 class="sub"><span class="no">2.1</span>电阻电路</h2>

<h3 class="mini">小标题</h3>
<p>正文……</p>

<div class="fx">$$R_{\text{eq}}=\frac{R_1R_2}{R_1+R_2}$$</div>

<table class="t">
<thead><tr><th style="width:22%">列名</th><th>说明</th></tr></thead>
<tbody>
<tr><td>……</td><td>……</td></tr>
</tbody>
</table>

<div class="callout key"><b>结论</b>　……</div>

<div class="ex">
<div class="ex-hd">例 1　标题<span class="src">第 2 章 32—34 页</span></div>
<div class="ex-bd">
<p>题目条件……</p>
<ol class="steps">
<li>第一步……</li>
<li>第二步……</li>
</ol>
<p><b>要点</b>：……</p>
</div>
</div>

<figure class="fig">
<svg viewBox="0 0 680 200" xmlns="http://www.w3.org/2000/svg"> … </svg>
<figcaption>图 2-1　说明文字</figcaption>
</figure>

<h2 class="sub">本章公式速查</h2>
<table class="t">…</table>

<h2 class="sub">本章易错点</h2>
<div class="two">
<div><div class="callout warn"><b>① ……</b>　……</div></div>
<div><div class="callout warn"><b>② ……</b>　……</div></div>
</div>
```

复习用途通常适合在章首写一条 `chapcore` 核心句，章末附公式速查与易错点；若材料不适合，可调整结构。

---

## 3. 可用组件（只有这些，不要发明新类）

| 类名 | 用途 | 用法要点 |
|---|---|---|
| `h1.chap` | 章标题 | 内含 `<span class="cn">CHAPTER N</span>` |
| `.chapcore` | 章核心句 | 紧跟 h1，一行 |
| `h2.sub` | 节标题 | `<span class="no">N.M</span>` 编号 |
| `h3.mini` | 小标题 | 自动带 ▍符号 |
| `p` | 正文段落 | 不要加 class |
| `.fx` | **独立公式框** | 里面放 `$$…$$`，蓝左条 + 白底 + 居中 |
| `table.t` | 表格 | 必须 `thead`+`tbody`，`th` 可加 `style="width:..%"`；单元格居中加 `class="c"` |
| `.callout.key` | 青色重点框 | `<b>标题</b>　正文` |
| `.callout.warn` | 红色易错框 | 同上 |
| `.callout.tip` | 橙色提示框 | 同上 |
| `.callout.ok` | 绿色结论框 | 同上 |
| `.ex` | 例题卡片 | 内含 `.ex-hd` + `.ex-bd` |
| `.ex-hd` | 例题标题栏 | 内含 `.src` 标注课件页码 |
| `.steps` | 编号步骤 | `<ol class="steps"><li>…</li></ol>`，自动画蓝色圆圈序号 |
| `ul.dot` | 要点列表 | 自动 ◆ |
| `ul.chk` | 自测清单 | 自动 □ |
| `ol.num` | 普通编号 | |
| `figure.fig` | 图片容器 | 内含 `<svg>` + `<figcaption>` |
| `.two` | 两列并排 | `<div class="two"><div>…</div><div>…</div></div>` |
| `.footnote` | 脚注小字 | |
| `b.k` | 蓝色加粗 | 关键词用 |
| `.hl` | 黄色高亮 | 慎用 |

---

## 4. 公式规范（KaTeX）

- 行内：`$u=Ri$`；独立成行：放在 `.fx` 里写 `$$…$$`。
- **行内公式禁止**：`\frac`、`\dfrac`、`\sum_{}^{}`、`\int`、`\begin{cases}`、`\sqrt` 带复杂内容。
  这些会把 24pt 行盒撑高、破坏横线网格。需要时**单独放一个 `.fx` 框**。
  行内要表达除法，写成 `u/R`、`i^{2}R`、`\mathrm{d}w/\mathrm{d}q` 这种斜线式。
- 微分符号用 `\mathrm{d}`（正体）：`\mathrm{d}w`、`\mathrm{d}t`。
- 中文下标必须包 `\text{}`：`p_{\text{吸}}`、`U_{\text{oc}}`、`i_{\text{S}}`。
- 单位：`5\ \mathrm{V}`、`0.4\ \mathrm{k\Omega}`、`50\ \mathrm{Hz}`。
- 相量：`\dot{U}`、`\dot{I}`。
- 分段函数、方程组用 `\begin{cases}` 或 `\begin{aligned}`，**只在 `.fx` 里用**。
- 同一行不要混用 `\displaystyle` 与普通 `\sum`。

### ⚠️ 必须转义

HTML 里 `<` 和 `>` **一律写成 `&lt;` / `&gt;`**，公式里也一样：
`$0&lt;r&lt;R$`、`$k&gt;1$`、`$R_1&lt;r&lt;R_2$`。
不转义会被浏览器当成标签解析，该条公式**整块退化成 LaTeX 源码**，而且只有部分公式会中招，极难发现。

---

## 5. SVG 图规范

需要图示时优先重绘能帮助理解的图，数量由原课件决定。宁可少而准，不要多而错。

### 基本规则

```html
<figure class="fig">
<svg viewBox="0 0 680 200" xmlns="http://www.w3.org/2000/svg">
  <line x1="40" y1="100" x2="200" y2="100" stroke="#37465c" stroke-width="1.4"/>
  <text class="svgtxt" x="120" y="90" font-size="11" text-anchor="middle" fill="#37465c">标注</text>
</svg>
<figcaption>图 2-1　说明</figcaption>
</figure>
```

- `viewBox` 宽度**统一 680**，高度按内容定（160–320 之间）。
- 线条明确写 inline `stroke`，封闭形状明确写 `fill` 和 `stroke`，文字明确写 `fill`；不要只依赖未定义的 CSS 颜色类。
- 所有 `<text>` 必须带 `class="svgtxt"`（否则退化成衬线体）。
- 中文按「1 字 ≈ 字号 px」估算宽度，**留足右边距**，超出 viewBox 会被静默裁掉。
- 下标用 tspan 且 `dy` 成对：`<text …>R<tspan font-size="7.5" dy="2">1</tspan><tspan dy="-2"> 的电压</tspan></text>`。
- 箭头用 `<marker>`，**同一文档内 id 不能重复**，请用 `ar_<章号><序号>` 命名，如 `ar2a`。
- 图注格式：`图 N-M　说明文字`，N 为章号，M 从 1 开始连续编号，**全章不重号**。
- 正文引用图时写「如图 N-M 所示」。

### 配色（与正文一致）

| 用途 | 颜色 |
|---|---|
| 导线、元件轮廓 | `#37465c` |
| 主色（电压、标注、强调） | `#1a5a9e` |
| 电流箭头 | `#a81d1d` |
| 次要说明文字 | `#65748a` |
| 受控源、辅助 | `#0b6a72` |
| 元件填充浅底 | `#e9f1fa` |

### 电路课程示例：元件符号画法

```svg
<!-- 电阻（竖放）：宽12 高36 的矩形，导线在上下 -->
<rect x="198" y="82" width="12" height="36" fill="#fff" stroke="#37465c" stroke-width="1.5"/>
<!-- 电阻（横放）：宽36 高12 -->
<rect x="322" y="60" width="36" height="12" fill="#fff" stroke="#37465c" stroke-width="1.5"/>

<!-- 电压源：圆 r=13，内标 + / − -->
<circle cx="60" cy="100" r="13" fill="#fff" stroke="#37465c" stroke-width="1.5"/>
<text class="svgtxt" x="60" y="97" font-size="10" text-anchor="middle" fill="#37465c">+</text>
<text class="svgtxt" x="60" y="110" font-size="10" text-anchor="middle" fill="#37465c">&#8722;</text>

<!-- 电流源：圆 r=13，内画向上箭头 -->
<circle cx="60" cy="100" r="13" fill="#fff" stroke="#37465c" stroke-width="1.5"/>
<line x1="60" y1="110" x2="60" y2="92" stroke="#37465c" stroke-width="1.6"/>
<path d="M55.5,97 L60,90.5 L64.5,97" fill="none" stroke="#37465c" stroke-width="1.6" stroke-linejoin="round"/>

<!-- 受控源：菱形，内画 +/− 或箭头 -->
<polygon points="90,58 118,90 90,122 62,90" fill="#e2f2f3" stroke="#0b6a72" stroke-width="1.5"/>

<!-- 电感：一串半圆弧 -->
<path d="M60,80 q6,-10 12,0 q6,-10 12,0 q6,-10 12,0 q6,-10 12,0"
      fill="none" stroke="#37465c" stroke-width="1.5"/>

<!-- 电容：两条平行短线 -->
<line x1="86" y1="85" x2="86" y2="115" stroke="#37465c" stroke-width="2"/>
<line x1="94" y1="85" x2="94" y2="115" stroke="#37465c" stroke-width="2"/>

<!-- 结点：实心圆 -->
<circle cx="200" cy="50" r="4" fill="#1a5a9e"/>
```

### 电路课程示例：图示检查

1. **回路必须闭合**：导线画成线段，在元件处**断开**，元件嵌进去。不要把元件浮在一个完整矩形框里——那看起来像「元件放在盒子里」，不是电路。
2. **箭头必须压在导线上**：电流箭头的 x（或 y）要等于该支路导线的 x（或 y），否则读起来像多出一条并联支路。
3. **两个元件的边框不能贴在一起**：至少留 14 单位空隙，中间用明确导线连到真正的结点，结点用实心圆标出。

### 坐标怎么定（省时间的做法）

先在纸上定「行/列」：
- 横向：左边界 x=40，右边界 x=640，中间按元件数均分。
- 纵向：常用 y=60（上导线）、y=140（下导线）、y=100（中线）。
- 一个标准串联回路：`40,60 → 640,60 → 640,140 → 40,140 → 闭合`，元件分别嵌在四条边上。

---

## 6. 硬性约束（踩过的坑，逐条遵守）

| # | 约束 | 后果 |
|---|---|---|
| 1 | 公式里的 `<` `>` 必须写 `&lt;` `&gt;` | 否则整条公式退化成源码 |
| 2 | 行内禁止 `\frac`/`\dfrac`/`\sum_{}^{}` | 撑破 24pt 行盒，横线错位 |
| 3 | 不要给 `table` 加 `break-inside:avoid` | 长表整块推走，产生大片空白 |
| 4 | 不要写 `<style>`、不要改 `note.css` | 会污染其他章 |
| 5 | SVG 线条、封闭形状与文字分别明确写描边或填充颜色 | 否则可能回退成黑色 |
| 6 | SVG 文字必须 `class="svgtxt"` | 否则退化成衬线体 |
| 7 | `<marker>` 的 id 必须全文档唯一 | 重复会导致箭头丢失 |
| 8 | 图注编号全章连续不重号 | 重复编号会被质检打回 |
| 9 | 不要引用外部图片、不要 `<img src="http…">` | 打印时缺图 |
| 10 | 不要留下待填写占位符或虚构的课件数据 | 可能混入最终成品 |

---

## 7. 写法要求

- **讲透原理，不只给结论**。公式要交代来源与适用条件；判据要说明为什么这么判。
- 课件口语化的表述（「本节任务」「学习要求」这类页）**直接删掉**，不要抄进来。
- 课件里反复出现的「解题步骤」只保留一次，合并成 `ol.steps` 或表格。
- 按用户要求选择或保留例题；引用课件例题时核对题目、答案和原始页码，编号保持连续。
- 例题步骤要能让人照着复现：设参考方向 → 判关联性 → 写 VCR → 列 KCL/KVL → 代入 → 校验。
- 语气：像学得比读者好一点的学长，直接、不客套，不用「同学们」「让我们」。

---

## 8. 交付前自检

在工程根目录运行：

```powershell
python build\check_chapter.py build\parts\chNN.html
```

这会检查章号、公式定界符、部分行内公式问题、图注和重复 id；它不能证明课程内容正确，也不能替代最终 PDF 的逐页目视检查。
