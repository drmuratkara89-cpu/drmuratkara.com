from pathlib import Path
import re, html, xml.etree.ElementTree as ET
from collections import defaultdict
from urllib.parse import urlparse

root = Path(__file__).resolve().parents[1]
files = sorted(root.glob("*.html"))
excluded = {"404.html", "gizlilik.html", "aydinlatma.html"}
priority = {
    "dudak-dolgusu.html": ("Dudak Dolgusu", True),
    "ilk-kez-dudak-dolgusu.html": ("Dudak Dolgusu", False),
    "dudak-dolgusu-sonrasi-sislik-iyilesme.html": ("Dudak Dolgusu", False),
    "botulinum-toksin.html": ("Botulinum Toksin", True),
    "masseter-botoks.html": ("Masseter Botoks", True),
    "terleme-botoksu.html": ("Terleme Botoksu", True),
    "goz-alti-isik-dolgusu.html": ("Göz Altı Işık Dolgusu", True),
    "jawline-dolgusu.html": ("Jawline Dolgusu", True),
    "cene-ucu-dolgusu.html": ("Çene Ucu Dolgusu", True),
}

def attr(tag, name):
    m = re.search(rf'\b{name}\s*=\s*(["\'])(.*?)\1', tag, re.I | re.S)
    return html.unescape(m.group(2)).strip() if m else ""

def clean(x):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()

titles = defaultdict(list)
descs = defaultdict(list)
canonicals = defaultdict(list)
issues = []
rows = {}
contextual_sources = {name: set() for name in priority}

for f in files:
    text = f.read_text(encoding="utf-8")
    main_match = re.search(r"<main\b[^>]*>(.*?)</main>", text, re.I | re.S)
    main_html = main_match.group(1) if main_match else ""
    for href in re.findall(r'href=["\']([^"\']+)["\']', main_html, re.I):
        path = href.split("?", 1)[0].split("#", 1)[0].lstrip("/")
        if path in contextual_sources and path != f.name:
            contextual_sources[path].add(f.name)
    tm = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    title = clean(tm.group(1)) if tm else ""
    meta = ""
    robots = ""
    for tag in re.findall(r"<meta\b[^>]*>", text, re.I | re.S):
        name = attr(tag, "name").lower()
        if name == "description":
            meta = attr(tag, "content")
        elif name == "robots":
            robots = attr(tag, "content").lower()
    can = ""
    for tag in re.findall(r"<link\b[^>]*>", text, re.I | re.S):
        if attr(tag, "rel").lower() == "canonical":
            can = attr(tag, "href")
            break
    hm = re.search(r"<h1\b[^>]*>(.*?)</h1>", text, re.I | re.S)
    h1 = clean(hm.group(1)) if hm else ""
    titles[title].append(f.name)
    if meta:
        descs[meta].append(f.name)
    if can:
        canonicals[can].append(f.name)
    rows[f.name] = (title, meta, h1, can, robots)

for value, names in titles.items():
    if value and len(names) > 1:
        issues.append("DUPLICATE TITLE: " + ", ".join(names))
for value, names in descs.items():
    if value and len(names) > 1:
        issues.append("DUPLICATE META: " + ", ".join(names))
for value, names in canonicals.items():
    if value and len(names) > 1:
        issues.append("DUPLICATE CANONICAL: " + ", ".join(names))

tree = ET.parse(root / "sitemap.xml")
ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
sitemap = {n.text.strip() for n in tree.findall(".//sm:loc", ns) if n.text}

for f in files:
    title, meta, h1, can, robots = rows[f.name]
    indexable = "noindex" not in robots and f.name not in excluded
    expected = "https://drmuratkara.com/" if f.name == "index.html" else f"https://drmuratkara.com/{f.name}"
    if indexable and expected not in sitemap:
        issues.append(f"SITEMAP MISSING INDEXABLE: {f.name}")
    if "noindex" in robots and expected in sitemap:
        issues.append(f"NOINDEX IN SITEMAP: {f.name}")
    if can and urlparse(can).scheme != "https":
        issues.append(f"NON-HTTPS CANONICAL: {f.name}")

for name, (intent, needs_ankara) in priority.items():
    title, meta, h1, can, robots = rows[name]
    checks = [("title", title), ("H1", h1)]
    for label, value in checks:
        if intent.lower() not in value.lower():
            issues.append(f"{name}: {label} missing intent '{intent}'")
        if needs_ankara and "ankara" not in value.lower():
            issues.append(f"{name}: {label} missing Ankara")
    if not meta:
        issues.append(f"{name}: missing meta description")
    if "noindex" in robots:
        issues.append(f"{name}: priority page is noindex")
    minimum_contextual = 2 if name in {
        "ilk-kez-dudak-dolgusu.html",
        "dudak-dolgusu-sonrasi-sislik-iyilesme.html",
    } else 1
    if len(contextual_sources[name]) < minimum_contextual:
        issues.append(
            f"{name}: contextual inbound links {len(contextual_sources[name])} < {minimum_contextual}"
        )

print("PRIORITY RELEASE AUDIT")
for name in priority:
    title, meta, h1, can, robots = rows[name]
    sources = ",".join(sorted(contextual_sources[name])) or "-"
    print(
        f"{name}|title={len(title)}|meta={len(meta)}|h1={h1}|"
        f"index={'noindex' not in robots}|contextual_inbound={len(contextual_sources[name])}|sources={sources}"
    )

if issues:
    print("\nISSUES")
    for item in issues:
        print(item)
    raise SystemExit(1)

print(f"\nOK: {len(files)} HTML files checked; duplicate title/meta/canonical, sitemap/indexability and priority intent checks passed.")
