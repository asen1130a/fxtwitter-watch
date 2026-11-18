# fxtwitter-watch

**Monitor X (Twitter) accounts for new posts — free, no account, no API key.**

[中文说明在下方](#中文说明)

`fxtwitter-watch` is a tiny, dependency-free Python CLI that watches a list of
X accounts and prints only their *new* posts. It talks to the free
[FxTwitter API](https://api.fxtwitter.com) (`api.fxtwitter.com`), so there is
nothing to sign up for and nothing to pay: no X account, no developer key,
no login cookies.

## Why

I wanted a simple thing: *tell me when these accounts post something new.*
The existing options all made it heavier than it should be:

- **Fetch tools** (like the excellent x-tweet-fetcher) are built for
  one-off fetching — and for timelines they route through Nitter, whose
  public instances keep dying; self-hosting one is a project of its own.
  They also don't watch anything: no watchlist, no memory of what you've
  already seen, so you get the same posts again and again.
- **Notification bots** want you to run a Discord/Telegram bot 24/7,
  with tokens to manage and a server to babysit.
- **Watcher scripts** that do exist mostly sit on top of the official
  X API — which is paywalled.

FxTwitter already does the hard part (it powers the embed fixes for
Discord/Telegram) and its public API is free. So this is the missing
piece: a small cron-friendly **watcher** on top of it. Add accounts,
run `check`, get only what's new. No server, no tokens, no Nitter,
no login.

## Features

- 👀 Watch any number of public accounts; only **new** posts are printed
- 🌱 First run seeds silently — no flood of old posts
- 🔁 Retries once on FxTwitter's intermittent 404s, and never reports
  "no posts" from a single failed request
- 📦 Zero dependencies: Python 3.8+ and `curl`, that's it
- 🧾 Human-readable output, or `--json` for machines
- 🔎 One-off lookups too: latest posts, profiles, single tweets, search

## Quick start

```bash
git clone https://github.com/asen1130a/fxtwitter-watch.git
cd fxtwitter-watch

# watch two accounts
python3 fxtwitter_watch.py add OpenAI
python3 fxtwitter_watch.py add AnthropicAI

# first run: seeds the state, prints nothing but a note
python3 fxtwitter_watch.py check

# later runs: prints only posts you haven't seen
python3 fxtwitter_watch.py check
python3 fxtwitter_watch.py check --json   # machine-readable
```

The watchlist lives in `watchlist.json`, the seen-posts state in
`state.json` (both created on first use; see `watchlist.example.json`).

## Run it on a schedule

```cron
*/10 * * * * cd /path/to/fxtwitter-watch && python3 fxtwitter_watch.py check >> new-posts.log 2>&1
```

## Other commands

```bash
python3 fxtwitter_watch.py user OpenAI 10        # latest 10 posts, no state involved
python3 fxtwitter_watch.py profile OpenAI        # bio, post & follower counts
python3 fxtwitter_watch.py status 2122750135608528984
python3 fxtwitter_watch.py search "free AI API" 20
python3 fxtwitter_watch.py remove OpenAI
```

## How it works

Discovery uses FxTwitter's search endpoint
(`GET /2/search?q=from:<handle>&count=N`) — in practice the reliable route.
The `/2/profile/<handle>/statuses` endpoint 404s intermittently, so this
tool never relies on it and retries a failed request once before believing
the answer. FxTwitter's v2 limit is roughly 1000 requests/minute per IP;
a handful of accounts checked every few minutes is far below that. Be polite
anyway.

## Notes & limits

- Only public accounts and public posts — that's all FxTwitter can see.
- Post IDs are kept per account (up to 200) in the state file; delete
  `state.json` to reseed from scratch.
- This is an unofficial tool built on a free community API; if FxTwitter
  changes, this may need a small update.

## Contact

Found a bug, want a feature, or building something on top of this?
Open an issue — or reach me directly:

- q179795724q@gmail.com
- 179795724@qq.com

Collaboration welcome.

## License

MIT — see [LICENSE](LICENSE).

---

## 中文说明

**免费监控 X（推特）账号的新帖：不用 X 账号、不用 API key、不用登录。**

`fxtwitter-watch` 是一个零依赖的小工具：把想盯的账号加进列表，运行
`check`，它只打印**没见过的新帖**，旧帖不会反复刷屏。数据来自免费的
FxTwitter 接口（`api.fxtwitter.com`），就是给 Discord/Telegram 做推文
嵌入预览的那个服务。

```bash
python3 fxtwitter_watch.py add OpenAI      # 加入监控
python3 fxtwitter_watch.py check           # 第一次运行是建档，之后只报新帖
python3 fxtwitter_watch.py check --json    # 机器可读输出，方便接机器人/脚本
```

配合 cron 每 10 分钟跑一次，就能做到「某账号一发新帖就落盘/推送」。
接口偶尔会 404，工具会自动重试一次，不会因为一次失败就误报「没有新帖」。

为什么再做一个：现有的抓取工具偏一次性抓取，看时间线还要依赖经常失效的
Nitter 实例（自己搭一个又是大工程），而且不带「只报新帖」的记忆；通知类
工具则要常驻跑一个机器人。这个工具只做一件事：盯账号、只报新帖，
零服务器、零令牌、零登录。

合作联系：q179795724q@gmail.com / 179795724@qq.com，也欢迎直接提 issue。
