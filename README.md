# distillation-lecture-slide-to-review-note

把已核对的 PDF 课件内容排成可打印的 A4 横线纸复习笔记。正文使用 HTML，数学公式由 KaTeX 排版；Edge/Chrome 打印 PDF 后，PyMuPDF 画横线、加页码，脚本自动回填目录。

这是一个 **Codex skill 与本地排版工具包**。课件到笔记的知识整理、公式校对和插图重绘需要人工或 agent 完成；它不是自动摘要或 OCR 服务。PPT/PPTX 请先导出 PDF。

## 环境

- Windows，Edge 或 Chrome
- Python 3.10+；安装 [requirements.txt](requirements.txt) 中的 PyMuPDF
- 首次下载 KaTeX 时可连接 npm registry。离线使用时，预先把完整 `package/dist/` 放在工程根目录。

PowerShell 快速体验自编示例：

```powershell
python -m pip install -r requirements.txt
python scripts/bootstrap.py .\_note --example
Set-Location .\_note
python build\ensure_katex.py .
python build\check_chapter.py build\parts\ch01.html
python build\finalize.py --title "自编电路示例" --out "示例_横线纸.pdf"
```

如果 `python` 指向无效的 Windows 应用别名，请改用已安装的 Python 程序完整路径执行这些命令。输出 PDF 在 `_note` 目录。`bootstrap.py` 不覆盖已有文件。

## 用自己的课件

1. 建工程：`python scripts/bootstrap.py .\_note`，进入 `_note` 后运行 `python build\ensure_katex.py .`。
2. 将原 PDF 放入 `src/`，用 `python build\extract_pdf_text.py src\chapter1.pdf src\chapter1.txt` 抽取文字，并对照原 PDF。文字层错乱时参照 [读图说明](references/broken-text-layer.md)。
3. 按 [章节规范](references/SPEC.md) 编写 `build/parts/ch01.html` 等片段。`CHAPTER N` 与文件名数字须一致。用 `python build\check_chapter.py build\parts\ch01.html` 检查结构。
4. 执行 `python build\finalize.py --title "课程复习笔记" --out "复习笔记.pdf"`。脚本自动发现章节、生成目录并核对最终页码。
5. 逐页查看 PDF，重点检查公式、图示裁切、字号、横线位置及课件事实。脚本检查不代替视觉和内容核对。

`finalize.py --browser "C:\path\to\msedge.exe"` 可指定浏览器。目录和正文页脚都使用 PDF 的绝对页码；封面和目录页不盖页脚。输出过程先写临时文件，失败时保留原目标 PDF。

## 文件

- [SKILL.md](SKILL.md)：Codex 触发范围和制作流程
- `scripts/`：建工程、抽取文字、读图、检查章节、下载 KaTeX、拼装与渲染
- `assets/note.css`：A4 页面与 HTML 组件样式
- `examples/`：自编短章节与通用封面
- `references/`：排版规范及坏文字层处理

## 许可与公开内容

本仓库的原创脚本、文档、样式和自编示例采用 [MIT License](LICENSE)，版权署名为 `distillation-lecture-slide-to-review-note contributors`。KaTeX 由安装脚本另行下载，不随仓库分发。

实际教师课件、抽取文本、生成的图片与 PDF 应留在本地工程；公开其他材料前请先确认有权公开。

运行回归检查：

```powershell
python -m unittest discover -s tests -v
```
