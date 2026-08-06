# 学生错题诊断 Skill · Student Wrong-Question Diagnosis

把**荧光笔圈出**的错题扫描件，一键转成**离线可看、公式不乱码**的错题诊断卡网页 + 7 步归因报告。

> 适用于：老师 / 家教 / 学生。零依赖、断网可用。

> 📌 当前版本：**v1.1.0** · 版本号见 `SKILL.md` 顶部 `version` 字段 · 变更记录见 [CHANGELOG.md](CHANGELOG.md) · 更新方式见下文「版本与从 GitHub 更新」

---

## ✨ 核心特性

- **荧光笔即指令**：扫描件里用荧光笔圈出的题目 = 待整理错题；蓝笔写的例题 / 变式 / 已订正当「巩固」卡。零学习成本。
- **完全离线**：诊断卡是单文件 HTML，60 个 KaTeX 字体全部内联，断网也能渲染公式，可打印、可转发。
- **五维错误归因**：知识没掌握 / 方法没想到 / 思维不完整 / 计算失误 / 审题问题 —— 报告直接说清卡在哪一环。
- **零依赖生成器**：`scripts/generate.py` 只依赖 Python 3，无需安装任何第三方库。

---

## 📂 目录结构

```
student-wrong-question-diagnosis/
├── SKILL.md                      # Skill 元信息与触发/执行说明（给 AI 助手看）
├── LICENSE.txt                   # MIT
├── README.md                     # 本文件
├── scripts/
│   └── generate.py               # 便携离线生成器（CDN / 离线两种模式）
├── assets/
│   ├── cards_data_template.py    # 卡片数据填空骨架（错题/巩固两示例）
│   └── katex-dist/               # 内置 KaTeX（60 字体 + JS），离线零配置
│       └── MANIFEST.md           # 资源完整性证明（60 字体 + 核心脚本 SHA-256 校验和）
└── references/
    ├── workflow.md               # 7 步工作流 + 荧光笔约定 + 清单兜底
    ├── schema.md                 # 卡片字段 + CHECKS 五维
    ├── formula.md                # 公式约定（<bs> 占位 / wrap_ce / 常见坑）
    └── report.md                 # 7 段报告结构 + 台账格式
```

---

## 🚀 安装（作为 Skill 使用）

**方式 A · 拷贝安装**
将本仓库整体拷到你的 Skill 目录：

- WorkBuddy：`~/.workbuddy/skills/student-wrong-question-diagnosis/`
- Claw/OpenClaw：`~/.openclaw/extensions/` 或对应 skills 目录

**方式 B · Git 克隆**
```bash
git clone <本仓库地址> ~/.workbuddy/skills/student-wrong-question-diagnosis
```

安装后，对一份学生错题扫描件说一句「处理这份错题扫描件」，Skill 即自动触发 7 步出卡 + 报告。

---

## 🛠 单独使用生成器（不用 Skill 框架也行）

```bash
# 离线单文件（断网可用，推荐）
python scripts/generate.py \
    --data cards_data_姓名.py \
    --out 姓名_错题诊断卡.html \
    --name 姓名 --pdf 扫描件.pdf --date 2026-07-25 \
    --offline assets/katex-dist

# 或 CDN 版（需联网看公式，更轻量）
python scripts/generate.py \
    --data cards_data_姓名.py \
    --out 姓名_错题诊断卡.html \
    --name 姓名 --pdf 扫描件.pdf --date 2026-07-25
```

卡片数据格式见 `assets/cards_data_template.py`；公式书写约定见 `references/formula.md`。

---

## 📋 学生极简准备（交给学生的说明书要点）

1. 用**扫描全能王**把错题本 / 卷子扫成 PDF；
2. 用**荧光笔圈出**要整理的题目（圈出 = 错题；蓝笔例题/变式/已订正不用圈）；
3. 给 Buddy 一张小纸条：姓名 / 科目 / 日期 / 文件名，圈不清就列「第几页第几题」；
4. 把扫描 PDF + 本工具箱一起发给自己的 AI 助手即可。

---

## 📌 版本与从 GitHub 更新

版本号以 `SKILL.md` 顶部 frontmatter 的 `version` 字段为准（当前 `version: 1.1.0`）。每次有实质改动时**递增该字段**，并在 [CHANGELOG.md](CHANGELOG.md) 记录本次变更；仓库同时打有对应 git tag（如 `v1.1.0`），可在 GitHub Releases 查看每个版本差异。

**① 从 SkillHub 拉取更新（推荐）**
在 SkillHub 中关联本 GitHub 仓库后，拉取即按 `version` 字段检测新版本并自动覆盖更新，**无需手动下载**。只要 GitHub 上的 `version` 比已安装的高，下次拉取就会更新。

**② 手动更新（git 方式）**
```bash
cd ~/.workbuddy/skills/student-wrong-question-diagnosis
git pull origin main
```
更新后重启 AI 助手会话即可加载新版本。

> 提示：所有改动都先进入 GitHub（本仓库），SkillHub 再从这里拉取——**GitHub 仓库就是唯一的版本发放源**。

---

## 📄 许可

MIT © 李悦超
