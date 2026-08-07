---
name: student-wrong-question-diagnosis
slug: student-wrong-question-diagnosis
displayName: 学生错题诊断卡（离线 · 错题选取灵活）
version: 1.1.5
description: >-
  This skill converts a student's scanned or photographed wrong-question material—where the questions to diagnose are indicated by the student (highlighter circles, hand-drawn boxes/frames, or directly photographed wrong-question pages)—into a self-contained offline HTML diagnosis card deck (KaTeX, zero internet) and a 7-step Markdown diagnosis report. Built for teachers/tutors/students doing AI-assisted error attribution. The marking method is OPTIONAL and never mandatory: circling, boxing, or simply photographing the problem pages all work. Standard trigger phrases (any one works): "处理学生错题扫描件", "生成错题诊断卡", "整理荧光笔圈出的错题", "把我框出来的错题做成卡", "把拍的错题整理成诊断卡", "离线打包错题卡". Also triggers when building, validating, or offline-packaging such a card deck, or bootstrapping from the bundled template. See the "触发方式" section for the authoritative list.
author: 李悦超
license: MIT
tags:
  - education
  - wrong-question
  - diagnosis
  - offline
  - katex
  - study
agent_created: true
---

# Student Wrong-Question Diagnosis（学生错题诊断卡）

## Overview
Turn a student's scanned or photographed wrong-question material into a self-contained offline HTML diagnosis card deck (KaTeX formulas, no internet needed) and a 7-step Markdown diagnosis report. The workflow is proven across multiple students and is fully offline-capable. **The question-selection method is optional and never mandatory**—students may circle with a highlighter, draw boxes/frames around the problem, or simply photograph the wrong-question pages; any of these tells the system "these are the questions I want diagnosed". Key features: flexible question identification (circle / box / photo), 7-step error attribution (知识没掌握 / 方法没想到 / 思维不完整 / 计算失误 / 审题问题), KaTeX offline rendering with bundled fonts, a triage rule for invalid selections, and a portable generator with zero third-party dependencies.

## 触发方式（Trigger）
当用户表达以下任一意图时即触发本技能（表述不必逐字一致，意思对即可）：

- **核心触发语句（标准说法，推荐统一使用）**
  1. 处理学生错题扫描件 / 照片
  2. 生成错题诊断卡
  3. 整理荧光笔圈出的错题
  4. 把我框出来的错题做成卡
  5. 把拍的错题整理成诊断卡
  6. 离线打包错题卡

- **等价说法（同义即可触发，无需照抄）**
  - "把荧光笔圈的题目整理成诊断卡" / "扫描件里圈出来的题做归因"
  - "把我框出来 / 画圈的题做成卡" / "我拍的这几页错题诊断一下"
  - "生成可离线看的错题卡" / "把错题扫描件 / 照片做成带公式的卡片"
  - 泛指"处理我的错题扫描件""诊断一下这份作业""这几张错题帮我归因"等，只要输入是**学生标出或拍出的错题**（荧光笔 / 框选 / 直接拍摄均可）即可。

- **不适用 / 不触发**
  - 纯文本错题（无任何扫描件 / 照片、也未标出任何题）建议走通用问答，不必走本流水线。
  - 老师蓝笔标记的例题 / 变式 / 已订正，归入"巩固"卡，不视为诊断对象（与选取方式无关）。

> 触发后固定走 7 步流程（见 `references/workflow.md`）；资源与模板见下方「Bundled resources」。

## When to use
- Input: a scanned PDF **or a photograph** of the student's wrong questions, where the target questions are indicated by the student—highlighter circles, hand-drawn boxes/frames, or simply the photographed problem pages. Blue-pen-titled 例题 / 变式 / 已订正 become "巩固" cards, not diagnosis targets.
- Output requested: 错题诊断卡 HTML + 诊断报告 .md, or any intermediate step toward them.
- **触发条件**：见上方「触发方式（Trigger）」小节——用户只要说出其中任一核心触发语句，即按本技能处理。

## Workflow (end-to-end)
Follow `references/workflow.md` for the full 7-step procedure. Key points:

1. Receive materials: PDF / photo + student info (姓名 / 科目 / 日期 / 文件名). If the student supplies a "第几页第几题" list, use it directly. Note the **selection method** the student used (highlighter circle / box / photo / list)—it is optional and never required.
2. PDF → PNG at 150 dpi (PyMuPDF/fitz), one image per page, page-numbered. For photos, use the image(s) directly.
3. Identify the target questions (selection method is flexible, see conventions):
   - Preferred: read the images, locate the student-indicated questions (highlighter ring, drawn box/frame, or the photographed problem pages).
   - Triage invalid selections: if a marked/boxed area clearly contains no real wrong question (blank space, page header/footer, teacher's remark, an already-corrected example, unrelated content), **skip it**—do not generate a card. Record it as an "无效选取" and confirm with the student when in doubt; never guess.
   - Fallback: if the environment cannot view images, **do not guess**—ask the student for the page/question list and proceed from that.
4. Author one card per wrong question using the schema in `references/schema.md`. Each card has 4 segments: correct approach (`one`), what went wrong (`mistake`), how to avoid it (`action`), plus `ability` / `checked` (error attribution). Consolidation cards use `kind="巩固"` with empty `mistake`.
5. Generate the HTML deck with `scripts/generate.py` (exact command in `references/workflow.md`). Default to offline mode with the bundled `assets/katex-dist` so the result is a zero-dependency single file.
6. Validate formulas: extract each `\(...\)` and render with node katex `renderToString({throwOnError:true})`; fix any LaTeX error (see `references/formula.md`) and regenerate.
7. Write the diagnosis report per `references/report.md`, then register in index / 台账 if a central repo exists.

## Bundled resources
- `scripts/generate.py` — portable offline generator (Python 3 only, no third-party deps). CDN by default; `--offline <katex-dist>` inlines 60 KaTeX fonts for a fully offline single file.
- `assets/katex-dist/` — KaTeX dist (css / js / contrib / fonts) for offline builds. 完整性证明见 `assets/MANIFEST.md`（含 60 字体 SHA-256 校验和）。
- `assets/cards_data_template.py` — fill-in skeleton for card data (Chinese-field comments, 错题 / 巩固 examples).
- `references/workflow.md` — full 7-step procedure + generate.py usage + deliverables + offline self-check.
- `references/schema.md` — card fields, CHECKS, examples.
- `references/formula.md` — `<bs>` placeholder, `wrap_ce`, LaTeX pitfall table, validation.
- `references/report.md` — 7-section report structure + 台账 format.

## Conventions (must hold)
- **题目选取方式非必须（核心改动）**：荧光笔圈、手绘框/画圈、直接拍错题页，都可作为「待诊断错题」的来源；核心约定是「学生自己标出或拍出的题 = 他想诊断的错题」，**不限定必须用荧光笔**。若学生未做任何标记、仅拍了错题页，整页即目标。
- **无效框选处置**：框/圈/拍出的区域若不含真实错题（空白、页眉页脚、老师批注、已订正例题、与题无关内容），不生成卡片，记为「无效选取」并在报告/台账说明；存疑时向学生确认，不臆测。
- 老师蓝笔标题的例题 / 变式 / 已订正 = 巩固卡（`kind="巩固"`），与选取方式无关，永远不作为诊断对象。
- In card text, represent backslash with `<bs>` (not a literal `\`), restored by `tex()` at build time.
- Offline output must be zero external CDN references (verify: `grep` for `cdn.jsdelivr` → 0; inline `data:font/woff2;base64` → 60).
