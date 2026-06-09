"""FastAPI route definitions for telint JSON API."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from telint import storage, scraper, monitor
from telint.export import export_csv, export_json

router = APIRouter()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class AddTargetRequest(BaseModel):
    handle: str
    type: str  # 'group' | 'channel'
    display_name: str = None


class ScrapeRequest(BaseModel):
    handle: str
    mode: str = "group"  # 'group' | 'reactions' | 'channel'
    posts_limit: int = None  # for reactions mode


class MonitorRequest(BaseModel):
    handle: str
    enabled: bool
    interval_hours: int = None


class ExportRequest(BaseModel):
    handle: str
    format: str = "csv"  # 'csv' | 'json'


# ---------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------

@router.get("/targets")
async def list_targets():
    """List all targets with their current member count."""
    targets = await storage.list_targets()
    result = []
    for t in targets:
        count = await storage.get_member_count(t["id"])
        result.append({**t, "member_count": count})
    return result


@router.post("/targets", status_code=201)
async def add_target(body: AddTargetRequest):
    """Add a new scrape target."""
    try:
        target_id = await storage.add_target(
            handle=body.handle,
            type_=body.type,
            display_name=body.display_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"id": target_id, "handle": body.handle}


@router.delete("/targets/{handle}", status_code=200)
async def delete_target(handle: str):
    """Delete a target and all associated data."""
    target = await storage.get_target(handle)
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")
    await storage.delete_target(handle)
    return {"deleted": handle}


@router.get("/targets/{handle}/members")
async def get_members(handle: str):
    """List all scraped members for a target."""
    target = await storage.get_target(handle)
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")
    members = await storage.get_members(target["id"])
    return {"handle": handle, "count": len(members), "members": members}


@router.get("/targets/{handle}/runs")
async def get_runs(handle: str):
    """Return scrape run history for a target."""
    target = await storage.get_target(handle)
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")
    runs = await storage.get_scrape_runs(target["id"])
    return {"handle": handle, "runs": runs}


# ---------------------------------------------------------------------------
# Scrape
# ---------------------------------------------------------------------------

@router.post("/scrape")
async def trigger_scrape(body: ScrapeRequest):
    """Manually trigger a scrape for a target."""
    handle = body.handle.lstrip("@")

    target = await storage.get_target(handle)
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")

    target_id = target["id"]

    if body.mode == "group":
        members_found, new_members = await scraper.scrape_group_members(handle)
    elif body.mode == "reactions":
        members_found, new_members = await scraper.scrape_channel_reactions(
            handle, posts_limit=body.posts_limit
        )
    elif body.mode == "channel":
        members_found, new_members = await scraper.scrape_channel_full(handle)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scrape mode '{body.mode}'. Use 'group', 'reactions', or 'channel'.",
        )

    await storage.record_scrape_run(target_id, members_found, new_members, "manual")

    return {"members_found": members_found, "new_members": new_members}


# ---------------------------------------------------------------------------
# Monitor
# ---------------------------------------------------------------------------

@router.post("/monitor")
async def toggle_monitor(body: MonitorRequest):
    """Enable or disable scheduled monitoring for a target."""
    handle = body.handle.lstrip("@")

    target = await storage.get_target(handle)
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")

    if body.enabled:
        await monitor.enable_monitoring(handle, body.interval_hours)
        return {"handle": handle, "monitoring": True, "interval_hours": body.interval_hours}
    else:
        await monitor.disable_monitoring(handle)
        return {"handle": handle, "monitoring": False}


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

@router.get("/export/{handle}")
async def export(
    handle: str,
    format: str = Query(default="csv", regex="^(csv|json)$"),
):
    """Download scraped members for a target as CSV or JSON."""
    handle_stripped = handle.lstrip("@")

    target = await storage.get_target(handle_stripped)
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")

    if format == "json":
        path = await export_json(handle_stripped)
        media_type = "application/json"
        filename = f"{handle_stripped}.json"
    else:
        path = await export_csv(handle_stripped)
        media_type = "text/csv"
        filename = f"{handle_stripped}.csv"

    return FileResponse(
        path=path,
        media_type=media_type,
        filename=filename,
    )
