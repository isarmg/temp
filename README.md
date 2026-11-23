# 2024 西电 821 电路与信号系统辅导讲义

## 821 A4 单列版（全面复核）

A4 竖版单列，共 99 页。电路 6 章与信号与系统 8 章均另起一页。电路和信号与系统目录各占一页，80 项均可点击跳转。Word 正文、表格和公式可编辑。

页码在页脚居中显示，封面计为第 1 页，从目录第 2 页开始显示。目录总标题、科目、大章和小节分别为 17、14、12、10.5 磅。

易串读的独立公式已分行或用标点隔开。已逐章复核卷积、傅里叶直流项、多频功率因数、端口等效及收敛域等公式和适用条件。四处分图标签已重新对齐，s 平面与 z 平面对应图已补全边界标注。

第 5 页 KVL「技巧」第 ①、② 条采用原讲义措辞。第 6 页两幅电压源图并排，右侧短接子图标有「×」。第 10 页在实际电源等效变换后加入三图并排的字母示例及端口伏安式。第 11 页加入三网孔字母示例、三条典型网孔方程，以及零自阻和零互阻图例。第 13 页节点 KCL 的展开式与矩阵式并排，并在列写步骤后加入三节点字母示例。

已删除考试大纲、章首复习提要、宣传信息、旧页码和教材出处标注。星级按 821 标注在对应小节。中文标题用黑体，正文用宋体，英文和常用符号采用 Times New Roman。

叠加定理与等效电阻求解方法中保留了五条笔记。全书小标题、等效电阻求解方法的 a–d 标签及笔记照片中的划线文字均已加粗。

- [下载 PDF](https://github.com/isarmg/temp/releases/download/xidian-handout-v1.3.16/xidian-821-reviewed.pdf)
- [下载 Word](https://github.com/isarmg/temp/releases/download/xidian-handout-v1.3.16/xidian-821-reviewed.docx)

## 源码与构建

讲义正文、样式、可编辑公式与内嵌图件位于 [`source/docx/`](source/docx/)，采用 Word 的 Open XML 格式。可编辑的 [SVG 图稿](source/drawings/) 与 [图件映射](source/figures.json) 同在仓库中。

下载或克隆仓库后，在仓库根目录运行以下命令。需要 Python 3.10 或更新版本。导出 PDF 还需要 LibreOffice。

```sh
python3 tools/build.py
```

生成的 Word 和 PDF 位于 `dist/`。只生成 Word 时运行 `python3 tools/build.py --word-only`。如果系统路径中没有 `soffice`，可用 `--soffice` 指定 LibreOffice 的可执行文件。

复现 PDF 版式时，请安装 Times New Roman、STIX Two Math、Noto Sans CJK SC 和 Noto Serif CJK SC。在使用 Fontconfig 的系统上，构建会读取当前的 `FONTCONFIG_FILE` 设置。

编辑 `source/drawings/` 中的图稿后，用 Inkscape 更新对应的内嵌 SVG 与 PNG，再运行构建。以下命令以三节点图为例。

```sh
python3 tools/render_figure.py node-three.svg
python3 tools/build.py
```

如需核对 PDF 的页码和目录跳转，安装 [PyMuPDF](https://pypi.org/project/PyMuPDF/) 后运行 `python3 tools/check_pdf.py`。

整理自《24西电晋程考研电路部分辅导讲义》和《24西电晋程考研信号部分辅导讲义》。
