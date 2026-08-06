---
name: student-wrong-question-diagnosis
slug: student-wrong-question-diagnosis
displayName: 学生错题诊断卡（离线 · 荧光笔圈题识别）
version: 1.1.2
description: >-
  This skill converts a student's scanned wrong-question PDF—where questions are marked with a highlighter—into a self-contained offline HTML diagnosis card deck (KaTeX, zero internet) and a 7-step Markdown diagnosis report. Built for teachers/tutors/students doing AI-assisted error attribution. Standard trigger phrases (any one works): "处理学生错题扫描件", "生成错题诊断卡", "整理荧光笔圈出的错题", "把圈出的错题做成诊断卡", "离线打包错题卡". Also triggers when building, validating, or offline-packaging such a card deck, or bootstrapping from the bundled template. See the "触发方式" section for the authoritative list.
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
Turn a student's scanned wrong-question PDF—where wrong questions are circled with a highlighter—into a self-contained offline HTML diagnosis card deck (KaTeX formulas, no internet needed) and a 7-step Markdown diagnosis report. The workflow is proven across multiple students and is fully offline-capable. Key features: highlighter-based question identification, 7-step error attribution (知识没掌握 / 方法没想到 / 思维不完整 / 计算失误 / 审题问题), KaTeX offline rendering with bundled fonts, and a portable generator with zero third-party dependencies.

## 触发方式（Trigger）
当用户表达以下任一意图时即触发本技能（表述不必逐字一致，意思对即可）：

- **核心触发语句（标准说法，推荐统一使用）**
  1. 处理学生错题扫描件
  2. 生成错题诊断卡
  3. 整理荧光笔圈出的错题
  4. 把圈出的错题做成诊断卡
  5. 离线打包错题卡

- **等价说法（同义即可触发，无需照抄）**
  - "把荧光笔圈的题目整理成诊断卡" / "扫描件里圈出来的题做归因"
  - "生成可离线看的错题卡" / "把错题扫描件做成带公式的卡片"
  - 泛指"处理我的错题扫描件""诊断一下这份作业"等，只要输入是荧光笔圈题的扫描 PDF 即可。

- **不适用 / 不触发**
  - 纯文本错题（无扫描件、无圈题）建议走通用问答，不必走本流水线。
  - 非荧光笔标记的例题 / 变式 / 已订正，归入"巩固"卡，不视为诊断对象。

> 触发后固定走 7 步流程（见 `references/workflow.md`）；资源与模板见下方「Bundled resources」。

## When to use
- Input: a scanned PDF where wrong questions are marked with a highlighter (荧光笔). Blue-pen-titled 例题 / 变式 / 已订正 become "巩固" cards, not diagnosis targets.
- Output requested: 错题诊断卡 HTML + 诊断报告 .md, or any intermediate step toward them.
- **触发条件**：见上方「触发方式（Trigger）」小节——用户只要说出其中任一核心触发语句，即按本技能处理。

## Workflow (end-to-end)
Follow `references/workflow.md` for the full 7-step procedure. Key points:

1. Receive materials: PDF + student info (姓名 / 科目 / 日期 / 文件名). If the student supplies a "第几页第几题" list, use it directly.
2. PDF → PNG at 150 dpi (PyMuPDF/fitz), one image per page, page-numbered.
3. Identify highlighted questions:
   - Preferred: read the PNGs, locate highlighter-marked questions.
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
- Highlighter circle = wrong question to diagnose. Never treat teacher blue-pen 例题 / 变式 / 已订正 as diagnosis targets.
- In card text, represent backslash with `<bs>` (not a literal `\`), restored by `tex()` at build time.
- Offline output must be zero external CDN references (verify: `grep` for `cdn.jsdelivr` → 0; inline `data:font/woff2;base64` → 60).
