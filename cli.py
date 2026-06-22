"""
telint CLI — Click + Rich interface.

All telint module imports are deferred inside command functions to avoid
loading config.py (which requires .env) at import time.
"""

import asyncio
import os
import subprocess
import sys

import click
from rich.console import Console
from rich.table import Table

console = Console()


# ---------------------------------------------------------------------------
# Click group
# ---------------------------------------------------------------------------

@click.group()
def cli():
    """telint — Telegram OSINT scraper."""
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """Run a coroutine, printing a friendly error and exiting on failure."""
    try:
        return asyncio.run(coro)
    except ValueError as e:
        console.print(f"[yellow]{e}[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Command: group
# ---------------------------------------------------------------------------

@cli.command("group")
@click.argument("handle")
@click.option(
    "--export",
    "export_fmt",
    type=click.Choice(["csv", "json"]),
    default=None,
    help="Export results to csv or json after scraping.",
)
def group_cmd(handle: str, export_fmt: str):
    """Scrape all members of a Telegram group/supergroup."""

    async def _group(handle: str, export_fmt: str):
        from telint import storage, scraper, export as export_mod

        await storage.init_db()

        console.print(f"[cyan]Scraping group members for {handle}...[/cyan]")
        members_found, new_members = await scraper.scrape_group_members(handle)

        target = await storage.get_target(handle.lstrip("@"))
        if target is not None:
            await storage.record_scrape_run(
                target["id"], members_found, new_members, "manual"
            )

        console.print(
            f"[green]Scraped {members_found} members ({new_members} new)[/green]"
        )

        if export_fmt == "csv":
            path = await export_mod.export_csv(handle)
            console.print(f"[blue]Exported CSV: {path}[/blue]")
        elif export_fmt == "json":
            path = await export_mod.export_json(handle)
            console.print(f"[blue]Exported JSON: {path}[/blue]")

    _run(_group(handle, export_fmt))


# ---------------------------------------------------------------------------
# Command: reactions
# ---------------------------------------------------------------------------

@cli.command("reactions")
@click.argument("handle")
@click.option(
    "--posts",
    default=100,
    show_default=True,
    help="Number of recent posts to scan for reactions.",
)
def reactions_cmd(handle: str, posts: int):
    """Scrape users who reacted to recent channel posts."""

    async def _reactions(handle: str, posts: int):
        from telint import storage, scraper

        await storage.init_db()

        console.print(
            f"[cyan]Scraping reactions for {handle} (last {posts} posts)...[/cyan]"
        )
        members_found, new_members = await scraper.scrape_channel_reactions(
            handle, posts_limit=posts
        )

        target = await storage.get_target(handle.lstrip("@"))
        if target is not None:
            await storage.record_scrape_run(
                target["id"], members_found, new_members, "manual"
            )

        console.print(
            f"[green]Scraped {members_found} reactor(s) ({new_members} new)[/green]"
        )

    _run(_reactions(handle, posts))


# ---------------------------------------------------------------------------
# Command: channel
# ---------------------------------------------------------------------------

@cli.command("channel")
@click.argument("handle")
@click.option(
    "--export",
    "export_fmt",
    type=click.Choice(["csv", "json"]),
    default=None,
    help="Export results to csv or json after scraping.",
)
def channel_cmd(handle: str, export_fmt: str):
    """Full channel scrape: reactions + linked group members."""

    async def _channel(handle: str, export_fmt: str):
        from telint import storage, scraper, export as export_mod

        await storage.init_db()

        console.print(f"[cyan]Running full channel scrape for {handle}...[/cyan]")
        members_found, new_members = await scraper.scrape_channel_full(handle)

        target = await storage.get_target(handle.lstrip("@"))
        if target is not None:
            await storage.record_scrape_run(
                target["id"], members_found, new_members, "manual"
            )

        console.print(
            f"[green]Scraped {members_found} total ({new_members} new)[/green]"
        )

        if export_fmt == "csv":
            path = await export_mod.export_csv(handle)
            console.print(f"[blue]Exported CSV: {path}[/blue]")
        elif export_fmt == "json":
            path = await export_mod.export_json(handle)
            console.print(f"[blue]Exported JSON: {path}[/blue]")

    _run(_channel(handle, export_fmt))


# ---------------------------------------------------------------------------
# Command: admins
# ---------------------------------------------------------------------------

@cli.command("admins")
@click.argument("handle")
def admins_cmd(handle: str):
    """Scrape admins of a Telegram group or channel."""

    async def _admins(handle: str):
        from telint import storage, scraper

        await storage.init_db()

        console.print(f"[cyan]Scraping admins for {handle}...[/cyan]")
        admins_found, new_members = await scraper.scrape_admins(handle)

        target = await storage.get_target(handle.lstrip("@"))
        if target is not None:
            await storage.record_scrape_run(
                target["id"], admins_found, new_members, "manual"
            )

        console.print(
            f"[green]Found {admins_found} admin(s) ({new_members} new to DB)[/green]"
        )

    _run(_admins(handle))


# ---------------------------------------------------------------------------
# Command: messages
# ---------------------------------------------------------------------------

@cli.command("messages")
@click.argument("handle")
@click.option(
    "--limit",
    default=200,
    show_default=True,
    help="Maximum number of messages to fetch.",
)
def messages_cmd(handle: str, limit: int):
    """Scrape messages from a Telegram group or channel as evidence."""

    async def _messages(handle: str, limit: int):
        from telint import storage, scraper

        await storage.init_db()

        console.print(
            f"[cyan]Scraping up to {limit} messages for {handle}...[/cyan]"
        )
        messages_saved, new_senders = await scraper.scrape_messages(handle, limit=limit)

        target = await storage.get_target(handle.lstrip("@"))
        if target is not None:
            await storage.record_scrape_run(
                target["id"], messages_saved, new_senders, "manual"
            )

        console.print(
            f"[green]Saved {messages_saved} message(s), {new_senders} new sender(s)[/green]"
        )

    _run(_messages(handle, limit))


# ---------------------------------------------------------------------------
# Command: monitor
# ---------------------------------------------------------------------------

@cli.command("monitor")
@click.argument("handle")
@click.option(
    "--interval",
    default=6,
    show_default=True,
    help="Polling interval in hours.",
)
@click.option(
    "--disable",
    "disable",
    is_flag=True,
    default=False,
    help="Disable monitoring for this target.",
)
def monitor_cmd(handle: str, interval: int, disable: bool):
    """Enable or disable continuous background monitoring for a target."""

    async def _monitor(handle: str, interval: int, disable: bool):
        from telint import storage
        from telint import monitor as monitor_mod

        await storage.init_db()

        if disable:
            await monitor_mod.disable_monitoring(handle)
            console.print(
                f"[yellow]Monitoring disabled for {handle}.[/yellow]"
            )
        else:
            await monitor_mod.enable_monitoring(handle, interval)
            console.print(
                f"[green]Monitoring enabled for {handle} "
                f"(every {interval}h).[/green]"
            )

    _run(_monitor(handle, interval, disable))


# ---------------------------------------------------------------------------
# Command: export
# ---------------------------------------------------------------------------

@cli.command("export")
@click.argument("handle")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["csv", "json"]),
    default="csv",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--output",
    "output_path",
    default=None,
    help="Output file path (auto-generated if omitted).",
)
def export_cmd(handle: str, fmt: str, output_path: str):
    """Export collected data for a target to CSV or JSON."""

    async def _export(handle: str, fmt: str, output_path: str):
        from telint import export as export_mod

        if fmt == "csv":
            path = await export_mod.export_csv(handle, output_path)
        else:
            path = await export_mod.export_json(handle, output_path)

        console.print(f"[green]Exported to: {path}[/green]")

    _run(_export(handle, fmt, output_path))


# ---------------------------------------------------------------------------
# Command: serve
# ---------------------------------------------------------------------------

@cli.command("serve")
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind host.")
@click.option("--port", default=8002, show_default=True, help="Bind port.")
def serve_cmd(host: str, port: int):
    """Start the web dashboard (uvicorn)."""
    console.print(f"[cyan]Starting dashboard on http://{host}:{port} ...[/cyan]")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "api.server:app",
            "--host", host,
            "--port", str(port),
            "--reload",
        ],
        check=False,
    )


# ---------------------------------------------------------------------------
# Command: targets
# ---------------------------------------------------------------------------

@cli.command("targets")
def targets_cmd():
    """List all targets stored in the database."""

    async def _targets():
        from telint import storage

        await storage.init_db()
        targets = await storage.list_targets()
        for t in targets:
            t["member_count"] = await storage.get_member_count(t["id"])
        return targets

    targets = _run(_targets())

    if not targets:
        console.print("[yellow]No targets found in database.[/yellow]")
        return

    table = Table(title="telint Targets", show_lines=True)
    table.add_column("Handle", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Display Name")
    table.add_column("Members", justify="right", style="green")
    table.add_column("Last Scraped")
    table.add_column("Monitoring", justify="center")

    for t in targets:
        monitoring_flag = "[green]YES[/green]" if t.get("monitoring") else "[red]NO[/red]"
        table.add_row(
            t.get("handle", ""),
            t.get("type", ""),
            t.get("display_name") or "",
            str(t.get("member_count", "")),
            t.get("last_scraped") or "never",
            monitoring_flag,
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
