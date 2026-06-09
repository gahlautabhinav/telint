# telint — Telegram OSINT Scraper

## Context
Standalone OSINT tool to enumerate Telegram group members and channel user data (via reactions + linked groups). my.telegram.org showed `[object Object]` on app creation — likely rendered but didn't display; fallback to Telegram Desktop public credentials included. User wants: standalone project, SQLite storage + export, web dashboard + CLI, both on-demand and continuous monitoring.

---

## Answers from reverse-prompting

| Q | Answer |
|---|--------|
| Standalone vs integrate | Standalone — `d:\random_tools\telint\` |
| Output | SQLite primary + export CSV/JSON on demand |
| Interface | CLI **and** web dashboard |
| Mode | Combination: on-demand scrape + continuous monitoring |

---

## Architecture

```
d:\random_tools\telint\
├── telint/
│   ├── __init__.py
│   ├── auth.py          # MTProto client, session management
│   ├── scraper.py       # group members, reactions, linked group scrapers
│   ├── monitor.py       # background scheduler, change detection
│   ├── storage.py       # SQLite via aiosqlite, schema, queries
│   └── export.py        # CSV + JSON export from DB
├── api/
│   ├── __init__.py
│   ├── server.py        # FastAPI app
│   ├── routes.py        # /targets, /members, /scrape, /monitor, /export
│   └── templates/       # Jinja2 HTML templates (no React build step)
│       ├── base.html
│       ├── index.html   # dashboard: targets list
│       └── members.html # member table for a target
├── cli.py               # Click CLI
├── setup.py             # interactive auth wizard (handles credential fallback)
├── config.py            # Pydantic settings from .env
├── requirements.txt
└── .env.example
```

---

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Telegram | Telethon | MTProto, only way to enumerate members |
| Backend | FastAPI + Jinja2 | Simple dashboard, no React build step needed |
| DB | aiosqlite | Lightweight, no server, matches xint-bias-agent pattern |
| CLI | Click + Rich | Same pattern as twitter-osint |
| Scheduling | APScheduler | In-process cron for continuous monitoring |
| Config | Pydantic BaseSettings | .env file |

---

## Credential Handling (setup.py)

1. Ask: do you have API_ID + API_HASH from my.telegram.org?
2. If yes → use them
3. If no → use Telegram Desktop fallback:
   ```
   API_ID=2040
   API_HASH=b18441a1ff607e10a989891a5462e627
   ```
   (public, in Telegram Desktop open-source code — works but shared, more rate-limited)
4. Prompt phone number → Telegram sends code → session file saved
5. Write `.env` automatically

---

## SQLite Schema

```sql
CREATE TABLE targets (
    id INTEGER PRIMARY KEY,
    handle TEXT UNIQUE,        -- @groupname or @channelname
    type TEXT,                 -- 'group' | 'channel'
    display_name TEXT,
    added_at TEXT,
    last_scraped TEXT,
    monitoring INTEGER DEFAULT 0,  -- bool
    monitor_interval_hours INTEGER DEFAULT 6
);

CREATE TABLE members (
    id INTEGER PRIMARY KEY,
    target_id INTEGER REFERENCES targets(id),
    user_id INTEGER,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    phone TEXT,
    is_bot INTEGER,
    scraped_via TEXT,          -- 'group_members' | 'reaction' | 'comment'
    first_seen TEXT,
    last_seen TEXT,
    UNIQUE(target_id, user_id)
);

CREATE TABLE scrape_runs (
    id INTEGER PRIMARY KEY,
    target_id INTEGER REFERENCES targets(id),
    run_at TEXT,
    members_found INTEGER,
    new_members INTEGER,
    mode TEXT                  -- 'manual' | 'scheduled'
);
```

---

## Scraper Logic (`telint/scraper.py`)

### Group members
```python
client.get_participants(target, aggressive=True)
# aggressive=True = full pagination, slower but complete
```

### Channel reactions (per post)
```python
GetMessageReactionsListRequest(peer=channel, id=post_id, reaction=None, limit=100)
# Paginate until no offset returned
# Iterate last N posts (configurable, default 100 posts)
```

### Channel linked group (best coverage)
```python
GetFullChannelRequest(channel)  # → linked_chat_id
client.get_participants(linked_chat_id, aggressive=True)
```

Rate limiting: 1 req/sec default, catch `FloodWaitError` → sleep exact Telegram-specified duration.

---

## Continuous Monitoring (`telint/monitor.py`)

- APScheduler `AsyncIOScheduler` runs inside FastAPI app
- Per-target configurable interval (default 6h)
- Each run: scrape → diff against existing `members` table → record new/departed in `scrape_runs`
- No alerts yet (v1) — just DB tracking

Enable via CLI: `py -3.10 cli.py monitor @groupname --interval 6`
Enable via web: toggle on dashboard

---

## CLI Commands

```bash
py -3.10 setup.py                      # first-time auth wizard

py -3.10 cli.py group @groupname       # scrape all group members
py -3.10 cli.py reactions @channel --posts 100   # reaction-based member scrape
py -3.10 cli.py channel @channel       # reactions + linked group combined
py -3.10 cli.py monitor @target --interval 6     # enable continuous monitoring
py -3.10 cli.py export @target --format csv      # export from DB to CSV/JSON
py -3.10 cli.py serve                  # start web dashboard (localhost:8000)
```

---

## Web Dashboard (Jinja2, no build step)

| Page | URL | Content |
|------|-----|---------|
| Dashboard | `/` | List of targets, last scraped, member count, monitor toggle |
| Members | `/target/@groupname` | Sortable table: user_id, username, name, phone, scraped_via |
| Scrape | POST `/scrape` | Trigger manual scrape, shows progress |
| Export | `/export/@groupname?format=csv` | Download file |

---

## Known Limitations

- Channel subscribers who never reacted/commented: not gettable (Telegram server-side)
- Private groups user isn't a member of: access denied
- Privacy settings: user ID always captured, username/phone may be null
- Telegram Desktop fallback credentials: more aggressive rate limiting may apply

---

## Verification

```bash
# 1. Run setup
py -3.10 setup.py

# 2. Scrape a known public group
py -3.10 cli.py group @telegram --export csv

# 3. Check DB has rows
py -3.10 -c "import sqlite3; c=sqlite3.connect('telint.db'); print(c.execute('SELECT COUNT(*) FROM members').fetchone())"

# 4. Start web server and check dashboard
py -3.10 cli.py serve
# Open http://localhost:8000

# 5. Test export
py -3.10 cli.py export @telegram --format csv
```
