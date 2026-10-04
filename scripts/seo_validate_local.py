from pathlib import Path
import html, json, re, sys
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

root = Path(__file__).resolve().parents[1]
files = sorted(root.glob("*.html"))
known = {"/" + f.name for f in files} | {"/"}
errors = []
warnings = []
faq_notes = []
canonicals = {}
date_modified_by_url = {}
inbound = {"/" + f.name: 0 for f in files}
contextual_inbound = {"/" + f.name: 0 for f in files}
priority_contextual_pages = {
    "/dudak-dolgusu.html",
    "/ilk-kez-dudak-dolgusu.html",
    "/dudak-dolgusu-sonrasi-sislik-iyilesme.html",
    "/botulinum-toksin.html",
    "/masseter-botoks.html",
    "/terleme-botoksu.html",
    "/goz-alti-isik-dolgusu.html",
    "/jawline-dolgusu.html",
    "/cene-ucu-dolgusu.html",
}
indexable_by_name = {}

def attr(tag, name):
    m = re.search(rf'\b{name}\s*=\s*(["\'])(.*?)\1', tag, re.I)
    return m.group(2) if m else None

for f in files:
    text = f.read_text(encoding="utf-8")
    h1 = len(re.findall(r"<h1\b", text, re.I))
    title_match = re.search(r"<title>(.*?)</title>", text, re.I | re.S)
    main_match = re.search(r"<main\b[^>]*>(.*?)</main>", text, re.I | re.S)
    main_html = main_match.group(1) if main_match else ""
    visible_source = re.sub(r"<(?:script|style)\b[^>]*>.*?</(?:script|style)>", " ", text, flags=re.I | re.S)
    visible_text = html.unescape(re.sub(r"<[^>]+>", " ", visible_source))
    visible_text = re.sub(r"\s+", " ", visible_text).strip()

    link_tags = re.findall(r"<link\b[^>]*>", text, re.I)
    canonical_urls = []
    for tag in link_tags:
        if (attr(tag, "rel") or "").lower() == "canonical":
            href = attr(tag, "href")
            if href:
                canonical_urls.append(href)

    meta_tags = re.findall(r"<meta\b[^>]*>", text, re.I)
    desc = None
    robots_content = ""
    for tag in meta_tags:
        meta_name = (attr(tag, "name") or "").lower()
        if meta_name == "description" and desc is None:
            desc = attr(tag, "content")
        elif meta_name == "robots":
            robots_content = (attr(tag, "content") or "").lower()
    is_indexable = "noindex" not in robots_content
    indexable_by_name[f.name] = is_indexable

    if h1 != 1:
        errors.append(f"{f.name}: H1={h1}")
    if len(canonical_urls) != 1:
        errors.append(f"{f.name}: canonical={len(canonical_urls)}")
    else:
        canonical = canonical_urls[0]
        if canonical in canonicals:
            errors.append(f"{f.name}: duplicate canonical also used by {canonicals[canonical]}: {canonical}")
        canonicals[canonical] = f.name
        if urlparse(canonical).netloc != "drmuratkara.com":
            errors.append(f"{f.name}: unexpected canonical host {canonical}")

    if not title_match:
        errors.append(f"{f.name}: missing title")
    else:
        title = re.sub(r"\s+", " ", title_match.group(1)).strip()
        if is_indexable and not (30 <= len(title) <= 70):
            warnings.append(f"{f.name}: title length {len(title)}")

    if desc is None:
        if is_indexable:
            warnings.append(f"{f.name}: missing meta description")
    else:
        desc_clean = re.sub(r"\s+", " ", desc).strip()
        if is_indexable and not (80 <= len(desc_clean) <= 180):
            warnings.append(f"{f.name}: meta description length {len(desc_clean)}")

    if '"opens": "10:00"' in text or '"closes": "19:00"' in text:
        errors.append(f"{f.name}: outdated 10:00-19:00 schema hours")
    if "Pazartesi – Cumartesi: 10:00 – 19:00" in text:
        errors.append(f"{f.name}: outdated visible 10:00-19:00 hours")

    for href in re.findall(r'href=["\']([^"\']+)["\']', text, re.I):
        if href.startswith("/") and not href.startswith("//"):
            path = href.split("?", 1)[0].split("#", 1)[0]
            if path and path != "/":
                if path not in known and not (root / path.lstrip("/")).exists():
                    errors.append(f"{f.name}: broken link {href}")
                elif path in inbound:
                    inbound[path] += 1

    for href in re.findall(r'href=["\']([^"\']+)["\']', main_html, re.I):
        if href.startswith("/") and not href.startswith("//"):
            path = href.split("?", 1)[0].split("#", 1)[0]
            if path in contextual_inbound and path != "/" + f.name:
                contextual_inbound[path] += 1

    schema_objects = []
    for block in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', text, re.I | re.S):
        try:
            parsed = json.loads(block)
            schema_objects.append(parsed)
        except Exception as e:
            errors.append(f"{f.name}: invalid JSON-LD {e}")

    visible_date = None
    dm = re.search(r"Son Güncelleme:\s*(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})", visible_text)
    if dm:
        months = {
            "Ocak":"01","Şubat":"02","Mart":"03","Nisan":"04","Mayıs":"05","Haziran":"06",
            "Temmuz":"07","Ağustos":"08","Eylül":"09","Ekim":"10","Kasım":"11","Aralık":"12"
        }
        if dm.group(2) in months:
            visible_date = f"{dm.group(3)}-{months[dm.group(2)]}-{int(dm.group(1)):02d}"

    def walk_schema(obj):
        if isinstance(obj, dict):
            yield obj
            for v in obj.values():
                yield from walk_schema(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from walk_schema(v)

    for schema in schema_objects:
        for obj in walk_schema(schema):
            if obj.get("@type") == "MedicalWebPage":
                modified = obj.get("dateModified")
                reviewed = obj.get("lastReviewed")
                page_url = obj.get("url")
                if page_url and modified:
                    date_modified_by_url[page_url] = modified
                if visible_date:
                    if modified and modified != visible_date:
                        warnings.append(f"{f.name}: visible update {visible_date} != schema dateModified {modified}")
                    if reviewed and reviewed != visible_date:
                        warnings.append(f"{f.name}: visible update {visible_date} != schema lastReviewed {reviewed}")
            if obj.get("@type") == "FAQPage":
                for q in obj.get("mainEntity", []):
                    name = re.sub(r"\s+", " ", (q.get("name") or "")).strip()
                    if name and name not in visible_text:
                        faq_notes.append(f"{f.name}: FAQ schema question not found in visible content: {name}")
                    answer_obj = q.get("acceptedAnswer") or {}
                    answer = re.sub(r"\s+", " ", (answer_obj.get("text") or "")).strip()
                    if answer and answer not in visible_text:
                        faq_notes.append(f"{f.name}: FAQ schema answer differs from visible content: {name}")

sitemap_path = root / "sitemap.xml"
try:
    tree = ET.parse(sitemap_path)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [n.text.strip() for n in tree.findall(".//sm:loc", ns) if n.text]
    if len(locs) != len(set(locs)):
        errors.append("sitemap.xml: duplicate URLs found")

    sitemap_lastmod = {}
    for url_node in tree.findall(".//sm:url", ns):
        loc_node = url_node.find("sm:loc", ns)
        mod_node = url_node.find("sm:lastmod", ns)
        if loc_node is not None and loc_node.text and mod_node is not None and mod_node.text:
            sitemap_lastmod[loc_node.text.strip()] = mod_node.text.strip()

    sitemap_set = set(locs)
    excluded = {"404.html", "gizlilik.html", "aydinlatma.html"}
    expected = {
        "https://drmuratkara.com/" if f.name == "index.html"
        else f"https://drmuratkara.com/{f.name}"
        for f in files if f.name not in excluded
    }
    for url in sorted(expected - sitemap_set):
        errors.append(f"sitemap.xml: missing {url}")
    for url in sorted(sitemap_set - expected):
        warnings.append(f"sitemap.xml: extra/unexpected {url}")

    for url, modified in sorted(date_modified_by_url.items()):
        lastmod = sitemap_lastmod.get(url)
        if lastmod and lastmod < modified:
            warnings.append(f"sitemap.xml: {url} lastmod {lastmod} is older than schema dateModified {modified}")
except Exception as e:
    errors.append(f"sitemap.xml: invalid XML {e}")

for path, count in sorted(inbound.items()):
    name = path.lstrip("/")
    if name not in {"index.html", "404.html", "gizlilik.html", "aydinlatma.html"} and count == 0:
        warnings.append(f"{name}: no internal inbound link detected")

for path in sorted(priority_contextual_pages):
    if path in contextual_inbound and contextual_inbound[path] == 0:
        warnings.append(f"{path.lstrip('/')}: no contextual inbound link from <main> content")

if errors:
    print("ERRORS")
    print("\n".join(errors))
if warnings:
    print("WARNINGS")
    print("\n".join(warnings))
if faq_notes:
    print(f"INFO: {len(faq_notes)} legacy FAQPage consistency note(s); non-blocking for Google Search.")
if errors:
    sys.exit(1)
print(f"OK: {len(files)} HTML files; structural, canonical, internal-link, JSON-LD, hours and sitemap checks passed.")
