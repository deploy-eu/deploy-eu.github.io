"""Build crawlable static pages from deploy-eu/case-library.

Usage: python3 tools/build_static.py <path-to-case-library-clone>
Writes cases/<author>/<slug>.html, members/<id>.html, sitemap.xml, robots.txt
and the generated part of llms.txt (between the AUTO markers). Run weekly.
"""
import html, json, os, re, sys, datetime, markdown

SITE = "https://deploy-eu.github.io"
REPO = "https://github.com/deploy-eu/case-library/blob/main/"
lib = sys.argv[1]
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def front(text):
    m = re.match(r"^---\n(.*?)\n---\s*(.*)$", text, re.S)
    if not m: return {}, text
    f = {}
    for line in m.group(1).split("\n"):
        k = re.match(r"^(\w+):\s*(.*?)\s*(#.*)?$", line)
        if not k: continue
        v = k.group(2)
        try: v = json.loads(v)
        except Exception: v = v.strip("\"'")
        f[k.group(1)] = v
    return f, m.group(2)

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · Deploy@EU</title><meta name="description" content="{desc}"><link rel="canonical" href="{url}">
<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}"><meta property="og:image" content="{site}/og.png">
<style>body{{margin:0;background:#08090e;color:#c0caf5;font:16px/1.65 system-ui,-apple-system,"Segoe UI",sans-serif}}main{{max-width:760px;margin:0 auto;padding:32px 16px 64px}}
a{{color:#7dcfff}}h1,h2,h3{{color:#eef1ff;line-height:1.25}}h1{{font-size:28px}}table{{border-collapse:collapse;width:100%;display:block;overflow-x:auto}}td,th{{border:1px solid #2f3550;padding:6px 10px;text-align:left}}
pre{{background:#10121a;border:1px solid #232838;padding:12px;overflow-x:auto}}code{{font-family:ui-monospace,Menlo,Consolas,monospace}}blockquote{{border-left:3px solid #bb9af7;margin:0;padding:4px 14px;color:#a9b1d6}}
.top{{font:600 14px ui-monospace,Menlo,monospace;margin-bottom:24px}}.meta{{color:#6b74a0;font-size:14px}}</style></head>
<body><main><div class="top"><a href="{site}/">deploy@eu</a> · <a href="{site}/#{back}">{backlabel}</a></div>
{body}
<p class="meta">Source: <a href="{src}">{src}</a> · Licensed CC BY 4.0</p></main></body></html>"""

urls, cases, members = [f"{SITE}/"], [], []
for dirpath, _, files in os.walk(os.path.join(lib, "cases")):
    for fn in sorted(files):
        if not fn.endswith(".md") or fn.startswith("_") or fn.lower() == "readme.md": continue
        rel = os.path.relpath(os.path.join(dirpath, fn), lib)
        parts = rel.split(os.sep)
        if len(parts) != 3: continue
        f, body = front(open(os.path.join(dirpath, fn), encoding="utf-8").read())
        sm = re.search(r">\s*\*\*Summary[^*]*\*\*\s*(.+)", body)
        desc = re.sub(r"\*\*", "", sm.group(1)) if sm else f.get("title", "")
        meta = " · ".join(str(x) for x in [f.get("status"), f.get("industry"), f.get("country")] if x and "not disclosed" not in str(x))
        authors = ", ".join(f.get("authors", [])) if isinstance(f.get("authors"), list) else str(f.get("authors", ""))
        h = markdown.markdown(body, extensions=["tables", "fenced_code"])
        h = f'<p class="meta">{html.escape(meta)} · by {html.escape(authors)}</p>' + h
        out = os.path.join(root, "cases", parts[1], fn[:-3] + ".html")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        url = f"{SITE}/cases/{parts[1]}/{fn[:-3]}.html"
        open(out, "w", encoding="utf-8").write(PAGE.format(title=html.escape(f.get("title", fn)), desc=html.escape(desc[:300]), url=url, site=SITE, back="cases", backlabel="Cases", body=h, src=REPO + rel.replace(os.sep, "/")))
        urls.append(url); cases.append((f.get("title", fn), url, authors, desc))
mdir = os.path.join(lib, "members")
for fn in sorted(os.listdir(mdir)) if os.path.isdir(mdir) else []:
    if not fn.endswith(".md") or fn.startswith("_"): continue
    f, body = front(open(os.path.join(mdir, fn), encoding="utf-8").read())
    body = re.sub(r"<sub>.*?</sub>", "", body, flags=re.S).strip()
    h = f"<h1>{html.escape(f.get('name', fn))}</h1><p class='meta'>{html.escape(f.get('headline', ''))} · {html.escape(f.get('city', ''))}</p>" + markdown.markdown(body)
    out = os.path.join(root, "members", fn[:-3] + ".html"); os.makedirs(os.path.dirname(out), exist_ok=True)
    url = f"{SITE}/members/{fn[:-3]}.html"
    open(out, "w", encoding="utf-8").write(PAGE.format(title=html.escape(f.get("name", fn)), desc=html.escape(f.get("headline", "")), url=url, site=SITE, back="members", backlabel="Members", body=h, src=REPO + "members/" + fn))
    urls.append(url); members.append((f.get("name", fn), url, f.get("headline", "")))
tools = []
tdir = os.path.join(lib, "tools")
for dirpath, _, files in os.walk(tdir):
    for fn in sorted(files):
        if not fn.endswith(".md") or fn.startswith("_") or fn.lower() == "readme.md" or dirpath == tdir: continue
        f, _b = front(open(os.path.join(dirpath, fn), encoding="utf-8").read())
        tools.append((f.get("name", fn), f.get("repo", ""), ", ".join(f.get("authors", [])) if isinstance(f.get("authors"), list) else str(f.get("authors", "")), f.get("summary", ""), ", ".join(f.get("walls", [])) if isinstance(f.get("walls"), list) else ""))
today = datetime.date.today().isoformat()
open(os.path.join(root, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"<url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls + [f"{SITE}/llms.txt"]) + "</urlset>\n")
open(os.path.join(root, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
p = os.path.join(root, "llms.txt"); t = open(p, encoding="utf-8").read()
auto = f"<!-- AUTO:START (generated {today} from the case library; do not edit by hand) -->\n## Cases ({len(cases)})\n" + "".join(f"- [{c[0]}]({c[1]}) by {c[2]}: {c[3]}\n" for c in cases) + f"\n## Tools ({len(tools)})\n" + "".join(f"- [{x[0]}]({x[1]}) by {x[2]}: {x[3]} (walls: {x[4]})\n" for x in tools) + f"\n## Member profiles ({len(members)})\n" + "".join(f"- [{m[0]}]({m[1]}): {m[2]}\n" for m in members) + "<!-- AUTO:END -->"
t = re.sub(r"<!-- AUTO:START.*?AUTO:END -->", auto, t, flags=re.S) if "AUTO:START" in t else t.rstrip() + "\n\n" + auto + "\n"
open(p, "w", encoding="utf-8").write(t)
print(f"{len(cases)} cases, {len(members)} members, {len(urls)} urls")
