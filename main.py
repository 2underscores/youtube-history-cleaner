#!/usr/bin/env python3
"""
youtube_history.py — Fetch your full YouTube watch history from myactivity.google.com
Uses Chrome's saved session cookies (no password needed, just needs Chrome logged in).

Usage:
    pip install browser-cookie3 --break-system-packages
    python3 youtube_history.py

Output:
    youtube_history.json — full list of watched videos with title, url, channel, timestamp
"""

import json
import re
import hashlib
import time
import urllib.parse
import urllib.request
import browser_cookie3
from datetime import datetime, timezone


# ── Auth helpers ──────────────────────────────────────────────────────────────

def get_chrome_cookies():
    cj = browser_cookie3.chrome(domain_name='.google.com')
    return {c.name: c.value for c in cj}


def compute_sapisidhash(sapisid, origin='https://myactivity.google.com'):
    """
    Google's auth token for XHR: SHA1(unix_ts + " " + SAPISID + " " + origin)
    Returned as the string  "SAPISIDHASH <ts>_<sha1hex>"
    """
    ts = str(int(time.time()))
    digest = hashlib.sha1(f"{ts} {sapisid} {origin}".encode()).hexdigest()
    return f"SAPISIDHASH {ts}_{digest}"


def cookie_header(cookies: dict) -> str:
    return '; '.join(f'{k}={v}' for k, v in cookies.items())


# ── Session params from initial page ─────────────────────────────────────────

def get_session_params(cookies: dict) -> dict:
    """
    Fetch the myactivity YouTube history page and extract the dynamic
    f.sid and bl (build label) values that must accompany every batchexecute call.
    """
    url = 'https://myactivity.google.com/product/youtube'
    req = urllib.request.Request(url, headers={
        'User-Agent': (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        ),
        'Cookie': cookie_header(cookies),
    })
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8')

    fsid_m = re.search(r'"FdrFJe":"(-?\d+)"', html)
    bl_m   = re.search(r'"cfb2h":"([^"]+)"', html)

    return {'f.sid': fsid_m.group(1), 'bl': bl_m.group(1)}


# ── batchexecute request ──────────────────────────────────────────────────────

BATCHEXECUTE_URL = (
    'https://myactivity.google.com/_/FootprintsMyactivityUi/data/batchexecute'
)
RPC_ID = 'y3VFHd'


def fetch_page(cookies: dict, sapisidhash: str, session: dict,
               page_token=None) -> str:
    """
    POST one batchexecute request for up to 100 history items.
    page_token=None fetches the first page.
    """
    # Inner JSON payload: [[null, ["youtube"]], PAGE_TOKEN_OR_NULL, 100]
    inner_payload = [[None, ["youtube"]], page_token, 100]
    inner_json = json.dumps(inner_payload, separators=(',', ':'))

    # f.req outer envelope
    freq = json.dumps(
        [[[RPC_ID, inner_json, None, "generic"]]],
        separators=(',', ':')
    )

    body = (
        f"f.req={urllib.parse.quote(freq)}"
        f"&at={urllib.parse.quote(sapisidhash)}"
    )

    params = urllib.parse.urlencode({
        'rpcids':        RPC_ID,
        'source-path':  '/product/youtube',
        'f.sid':         session['f.sid'],
        'bl':            session['bl'],
        'hl':            'en',
        'soc-app':       '712',
        'soc-platform':  '1',
        'soc-device':    '1',
        'rt':            'c',
    })

    req = urllib.request.Request(
        f"{BATCHEXECUTE_URL}?{params}",
        data=body.encode(),
        method='POST',
        headers={
            'Content-Type':  'application/x-www-form-urlencoded',
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/124.0.0.0 Safari/537.36'
            ),
            'Origin':        'https://myactivity.google.com',
            'Referer':       'https://myactivity.google.com/product/youtube',
            'X-Same-Domain': '1',
            'Cookie':        cookie_header(cookies),
        }
    )

    with urllib.request.urlopen(req) as resp:
        return resp.read().decode('utf-8')


# ── Response parser ───────────────────────────────────────────────────────────

def parse_response(raw: str):
    """
    Parse the batchexecute response.

    Response format:
        )]}'\n
        <size>\n
        [["wrb.fr","y3VFHd","<inner_json_string>",...],...]\n
        ...

    Inner JSON is a list-of-lists. Each item is one watched video:
        [0]  null
        [1]  null
        [2]  null
        [3]  [26]                           product tag
        [4]  <timestamp_microseconds>
        [5]  <next_page_token>              (use last item's token for next page)
        [6]  null
        [7]  ["YouTube", null, logo_url]   product info
        [8]  null
        [9]  [title, null, "Watched", url] ← video title + URL
        ...
        [-1] [[null, channel, null, channel_url]]

    Returns: (list_of_video_dicts, next_page_token_or_None)
    """
    # Find the wrb.fr line
    json_line = None
    for line in raw.splitlines():
        if line.startswith('[["wrb.fr"'):
            json_line = line
            break

    if not json_line:
        return [], None

    outer = json.loads(json_line)

    # Locate the y3VFHd entry
    inner_json_str = None
    for entry in outer:
        if (isinstance(entry, list) and len(entry) >= 3
                and entry[0] == 'wrb.fr' and entry[1] == RPC_ID):
            inner_json_str = entry[2]
            break

    if not inner_json_str:
        return [], None

    inner = json.loads(inner_json_str)
    activity_list = inner[0] if inner and isinstance(inner[0], list) else []

    videos = []
    last_token = None

    for item in activity_list:
        try:
            ts_us    = item[4]                          # microseconds since epoch
            token    = item[5]                          # per-item page token
            video    = item[9]                          # [title, null, "Watched", url]
            title    = video[0] if video else None
            url      = video[3] if video and len(video) > 3 else None

            # Channel is in the last non-null nested list
            channel = None
            if isinstance(item[-1], list) and item[-1]:
                ch = item[-1][0]
                if isinstance(ch, list) and len(ch) > 1:
                    channel = ch[1]

            if title and url:
                dt = datetime.fromtimestamp(ts_us / 1e6, tz=timezone.utc)
                videos.append({
                    'title':     title,
                    'url':       url,
                    'channel':   channel,
                    'watched_at': dt.isoformat(),
                    '_token':    token,   # internal — used for pagination
                })
                last_token = token

        except (IndexError, TypeError):
            continue

    return videos, last_token


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    cookies = get_chrome_cookies()

    sapisid = cookies.get('SAPISID') or cookies['__Secure-3PAPISID']
    sapisidhash  = compute_sapisidhash(sapisid)
    session      = get_session_params(cookies)
    print(f"Session ready — bl: {session['bl']}")

    all_videos = []
    page_token = None
    page_num   = 0

    while True:
        page_num += 1
        print(f"Fetching page {page_num}…", end=' ', flush=True)

        raw = fetch_page(cookies, sapisidhash, session, page_token)
        items, next_token = parse_response(raw)

        print(f"{len(items)} videos")

        if not items:
            break

        all_videos.extend(items)

        # Stop if we got no new token or same token (end of history)
        if not next_token or next_token == page_token:
            break

        page_token = next_token

        # Be polite — don't hammer the API
        time.sleep(0.5)

    # Strip internal _token field before saving
    for v in all_videos:
        v.pop('_token', None)

    out_file = 'youtube_history.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(all_videos, f, indent=2, ensure_ascii=False)

    print(f"\n✓ {len(all_videos)} videos saved to {out_file}")
    print("\nFirst 10:")
    for v in all_videos[:10]:
        print(f"  [{v['watched_at'][:10]}] {v['title']}  —  {v['channel']}")


if __name__ == '__main__':
    main()
