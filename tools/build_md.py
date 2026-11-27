#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""零第三方依赖的 Markdown -> 静态 HTML 构建器。

站点只维护一份 .md 源文件；本脚本在 GitHub Actions 构建时把九份教程
渲染成带目录、表格、代码块与 Mermaid 渐进增强的 HTML 阅读页。
本地亦可运行：python3 tools/build_md.py
"""
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = [
    ("rag-evaluation-tutorial/RAG评测完全教程.md", "RAG 评测完全教程", "rag-evaluation-tutorial/index.html", "RAG / 评测"),
    ("agent-evaluation-tutorial/Agent评测体系完全教程.md", "Agent 评测体系完全教程", "agent-evaluation-tutorial/index.html", "Agent / 评测体系"),
    ("agent-eval-driven-tutorial/Agent评测驱动迭代完全教程.md", "评测驱动 Agent 迭代 · 完全教程", "agent-eval-driven-tutorial/index.html", "Agent / 迭代"),
    ("agent-architecture-tutorial/Agent开发架构选型完全教程.md", "Agent 开发架构选型 · 完全教程", "agent-architecture-tutorial/index.html", "Agent / 架构选型"),
    ("agent-metrics-tutorial/Agent评测指标系统完全教程.md", "Agent 评测指标系统 · 完全教程", "agent-metrics-tutorial/index.html", "Agent / 评测指标"),
    ("agent-eval-method-tutorial/Agent评测方法论完全教程.md", "Agent 评测方法论 · 从 Test 到 Evaluation", "agent-eval-method-tutorial/index.html", "Agent / 评测方法论"),
    ("agent-judge-bias-tutorial/Agent评测偏见消除完全教程.md", "消除 LLM Judge 偏见 · 完全教程", "agent-judge-bias-tutorial/index.html", "Agent / Judge 偏见"),
    ("agent-eval-system-tutorial/Agent评测系统搭建完全教程.md", "从 0 到 1 搭建 Agent 评测系统 · 完全教程", "agent-eval-system-tutorial/index.html", "Agent / 评测系统"),
    ("agent-framework-tutorial/Agent开发框架选型完全教程.md", "LangChain / LangGraph / Deep Agents 框架选型 · 完全教程", "agent-framework-tutorial/index.html", "Agent / 框架选型"),
]

FENCE = re.compile(r"^```([^\s`]*)\s*$")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
LISTITEM = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.+)$")
QUOTE = re.compile(r"^>\s?(.*)$")
HR = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
TABLESEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")


def slug(text):
    """GitHub 风格锚点：保留中英文/数字/空格/连字符，其余标点移除，空格转连字符。"""
    t = re.sub(r"<[^>]+>", "", text).strip().lower()
    t = "".join(c for c in t if c.isalnum() or c in (" ", "-", "_"))
    return t.replace(" ", "-")


class Renderer:
    def __init__(self, text, figures=None):
        self.lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        self.ids = {}
        self.toc = []
        self.figures = list(figures or [])
        self.fig_idx = 0
        self._collect_ids()

    def _collect_ids(self):
        seen = {}
        in_fence = False
        for ln in self.lines:
            if FENCE.match(ln):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            m = HEADING.match(ln)
            if not m:
                continue
            level, title = len(m.group(1)), m.group(2).strip()
            base = slug(title) or "section"
            n = seen.get(base, 0)
            seen[base] = n + 1
            ident = base if n == 0 else f"{base}-{n}"
            self.ids[ident] = True
            if level in (2, 3):
                self.toc.append((level, title, ident))

    def inline(self, s):
        # 白名单标签先行保护（MD 中仅使用 <br/>）
        s = s.replace("<br/>", "\x00BR\x00").replace("<br>", "\x00BR\x00")
        s = html.escape(s, quote=False)
        # 行内代码
        codes = []

        def keep_code(m):
            codes.append(m.group(1))
            return f"\x00CODE{len(codes)-1}\x00"

        s = re.sub(r"`([^`]+)`", keep_code, s)
        # 链接（含目录锚点修正）
        def link(m):
            label, url = m.group(1), m.group(2)
            if url.startswith("#"):
                anchor = url[1:]
                if anchor not in self.ids:
                    guess = slug(label)
                    if guess in self.ids:
                        anchor = guess
                    else:
                        cand = [i for i in self.ids if i.startswith(guess)]
                        if len(cand) == 1:
                            anchor = cand[0]
                url = "#" + anchor
            return f'<a href="{html.escape(url, quote=True)}">{label}</a>'

        s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"<em>\1</em>", s)
        s = re.sub(r"~~([^~]+)~~", r"<del>\1</del>", s)
        s = s.replace("\x00BR\x00", "<br/>")
        for i, c in enumerate(codes):
            s = s.replace(f"\x00CODE{i}\x00", f"<code>{c}</code>")
        return s

    def render_table(self, rows):
        def cells(line):
            line = line.strip()
            if line.startswith("|"):
                line = line[1:]
            if line.endswith("|"):
                line = line[:-1]
            return [c.strip() for c in line.split("|")]

        head = cells(rows[0])
        body = rows[2:] if len(rows) > 2 and TABLESEP.match(rows[1]) else rows[1:]
        out = ['<table><thead><tr>']
        out += [f"<th>{self.inline(c)}</th>" for c in head]
        out.append("</tr></thead><tbody>")
        for r in body:
            cs = cells(r)
            out.append("<tr>" + "".join(f"<td>{self.inline(c)}</td>" for c in cs) + "</tr>")
        out.append("</tbody></table>")
        return "".join(out)

    def render_list(self, items):
        root = []
        stack = [(-1, root)]
        for indent, marker, text in items:
            while len(stack) > 1 and stack[-1][0] >= indent:
                stack.pop()
            node = {"text": text, "children": [], "ordered": marker[-1] in ".)"}
            stack[-1][1].append(node)
            stack.append((indent, node["children"]))

        def build(nodes):
            if not nodes:
                return ""
            tag = "ol" if nodes[0]["ordered"] else "ul"
            out = [f"<{tag}>"]
            for n in nodes:
                out.append("<li>" + self.inline(n["text"]))
                if n["children"]:
                    out.append(build(n["children"]))
                out.append("</li>")
            out.append(f"</{tag}>")
            return "".join(out)

        return build(root)

    def render_blocks(self, lines):
        out = []
        i, n = 0, len(lines)
        while i < n:
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            # 代码围栏
            fm = FENCE.match(line)
            if fm:
                lang = fm.group(1).lower()
                buf = []
                i += 1
                while i < n and not FENCE.match(lines[i]):
                    buf.append(lines[i])
                    i += 1
                i += 1
                code = html.escape("\n".join(buf), quote=False)
                if lang == "mermaid":
                    if self.fig_idx < len(self.figures):
                        fig = self.figures[self.fig_idx]
                        self.fig_idx += 1
                        out.append(
                            fig +
                            '<details class="mermaid-src"><summary>查看 Mermaid 源码</summary>'
                            f'<pre><code class="language-mermaid">{code}</code></pre></details>'
                        )
                        # 复用的 SVG 已自带完整图注，跳过 MD 里紧跟的那行重复图注
                        k = i
                        while k < n and not lines[k].strip():
                            k += 1
                        if k < n and re.match(r"^\*\*图\s*\d+[｜|].*\*\*\s*$", lines[k].strip()):
                            i = k + 1
                    else:
                        out.append(f'<pre class="mermaid">{code}</pre>')
                else:
                    cls = f' class="language-{lang}"' if lang else ""
                    out.append(f"<pre><code{cls}>{code}</code></pre>")
                continue
            # 标题
            hm = HEADING.match(line)
            if hm:
                level, title = len(hm.group(1)), hm.group(2).strip()
                ident = slug(title) or "section"
                if ident not in self.ids:
                    k = 1
                    while f"{ident}-{k}" in self.ids:
                        k += 1
                    # 与 _collect_ids 保持一致：优先使用无后缀版本
                out.append(f'<h{level} id="{html.escape(ident, quote=True)}">{self.inline(title)}</h{level}>')
                i += 1
                continue
            # 分隔线
            if HR.match(line):
                out.append("<hr/>")
                i += 1
                continue
            # 表格
            if line.lstrip().startswith("|") and i + 1 < n and TABLESEP.match(lines[i + 1]):
                rows = []
                while i < n and lines[i].lstrip().startswith("|"):
                    rows.append(lines[i])
                    i += 1
                out.append(self.render_table(rows))
                continue
            # 引用
            if QUOTE.match(line):
                buf = []
                while i < n and QUOTE.match(lines[i]):
                    buf.append(QUOTE.match(lines[i]).group(1))
                    i += 1
                out.append('<blockquote>' + self.render_blocks(buf) + '</blockquote>')
                continue
            # 列表
            if LISTITEM.match(line):
                items = []
                while i < n and LISTITEM.match(lines[i]):
                    m = LISTITEM.match(lines[i])
                    items.append((len(m.group(1)), m.group(2), m.group(3)))
                    i += 1
                out.append(self.render_list(items))
                continue
            # 段落
            buf = []
            while i < n and lines[i].strip() and not FENCE.match(lines[i]) \
                    and not HEADING.match(lines[i]) and not HR.match(lines[i]) \
                    and not QUOTE.match(lines[i]) and not LISTITEM.match(lines[i]) \
                    and not (lines[i].lstrip().startswith("|") and i + 1 < n and TABLESEP.match(lines[i + 1])):
                buf.append(lines[i].strip())
                i += 1
            if buf:
                out.append("<p>" + "<br/>".join(self.inline(b) for b in buf) + "</p>")
            else:
                i += 1
        return "\n".join(out)

    def render(self):
        return self.render_blocks(self.lines)


CSS = r"""
:root{--bg:#f6f7f9;--card:#fff;--ink:#1e2430;--muted:#667085;--line:#e4e7ec;
--brand:#2563eb;--soft:#eff4ff;--code:#111827}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-size:15.5px;line-height:1.85;
 font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",Segoe UI,sans-serif;
 -webkit-font-smoothing:antialiased}
a{color:var(--brand);text-decoration:none}a:hover{text-decoration:underline}
.topbar{position:sticky;top:0;z-index:30;background:rgba(255,255,255,.95);
 backdrop-filter:saturate(180%) blur(10px);border-bottom:1px solid var(--line);
 padding:10px 22px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-size:13px}
.topbar .t{font-weight:800;font-size:14px;margin-right:auto}
.topbar a.btn{border:1px solid #cddcfb;background:#fff;border-radius:7px;padding:5px 11px;font-size:12.5px}
.topbar a.btn:hover{background:var(--soft);text-decoration:none}
.wrap{display:flex;gap:28px;max-width:1400px;margin:0 auto;padding:0 22px}
nav.toc{width:248px;flex:none;position:sticky;top:52px;height:calc(100vh - 52px);overflow-y:auto;
 padding:22px 8px 60px 0;font-size:12.8px}
nav.toc .h{font-weight:800;font-size:13px;margin-bottom:10px;color:#344054}
nav.toc ul{list-style:none;margin:0;padding:0}
nav.toc li{margin:1px 0}
nav.toc a{display:block;padding:4px 9px;border-radius:6px;color:#4a5568}
nav.toc a:hover,nav.toc a.on{background:var(--soft);color:var(--brand);text-decoration:none;font-weight:700}
nav.toc .lv3{padding-left:22px;font-size:12.2px}
main{flex:1;min-width:0;max-width:1000px;padding:28px 0 90px}
article{background:var(--card);border:1px solid var(--line);border-radius:14px;
 padding:30px 36px;box-shadow:0 1px 3px rgba(16,24,40,.04)}
h1{font-size:29px;line-height:1.4;margin:0 0 6px;color:#1b2a4a}
h2{font-size:23px;margin:46px 0 14px;padding-bottom:9px;border-bottom:2px solid var(--brand);color:#1b2a4a}
h3{font-size:18.5px;margin:32px 0 10px;color:#1b2a4a}
h4{font-size:16px;margin:24px 0 8px;color:#344054}
p{margin:11px 0}
ul,ol{padding-left:24px;margin:10px 0}li{margin:4px 0}
blockquote{background:#f8fafc;border-left:4px solid var(--brand);border-radius:0 9px 9px 0;
 margin:14px 0;padding:10px 16px;color:#3b4557}
blockquote p{margin:5px 0}
hr{border:0;border-top:1px solid var(--line);margin:26px 0}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:13.5px;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:8px 11px;text-align:left;vertical-align:top;white-space:normal}
th{background:#f2f5f9;font-weight:700;color:#2b3547;white-space:nowrap}
tr:nth-child(even) td{background:#fbfcfe}
code{background:#f1f4f9;border-radius:4px;padding:1px 5px;font-size:12.8px;color:#1d4ed8;
 font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
pre{background:var(--code);color:#e6edf7;border-radius:11px;padding:16px 18px;overflow:auto;
 font-size:12.6px;line-height:1.72;margin:14px 0}
pre code{background:none;color:inherit;padding:0;font-size:inherit}
pre.mermaid{background:#fbfcff;color:#344054;border:1px dashed #cddcfb;text-align:center;font-size:12px}
.figure{background:#fff;border:1px solid var(--line);border-radius:13px;padding:18px 20px 14px;margin:22px 0}
.figure svg{width:100%;height:auto;display:block}
.figure .cap{font-size:12.8px;color:var(--muted);margin-top:10px;text-align:center}
details.mermaid-src{margin:-14px 0 22px;font-size:12px;color:var(--muted)}
details.mermaid-src summary{cursor:pointer;padding:4px 0}
details.mermaid-src pre{margin:8px 0 0}
.footer{margin-top:34px;padding-top:16px;border-top:1px solid var(--line);color:var(--muted);font-size:12.5px}
@media(max-width:980px){nav.toc{display:none}article{padding:20px}.wrap{padding:0 14px}}
#progress{position:fixed;top:0;left:0;height:3px;width:0;background:linear-gradient(90deg,#2563eb,#39a97a);z-index:120;transition:width .08s linear}
#totop{position:fixed;right:24px;bottom:26px;z-index:110;border:1px solid #cddcfb;background:#fff;color:var(--brand);border-radius:22px;padding:8px 15px;font-size:13px;cursor:pointer;box-shadow:0 3px 12px rgba(16,24,40,.10);display:none}
#totop:hover{background:var(--soft)}
@media print{nav.toc,.topbar{display:none}article{border:0;box-shadow:none}#progress,#totop{display:none!important}}
"""

JS = r"""
<script>
(function(){
  var links = Array.prototype.slice.call(document.querySelectorAll('nav.toc a'));
  var heads = Array.prototype.slice.call(document.querySelectorAll('article h2, article h3'));
  function upd(){
    var cur=null;
    heads.forEach(function(h){ if(h.getBoundingClientRect().top<=140) cur=h.id; });
    links.forEach(function(a){ a.classList.toggle('on', a.getAttribute('href')==='#'+cur); });
  }
  window.addEventListener('scroll',upd,{passive:true}); upd();
})();
</script>
<script>
(function(){
  var prog=document.getElementById('progress'), top=document.getElementById('totop');
  function upd(){
    var doc=document.documentElement;
    var st=window.scrollY||doc.scrollTop||0, max=doc.scrollHeight-doc.clientHeight;
    if(prog) prog.style.width=(max>0?Math.min(100,st/max*100):0)+'%';
    if(top) top.style.display=st>600?'block':'none';
  }
  window.addEventListener('scroll',upd,{passive:true});
  window.addEventListener('resize',upd);
  if(top) top.addEventListener('click',function(){ window.scrollTo({top:0,behavior:'smooth'}); });
  upd();
})();
</script>
"""


def page(title, subtitle, figure_url, md_path, body, toc):
    toc_html = []
    for level, text, ident in toc:
        cls = ' class="lv3"' if level == 3 else ""
        toc_html.append(f'<li{cls}><a href="#{html.escape(ident, quote=True)}">{html.escape(text)}</a></li>')
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} · Markdown 阅读版</title>
<style>{CSS}</style>
<link rel="stylesheet" href="../assets/code-blocks.css">
<script src="../assets/code-blocks.js" defer></script>
<link rel="stylesheet" href="../assets/toc-nav.css">
<script src="../assets/toc-nav.js" defer></script>
</head>
<body>
<div id="progress" aria-hidden="true"></div>
<button id="totop" type="button" aria-label="回到顶部">↑ 回到顶部</button>
<div class="topbar">
  <span class="t">{html.escape(title)} · Markdown 阅读版</span>
  <a class="btn" href="../index.html">← 返回知识库</a>
  <a class="btn" href="{html.escape(figure_url.split('/')[-1])}">图文版（含 SVG 图）</a>
  <a class="btn" href="{html.escape(md_path.name)}" download>下载 .md 原文</a>
</div>
<div class="wrap">
<nav class="toc"><div class="h">本页目录</div><ul>{''.join(toc_html)}</ul></nav>
<main><article>
{body}
<div class="footer">本页由 <code>tools/build_md.py</code> 从 Markdown 源文件自动生成；示意图直接复用<a href="{html.escape(figure_url.split('/')[-1])}">图文阅读版</a>的 SVG，无需外部依赖。展开每图下方可查看 Mermaid 源码。</div>
</article></main>
</div>
{JS}
</body>
</html>
"""


def main():
    FIG_RE = re.compile(
        r'<div class="figure">\s*<svg.*?</svg>\s*<div class="cap">.*?</div>\s*</div>', re.S)
    for rel, title, figure_url, subtitle in TARGETS:
        md = ROOT / rel
        idx = ROOT / figure_url
        figures = FIG_RE.findall(idx.read_text(encoding="utf-8"))
        r = Renderer(md.read_text(encoding="utf-8"), figures)
        body = r.render()
        # 阅读页内互链指向同风格的在线阅读页，而不是图文版
        body = (body
                .replace("../rag-evaluation-tutorial/index.html", "../rag-evaluation-tutorial/RAG评测完全教程.html")
                .replace("../agent-evaluation-tutorial/index.html", "../agent-evaluation-tutorial/Agent评测体系完全教程.html")
                .replace("../agent-eval-driven-tutorial/index.html", "../agent-eval-driven-tutorial/Agent评测驱动迭代完全教程.html")
                .replace("../agent-architecture-tutorial/index.html", "../agent-architecture-tutorial/Agent开发架构选型完全教程.html"))
        out = md.with_suffix(".html")
        out.write_text(page(title, subtitle, figure_url, md, body, r.toc), encoding="utf-8")
        print(f"OK  {md.relative_to(ROOT)}  ->  {out.relative_to(ROOT)}  "
              f"({len(r.toc)} TOC / {r.fig_idx} SVG figures)")


if __name__ == "__main__":
    main()
