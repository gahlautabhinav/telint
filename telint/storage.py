"""
Async SQLite data layer for telint using aiosqlite.
"""

import sqlite3

import aiosqlite
from datetime import datetime

from config import settings


async def init_db() -> None:
    """Create tables if not exist. Call once at startup."""
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                handle TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('group', 'channel')),
                display_name TEXT,
                added_at TEXT NOT NULL,
                last_scraped TEXT,
                monitoring INTEGER DEFAULT 0,
                monitor_interval_hours INTEGER DEFAULT 6
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_id INTEGER NOT NULL REFERENCES targets(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                is_bot INTEGER DEFAULT 0,
                scraped_via TEXT NOT NULL CHECK(scraped_via IN ('group_members', 'reaction', 'comment')),
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                UNIQUE(target_id, user_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS scrape_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_id INTEGER NOT NULL REFERENCES targets(id) ON DELETE CASCADE,
                run_at TEXT NOT NULL,
                members_found INTEGER DEFAULT 0,
                new_members INTEGER DEFAULT 0,
                mode TEXT NOT NULL CHECK(mode IN ('manual', 'scheduled'))
            )
        """)

        # Migrate existing members table — add admin columns if not present
        try:
            await db.execute("ALTER TABLE members ADD COLUMN is_admin INTEGER DEFAULT 0")
        except Exception:
            pass  # column already exists on existing DBs
        try:
            await db.execute("ALTER TABLE members ADD COLUMN admin_title TEXT")
        except Exception:
            pass  # column already exists on existing DBs

        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_id INTEGER NOT NULL REFERENCES targets(id) ON DELETE CASCADE,
                message_id INTEGER NOT NULL,
                sender_user_id INTEGER,
                sender_username TEXT,
                sender_first_name TEXT,
                sender_last_name TEXT,
                text TEXT,
                date TEXT,
                media_type TEXT,
                reply_to_message_id INTEGER,
                scraped_at TEXT NOT NULL,
                UNIQUE(target_id, message_id)
            )
        """)

        await db.commit()


async def add_target(handle: str, type_: str, display_name: str = None) -> int:
    """Insert target, return its id. Raise ValueError if handle already exists."""
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("PRAGMA foreign_keys=ON")
        added_at = datetime.utcnow().isoformat()
        try:
            async with db.execute(
                "INSERT INTO targets (handle, type, display_name, added_at) VALUES (?, ?, ?, ?)",
                (handle, type_, display_name, added_at),
            ) as cursor:
                row_id = cursor.lastrowid
        except (aiosqlite.IntegrityError, sqlite3.IntegrityError):
            raise ValueError(f"Target with handle '{handle}' already exists.")
        await db.commit()
        return row_id


async def get_target(handle: str) -> dict | None:
    """Return target row as dict or None."""
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM targets WHERE handle = ?", (handle,)) as cursor:
            row = await cursor.fetchone()
        return dict(row) if row is not None else None


async def list_targets() -> list[dict]:
    """Return all targets as list of dicts."""
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM targets ORDER BY added_at") as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def upsert_member(
    target_id: int,
    user_id: int,
    username: str,
    first_name: str,
    last_name: str,
    phone: str,
    is_bot: bool,
    scraped_via: str,
    is_admin: bool = False,
    admin_title: str = None,
) -> bool:
    """Insert or update member. Returns True if new member, False if existing."""
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("PRAGMA foreign_keys=ON")
        db.row_factory = aiosqlite.Row

        now = datetime.utcnow().isoformat()
        is_bot_int = 1 if is_bot else 0
        is_admin_int = 1 if is_admin else 0

        # INSERT OR IGNORE preserves first_seen on conflict; rowcount=1 means new row
        async with db.execute(
            """
            INSERT OR IGNORE INTO members
                (target_id, user_id, username, first_name, last_name, phone, is_bot, scraped_via, first_seen, last_seen, is_admin, admin_title)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (target_id, user_id, username, first_name, last_name, phone, is_bot_int, scraped_via, now, now, is_admin_int, admin_title),
        ) as cursor:
            is_new = cursor.rowcount == 1

        # UPDATE mutable fields (but leave first_seen and admin columns untouched)
        await db.execute(
            """
            UPDATE members
            SET username = ?, first_name = ?, last_name = ?, phone = ?,
                is_bot = ?, scraped_via = ?, last_seen = ?
            WHERE target_id = ? AND user_id = ?
            """,
            (username, first_name, last_name, phone, is_bot_int, scraped_via, now, target_id, user_id),
        )

        await db.commit()
        return is_new


async def get_members(target_id: int) -> list[dict]:
    """Return all members for a target as list of dicts."""
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM members WHERE target_id = ? ORDER BY first_seen",
            (target_id,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_member_count(target_id: int) -> int:
    """Return the number of members for a target."""
    async with aiosqlite.connect(settings.db_path) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM members WHERE target_id = ?", (target_id,)
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row is not None else 0


async def set_member_admin(target_id: int, user_id: int, is_admin: bool, admin_title: str) -> None:
    """Update admin flag and title on an existing member record."""
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("PRAGMA foreign_keys=ON")
        is_admin_int = 1 if is_admin else 0
        await db.execute(
            "UPDATE members SET is_admin = ?, admin_title = ? WHERE target_id = ? AND user_id = ?",
            (is_admin_int, admin_title, target_id, user_id),
        )
        await db.commit()


async def upsert_message(
    target_id: int,
    message_id: int,
    sender_user_id: int,
    sender_username: str,
    sender_first_name: str,
    sender_last_name: str,
    text: str,
    date: str,
    media_type: str,
    reply_to_message_id: int,
) -> bool:
    """Insert message. Returns True if new. Messages are immutable evidence — no UPDATE after INSERT."""
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("PRAGMA foreign_keys=ON")
        scraped_at = datetime.utcnow().isoformat()
        async with db.execute(
            """
            INSERT OR IGNORE INTO messages
                (target_id, message_id, sender_user_id, sender_username, sender_first_name,
                 sender_last_name, text, date, media_type, reply_to_message_id, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (target_id, message_id, sender_user_id, sender_username, sender_first_name,
             sender_last_name, text, date, media_type, reply_to_message_id, scraped_at),
        ) as cursor:
            is_new = cursor.rowcount == 1
        await db.commit()
        return is_new


async def get_messages(target_id: int, limit: int = None) -> list[dict]:
    """Return messages for a target ordered by date DESC."""
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        if limit is not None:
            async with db.execute(
                "SELECT * FROM messages WHERE target_id = ? ORDER BY date DESC LIMIT ?",
                (target_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            async with db.execute(
                "SELECT * FROM messages WHERE target_id = ? ORDER BY date DESC",
                (target_id,),
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_message_count(target_id: int) -> int:
    """Return count of messages for a target."""
    async with aiosqlite.connect(settings.db_path) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM messages WHERE target_id = ?", (target_id,)
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row is not None else 0


async def record_scrape_run(
    target_id: int, members_found: int, new_members: int, mode: str
) -> int:
    """Insert scrape run record, return its id."""
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("PRAGMA foreign_keys=ON")

        run_at = datetime.utcnow().isoformat()
        async with db.execute(
            "INSERT INTO scrape_runs (target_id, run_at, members_found, new_members, mode) VALUES (?, ?, ?, ?, ?)",
            (target_id, run_at, members_found, new_members, mode),
        ) as cursor:
            row_id = cursor.lastrowid

        await db.commit()
        return row_id


async def set_monitoring(handle: str, enabled: bool, interval_hours: int = 6) -> None:
    """Toggle monitoring flag and interval on a target."""
    async with aiosqlite.connect(settings.db_path) as db:
        monitoring_int = 1 if enabled else 0
        await db.execute(
            "UPDATE targets SET monitoring = ?, monitor_interval_hours = ? WHERE handle = ?",
            (monitoring_int, interval_hours, handle),
        )
        await db.commit()


async def update_last_scraped(target_id: int) -> None:
    """Set last_scraped to current UTC datetime."""
    async with aiosqlite.connect(settings.db_path) as db:
        last_scraped = datetime.utcnow().isoformat()
        await db.execute(
            "UPDATE targets SET last_scraped = ? WHERE id = ?",
            (last_scraped, target_id),
        )
        await db.commit()


async def delete_target(handle: str) -> None:
    """Delete target and cascade-delete members + runs."""
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("PRAGMA foreign_keys=ON")
        await db.execute("DELETE FROM targets WHERE handle = ?", (handle,))
        await db.commit()


async def get_scrape_runs(target_id: int) -> list[dict]:
    """Return all scrape runs for a target ordered by most recent first."""
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM scrape_runs WHERE target_id = ? ORDER BY run_at DESC",
            (target_id,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]
