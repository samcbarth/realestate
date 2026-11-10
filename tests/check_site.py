#!/usr/bin/env python3
"""Site checks: internal links and assets resolve, every page has the required head
tags, JSON-LD parses, titles/descriptions are unique, no leftover placeholders,
no em dashes or emojis. `--external` also requests every external link.

Run: python tests/check_site.py [--external]
"""
import json
import pathlib
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKIP_DIRS = {"content", "tests", "data", ".git", ".claude"}
errors = []


class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ld, self._in_ld, self._buf = [], [], False, ""
        self.title, self._in_title, self.meta = "", False, {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for k in ("href", "src", "srcset"):
            if a.get(k) and not (tag == "link" and a.get("rel") in ("canonical", "alternate") and k == "href" and a[k].startswith("http")):
                self.links.append(a[k].split()[0])
        if tag == "script" and a.get("type") == "application/ld+json":
            self._in_ld, self._buf = True, ""
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            key = a.get("name") or a.get("property")
            if key:
                self.meta[key] = a.get("content", "")
        if tag == "link" and a.get("rel") == "canonical":
            self.meta["canonical"] = a.get("href")

    def handle_endtag(self, tag):
        if tag == "script" and self._in_ld:
            self.ld.append(self._buf)
            self._in_ld = False
        if tag == "title":
            self._in_title = False

    def handle_data(self, d):
        if self._in_ld:
            self._buf += d
        if self._in_title:
            self.title += d


def pages():
    for p in ROOT.rglob("*.html"):
        if not set(p.relative_to(ROOT).parts) & SKIP_DIRS:
            yield p


def resolve(page, href):
    u = urlparse(href)
    if u.scheme or href.startswith(("#", "mailto:", "tel:", "data:")):
        return None
    path = u.path
    if not path:
        return None
    target = ROOT / path.lstrip("/") if path.startswith("/") else page.parent / path
    if path.endswith("/"):
        target = target / "index.html"
    return target


EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
titles, descs, external = {}, {}, set()
count = 0
for page in pages():
    count += 1
    rel = page.relative_to(ROOT).as_posix()
    text = page.read_text(encoding="utf-8")
    p = P()
    p.feed(text)
    if "G-XHPZSNJ2NL" not in text.split("<meta", 1)[0]:
        errors.append(f"{rel}: GTM snippet not right after <head>")
    for need in ("description", "og:title", "og:image", "canonical"):
        if not p.meta.get(need):
            errors.append(f"{rel}: missing {need}")
    if "{{" in text:
        errors.append(f"{rel}: leftover placeholder")
    if "—" in text:
        errors.append(f"{rel}: em dash")
    if EMOJI.search(text):
        errors.append(f"{rel}: emoji")
    for blob in p.ld:
        try:
            json.loads(blob)
        except ValueError as ex:
            errors.append(f"{rel}: bad JSON-LD {ex}")
    if rel != "404.html":
        if not p.ld:
            errors.append(f"{rel}: no JSON-LD")
        titles.setdefault(p.title, []).append(rel)
        descs.setdefault(p.meta.get("description"), []).append(rel)
    for href in p.links:
        if href.startswith("http"):
            external.add(href)
            continue
        t = resolve(page, href)
        if t is not None and not t.exists():
            errors.append(f"{rel}: broken link {href}")

for t, ps in titles.items():
    if len(ps) > 1:
        errors.append(f"duplicate title '{t}': {ps}")
for d, ps in descs.items():
    if len(ps) > 1:
        errors.append(f"duplicate description: {ps}")
for f in ["sitemap.xml", "robots.txt", "rss.xml", "llms.txt", "news/feed.json", "CNAME", "assets/config.js"]:
    if not (ROOT / f).exists():
        errors.append(f"missing {f}")
feed = json.loads((ROOT / "news/feed.json").read_text(encoding="utf-8"))
for it in feed["items"]:
    for k in ("title", "url", "date_published", "summary", "image", "tags"):
        if not it.get(k):
            errors.append(f"feed item missing {k}: {it.get('id')}")

if "--external" in sys.argv:
    UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130 link-check"}

    def check(u):
        for method in ("HEAD", "GET"):
            try:
                r = urllib.request.urlopen(urllib.request.Request(u, headers=UA, method=method), timeout=25)
                return u, r.status
            except urllib.error.HTTPError as ex:
                if method == "GET":
                    return u, ex.code
            except Exception as ex:
                if method == "GET":
                    return u, str(ex)[:60]
        return u, "?"
    skip = ("googletagmanager", "googlesyndication", "hsforms", "samcbarth.com")
    with ThreadPoolExecutor(12) as ex:
        for u, st in ex.map(check, sorted(x for x in external if not any(s in x for s in skip))):
            if st != 200:
                print(f"external {st}: {u}")

print(f"Checked {count} pages, {len(external)} external links.")
if errors:
    print("\n".join(errors))
    sys.exit(1)
print("All checks passed.")
