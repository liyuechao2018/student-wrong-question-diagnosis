# 更新日志 / Changelog

本仓库的**版本号以 `SKILL.md` 顶部 frontmatter 的 `version` 字段为准**（如 `version: 1.1.5`）。
SkillHub 从 GitHub 拉取时，依据该字段判断是否需要更新；每次实质改动请递增该字段并在此文件记录。

版本格式遵循 [语义化版本 SemVer](https://semver.org/lang/zh-CN/)：
- **主版本号**：不兼容的接口/工作流重构
- **次版本号**：向下兼容的新功能 / 重要改进
- **修订号**：向下兼容的问题修复

---

## [1.1.5] - 2026-08-07

### 修复
- **公式块内 Unicode 数学符号自动转 LaTeX（兜底层）**：`generate.py` 的 `tex()` 在还原 `<bs>` 之后，新增 `_fix_math_blocks()`，对所有 `\(...\)` / `$$...$$` 公式块内的 Unicode 数学符号（`∈ Δ ⇒ ≤ ≥ ≠ π θ` 等 50+ 个）自动转 LaTeX 命令。**块外的中文 / 全角括号 / 中文标点完全保持原样不被污染**。
  - 修复现象：学生写 `<bs>(a≠0<bs>)` 时，`≠` 是 Unicode，KaTeX 不认，整条 `\(...\)` 解析失败后被截断，截图末尾出现孤零零的 `\)` 字符。现在自动转成 `\(a \neq 0\)` 正常渲染。
  - 同步更新 `references/formula.md` 加「Unicode → LaTeX 自动兜底」小节，列出完整对照表与生效范围。
  - 仍然**推荐**数据里直接写 LaTeX 命令（更可控），但写错也不会再让整条公式挂掉。

### 顺带验证
- GJY（12 道集合与二次方程参数）卡用 v1.1.5 的 `generate.py` 重跑：所有 `∈` `Δ` `⇒` `≤` `≠` 在 math 块内**全部自动转好**，产物零 `Unsupported` 截断。
- 顶部 meta 行已无「荧光笔圈出共」残留（v1.1.4 已修，本版本再次确认）。

---

## [1.1.4] - 2026-08-06

### 改进（核心工作流放宽）
- **题目选取方式「非必须」**：不再强制要求荧光笔圈题。学生可用 **荧光笔圈出 / 手绘框·画圈 / 直接拍摄错题页 / 提供「第几页第几题」清单** 任一方式标出想诊断的题；仅拍错题页时整页即目标。核心约定改为「学生自己标出或拍出的题 = 他想诊断的错题」。
- **新增无效框选处置**：框 / 圈 / 拍出的区域若明显不含真实错题（空白、页眉页脚、老师批注、已订正例题、与题无关内容），**跳过、不生成卡片**，记为「无效选取」并在报告/台账说明；存疑时向学生确认，不臆测。
- `SKILL.md`：displayName 改为「错题选取灵活」；Overview / 触发方式 / When to use / Conventions 全面放宽；新增框选 / 拍摄触发语。
- `references/workflow.md`：标记约定改为「选取方式四选一（非必须）」+ 无效框选处置；步骤 1/2/3 适配照片与框选。
- `references/schema.md`：新增可选字段 `mark`（本题选取方式：荧光笔圈出 / 框选 / 拍摄 / 清单），并注明无效框选不写进 CARDS。
- `assets/cards_data_template.py`：新增模块级 `SELECT_METHOD`（顶部元信息展示用），示例卡补充 `mark`。
- `scripts/generate.py`：`build_cdn` 元信息行改为中性的「共 N 道（错题 X / 巩固 K）」，不再写死「荧光笔圈出」；顶部可选展示「选取方式：…」；卡片来源行追加「选取：…」（如填了 `mark`）。
- `references/report.md`：错题全景 / 台账格式改为选取方式无关，并新增「无效选取」列。

---

## [1.1.3] - 2026-08-06

### 修复（平台兼容）
- **SkillHub 平台禁止上传字体二进制**（`.ttf`/`.woff`/`.woff2` 均被后端拒绝）。改为把离线所需字体以 **base64 写入 `assets/katex-dist/fonts_b64.json`**（`.json` 为平台允许类型）。
- `scripts/generate.py`：新增 `load_font_b64_map()`，`inline_fonts()` 改为从「`fonts_b64.json` → `fonts/` 目录」两级收集字体 base64 内联；正则**仅匹配 `.woff2`**（离线 HTML 只需 woff2，现代浏览器均支持，woff/ttf fallback 缺失不影响渲染）。字体彻底缺失时才回退到 GitHub 联网拉取。
- 效果：从 SkillHub 安装的 Skill **零字体文件、完全离线、开箱即用**；实测仅含 `fonts_b64.json` 时生成 0 个 CDN 引用、20 字体内联。

---

## [1.1.1] - 2026-08-06

### 修复
- `SKILL.md` 的 `description` 字段原为单行未加引号的 YAML 标量，内含冒号（`any one works):`）导致 SkillHub CLI（`skillhub install --no-api`）与网页端解析 frontmatter 失败。**改为 `>-` 块标量**，冒号/引号均安全，可被正常拉取。
- 顺带明确"从 GitHub 拉取"的命令：`skillhub install --no-api <owner>/<repo>`（跳过 API、直接 clone 仓库）。

---

## [1.1.0] - 2026-08-06

### 新增
- `assets/MANIFEST.md`：列出 `assets/katex-dist/fonts/` 全部 **60 个字体文件**（20 woff2 + 20 woff + 20 ttf）与核心脚本的 **SHA-256 校验和**，作为离线资源完整性证明（回应评测"资源包不完整"的质疑，便于自动校验确认资源齐全）。

### 改进
- `scripts/generate.py`：新增 `SkillError` **中文友好异常体系**，包裹数据加载 / 字体内联 / 离线资源校验 / 主流程；出错时给出中文提示而非裸 traceback（消除原评测中 R 可靠性"英文报错"扣分项）。
- `SKILL.md`：新增「**触发方式（Trigger）**」小节作为**唯一权威触发词清单**，收敛此前散落在多处、表述不一的触发语。

---

## [1.0.0] - 2026-07-25

### 初始发布
- 荧光笔圈题识别 → 离线错题诊断卡（单文件 HTML，60 字体内联）+ 7 步归因报告。
- 便携生成器 `scripts/generate.py`（CDN / 离线两种模式，仅依赖 Python 3）。
- 模板 `assets/cards_data_template.py` 与 4 份 references（workflow / schema / formula / report）。
- 内置 KaTeX 0.16.9 dist（60 字体），离线零配置。
