"""Premium V2 regression checks: read-only, no browser or production changes."""
from pathlib import Path
import re
import subprocess
from PIL import Image
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1]
PAGES=("index.html","dr-murat-kara.html")

def original(page):
    return subprocess.check_output(
        ["git","show",f"FETCH_HEAD:{page}"],cwd=ROOT).decode("utf-8-sig")

def meta_tags(html):
    patterns={
        "title":r"<title[^>]*>.*?</title>",
        "description":r'<meta\s+[^>]*name=["\']description["\'][^>]*>',
        "canonical":r'<link\s+[^>]*rel=["\']canonical["\'][^>]*>',
        "robots":r'<meta\s+[^>]*name=["\']robots["\'][^>]*>',
        "schema":r'<script\s+type=["\']application/ld\+json["\']>.*?</script>',
    }
    return {key:(re.search(pattern,html,re.S|re.I).group(0) if re.search(pattern,html,re.S|re.I) else None)
            for key,pattern in patterns.items()}

def verify():
    image=ROOT/"murat-premium-hero.webp"
    with Image.open(image) as img:
        assert img.format=="WEBP" and img.width>=1000 and img.height>=1000
        print("PASS image", img.size, image.stat().st_size, "bytes")
    for page in PAGES:
        html=(ROOT/page).read_text(encoding="utf-8-sig")
        assert meta_tags(html)==meta_tags(original(page)), f"SEO metadata changed: {page}"
        assert len(re.findall(r"<h1(?:\s|>)",html,re.I))==1, f"H1 count {page}"
        expected=2 if page=="index.html" else 1
        assert html.count('src="/murat-premium-hero.webp"')==expected
        assert 'width="1148" height="1371"' in html
        local=set(re.findall(r'(?:href|src)=["\'](/[^"\'#?]+)',html))
        missing=[path for path in local if path!="/" and not (ROOT/path.lstrip("/")).exists()]
        assert not missing, f"Local paths missing: {page}, {missing}"
        print("PASS",page,"SEO, portrait, local paths")
    css=(ROOT/"styles.css").read_text(encoding="utf-8-sig")
    assert re.search(r"\.premium-home \.floating-whatsapp\s*\{[^}]*background:\s*#25d366",css,re.I|re.S)
    assert re.search(r"\.premium-profile \.doctor-avatar-box \.btn-whatsapp\s*\{[^}]*background:\s*#25d366",css,re.I|re.S)
    print("PASS WhatsApp green and premium styling")

if __name__=="__main__":
    verify()
