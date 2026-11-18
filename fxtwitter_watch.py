#!/usr/bin/env python3
"""fxtwitter-watch — monitor X (Twitter) accounts for new posts, for free.

Uses the free FxTwitter API (https://api.fxtwitter.com) — no X account,
no API key, no login. Discovery goes through the search endpoint
`/2/search?q=from:<handle>`, which is the reliable route; the
`/2/profile/<handle>/statuses` endpoint 404s intermittently, so this
tool retries once and falls back to search instead of reporting
"no posts" from a single 404.

Usage:
  fxtwitter_watch.py check [--config watchlist.json] [--state state.json] [--json]
  fxtwitter_watch.py add <handle> [--config watchlist.json]
  fxtwitter_watch.py remove <handle> [--config watchlist.json]
  fxtwitter_watch.py user <handle> [count]
  fxtwitter_watch.py profile <handle>
  fxtwitter_watch.py status <tweet_id>
  fxtwitter_watch.py search "<query>" [count]

`check` compares each watched account's latest posts against a state
file and prints only the new ones. The first run for an account just
seeds the state (nothing is printed), so you never get flooded with
old posts. Run it from cron every few minutes and pipe the output
wherever you want to be notified.

Requires: Python 3.8+ and curl. No third-party packages.
FxTwitter v2 rate limit: ~1000 requests/minute per IP — be polite.
"""

import json
import subprocess
import sys
import urllib.parse

API = "https://api.fxtwitter.com/2"
DEFAULT_COUNT = 20
SEEN_CAP = 200  # keep at most this many seen ids per account


def curl(url, timeout=20):
    """GET a URL with curl and parse the JSON body. Never raises."""
    try:
        out = subprocess.run(
            ["curl", "-s", "-m", str(timeout), url],
            capture_output=True, text=True,
        )
        return json.loads(out.stdout)
    except Exception as exc:  # network down, bad JSON, curl missing...
        return {"code": 0, "error": str(exc)}


def fetch_user_posts(handle, count=DEFAULT_COUNT):
    """Latest posts of one account via the search endpoint.

    Retries once on a non-200 code: FxTwitter endpoints 404
    intermittently, and a single 404 must never read as "no posts".
    """
    q = urllib.parse.quote(f"from:{handle}")
    url = f"{API}/search?q={q}&count={count}"
    data = curl(url)
    if data.get("code") != 200:
        data = curl(url)
    return data.get("results") or []


def show_status(s, out=sys.stdout):
    a = (s.get("author") or {}).get("screen_name", "?")
    print(f"{s.get('id')} @{a} {s.get('created_at', '')}", file=out)
    print((s.get("text") or "").replace("\n", " "), file=out)
    print(s.get("url", ""), file=out)
    print(file=out)


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def opt(args, name, default):
    """Read `--name value` from args, returning (value, remaining args)."""
    if name in args:
        i = args.index(name)
        if i + 1 < len(args):
            return args[i + 1], args[:i] + args[i + 2:]
    return default, args


def cmd_check(args):
    config_path, args = opt(args, "--config", "watchlist.json")
    state_path, args = opt(args, "--state", "state.json")
    as_json = "--json" in args

    config = load_json(config_path, {"accounts": [], "count": DEFAULT_COUNT})
    accounts = config.get("accounts") or []
    count = int(config.get("count") or DEFAULT_COUNT)
    state = load_json(state_path, {})

    new_posts = []
    for handle in accounts:
        handle = handle.lstrip("@")
        posts = fetch_user_posts(handle, count)
        if not posts:
            continue
        seen = state.get(handle, {}).get("seen")
        ids = [str(p.get("id")) for p in posts]
        if seen is None:
            # First run for this account: seed silently.
            state[handle] = {"seen": ids[:SEEN_CAP]}
            if not as_json:
                print(f"[@{handle}] seeded with {len(ids)} recent posts; "
                      "new posts will show up from the next run on.")
            continue
        fresh = [p for p in posts if str(p.get("id")) not in seen]
        # Print oldest first so the output reads chronologically.
        for p in reversed(fresh):
            new_posts.append(p)
            if not as_json:
                show_status(p)
        merged = list(dict.fromkeys(ids + seen))[:SEEN_CAP]
        state[handle] = {"seen": merged}

    save_json(state_path, state)
    if as_json:
        print(json.dumps(new_posts, ensure_ascii=False, indent=2))
    elif not new_posts and accounts:
        print("No new posts.")
    return 0


def cmd_add_remove(args, add=True):
    config_path, args = opt(args, "--config", "watchlist.json")
    if not args:
        print(__doc__)
        return 2
    handle = args[0].lstrip("@")
    config = load_json(config_path, {"accounts": [], "count": DEFAULT_COUNT})
    accounts = config.setdefault("accounts", [])
    if add and handle not in accounts:
        accounts.append(handle)
    if not add and handle in accounts:
        accounts.remove(handle)
    save_json(config_path, config)
    print(f"{'Added' if add else 'Removed'} @{handle}. "
          f"Watching now: {', '.join('@' + a for a in accounts) or '(none)'}")
    return 0


def cmd_user(args):
    handle = args[0].lstrip("@")
    count = args[1] if len(args) > 1 else str(DEFAULT_COUNT)
    for r in fetch_user_posts(handle, count):
        show_status(r)
    return 0


def cmd_profile(args):
    handle = args[0].lstrip("@")
    d = curl(f"{API}/profile/{handle}")
    if d.get("code") != 200:
        d = curl(f"{API}/profile/{handle}")
    u = d.get("user") or {}
    print(f"@{u.get('screen_name')} — {u.get('name', '')}")
    print(f"statuses: {u.get('statuses')}  followers: {u.get('followers')}")
    print(u.get("description", ""))
    return 0


def cmd_status(args):
    d = curl(f"{API}/status/{args[0]}")
    if d.get("status"):
        show_status(d["status"])
    else:
        print(f"No status found (code {d.get('code')}).")
    return 0


def cmd_search(args):
    q = urllib.parse.quote(args[0])
    count = args[1] if len(args) > 1 else str(DEFAULT_COUNT)
    d = curl(f"{API}/search?q={q}&count={count}")
    for r in d.get("results") or []:
        show_status(r)
    return 0


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd, rest = argv[1], argv[2:]
    if cmd == "check":
        return cmd_check(rest)
    if cmd == "add":
        return cmd_add_remove(rest, add=True)
    if cmd == "remove":
        return cmd_add_remove(rest, add=False)
    if cmd in ("user", "profile", "status", "search") and rest:
        return {"user": cmd_user, "profile": cmd_profile,
                "status": cmd_status, "search": cmd_search}[cmd](rest)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
