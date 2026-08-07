#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""学生错题诊断卡生成器（便携版，单文件，不依赖任何工作区路径）。

用法：
  python generate.py --data cards_data_xxx.py --out 诊断卡.html \
      --name 姓名 --pdf 扫描件.pdf --date 2026-07-25 \
      [--offline <katex-dist 目录>]

  --data   卡片数据模块（.py 文件，需定义 CARDS 与 CHECKS，字段见 HANDOFF.md §3）
  --out    输出 HTML 路径
  --name   学生姓名（用于标题）
  --pdf    源 PDF 文件名（仅用于元信息展示）
  --date   日期（默认 2026-07-25）
  --offline 可选。传入 KaTeX 的 dist 目录（含 katex.min.css/js、contrib/、fonts/）后，
           会把字体与 JS 全部 base64 内联，生成「完全离线、单文件」的 HTML（断网也能渲染公式）。

不传 --offline 时，HTML 通过 jsDelivr CDN 加载 KaTeX，需联网查看公式。
字段结构与李老师既有流水线（build_from_data.py / rebuild_offline.py）完全一致。
"""
import argparse
import importlib.util
import pathlib
import re
import base64
import sys
import json
import urllib.request

BS = chr(92)  # 反斜杠

# 离线字体来源：当本地 katex-dist 缺失时，从 GitHub 仓库自动拉取（一次性联网）。
# 这样即便 SkillHub CLI 拉取时剔除了嵌套的 assets/katex-dist/ 子目录，
# 生成离线卡时也能自动补齐字体，保证「拉取后开箱即用」。
GITHUB_REPO = "liyuechao2018/student-wrong-question-diagnosis"
GITHUB_BRANCH = "main"
KATEX_DIST_PREFIX = "assets/katex-dist"


class SkillError(Exception):
    """业务层面错误，携带可理解的中文说明，避免向用户抛出英文 traceback。"""


STYLE = """
html{color-scheme:light}
:root{
  --bg:#f5f6f8; --card:#ffffff; --ink:#1f2329; --sub:#5b6168;
  --line:#e6e8eb; --brand:#2f6fed; --brand-soft:#eaf1ff;
  --tag:#eef2f7; --warn:#c0392b; --ok:#0f9d58;
}
*{box-sizing:border-box}
body{margin:0;background:#f5f6f8;color:#1f2329;
  font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
  line-height:1.65;padding:24px}
.wrap{max-width:860px;margin:0 auto}
.doc-title{font-size:24px;font-weight:700;margin:0 0 4px}
.doc-meta{color:var(--sub);font-size:13px;margin:0 0 18px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;
  padding:18px 20px;margin:0 0 16px;box-shadow:0 1px 3px rgba(0,0,0,.04)}
.card h2{font-size:16px;margin:0 0 10px;display:flex;align-items:center;gap:8px}
.card h2 .num{background:var(--brand);color:#fff;font-size:12px;
  padding:2px 9px;border-radius:999px}
.card h2 .kind{font-size:11px;color:#fff;background:var(--ok);padding:1px 7px;border-radius:999px}
.card h2 .kind.wrong{background:var(--warn)}
.origin{background:var(--brand-soft);border-radius:10px;padding:9px 13px;
  font-size:13.5px;margin-bottom:12px}
.origin .src{color:var(--sub);font-size:11.5px;display:block;margin-top:3px}
.blk{margin:0 0 11px}
.blk .lab{font-weight:700;color:var(--brand);font-size:13px;margin-bottom:3px}
.blk .body{font-size:13.5px}
.steps{display:flex;flex-wrap:wrap;gap:6px;margin-top:5px}
.step{background:var(--brand-soft);color:var(--brand);border-radius:999px;
  padding:3px 10px;font-size:12px}
.checks{display:flex;flex-wrap:wrap;gap:8px 16px;margin-top:5px;font-size:13px}
.action{background:var(--tag);border-radius:10px;padding:8px 12px;font-size:13px}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.tag{background:var(--tag);border-radius:8px;padding:3px 9px;font-size:12px;color:var(--sub)}
.tag b{color:var(--ink)}
.blank{border-bottom:1px dashed var(--sub);min-width:80px;display:inline-block}
.foot{color:var(--sub);font-size:12px;text-align:center;margin-top:10px}
@media print{
  body{background:#fff;padding:0}
  .card{box-shadow:none;break-inside:avoid;margin:0 0 12px}
  .doc-meta{display:none}
}
"""


def wrap_ce(s):
    """把裸的 \\ce{...}（平衡花括号）包进 \\( ... \\)，让 KaTeX auto-render 渲染化学公式；
    已处于 \\( ... \\) 内的 \\ce 不重复包裹。"""
    out = []
    i = 0
    n = len(s)
    in_math = False
    while i < n:
        if not in_math and s[i:i + 4] == BS + "ce{":
            depth = 0
            p = i + 3
            while p < n:
                if s[p] == "{":
                    depth += 1
                elif s[p] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                p += 1
            out.append(BS + "(" + s[i:p + 1] + BS + ")")
            i = p + 1
            continue
        if s[i:i + 2] == BS + "(":
            in_math = True
            out.append(s[i:i + 2]); i += 2; continue
        if s[i:i + 2] == BS + ")":
            in_math = False
            out.append(s[i:i + 2]); i += 2; continue
        out.append(s[i]); i += 1
    return "".join(out)


# KaTeX 不直接认这些 Unicode 数学符号（如 ∈、Δ、⇒、≤），学生容易直接
# 粘贴过来导致公式解析失败。tex() 在还原 <bs> 之后，会对所有 \(...\) 和
# $$...$$ 公式块内的 Unicode 自动转 LaTeX 命令，做到"写错了也能渲"。
_UNICODE_TO_LATEX = {
    # 集合 / 关系
    "∈": r" \in ", "∉": r" \notin ",
    "⊂": r" \subset ", "⊆": r" \subseteq ",
    "⊃": r" \supset ", "⊇": r" \supseteq ",
    "∪": r" \cup ", "∩": r" \cap ", "∅": r" \emptyset ",
    # 箭头
    "⇒": r" \Rightarrow ", "⇐": r" \Leftarrow ", "⇔": r" \Leftrightarrow ",
    "→": r" \to ", "←": r" \leftarrow ", "↔": r" \leftrightarrow ",
    "↦": r" \mapsto ",
    # 不等 / 序
    "≤": r" \leq ", "≥": r" \geq ", "≠": r" \neq ",
    "≪": r" \ll ", "≫": r" \gg ", "≺": r" \prec ", "≻": r" \succ ",
    # 希腊大写（KaTeX 认 \Delta 但不认 Unicode）
    "Δ": r" \Delta ", "Σ": r" \Sigma ", "Π": r" \Pi ", "Ω": r" \Omega ",
    "Θ": r" \Theta ", "Λ": r" \Lambda ", "Φ": r" \Phi ", "Ψ": r" \Psi ",
    # 希腊小写
    "α": r" \alpha ", "β": r" \beta ", "γ": r" \gamma ", "δ": r" \delta ",
    "ε": r" \epsilon ", "ζ": r" \zeta ", "η": r" \eta ",
    "θ": r" \theta ", "ι": r" \iota ", "κ": r" \kappa ",
    "λ": r" \lambda ", "μ": r" \mu ", "ν": r" \nu ",
    "ξ": r" \xi ", "π": r" \pi ", "ρ": r" \rho ",
    "σ": r" \sigma ", "τ": r" \tau ", "φ": r" \phi ", "χ": r" \chi ",
    "ψ": r" \psi ", "ω": r" \omega ",
    # 算子
    "∞": r" \infty ", "∂": r" \partial ",
    "±": r" \pm ", "∓": r" \mp ",
    "×": r" \times ", "÷": r" \div ", "·": r" \cdot ",
    "√": r" \sqrt{} ",
    "∑": r" \sum ", "∏": r" \prod ", "∫": r" \int ", "∮": r" \oint ",
    "∮": r" \oint ",
    # 其他
    "≈": r" \approx ", "≡": r" \equiv ", "≅": r" \cong ",
    "∝": r" \propto ", "⊥": r" \perp ", "∥": r" \parallel ",
    "∠": r" \angle ", "∴": r" \therefore ", "∵": r" \because ",
    # 中文括号/全角标点在公式里换成 ASCII，避免 KaTeX 报错
    "（": r"(", "）": r")",
    "，": r",\ ", "；": r";\ ", "：": r":\ ",
}


def _latex_unicode_fix(s):
    """对单段文本中的 Unicode 数学符号做 LaTeX 命令替换。"""
    out = s
    for k, v in _UNICODE_TO_LATEX.items():
        out = out.replace(k, v)
    return out


def _fix_math_blocks(s):
    """仅在 \\( ... \\) 与 $$ ... $$ 公式块内做 Unicode → LaTeX 兜底；
    块外的中文/全角标点/换行保持原样不被污染。"""
    def repl_inline(m):
        return _latex_unicode_fix(m.group(0))
    s = re.sub(r"\\\([\s\S]*?\\\)", repl_inline, s)
    s = re.sub(r"\$\$[\s\S]*?\$\$", repl_inline, s)
    return s


def tex(s):
    """还原 <bs> 为 \\，对公式块内 Unicode 数学符号做 LaTeX 兜底，
    再把裸的 \\ce{...}（化学式）自动包进 \\(...\\) 供 KaTeX 渲染。"""
    if s is None:
        return ""
    s = s.replace("<bs>", BS)
    s = _fix_math_blocks(s)
    return wrap_ce(s)


def render_card(item, checks):
    no = item["no"]
    title = tex(item["title"])
    page = item["page"]
    kind = item["kind"]
    origin = tex(item["origin"])
    ability = tex(item["ability"])
    one = tex(item["one"])
    action = tex(item["action"])
    tags = item.get("tags", [])
    checked = set(item.get("checked", []))
    mark = item.get("mark", "")

    kind_cls = "kind wrong" if kind == "错题" else "kind"
    kind_text = "错题" if kind == "错题" else "巩固"

    checks_html = []
    for i, label in enumerate(checks):
        symbol = "☑" if i in checked else "☐"
        checks_html.append(f"<span>{symbol} {label}</span>")
    checks_html = "".join(checks_html)

    if kind == "错题":
        mistake = tex(item["mistake"])
        mistake_html = f'<div class="body">我的主要问题：{mistake}</div>'
    else:
        mistake_html = (
            '<div class="body">本题为课堂例题/变式/已订正，蓝标为老师强调重点，原无实际错误，'
            '并入本卡用于巩固。</div>'
        )

    tags_html = "".join(f'<span class="tag"><b>{k}</b> {v}</span>' for k, v in tags)

    mark_html = f" ｜ 选取：{mark}" if mark else ""

    return f"""  <section class="card">
    <h2><span class="num">{no}</span> {title}<span class="{kind_cls}">{kind_text}</span></h2>
    <div class="origin">
      <b>【原题】</b> {origin}
      <span class="src">来源：{page}{mark_html}</span>
    </div>
    <div class="blk"><div class="lab">① 这题考什么？</div>
      <div class="body">知识点：{title}；核心能力：{ability}。</div>
    </div>
    <div class="blk"><div class="lab">② 正确思路</div>
      <div class="body">一句话：{one}</div>
    </div>
    <div class="blk"><div class="lab">③ 我为什么错？</div>
      <div class="checks">{checks_html}</div>
      {mistake_html}
    </div>
    <div class="blk"><div class="lab">④ 下次怎么避免？</div>
      <div class="action">{action}</div>
    </div>
    <div class="blk"><div class="lab">错题标签</div>
      <div class="tags">{tags_html}</div>
    </div>
  </section>
"""


def build_cdn(data_mod, out_html, student_name, pdf_name, date_str, select_method=None):
    cards_html = "\n".join(render_card(c, data_mod.CHECKS) for c in data_mod.CARDS)
    wrong_count = sum(1 for c in data_mod.CARDS if c["kind"] == "错题")
    total = len(data_mod.CARDS)
    cons = total - wrong_count
    method_text = f" ｜ 选取方式：{select_method}" if select_method else ""

    html_doc = (
        '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f'<title>{student_name} · 错题诊断卡（完整版）</title>\n'
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">\n'
        '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>\n'
        '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"\n'
        '  onload="renderMathInElement(document.body,{delimiters:[{left:&#39;\\\\(&#39;,right:&#39;\\\\)&#39;,display:false},{left:&#39;$$&#39;,right:&#39;$$&#39;,display:true}],throwOnError:false});"></script>\n'
        f"<style>\n{STYLE}\n</style>\n"
        '</head>\n<body>\n<div class="wrap">\n'
        f'  <h1 class="doc-title">错题诊断卡 · {student_name}（完整版）</h1>\n'
        f'  <p class="doc-meta">日期：{date_str} ｜ 扫描源：{pdf_name}{method_text} ｜ '
        f'共 <b>{total} 道</b>（错题 {wrong_count} 道，巩固 {cons} 道）</p>\n'
        f"{cards_html}"
        f'  <p class="foot">生成时间：{date_str} · 按页码与知识点排序</p>\n'
        '</div>\n</body>\n</html>\n'
    )
    out_path = pathlib.Path(out_html)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_doc, encoding="utf-8")
    print(f"CDN_HTML written: {out_path} ({len(html_doc)} bytes)")
    return out_path


# ---------- 离线嵌入（移植自 rebuild_offline.py，DIST 改为参数） ----------

def load_font_b64_map(dist):
    """收集离线字体 base64：优先目录里的 .woff2，再用 fonts_b64.json 补充。

    SkillHub 等平台禁止上传字体二进制（.ttf/.woff/.woff2），因此发布时把
    字体以 base64 形式存入 fonts_b64.json（.json 为平台允许类型），离线生成
    时从此处内联，实现「零字体文件、完全离线」。目录里若有真实 .woff2 也兼容。
    """
    dist = pathlib.Path(dist)
    b64_map = {}
    fonts_dir = dist / "fonts"
    if fonts_dir.is_dir():
        for f in fonts_dir.glob("*.woff2"):
            b64_map[f.name] = base64.b64encode(f.read_bytes()).decode()
    json_path = dist / "fonts_b64.json"
    if json_path.is_file():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            for k, v in data.items():
                if k not in b64_map:
                    b64_map[k] = v
        except Exception:
            pass  # 损坏的 json 忽略，交给后续兜底
    return b64_map


def inline_fonts(css, b64_map):
    bs = chr(92)
    qt = chr(39)
    dq = chr(34)
    # 仅内联 .woff2（离线 HTML 只需 woff2，现代浏览器均支持；woff/ttf 作为
    # 不存在的 fallback 会被浏览器忽略，不影响渲染）。
    url_pat = ("url" + bs + "(" + "([" + qt + dq + "]?)" + "(" + "fonts/[^"
               + qt + dq + "]*?" + bs + ".woff2)" + bs + "1" + bs + ")")

    def repl(m):
        rel = m.group(2)
        name = pathlib.Path(rel).name
        if name not in b64_map:
            raise SkillError(
                f"离线字体缺失：{rel}\n"
                f"请确认存在 fonts_b64.json（含 20 个 woff2 base64）或完整的 fonts/ 目录。"
            )
        return "url(data:font/woff2;base64," + b64_map[name] + ")"

    return re.sub(url_pat, repl, css)


def _download_katex_dist(dist):
    """从 GitHub 仓库递归拉取 katex-dist 目录（一次性联网）。"""
    api = (f"https://api.github.com/repos/{GITHUB_REPO}/git/trees/"
           f"{GITHUB_BRANCH}?recursive=1")
    req = urllib.request.Request(api, headers={"User-Agent": "skill-generate"})
    with urllib.request.urlopen(req, timeout=30) as r:
        tree = json.load(r)
    prefix = KATEX_DIST_PREFIX + "/"
    files = [t["path"] for t in tree.get("tree", [])
             if t.get("type") == "blob" and t["path"].startswith(prefix)]
    if not files:
        raise RuntimeError("GitHub 仓库中未找到 katex-dist 文件")
    dist.mkdir(parents=True, exist_ok=True)
    for rel in files:
        sub = rel[len(prefix):]          # 相对 katex-dist 的路径
        target = dist / sub
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = (f"https://raw.githubusercontent.com/{GITHUB_REPO}/"
               f"{GITHUB_BRANCH}/{rel}")
        req2 = urllib.request.Request(raw, headers={"User-Agent": "skill-generate"})
        with urllib.request.urlopen(req2, timeout=60) as rr:
            target.write_bytes(rr.read())
    return len(files)


def ensure_katex_dist(dist_dir):
    """确保离线所需的 katex-dist 存在且完整；缺失则自动从 GitHub 拉取。"""
    dist = pathlib.Path(dist_dir)
    complete = (
        dist.is_dir()
        and (dist / "katex.min.css").is_file()
        and (dist / "fonts").is_dir()
        and len(list((dist / "fonts").glob("*.woff2"))) > 0
    )
    if complete:
        return  # 已存在且完整 → 纯离线，无需联网
    print("⚠️ 本地未找到完整的 katex-dist，正在从 GitHub 仓库自动获取"
          f"（{GITHUB_REPO}，需联网一次）…", file=sys.stderr)
    try:
        n = _download_katex_dist(dist)
    except Exception as e:
        raise SkillError(
            f"离线资源目录缺失，且自动从 GitHub 获取失败：{e}\n"
            f"请手动获取后重试：\n"
            f"  git clone https://github.com/{GITHUB_REPO}.git _katex_tmp\n"
            f"  再将 --offline 指向 _katex_tmp/{KATEX_DIST_PREFIX}"
        )
    print(f"✔ 已从 GitHub 获取 katex-dist（{n} 个文件）到 {dist}",
          file=sys.stderr)


def rebuild_offline(raw_path, dist_dir):
    dist = pathlib.Path(dist_dir)
    if not dist.is_dir():
        raise SkillError(
            f"离线资源目录不存在：{dist_dir}\n"
            f"请确认 --offline 指向 KaTeX 的 dist 目录"
            f"（需含 katex.min.css、katex.min.js、fonts_b64.json 或 fonts/）。"
        )
    missing = [
        r for r in ("katex.min.css", "katex.min.js",
                    "contrib/auto-render.min.js", "contrib/mhchem.min.js")
        if not (dist / r).is_file()
    ]
    if missing:
        raise SkillError(
            "离线资源不完整，缺少以下文件：\n  " + "\n  ".join(missing) + "\n"
            "请确认 --offline 指向完整的 katex-dist 目录。"
        )
    # 优先从 fonts_b64.json / 目录收集字体 base64；都为空才走 GitHub 联网兜底
    b64_map = load_font_b64_map(dist)
    if not b64_map:
        ensure_katex_dist(dist_dir)
        b64_map = load_font_b64_map(dist)
    if not b64_map:
        raise SkillError(
            "离线字体缺失，且自动从 GitHub 获取失败。\n"
            "请确认 katex-dist 含 fonts_b64.json（20 个 woff2 base64）或完整 fonts/ 目录。"
        )
    bs = chr(92)
    qt = chr(39)
    dq = chr(34)

    raw = raw_path.read_text(encoding="utf-8")
    title_m = re.search("<title>(.*?)</title>", raw, re.S)
    title = title_m.group(1).strip() if title_m else "错题诊断卡"

    body_m = re.search("<body>(.*)</body>", raw, re.S)
    body_inner = body_m.group(1) if body_m else ""
    body_inner = re.sub("<script[" + bs + "s" + bs + "S]*?</script>", "", body_inner).strip()

    styles = re.findall("<style>[" + bs + "s" + bs + "S]*?</style>", raw)
    orig_style = next((s for s in styles if "@font-face" not in s), "")

    katex_css = inline_fonts((dist / "katex.min.css").read_text(encoding="utf-8"), b64_map)
    katex_js = (dist / "katex.min.js").read_text(encoding="utf-8").replace(
        "</script>", "<" + bs + "/script>")
    mhchem_js = (dist / "contrib" / "mhchem.min.js").read_text(
        encoding="utf-8").replace("</script>", "<" + bs + "/script>")
    ar_js = (dist / "contrib" / "auto-render.min.js").read_text(
        encoding="utf-8").replace("</script>", "<" + bs + "/script>")

    render = ("<script>" + katex_js + "</script>\n<script>" + mhchem_js
              + "</script>\n<script>" + ar_js + "</script>\n"
              + "<script>renderMathInElement(document.body,{delimiters:[{left:"
              + dq + bs + bs + "(" + dq + ",right:" + dq + bs + bs + ")" + dq
              + ",display:false},{left:" + dq + "$$" + dq + ",right:" + dq + "$$"
              + dq + ",display:true}],throwOnError:false});</script>")

    new_html = ("<!DOCTYPE html>\n<html lang=" + dq + "zh-CN" + dq + ">\n<head>\n"
                "<meta charset=" + dq + "UTF-8" + dq + ">\n"
                "<meta name=" + dq + "viewport" + dq + " content=" + dq
                + "width=device-width, initial-scale=1.0" + dq + ">\n"
                + "<title>" + title + "</title>\n"
                + "<style>\n" + orig_style + "\n</style>\n"
                + "<style>\n" + katex_css + "\n</style>\n"
                + "</head>\n<body>\n" + body_inner + "\n" + render
                + "\n</body>\n</html>\n")
    raw_path.write_text(new_html, encoding="utf-8")
    print("OFFLINE_OK " + raw_path.name + " -> " + str(len(new_html))
          + " bytes; cards=" + str(len(body_inner))
          + "; base64_fonts=" + str(new_html.count("data:font/woff2;base64")))


def load_module(py_path):
    p = pathlib.Path(py_path)
    if not p.is_file():
        raise SkillError(
            f"找不到数据文件：{py_path}\n"
            f"请检查 --data 参数指向的 .py 文件是否存在、路径是否正确。"
        )
    try:
        spec = importlib.util.spec_from_file_location("cards_data_user", str(p))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except SyntaxError as e:
        raise SkillError(
            f"数据文件存在语法错误：{p.name}\n"
            f"第 {e.lineno} 行附近：{e.msg}\n"
            f"请检查卡片数据里的引号、括号、多行字符串是否成对。"
        )
    except SkillError:
        raise
    except Exception as e:
        raise SkillError(
            f"加载数据文件失败：{p.name}\n原因：{e}\n"
            f"请确认该文件是标准的 cards_data 模块（需定义 CARDS 列表与 CHECKS 列表）。"
        )
    return mod


def parse_args():
    parser = argparse.ArgumentParser(description="生成学生错题诊断卡 HTML（便携版）")
    parser.add_argument("--data", required=True, help="cards_data 模块路径（.py）")
    parser.add_argument("--out", required=True, help="输出 HTML 路径")
    parser.add_argument("--name", required=True, help="学生姓名，用于标题")
    parser.add_argument("--pdf", required=True, help="源 PDF 文件名，用于元信息")
    parser.add_argument("--date", default="2026-07-25", help="日期")
    parser.add_argument("--offline", default=None,
                        help="KaTeX dist 目录（含 katex.min.css/js、contrib/、fonts/），"
                             "传入则生成完全离线单文件")
    return parser.parse_args()


def do_generate(args):
    mod = load_module(args.data)
    if not hasattr(mod, "CARDS"):
        raise SkillError(
            "数据文件缺少 CARDS 列表。\n"
            "请按 assets/cards_data_template.py 模板，定义每张卡片的字典列表 CARDS。"
        )
    if not hasattr(mod, "CHECKS"):
        raise SkillError(
            "数据文件缺少 CHECKS 列表。\n"
            "请定义错误归因维度 CHECKS（如：知识没掌握 / 方法没想到 /"
            "思维不完整 / 计算失误 / 审题问题）。"
        )
    try:
        select_method = getattr(mod, "SELECT_METHOD", None)
        out_path = build_cdn(mod, args.out, args.name, args.pdf, args.date, select_method)
    except OSError as e:
        raise SkillError(
            f"写入输出文件失败：{args.out}\n原因：{e}\n"
            f"请检查输出目录是否存在、是否有写入权限。"
        )
    if args.offline:
        rebuild_offline(out_path, args.offline)
    else:
        print("OFFLINE skipped (CDN mode). 传入 --offline <katex-dist> 可生成离线版。")


def main():
    args = parse_args()  # 参数解析失败由 argparse 自动给出友好提示
    try:
        do_generate(args)
    except SkillError as e:
        print("\n❌ 生成失败：", file=sys.stderr)
        print(str(e), file=sys.stderr)
        sys.exit(2)
    except FileNotFoundError as e:
        print(f"\n❌ 找不到文件：{getattr(e, 'filename', e)}", file=sys.stderr)
        print("请检查相关路径是否正确。", file=sys.stderr)
        sys.exit(2)
    except KeyboardInterrupt:
        print("\n已取消。", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 生成过程中出现意外错误：{e}", file=sys.stderr)
        print("如无法自行解决，请检查卡片数据格式或参考 references/ 下的说明。",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
