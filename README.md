# telint

Telegram OSINT scraper. Maps group/channel membership, admin hierarchies, reaction engagement, and message evidence — via a local web UI or CLI.

Built on Telethon + FastAPI + React.

---

## Features

- **Member scraping** — scrape all participants of a group or channel
- **Admin tracking** — identify admins and creators, store titles
- **Reaction scraping** — collect users who reacted to recent channel posts
- **Message evidence** — store messages (text, media type, sender, date, reply chain) as immutable OSINT evidence
- **Export** — download members as CSV or JSON
- **Scheduled monitoring** — auto-rescrape targets on a configurable interval
- **Web UI** — React dashboard with filtering, sorting, pagination, and a message expand modal

---

## Stack

| Layer | Tech |
|-------|------|
| Telegram client | Telethon (MTProto) |
| Backend | FastAPI + Uvicorn |
| Database | SQLite via aiosqlite |
| Scheduler | APScheduler |
| Frontend | React + Vite |
| CLI | Click + Rich |

---

## Setup

### 1. Clone and create virtualenv

```bash
git clone https://github.com/gahlautabhinav/telint.git
cd telint
py -3.10 -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # macOS/Linux
pip install -r requirements.txt
```

### 2. Get Telegram API credentials

Go to [my.telegram.org](https://my.telegram.org) → **API development tools** → create an app → copy `api_id` and `api_hash`.

Alternatively use the Telegram Desktop fallback credentials (already baked into `setup.py`):
- `API_ID=2040`
- `API_HASH=b18441a1ff607e10a989891a5462e627`

### 3. Create `.env`

```env
API_ID=2040
API_HASH=b18441a1ff607e10a989891a5462e627
PHONE=+1XXXXXXXXXX
```

### 4. Authenticate (one-time)

```bash
python setup.py
```

Sends an OTP to your Telegram account. Enter it when prompted. Creates a `telint.session` file — do not delete it.

### 5. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

---

## Running

**Backend** (port 8002):
```bash
python cli.py serve
```

**Frontend** (port 5175) — in a separate terminal:
```bash
cd frontend
npm run dev
```

Open [http://localhost:5175](http://localhost:5175).

---

## Web UI Usage

1. **Add Target** — enter a Telegram group or channel handle (e.g. `durov`)
2. **Scrape** — fetches members (groups) or reactions (channels)
3. **Members tab** — browse scraped users; ADMIN badge shown for admins
4. **Scrape Admins** — from the Members page, marks admins with titles
5. **Messages tab** — scrape evidence; set message limit (default 200); click any row to expand full text
6. **Export** — CSV or JSON download from Members page
7. **Monitoring** — toggle per-target to auto-rescrape on a schedule

---

## CLI Usage

```bash
# Scrape group members
python cli.py group @targethandle

# Scrape channel (reactions + linked group)
python cli.py channel @targethandle

# Scrape admins
python cli.py admins @targethandle

# Scrape messages as evidence
python cli.py messages @targethandle --limit 500

# Start web server
python cli.py serve

# Start background monitor
python cli.py monitor
```

---

## Configuration

All settings can be set in `.env` or as environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `API_ID` | — | Telegram API ID |
| `API_HASH` | — | Telegram API hash |
| `PHONE` | — | Phone number with country code |
| `SESSION_NAME` | `telint` | Telethon session filename |
| `DB_PATH` | `telint.db` | SQLite database path |
| `MONITOR_INTERVAL_HOURS` | `6` | Auto-rescrape interval |
| `REACTION_POSTS_LIMIT` | `100` | Max posts to scan for reactions |
| `MESSAGE_SCRAPE_LIMIT` | `200` | Default message scrape count |
| `RATE_LIMIT_DELAY` | `1.0` | Seconds between API calls |

---

## Database Schema

```
targets      — tracked groups/channels
members      — scraped users (is_admin, admin_title columns)
messages     — scraped messages (immutable evidence)
scrape_runs  — history of scrape operations
```

---

## Notes

- Telegram's API restricts `get_participants` to groups you are a member of, or channels where you have admin rights. For public channels, use reaction or message scraping instead.
- Message evidence is **write-once** — existing messages are never overwritten.
- Media attachments (photos, documents) are not downloaded; only the type is recorded.

---

## License

MIT
