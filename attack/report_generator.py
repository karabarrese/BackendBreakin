"""
Generate a polished HTML report from a run logfile (runs/latest.jsonl).

Reads the same JSONL the LogBook writes and renders a clean penetration-test
report: a summary header, a timeline of steps, each agent reasoning block
rendered from markdown, and every tool call with colour-coded, syntax-aware
input/output.

Run after an agent completes:
    python report_generator.py runs/latest.jsonl [out.html]
"""

import html
import json
import re
import sys


# --------------------------------------------------------------------------- #
#  Minimal, dependency-free markdown -> HTML (the agent writes markdown)
# --------------------------------------------------------------------------- #

def _inline(text):
    """Escape HTML, then apply inline markdown: code, bold, italic, links."""
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
                  r'<a href="\2">\1</a>', text)
    return text


def md_to_html(text):
    """Convert a block of markdown to HTML. Handles headings, lists, tables,
    fenced code, blockquotes and paragraphs -- enough for the agent's output."""
    lines = (text or "").split("\n")
    out, i, n = [], 0, len(lines)

    def flush_para(buf):
        if buf:
            out.append("<p>" + "<br>".join(_inline(b) for b in buf) + "</p>")
            buf.clear()

    para = []
    while i < n:
        line = lines[i]
        stripped = line.strip()

        # fenced code block
        if stripped.startswith("```"):
            flush_para(para)
            lang = stripped[3:].strip()
            code = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            cls = " class=\"lang-sql\"" if lang.lower() == "sql" else ""
            out.append(f"<pre class=\"code\"><code{cls}>" +
                       html.escape("\n".join(code)) + "</code></pre>")
            continue

        # table: a line of | ... | followed by a |---| separator
        if "|" in line and i + 1 < n and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]) \
                and "|" in lines[i + 1] and "-" in lines[i + 1]:
            flush_para(para)
            def cells(row):
                row = row.strip().strip("|")
                return [c.strip() for c in row.split("|")]
            header = cells(line)
            i += 2
            body = []
            while i < n and "|" in lines[i] and lines[i].strip():
                body.append(cells(lines[i]))
                i += 1
            t = ["<table><thead><tr>"]
            t += [f"<th>{_inline(c)}</th>" for c in header]
            t.append("</tr></thead><tbody>")
            for row in body:
                t.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row) + "</tr>")
            t.append("</tbody></table>")
            out.append("".join(t))
            continue

        # heading
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_para(para)
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{_inline(m.group(2))}</h{lvl}>")
            i += 1
            continue

        # horizontal rule
        if re.match(r"^(\*\*\*+|---+|___+)$", stripped):
            flush_para(para)
            out.append("<hr>")
            i += 1
            continue

        # blockquote
        if stripped.startswith(">"):
            flush_para(para)
            quote = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            out.append("<blockquote>" + "<br>".join(_inline(q) for q in quote) + "</blockquote>")
            continue

        # unordered list
        if re.match(r"^[-*+]\s+", stripped):
            flush_para(para)
            items = []
            while i < n and re.match(r"^[-*+]\s+", lines[i].strip()):
                items.append(re.sub(r"^[-*+]\s+", "", lines[i].strip()))
                i += 1
            out.append("<ul>" + "".join(f"<li>{_inline(it)}</li>" for it in items) + "</ul>")
            continue

        # ordered list
        if re.match(r"^\d+[.)]\s+", stripped):
            flush_para(para)
            items = []
            while i < n and re.match(r"^\d+[.)]\s+", lines[i].strip()):
                items.append(re.sub(r"^\d+[.)]\s+", "", lines[i].strip()))
                i += 1
            out.append("<ol>" + "".join(f"<li>{_inline(it)}</li>" for it in items) + "</ol>")
            continue

        # blank line = paragraph break
        if not stripped:
            flush_para(para)
            i += 1
            continue

        para.append(stripped)
        i += 1

    flush_para(para)
    return "\n".join(out)


# --------------------------------------------------------------------------- #
#  Log parsing
# --------------------------------------------------------------------------- #

TOOL_META = {
    "recon_nmap":      ("Recon",   "nmap"),
    "http_probe":      ("Web",     "http"),
    "pg_query":        ("Database", "sql"),
    "try_credentials": ("Credentials", "key"),
}


def parse_log(path):
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))

    meta, steps = {}, {}
    tool_calls = 0
    errors = 0
    for e in entries:
        kind = e.get("kind")
        step = e.get("step", -1)
        if kind == "run_start":
            meta = dict(e)
        elif kind == "run_end":
            meta["end_reason"] = e.get("stop_reason")
        elif step >= 0:
            s = steps.setdefault(step, {"reasoning": [], "tools": []})
            if kind == "model_text":
                s["reasoning"].append(e["text"])
            elif kind == "tool_call":
                tool_calls += 1
                s["tools"].append({"name": e["tool"], "input": e["input"], "output": ""})
            elif kind == "tool_result":
                out = e.get("output", "")
                if s["tools"]:
                    s["tools"][-1]["output"] = out
                if _is_error(out):
                    errors += 1
    return meta, steps, {"steps": len(steps), "tool_calls": tool_calls, "errors": errors}


def _is_error(out):
    o = str(out)
    return o.startswith("ERROR") or o.startswith("DB ERROR") or "permission denied" in o


# --------------------------------------------------------------------------- #
#  Rendering
# --------------------------------------------------------------------------- #

CSS = """
:root{
  --bg:#eef1f6; --panel:#ffffff; --ink:#1c2534; --muted:#64748b; --line:#e3e8f0;
  --accent:#4f46e5; --accent-soft:#eef2ff;
  --code-bg:#0f172a; --code-ink:#e2e8f0; --code-key:#7dd3fc; --code-str:#86efac;
  --ok:#0f9d58; --warn:#b45309; --err:#dc2626; --err-soft:#fef2f2;
  --t-recon:#0d9488; --t-web:#7c3aed; --t-db:#2563eb; --t-cred:#d97706;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:960px;margin:0 auto;padding:40px 24px 80px}

header.report{background:linear-gradient(135deg,#1e1b4b,#312e81);color:#fff;
  border-radius:16px;padding:30px 34px;box-shadow:0 10px 30px rgba(49,46,129,.25)}
header.report .eyebrow{text-transform:uppercase;letter-spacing:.14em;font-size:12px;
  font-weight:600;color:#c7d2fe;margin-bottom:6px}
header.report h1{margin:0 0 4px;font-size:26px;letter-spacing:-.01em}
header.report .goal{color:#e0e7ff;font-size:15px;margin-top:10px;
  padding-top:14px;border-top:1px solid rgba(255,255,255,.15)}

.stats{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0 6px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  padding:12px 16px;flex:1;min-width:120px}
.stat .num{font-size:24px;font-weight:700;line-height:1}
.stat .lbl{font-size:12px;color:var(--muted);margin-top:4px;text-transform:uppercase;letter-spacing:.06em}
.pill{display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:600}
.pill.ok{background:#dcfce7;color:var(--ok)} .pill.warn{background:#fef3c7;color:var(--warn)}
.pill.err{background:var(--err-soft);color:var(--err)}

.meta-row{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.chip{background:rgba(255,255,255,.12);color:#e0e7ff;border-radius:8px;
  padding:5px 10px;font-size:12.5px}
.chip b{color:#fff;font-weight:600}

h2.section{font-size:13px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);
  margin:34px 2px 14px}

.step{position:relative;display:flex;gap:18px;margin-bottom:18px}
.rail{flex:0 0 auto;display:flex;flex-direction:column;align-items:center}
.rail .dot{width:32px;height:32px;border-radius:50%;background:var(--accent);color:#fff;
  display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;
  box-shadow:0 2px 6px rgba(79,70,229,.4)}
.rail .line{flex:1;width:2px;background:var(--line);margin-top:4px}
.step:last-child .rail .line{display:none}

.body{flex:1;min-width:0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;
  padding:18px 20px;box-shadow:0 1px 2px rgba(16,24,40,.04)}
.reasoning{font-size:15px}
.reasoning h1,.reasoning h2,.reasoning h3,.reasoning h4{line-height:1.3;margin:16px 0 8px}
.reasoning h1{font-size:20px} .reasoning h2{font-size:17px} .reasoning h3{font-size:15px}
.reasoning p{margin:8px 0}
.reasoning ul,.reasoning ol{margin:8px 0;padding-left:22px}
.reasoning li{margin:3px 0}
.reasoning table{border-collapse:collapse;width:100%;margin:12px 0;font-size:13.5px}
.reasoning th,.reasoning td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}
.reasoning th{background:#f8fafc;font-weight:600}
.reasoning blockquote{margin:10px 0;padding:8px 14px;border-left:3px solid var(--accent);
  background:var(--accent-soft);border-radius:0 8px 8px 0;color:#3730a3}
.reasoning hr{border:0;border-top:1px solid var(--line);margin:16px 0}
.reasoning code{background:#eef2f7;padding:1px 6px;border-radius:5px;font-size:.88em;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.reasoning pre.code{background:var(--code-bg);color:var(--code-ink);padding:14px 16px;
  border-radius:10px;overflow-x:auto;margin:12px 0}
.reasoning pre.code code{background:none;color:inherit;padding:0;font-size:13px}

.tool{margin-top:12px;border:1px solid var(--line);border-radius:12px;overflow:hidden;background:var(--panel)}
.tool-head{display:flex;align-items:center;gap:10px;padding:10px 14px;border-bottom:1px solid var(--line);background:#fbfcfe}
.badge{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;
  color:#fff;border-radius:6px;padding:3px 8px}
.badge.recon{background:var(--t-recon)} .badge.web{background:var(--t-web)}
.badge.db{background:var(--t-db)} .badge.cred{background:var(--t-cred)}
.badge.other{background:var(--muted)}
.tool-name{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px;font-weight:600}
.tool-sub{color:var(--muted);font-size:12.5px;margin-left:auto;font-family:ui-monospace,monospace}
.io{padding:12px 14px}
.io .lbl{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin-bottom:6px}
.io pre{margin:0;background:var(--code-bg);color:var(--code-ink);padding:12px 14px;border-radius:9px;
  overflow-x:auto;font-size:12.5px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;line-height:1.5}
.io pre.result{background:#0b1220}
.io pre.error{background:#2a0f12;color:#fecaca;border:1px solid #7f1d1d}
.io .sqlkw{color:var(--code-key)} .io .sqlstr{color:var(--code-str)}
footer{text-align:center;color:var(--muted);font-size:12px;margin-top:40px}
@media (max-width:620px){.wrap{padding:20px 14px 60px}.step{gap:12px}}
"""

SQL_KEYWORDS = (r"\b(SELECT|FROM|WHERE|INSERT|INTO|VALUES|UPDATE|SET|DELETE|DROP|CREATE|"
                r"TABLE|ROLE|USER|GRANT|REVOKE|ALTER|AND|OR|NOT|NULL|ORDER BY|GROUP BY|"
                r"LIMIT|JOIN|ON|AS|UNION|TRUNCATE|DISTINCT)\b")


def _highlight_sql(sql):
    s = html.escape(sql)
    s = re.sub(r"('[^']*')", r'<span class="sqlstr">\1</span>', s)
    s = re.sub(SQL_KEYWORDS, r'<span class="sqlkw">\1</span>', s, flags=re.I)
    return s


def _badge_class(tool):
    return {"recon_nmap": "recon", "http_probe": "web",
            "pg_query": "db", "try_credentials": "cred"}.get(tool, "other")


def _tool_input_html(tool, inp):
    if tool == "pg_query":
        sub = inp.get("user") or "app_user"
        body = f'<div class="io"><div class="lbl">SQL — as {html.escape(str(sub))}</div>' \
               f'<pre>{_highlight_sql(inp.get("sql",""))}</pre></div>'
        return f'as {html.escape(str(sub))}', body
    if tool == "http_probe":
        method = inp.get("method", "GET")
        path = inp.get("path", "/")
        sub = f"{method} {path}"
        lines = f"{method} {path}"
        if inp.get("body"):
            lines += "\n\n" + inp["body"]
        return sub, f'<div class="io"><div class="lbl">Request</div><pre>{html.escape(lines)}</pre></div>'
    if tool == "recon_nmap":
        sub = inp.get("ports", "")
        return f"ports {sub}", f'<div class="io"><div class="lbl">Input</div><pre>{html.escape(json.dumps(inp))}</pre></div>'
    # generic
    return "", f'<div class="io"><div class="lbl">Input</div><pre>{html.escape(json.dumps(inp, indent=2))}</pre></div>'


def _tool_output_html(out):
    if not out:
        return ""
    cls = "result error" if _is_error(out) else "result"
    text = str(out)
    if len(text) > 4000:
        text = text[:4000] + "\n… (truncated)"
    return f'<div class="io"><div class="lbl">Result</div><pre class="{cls}">{html.escape(text)}</pre></div>'


def _status_pill(reason):
    if reason == "end_turn":
        return '<span class="pill ok">Completed</span>'
    if reason in ("max_steps", "tool_use"):
        return '<span class="pill warn">Hit step limit</span>'
    if reason == "error":
        return '<span class="pill err">Error</span>'
    return f'<span class="pill warn">{html.escape(str(reason))}</span>'


def generate_html_report(logbook_path, output_path=None):
    if output_path is None:
        output_path = logbook_path.replace(".jsonl", ".html")
    meta, steps, stats = parse_log(logbook_path)

    chips = "".join(
        f'<span class="chip"><b>{k}:</b> {html.escape(str(meta.get(v,"N/A")))}</span>'
        for k, v in [("Target", "target"), ("Model", "model")]
    )
    head = f"""
    <header class="report">
      <div class="eyebrow">Breach Lab · Penetration Test Report</div>
      <h1>Agent Run Summary</h1>
      <div class="meta-row">{chips}</div>
      <div class="goal"><b>Goal:</b> {html.escape(str(meta.get('goal','N/A')))}</div>
    </header>
    <div class="stats">
      <div class="stat"><div class="num">{stats['steps']}</div><div class="lbl">Steps</div></div>
      <div class="stat"><div class="num">{stats['tool_calls']}</div><div class="lbl">Tool calls</div></div>
      <div class="stat"><div class="num">{stats['errors']}</div><div class="lbl">Denied / errors</div></div>
      <div class="stat"><div class="num" style="font-size:16px;padding-top:4px">{_status_pill(meta.get('end_reason'))}</div><div class="lbl">Result</div></div>
    </div>
    """

    body = ['<h2 class="section">Timeline</h2>']
    for num in sorted(steps):
        s = steps[num]
        reasoning = "".join(f'<div class="reasoning">{md_to_html(r)}</div>' for r in s["reasoning"])
        tools_html = ""
        for t in s["tools"]:
            bclass = _badge_class(t["name"])
            label, inp_html = _tool_input_html(t["name"], t["input"] if isinstance(t["input"], dict) else {})
            out_html = _tool_output_html(t["output"])
            tools_html += f"""
            <div class="tool">
              <div class="tool-head">
                <span class="badge {bclass}">{html.escape(t['name'])}</span>
                <span class="tool-name">{html.escape(t['name'])}</span>
                <span class="tool-sub">{html.escape(label)}</span>
              </div>
              {inp_html}{out_html}
            </div>"""
        card = f'<div class="card">{reasoning or "<p class=\'tool-sub\'>(tool step)</p>"}{tools_html}</div>'
        body.append(f'<div class="step"><div class="rail"><div class="dot">{num}</div>'
                    f'<div class="line"></div></div><div class="body">{card}</div></div>')

    htmldoc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Breach Lab Report</title><style>{CSS}</style></head>
<body><div class="wrap">{head}{''.join(body)}
<footer>Generated by the Breach Lab agent · report_generator.py</footer>
</div></body></html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(htmldoc)
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python report_generator.py <logbook.jsonl> [output.html]")
        sys.exit(1)
    out = generate_html_report(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(f"Report generated: {out}")
