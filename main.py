#!/usr/bin/env python3
"""
YouTube Watch History Lister
Uses Chrome cookies + Google's batchexecute RPC to fetch history from myactivity.google.com
"""

import browser_cookie3
import requests
import json
import re
import sys
from datetime import datetime, timezone

BASE_URL = "https://myactivity.google.com"
BATCHEXECUTE_PATH = "/_/FootprintsMyactivityUi/data/batchexecute"
RPC_ID = "y3VFHd"
PAGE_SIZE = 100


def get_google_session():
    """Create a requests session with Chrome's Google cookies."""
    try:
        cookies = browser_cookie3.chrome(domain_name=".google.com")
    except Exception as e:
        print(f"Failed to get Chrome cookies: {e}", file=sys.stderr)
        sys.exit(1)

    session = requests.Session()
    for cookie in cookies:
        session.cookies.set(cookie.name, cookie.value, domain=cookie.domain)

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": BASE_URL + "/product/youtube",
    })
    return session


def extract_page_config(html):
    """Extract WIZ_global_data values needed for batchexecute (XSRF, f.sid, bl)."""
    config = {}
    for key, field in [("SNlM0e", "xsrf"), ("FdrFJe", "fsid"), ("cfb2h", "bl")]:
        m = re.search(rf'"{re.escape(key)}"\s*:\s*"([^"]+)"', html)
        if m:
            config[field] = m.group(1)
    return config


def fetch_history_page(session, config, continuation_token=None):
    """POST one batchexecute request for YouTube history. Returns raw response text."""
    inner_payload = [[None, ["youtube"]], continuation_token, PAGE_SIZE]
    freq_inner = json.dumps(inner_payload, separators=(",", ":"))
    freq = json.dumps([[[RPC_ID, freq_inner, None, "generic"]]], separators=(",", ":"))

    params = {
        "rpcids": RPC_ID,
        "source-path": "/product/youtube",
        "f.sid": config.get("fsid", ""),
        "bl": config.get("bl", ""),
        "hl": "en",
        "soc-app": "712",
        "soc-platform": "1",
        "soc-device": "1",
        "_reqid": "246290",
        "rt": "c",
    }
    data = {"f.req": freq, "at": config.get("xsrf", "")}

    resp = session.post(BASE_URL + BATCHEXECUTE_PATH, params=params, data=data)
    resp.raise_for_status()
    return resp.text


def parse_response(raw):
    """
    Parse Google's streaming batchexecute response format:
      )]}'\n\n<size>\n<json_chunk>\n<size>\n<json_chunk>...

    Returns (items, continuation_token).
    Each item: {"title": str, "url": str, "video_id": str, "watched_at": datetime}
    """
    # Strip XSSI prefix, then split on \n<digits>\n boundaries
    text = re.sub(r"^\)\]\}'\s*", "", raw)
    parts = re.split(r"\n\d+\n", text)

    # Find the wrb.fr chunk containing our RPC response
    inner = None
    for part in parts:
        stripped = re.sub(r"^\d+\n", "", part).strip()
        if not stripped:
            continue
        try:
            chunk = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if not isinstance(chunk, list):
            continue
        for frame in chunk:
            if isinstance(frame, list) and len(frame) >= 3 and frame[0] == "wrb.fr" and frame[1] == RPC_ID:
                try:
                    inner = json.loads(frame[2])
                except json.JSONDecodeError:
                    pass
                break
        if inner is not None:
            break

    if inner is None:
        return [], None

    # inner[0] = list of activity items
    # inner[1] = continuation token (string) or null
    activity_items = inner[0] if len(inner) > 0 and isinstance(inner[0], list) else []
    continuation_token = inner[1] if len(inner) > 1 and inner[1] else None

    videos = []
    for item in activity_items:
        if not isinstance(item, list):
            continue

        # item[9] = [title, null, "Watched", url]
        if len(item) <= 9 or not isinstance(item[9], list) or len(item[9]) < 4:
            continue

        title = item[9][0]
        url = item[9][3]

        if not url or "youtube.com/watch" not in url:
            continue

        vid_match = re.search(r"v=([\w-]+)", url)
        if not vid_match:
            continue

        # item[4] = timestamp in microseconds
        ts_us = item[4] if len(item) > 4 and isinstance(item[4], int) else None
        watched_at = None
        if ts_us:
            try:
                watched_at = datetime.fromtimestamp(ts_us / 1e6, tz=timezone.utc)
            except (OSError, OverflowError):
                pass

        videos.append({
            "title": title or "(no title)",
            "url": url,
            "video_id": vid_match.group(1),
            "watched_at": watched_at.isoformat() if watched_at else None,
        })

    return videos, continuation_token


def fetch_all_history(session, config, max_pages=None):
    """Paginate through all YouTube watch history. Returns list of video dicts."""
    all_videos = []
    continuation_token = None
    page = 0

    while True:
        page += 1
        print(f"  Page {page}...", end=" ", flush=True)

        raw = fetch_history_page(session, config, continuation_token)
        items, continuation_token = parse_response(raw)

        print(f"{len(items)} videos")
        all_videos.extend(items)

        if not continuation_token:
            print("  Done.")
            break
        if max_pages and page >= max_pages:
            print(f"  Stopped at {max_pages} pages.")
            break

    return all_videos


def main():
    print("Fetching YouTube watch history from Google My Activity\n")

    print("1. Getting Chrome session...")
    session = get_google_session()

    print("2. Loading myactivity page for session config...")
    resp = session.get(BASE_URL + "/product/youtube")
    resp.raise_for_status()
    config = extract_page_config(resp.text)

    if not config.get("xsrf"):
        print("ERROR: Could not extract XSRF token. Make sure you're signed into Google in Chrome.")
        sys.exit(1)

    print(f"   bl={config['bl'][:40]}")

    print("3. Fetching history pages...")
    videos = fetch_all_history(session, config)

    # Deduplicate by video_id (keep most recent watch)
    seen = set()
    unique = []
    for v in videos:
        if v["video_id"] not in seen:
            seen.add(v["video_id"])
            unique.append(v)

    print(f"\n{'='*60}")
    print(f"Total: {len(videos)} watches, {len(unique)} unique videos\n")

    for i, v in enumerate(unique, 1):
        date = v["watched_at"][:10] if v["watched_at"] else "unknown"
        print(f"  {i:4}. [{date}] {v['title']}")
        print(f"         {v['url']}")

    with open("history.json", "w") as f:
        json.dump(unique, f, indent=2)
    print(f"\nSaved {len(unique)} videos to history.json")


if __name__ == "__main__":
    main()
