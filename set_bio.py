#!/usr/bin/env python3
"""Set the GitHub profile name/bio. Needs a token with the `user` scope (classic) or
fine-grained 'Profile: write'. Reads GITHUB_TOKEN from ~/.hermes/.env or the environment."""
import json, os, re, sys, urllib.request, urllib.error

def token():
    t = os.environ.get("GITHUB_TOKEN")
    if t:
        return t.strip()
    p = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(p):
        m = re.search(r'^\s*GITHUB_TOKEN\s*=\s*["\']?([^"\'\s]+)', open(p).read(), re.M)
        if m:
            return m.group(1)
    sys.exit("no GITHUB_TOKEN found in env or ~/.hermes/.env")

NAME = sys.argv[1] if len(sys.argv) > 1 else None
BIO  = sys.argv[2] if len(sys.argv) > 2 else None
if BIO and len(BIO) > 160:
    sys.exit(f"bio is {len(BIO)} chars; GitHub's limit is 160")

body = {}
if NAME: body["name"] = NAME
if BIO:  body["bio"]  = BIO
if not body: sys.exit("nothing to set: pass <name> <bio>")

req = urllib.request.Request(
    "https://api.github.com/user", method="PATCH",
    data=json.dumps(body).encode(),
    headers={"Authorization": f"Bearer {token()}",
             "Accept": "application/vnd.github+json",
             "X-GitHub-Api-Version": "2022-11-28",
             "User-Agent": "ytmla"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    print(f"  set: name={d.get('name')!r} bio={d.get('bio')!r}")
except urllib.error.HTTPError as e:
    detail = e.read().decode()[:300]
    sys.exit(f"  HTTP {e.code}: {detail}\n"
             "  401/403 usually means the token lacks the `user` scope.")
