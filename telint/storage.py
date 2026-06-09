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
) -> bool:
    """Insert or update member. Returns True if new member, False if existing."""
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("PRAGMA foreign_keys=ON")
        db.row_factory = aiosqlite.Row

        now = datetime.utcnow().isoformat()
        is_bot_int = 1 if is_bot else 0

        # INSERT OR IGNORE preserves first_seen on conflict; rowcount=1 means new row
        async with db.execute(
            """
            INSERT OR IGNORE INTO members
                (target_id, user_id, username, first_name, last_name, phone, is_bot, scraped_via, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (target_id, user_id, username, first_name, last_name, phone, is_bot_int, scraped_via, now, now),
        ) as cursor:
            is_new = cursor.rowcount == 1

        # UPDATE mutable fields (but leave first_seen untouched)
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
