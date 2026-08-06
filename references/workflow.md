# 端到端工作流（Buddy 执行 7 步）

输入：学生扫描 PDF（扫描全能王）+ 荧光笔圈出的错题（或圈不清时的「第几页第几题」清单）
输出：离线错题诊断卡 HTML（含 KaTeX 公式）+ 7 步诊断报告 .md

## 标记约定（全学科通用）
- **荧光笔圈出 = 待识别整理的错题**。
- 老师用蓝笔标题的「例题 / 变式 / 已订正」= 巩固卡（`kind="巩固"`），不圈、不强制识别，原无错误，并入卡页。

## 步骤
1. **接收材料**：PDF + 学生填写的姓名 / 科目 / 日期 / 文件名；若学生提供了「第几页第几题」清单，直接采用。
2. **PDF → PNG**：用 PyMuPDF(fitz) 以 150 dpi 转图，逐页保存，文件名带页码。
3. **识别荧光笔圈**：
   - 优先：读取 PNG，定位荧光笔高亮区域对应的题目。
   - 兜底：若运行环境无法看图（模型不支持图片 / 圈色与背景难分），**不要猜测**，向学生索取「第几页第几题」清单；照清单处理。
4. **逐题写卡片数据**：每道错题对应一张卡，字段见 `schema.md`。4 段内容：
   - `one`（正确思路）：标准解法 / 关键步骤。
   - `mistake`（错在哪）：学生实际错误点。
   - `action`（怎么不再错）：防错动作。
   - `ability`（能力项）/ `checked`（错误归因五选，见 schema）。
   巩固卡：`kind="巩固"`，`mistake` 可留空，生成器显示「原无实际错误」。
5. **生成 HTML**：运行 `scripts/generate.py`。默认离线 `--offline assets/katex-dist` 产出零依赖单文件。
6. **公式校验**：抽取 `<body>` 内 `\(...\)` 公式，用 node katex `renderToString({throwOnError:true})` 验证；任一失败则回到第 4 步修 LaTeX（见 `formula.md`）。
7. **写诊断报告**：按 `report.md` 的 7 段结构生成 .md；登记到 index.html / 台账（若老师有集中仓库）。

## generate.py 用法
```bash
python scripts/generate.py --data cards_data_xxx.py --out 姓名_错题诊断卡.html \
    --name 姓名 --pdf 扫描件.pdf --date 2026-07-25 \
    --offline assets/katex-dist
```
- 不传 `--offline` 走 CDN（需联网渲染公式），更轻量。
- 输出：离线单文件 = 60 个 KaTeX 字体 base64 内联、0 个外部 CDN 引用、可断网渲染。

## 交付物清单
- `姓名_错题诊断卡.html`：每张卡 4 段（错在哪 / 为什么错 / 正确思路 / 怎么不再错）；`kind=错题` 显示红色「错题」标，巩固卡显示「巩固」标。
- `错题诊断报告.md`：能力画像 + 错误归因统计 + 薄弱知识点 + 7 天 / 4 周计划。

## 离线产物自检
- `grep -c "cdn.jsdelivr" 产物.html` → 应为 0
- `grep -o "data:font/woff2;base64" 产物.html | wc -l` → 应为 60
- `grep -o 'class="card"' 产物.html | wc -l` → 应等于卡数
