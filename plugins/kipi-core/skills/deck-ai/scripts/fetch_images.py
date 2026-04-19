#!/usr/bin/env python3
"""
Unsplash keyword → image URL resolver.

Importable:
    from fetch_images import resolve_url
    url = resolve_url("koi fish", access_key)

CLI (debug only):
    python3 scripts/fetch_images.py "koi fish"
    → prints URL to stdout, or exits 1 if not found.

Requires env var UNSPLASH_ACCESS_KEY for the CLI.
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

UNSPLASH_SEARCH = "https://api.unsplash.com/search/photos"


def resolve_url(keyword, access_key, orientation="landscape", polite=True):
    """Return a photo URL for `keyword`, or None if nothing matches.

    Raises urllib.error.HTTPError on auth / rate limit errors so callers
    can distinguish between "no match" (return None) and "infra broken".
    """
    params = urllib.parse.urlencode({
        "query": keyword,
        "per_page": 1,
        "orientation": orientation,
        "content_filter": "high",
    })
    req = urllib.request.Request(
        f"{UNSPLASH_SEARCH}?{params}",
        headers={"Authorization": f"Client-ID {access_key}"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())

    if polite:
        time.sleep(0.2)  # Unsplash free tier: 50/hr

    results = data.get("results", [])
    if not results:
        return None
    return results[0]["urls"]["regular"]


def main():
    if len(sys.argv) != 2:
        print("usage: fetch_images.py <keyword>", file=sys.stderr)
        sys.exit(2)
    access_key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not access_key:
        print("ERROR: UNSPLASH_ACCESS_KEY not set", file=sys.stderr)
        sys.exit(1)
    url = resolve_url(sys.argv[1], access_key)
    if not url:
        print("no match", file=sys.stderr)
        sys.exit(1)
    print(url)


if __name__ == "__main__":
    main()
