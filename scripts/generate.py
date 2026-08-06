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


def tex(s):
    return wrap_ce(s.replace("<bs>", BS))


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

    return f"""  <section class="card">
    <h2><span class="num">{no}</span> {title}<span class="{kind_cls}">{kind_text}</span></h2>
    <div class="origin">
      <b>【原题】</b> {origin}
      <span class="src">来源：{page}</span>
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


def build_cdn(data_mod, out_html, student_name, pdf_name, date_str):
    cards_html = "\n".join(render_card(c, data_mod.CHECKS) for c in data_mod.CARDS)
    wrong_count = sum(1 for c in data_mod.CARDS if c["kind"] == "错题")
    total = len(data_mod.CARDS)

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
        f'  <p class="doc-meta">日期：{date_str} ｜ 扫描源：{pdf_name} ｜ '
        f'荧光笔圈出共：<b>{total} 道</b>（错题 {wrong_count} 道，巩固 {total-wrong_count} 道）</p>\n'
        f"{cards_html}"
        f'  <p class="foot">生成时间：{date_str} · 按页码与知识点排序 · 荧光笔圈出全部并入</p>\n'
        '</div>\n</body>\n</html>\n'
    )
    out_path = pathlib.Path(out_html)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_doc, encoding="utf-8")
    print(f"CDN_HTML written: {out_path} ({len(html_doc)} bytes)")
    return out_path


# ---------- 离线嵌入（移植自 rebuild_offline.py，DIST 改为参数） ----------

def inline_fonts(css, fonts_dir):
    bs = chr(92)
    qt = chr(39)
    dq = chr(34)
    url_pat = ("url" + bs + "(" + "([" + qt + dq + "]?)" + "(" + "fonts/[^"
               + qt + dq + ")]+" + ")" + bs + "1" + bs + ")")

    def repl(m):
        rel = m.group(2)
        p = fonts_dir / pathlib.Path(rel).name
        if not p.is_file():
            raise SkillError(
                f"离线字体缺失：{rel}\n"
                f"请确认 katex-dist/fonts/ 完整（应含 60 个字体文件，"
                f"参考 assets/MANIFEST.md 校验）。"
            )
        data = p.read_bytes()
        b64 = base64.b64encode(data).decode()
        return "url(data:font/woff2;base64," + b64 + ")"

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
    ensure_katex_dist(dist_dir)
    dist = pathlib.Path(dist_dir)
    if not dist.is_dir():
        raise SkillError(
            f"离线资源目录不存在：{dist_dir}\n"
            f"请确认 --offline 指向 KaTeX 的 dist 目录"
            f"（需含 katex.min.css、katex.min.js、fonts/）。"
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
    fonts_dir = dist / "fonts"
    if not fonts_dir.is_dir() or len(list(fonts_dir.glob("*.woff2"))) == 0:
        raise SkillError(
            "离线字体目录 fonts/ 不存在或没有 .woff2 字体，无法内联公式。\n"
            "请确认 katex-dist/fonts/ 完整（详见 assets/MANIFEST.md）。"
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

    katex_css = inline_fonts((dist / "katex.min.css").read_text(encoding="utf-8"), fonts_dir)
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
        out_path = build_cdn(mod, args.out, args.name, args.pdf, args.date)
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
