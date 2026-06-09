#!/usr/bin/env python
"""First-time auth wizard for telint."""

import asyncio
import os
import sys

from rich.console import Console

console = Console()


def _prompt(label: str, default: str = "") -> str:
    """Plain input() prompt with optional default shown."""
    if default:
        value = input(f"{label} [{default}]: ").strip()
        return value if value else default
    return input(f"{label}: ").strip()


def main() -> None:
    console.rule("[bold cyan]telint — first-time setup wizard[/bold cyan]")
    console.print()

    # Step 1: Ask for API credentials
    own_creds = input("Do you have your own API credentials from my.telegram.org? [y/N]: ").strip().lower()

    if own_creds == "y":
        raw_id = _prompt("API_ID (integer)")
        while not raw_id.isdigit():
            console.print("[red]API_ID must be an integer. Try again.[/red]")
            raw_id = _prompt("API_ID (integer)")
        api_id = int(raw_id)
        api_hash = _prompt("API_HASH")
        while not api_hash:
            console.print("[red]API_HASH cannot be empty. Try again.[/red]")
            api_hash = _prompt("API_HASH")
    else:
        api_id = 2040
        api_hash = "b18441a1ff607e10a989891a5462e627"
        console.print(
            "[yellow]Warning:[/yellow] Using public Telegram Desktop credentials "
            "(API_ID=2040). These are more rate-limited than personal credentials."
        )

    console.print()

    # Step 2: Phone number
    phone = _prompt("PHONE (e.g. +12025551234)")
    while not phone.startswith("+"):
        console.print("[red]Phone must start with + and country code. Try again.[/red]")
        phone = _prompt("PHONE (e.g. +12025551234)")

    # Step 3: Session name
    session_name = _prompt("SESSION_NAME", default="telint")

    # Step 4: DB path
    db_path = _prompt("DB_PATH", default="telint.db")

    # Step 5: Write .env
    env_content = (
        f"API_ID={api_id}\n"
        f"API_HASH={api_hash}\n"
        f"PHONE={phone}\n"
        f"SESSION_NAME={session_name}\n"
        f"DB_PATH={db_path}\n"
        "MONITOR_INTERVAL_HOURS=6\n"
        "REACTION_POSTS_LIMIT=100\n"
        "RATE_LIMIT_DELAY=1.0\n"
    )

    def _open_private(path, flags):
        return os.open(path, flags, 0o600)

    with open(".env", "w", encoding="utf-8", opener=_open_private) as f:
        f.write(env_content)

    console.print()
    console.print("[green].env written.[/green] Testing authentication — Telegram will send you a code...")
    console.print()

    # Step 6: Test auth
    async def _test_auth() -> None:
        from telethon import TelegramClient
        client = TelegramClient(session_name, api_id, api_hash)
        await asyncio.wait_for(client.start(phone=phone), timeout=120)
        await client.disconnect()

    try:
        asyncio.run(_test_auth())
    except Exception as exc:
        # Clean up .env on failure so next run starts fresh
        if os.path.exists(".env"):
            os.remove(".env")
        console.print(f"[bold red]Authentication failed:[/bold red] {exc}")
        sys.exit(1)

    console.print()
    console.print("[bold green]✓ Authentication successful! Session saved.[/bold green]")
    console.print(f"  Session file: [cyan]{session_name}.session[/cyan]")
    console.print(f"  Database    : [cyan]{db_path}[/cyan]")
    console.print()
    console.print("You can now run [bold]telint[/bold].")


if __name__ == "__main__":
    main()
