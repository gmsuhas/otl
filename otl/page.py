"""One HTML page from a text file. Styling is inlined, so nothing is fetched.

The text is the page. A line that is just `---` starts a new section, and the
next non-empty line is its heading. Everything else is a paragraph, kept as
written, including blank lines inside a fenced block.
"""

from __future__ import annotations

import html


def render_page(title, text, lead=""):
    sections = _sections(text)
    body = "\n".join(_section_html(section) for section in sections)
    lead_html = ""
    if lead:
        lead_html = '<p class="lead">%s</p>\n' % html.escape(lead)
    return _TEMPLATE % {
        "title": html.escape(title),
        "lead": lead_html,
        "body": body,
    }


def _sections(text):
    sections = []
    current = {"heading": "", "blocks": []}
    paragraph = []
    fence = None

    def flush_paragraph():
        if paragraph:
            current["blocks"].append(("p", "\n".join(paragraph)))
            paragraph.clear()

    for line in text.splitlines():
        if fence is not None:
            if line.strip() == fence:
                current["blocks"].append(("pre", "\n".join(paragraph)))
                paragraph.clear()
                fence = None
            else:
                paragraph.append(line)
            continue
        if line.strip() in ("```", "```sh"):
            flush_paragraph()
            fence = line.strip()
            continue
        if line.strip() == "---":
            flush_paragraph()
            if current["heading"] or current["blocks"]:
                sections.append(current)
            current = {"heading": "", "blocks": []}
            continue
        if not line.strip():
            flush_paragraph()
            continue
        if not current["heading"] and not current["blocks"] and not paragraph:
            current["heading"] = line.strip()
            continue
        paragraph.append(line)
    if fence is not None:
        current["blocks"].append(("pre", "\n".join(paragraph)))
    else:
        flush_paragraph()
    if current["heading"] or current["blocks"]:
        sections.append(current)
    return sections


def _section_html(section):
    parts = ["<section>"]
    if section["heading"]:
        parts.append("<h2>%s</h2>" % html.escape(section["heading"]))
    for kind, text in section["blocks"]:
        escaped = html.escape(text)
        if kind == "pre":
            parts.append("<pre>%s</pre>" % escaped)
        else:
            parts.append("<p>%s</p>" % escaped.replace("\n", "<br>\n"))
    parts.append("</section>")
    return "\n".join(parts)


_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<style>
  :root { color-scheme: light; }
  body { margin: 0; font: 18px/1.5 Palatino, "Palatino Linotype", Georgia, serif;
         color: #1c1915; background: #f6f1e7; }
  main { max-width: 40rem; margin: 0 auto; padding: 3rem 1.25rem 4rem; }
  h1 { font-weight: 600; font-size: 2rem; letter-spacing: -0.02em; margin: 0 0 0.4rem; }
  h2 { font-size: 1.15rem; font-weight: 600; margin: 0 0 0.6rem; }
  .lead { color: #5c5346; margin-top: 0; }
  section { margin-top: 1.8rem; }
  p { margin: 0.4rem 0 0.8rem; }
  pre { background: #1c1915; color: #f6f1e7; padding: 0.9rem 1rem; overflow: auto;
        font: 14px/1.45 ui-monospace, "SF Mono", Menlo, Consolas, monospace;
        border-radius: 6px; }
  a { color: #8a3b12; }
</style>
</head>
<body>
<main>
<h1>%(title)s</h1>
%(lead)s%(body)s
</main>
</body>
</html>
"""
