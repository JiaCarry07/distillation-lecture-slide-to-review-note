# distillation-lecture-slide-to-review-note

课件笔记工作台（Courseware Note Studio）是本 skill 的更新版。它扩展了原版的课件整理流程：支持 PDF 讲义、原生 PPTX 和习题集，输出自然流式 A4 笔记。**新版不再生成横线纸**；如需旧版，可查看 [旧版仓库快照](https://github.com/JiaCarry07/distillation-lecture-slide-to-review-note/tree/8b0bd293ca6c7fe351fce8189dbb1df74c85707c)。

把 PDF 讲义、PPTX 或习题集整理为可打印的 A4 中文复习笔记。内容和公式需要对照原课件核对；脚本协助排版和检查。输出为自然流式页面。

## 安装到 Codex

在 Codex 中发送以下请求，让内置安装器从本仓库根目录安装：

```text
使用 $skill-installer 安装 JiaCarry07/distillation-lecture-slide-to-review-note 仓库根目录的 skill，安装名称为 distillation-lecture-slide-to-review-note。
```

安装后开启新的 Codex 对话，然后说“使用 distillation-lecture-slide-to-review-note 整理这些课件”，并提供课件和希望的范围。已有旧版时，先备份旧 skill；安装器不会覆盖同名目录，需按自己的环境处理旧目录后再安装。

也可以从 GitHub 点击 **Code → Download ZIP** 下载，将解压后包含 `SKILL.md` 的整个文件夹命名为 `distillation-lecture-slide-to-review-note`，放到用户的 Codex skills 目录中。安装过程中的依赖配置见下文。

## 环境

Python 3.10+、Edge 或 Chrome；`pip install -r requirements.txt`。PPTX 高保真导出路线还需 Windows 桌面版 PowerPoint。首次下载 KaTeX 需要网络；也可把已取得的 KaTeX `package/dist` 放入工程的 `.courseware-note-studio/package/dist`。

## 快速开始（PowerShell）

在本 skill 文件夹运行：

```powershell
python -m pip install -r requirements.txt
python scripts/bootstrap.py 'D:\笔记工程' --example
python scripts/ensure_katex.py 'D:\笔记工程\.courseware-note-studio'
python 'D:\笔记工程\.courseware-note-studio\build\finalize.py' --title '示例复习笔记' --out '示例.pdf'
python 'D:\笔记工程\.courseware-note-studio\build\tools\verify_pdf.py' 'D:\笔记工程\示例.pdf'
```

初始化不会覆盖已有文件。真实使用时，把课件放在工程目录，替换或新增 `.courseware-note-studio/build/parts/chNN.html`，并删除两个示例章节。目录按章节标题自动生成。浏览器不在默认位置时，给 `finalize.py` 传 `--browser '浏览器程序路径'`；要覆盖已有 PDF 须显式传 `--force`。输出 PDF 位于工程目录，可编辑 HTML 位于隐藏工程目录。

旧版横线纸工程与新版工程布局、样式和页码规则不同。建议先用新版初始化一个新工程，再按新版规范迁移并检查章节内容；旧工程请保留备份。

### 页码位置

封面和目录不编号，正文从第 1 页开始；目录中显示的也是正文页码。普通打印默认将页码放在右下角。准备双面打印并装订成书时，运行时加上 `--page-number-position outer`，正文奇数页在右、偶数页在左。还可以选择 `right`（默认）、`left` 或 `center`。

```powershell
python 'D:\笔记工程\.courseware-note-studio\build\finalize.py' --title '课程复习笔记' --out '书籍版.pdf' --page-number-position outer
```

奇偶只按正文页码计算。实际装订时，请确保正文第 1 页在右侧（纸张正面）：如果封面和目录等前置页面总数为奇数，可能需要在正文前插入一页空白。跳页或使用小册子拼版时，也应先检查实际装订位置。页码放在左侧时，页脚文字会移到右侧。

初始化会保留已有文件。已有工程要使用新增位置选项，请先备份工程，再将本包 `scripts/finalize.py` 和 `scripts/render.py` 复制到工程的 `build` 目录；如果使用单文件渲染入口，也将 `scripts/html_to_pdf.py` 复制到 `build/tools`。

从旧工程更新为正文独立编号时，请保留自定义封面内容，并将目录表头改为“正文页码”、页数说明改为“正文共……页”；现有 `data-toc` 和 `data-pg` 锚点需要保留。

## PPTX 和插图

在 Windows 上运行 `build/tools/extract_pptx.py`，检查 `build/src/_index.json`。将 PPTX 通过 PowerPoint 只读导出到 `build/pdf/f01.pdf` 等对应文件。人工核对章节及页码后创建 `build/src/chapter_map.json`，例如：

下面的 PowerShell 示例按索引导出；将 `$build` 改成实际的 `.courseware-note-studio\build` 路径：

```powershell
$build = 'D:\笔记工程\.courseware-note-studio\build'
$index = Get-Content -Raw -Encoding UTF8 (Join-Path $build 'src\_index.json') | ConvertFrom-Json
$app = New-Object -ComObject PowerPoint.Application
try {
  foreach ($item in $index) {
    $presentation = $app.Presentations.Open($item.path, $true, $false, $false)
    try { $presentation.SaveAs((Join-Path $build ("pdf\{0}.pdf" -f $item.id)), 32) }
    finally { $presentation.Close() }
  }
} finally { $app.Quit() }
```

章节映射示例：

```json
{"chapters":[{"number":1,"title":"第一章","sources":[{"id":"f01","description":"第一节","pages":[1,10]}]}]}
```

`pages` 可省略以使用整份课件。运行 `build/tools/make_figs.py`；联系表和配图均需逐页核对，自动裁切可能漏掉图形。`tighten_figs.py` 默认写入 `figs_v2`，`--apply` 会覆盖配图；使用前备份并比较。`verify_coverage.py` 的文本匹配结果是线索，不能证明覆盖完整。

最终 PDF 可选运行 `build/tools/postprocess_pdf.py <PDF>`、`enhance_navigation.py <PDF>`、`link_figures.py <PDF>`。这些工具会修改指定 PDF；建议先保留副本。导航脚本可用 `--split-dir <新目录>` 输出分章文件，已有同名文件时停止。书签、目录链接及图号跳转须人工核对。

## 验证与授权

运行 `verify_pdf.py` 后逐页查看 PDF，并核对公式、插图、目录和课件内容。本仓库以 [MIT 许可证](LICENSE)发布；引用来源不明的外部代码或课件时应确认相应授权。真实课件及其裁图的使用权限由各自权利人决定。
