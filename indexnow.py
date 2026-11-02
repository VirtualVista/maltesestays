#!/usr/bin/env python3
"""Find pages whose HTML changed since the last deploy and write them to changed-urls.json.
Hashes are kept in data/page-hashes.json (committed by the workflow)."""
import hashlib, json, os, re
ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
SITE = "https://maltesestays.com"
fp = os.path.join(ROOT, "data", "page-hashes.json")
try:
    old = json.load(open(fp))
except Exception:
    old = {}
new, changed = {}, []
for dp, _, files in os.walk(DIST):
    for f in files:
        if not f.endswith(".html") or f.startswith("google") or f == "404.html":
            continue
        rel = os.path.relpath(os.path.join(dp, f), DIST).replace(os.sep, "/")
        url = SITE + "/" + (rel[:-len("index.html")] if rel.endswith("index.html") else rel)
        html = open(os.path.join(dp, f), encoding="utf-8").read()
        html = re.sub(r"Updated [A-Z][a-z]+ \d{4}", "", html)  # ignore the month stamp
        h = hashlib.sha256(html.encode()).hexdigest()[:16]
        new[url] = h
        if old.get(url) != h:
            changed.append(url)
for extra in ("/llms.txt", "/llms-full.txt", "/sitemap.xml"):
    if changed:
        changed.append(SITE + extra)
json.dump(new, open(fp, "w"), indent=0, sort_keys=True)
json.dump(changed[:10000], open(os.path.join(ROOT, "changed-urls.json"), "w"))
print(f"IndexNow: {len(changed)} changed URLs")
