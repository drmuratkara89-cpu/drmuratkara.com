#!/usr/bin/env python3
"""
IndexNow Submission Script for drmuratkara.com
Submits modified, newly added, or all indexable URLs to IndexNow API.
Avoids spam by only submitting relevant indexable HTML pages.
"""

import sys
import os
import json
import urllib.request
import urllib.error
import subprocess
import argparse

HOST = "drmuratkara.com"
KEY = "9a8f3b2e7c1d4e5f6a0b8c9d1e2f3a4b"
KEY_LOCATION = f"https://{HOST}/9a8f3b2e7c1d4e5f6a0b8c9d1e2f3a4b.txt"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"

# Non-indexable or system pages that should NEVER be sent to IndexNow
IGNORED_FILES = {
    "404.html",
    "gizlilik.html",
    "aydinlatma.html"
}

def get_changed_files_from_git():
    """Detects modified or added HTML files in the last commit."""
    try:
        # Check if HEAD~1 exists
        res = subprocess.run(
            ["git", "rev-parse", "HEAD~1"],
            capture_output=True, text=True, check=False
        )
        if res.returncode != 0:
            print("Notice: No previous commit found (shallow clone or initial commit).")
            return None

        diff_res = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMRT", "HEAD~1", "HEAD"],
            capture_output=True, text=True, check=True
        )
        changed = [line.strip() for line in diff_res.stdout.splitlines() if line.strip()]
        return changed
    except Exception as e:
        print(f"Warning: Could not determine git diff: {e}")
        return None

def file_to_url(filepath):
    """Converts local file path to canonical public URL."""
    basename = os.path.basename(filepath)
    if basename == "index.html":
        return f"https://{HOST}/"
    return f"https://{HOST}/{basename}"

def get_all_sitemap_urls():
    """Parses sitemap.xml to get all current indexable URLs."""
    urls = []
    sitemap_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sitemap.xml")
    if not os.path.exists(sitemap_path):
        sitemap_path = "sitemap.xml"
    if os.path.exists(sitemap_path):
        import xml.etree.ElementTree as ET
        tree = ET.parse(sitemap_path)
        root = tree.getroot()
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        for loc in root.findall('.//ns:loc', namespace):
            if loc.text:
                urls.append(loc.text.strip())
    return urls

def submit_to_indexnow(urls, dry_run=False):
    """Submits the URL list to IndexNow API."""
    if not urls:
        print("No URLs to submit. Skipping IndexNow request.")
        return True

    payload = {
        "host": HOST,
        "key": KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": sorted(list(set(urls)))
    }

    print(f"\nSubmitting {len(payload['urlList'])} URLs to IndexNow ({INDEXNOW_ENDPOINT}):")
    for u in payload['urlList']:
        print(f"  - {u}")

    if dry_run:
        print("\n[Dry-run] Request skipped.")
        return True

    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        INDEXNOW_ENDPOINT,
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "IndexNow-AutoSubmitter/1.0"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            body = resp.read().decode('utf-8')
            print(f"\nIndexNow API Response: HTTP {status} (Accepted/Success)")
            if body:
                print(f"Response body: {body}")
            return True
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode('utf-8')
        print(f"\nIndexNow API Error: HTTP {status}")
        print(f"Response: {body}")
        # Note: 200 or 202 are success, 422 usually indicates key/url mismatch, 429 rate limit
        return False
    except Exception as e:
        print(f"\nFailed to connect to IndexNow: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Submit URLs to IndexNow")
    parser.add_argument("--all", action="store_true", help="Submit all URLs from sitemap.xml")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without submitting")
    parser.add_argument("urls", nargs="*", help="Optional specific URLs to submit")
    args = parser.parse_args()

    urls_to_submit = []

    if args.urls:
        urls_to_submit = args.urls
    elif args.all:
        urls_to_submit = get_all_sitemap_urls()
        print(f"Loaded {len(urls_to_submit)} URLs from sitemap.xml (--all mode)")
    else:
        changed_files = get_changed_files_from_git()
        if changed_files is None:
            # Fallback to all sitemap URLs if git history unavailable
            print("Submitting full sitemap as fallback...")
            urls_to_submit = get_all_sitemap_urls()
        else:
            print(f"Git diff detected {len(changed_files)} changed files in commit.")
            for f in changed_files:
                basename = os.path.basename(f)
                if basename.endswith(".html") and basename not in IGNORED_FILES:
                    urls_to_submit.append(file_to_url(f))
                elif basename == "sitemap.xml":
                    # If sitemap itself changed, submit all current sitemap URLs
                    print("sitemap.xml was modified; submitting all URLs.")
                    urls_to_submit = get_all_sitemap_urls()
                    break

    # Filter out empty or duplicate
    urls_to_submit = [u for u in set(urls_to_submit) if u]

    if not urls_to_submit:
        print("No indexable HTML changes detected in this commit. No IndexNow request sent.")
        return

    success = submit_to_indexnow(urls_to_submit, dry_run=args.dry_run)
    if not success and not args.dry_run:
        sys.exit(1)

if __name__ == "__main__":
    main()
