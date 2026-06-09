"""CSV and JSON export from telint DB."""
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from telint import storage


async def export_csv(handle: str, output_path: str = None) -> str:
    """Export members of target to CSV. Returns path of written file."""
    handle_stripped = handle.lstrip("@")

    if output_path is None:
        exports_dir = Path("exports")
        exports_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(exports_dir / f"{handle_stripped}.csv")

    target = await storage.get_target(handle_stripped)
    if target is None:
        raise ValueError(f"Target '{handle}' not found in database.")

    members = await storage.get_members(target["id"])

    fieldnames = [
        "user_id",
        "username",
        "first_name",
        "last_name",
        "phone",
        "is_bot",
        "scraped_via",
        "first_seen",
        "last_seen",
    ]

    abs_path = os.path.abspath(output_path)
    with open(abs_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for member in members:
            writer.writerow({k: member.get(k) for k in fieldnames})

    return abs_path


async def export_json(handle: str, output_path: str = None) -> str:
    """Export members of target to JSON. Returns path of written file."""
    handle_stripped = handle.lstrip("@")

    if output_path is None:
        exports_dir = Path("exports")
        exports_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(exports_dir / f"{handle_stripped}.json")

    target = await storage.get_target(handle_stripped)
    if target is None:
        raise ValueError(f"Target '{handle}' not found in database.")

    members = await storage.get_members(target["id"])

    exported_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "target": handle,
        "exported_at": exported_at,
        "count": len(members),
        "members": members,
    }

    abs_path = os.path.abspath(output_path)
    with open(abs_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return abs_path
