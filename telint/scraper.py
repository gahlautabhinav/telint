"""
Scraping strategies for telint.

All public functions return (members_found: int, new_members: int).
"""

import asyncio

from telethon.errors import FloodWaitError
from telethon.tl.functions.channels import GetFullChannelRequest, GetParticipantsRequest
from telethon.tl.functions.messages import GetMessageReactionsListRequest

from config import settings
from telint import storage
from telint.auth import get_client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_or_create_target(handle: str, type_: str, display_name: str) -> int:
    """Get target_id from DB, creating if missing."""
    target = await storage.get_target(handle)
    if target is None:
        return await storage.add_target(handle, type_, display_name)
    return target["id"]


async def _rate_sleep() -> None:
    await asyncio.sleep(settings.rate_limit_delay)


def _clean_handle(handle: str) -> str:
    """Strip leading @ from handle."""
    return handle.lstrip("@")


# ---------------------------------------------------------------------------
# Strategy 1: Group members
# ---------------------------------------------------------------------------

async def scrape_group_members(handle: str) -> tuple[int, int]:
    """
    Scrape all participants of a group/supergroup.

    Returns (members_found, new_members).
    """
    handle = _clean_handle(handle)
    client = await get_client()

    entity = await client.get_entity(handle)

    target_id = await _get_or_create_target(
        handle,
        "group",
        getattr(entity, "title", handle),
    )

    total_found = 0
    new_count = 0
    batch_counter = 0

    # get_participants with aggressive=True fetches all members even in large groups
    participants = await client.get_participants(entity, aggressive=True)

    for user in participants:
        # Skip deleted accounts
        if getattr(user, "deleted", False):
            continue

        total_found += 1
        batch_counter += 1

        is_new = await storage.upsert_member(
            target_id=target_id,
            user_id=user.id,
            username=getattr(user, "username", None),
            first_name=getattr(user, "first_name", None),
            last_name=getattr(user, "last_name", None),
            phone=getattr(user, "phone", None),
            is_bot=bool(getattr(user, "bot", False)),
            scraped_via="group_members",
        )
        if is_new:
            new_count += 1

        # Rate limit every 100 participants
        if batch_counter % 100 == 0:
            await _rate_sleep()

    await storage.update_last_scraped(target_id)
    return total_found, new_count


# ---------------------------------------------------------------------------
# Strategy 2: Channel reactions
# ---------------------------------------------------------------------------

async def scrape_channel_reactions(
    handle: str, posts_limit: int = None
) -> tuple[int, int]:
    """
    Scrape users who reacted to recent channel posts.

    Returns (members_found, new_members).
    """
    if posts_limit is None:
        posts_limit = settings.reaction_posts_limit

    handle = _clean_handle(handle)
    client = await get_client()

    entity = await client.get_entity(handle)

    target_id = await _get_or_create_target(
        handle,
        "channel",
        getattr(entity, "title", handle),
    )

    total_found = 0
    new_count = 0

    messages = await client.get_messages(entity, limit=posts_limit)

    for message in messages:
        if message is None or not hasattr(message, "id"):
            continue

        offset_id = ""
        while True:
            try:
                result = await client(
                    GetMessageReactionsListRequest(
                        peer=entity,
                        id=message.id,
                        reaction=None,
                        limit=100,
                        offset=offset_id,
                    )
                )
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds + 1)
                result = await client(
                    GetMessageReactionsListRequest(
                        peer=entity,
                        id=message.id,
                        reaction=None,
                        limit=100,
                        offset=offset_id,
                    )
                )

            for user in result.users:
                if getattr(user, "deleted", False):
                    continue

                total_found += 1
                is_new = await storage.upsert_member(
                    target_id=target_id,
                    user_id=user.id,
                    username=getattr(user, "username", None),
                    first_name=getattr(user, "first_name", None),
                    last_name=getattr(user, "last_name", None),
                    phone=getattr(user, "phone", None),
                    is_bot=bool(getattr(user, "bot", False)),
                    scraped_via="reaction",
                )
                if is_new:
                    new_count += 1

            if not result.next_offset:
                break
            offset_id = result.next_offset

        # Rate limit between messages
        await _rate_sleep()

    await storage.update_last_scraped(target_id)
    return total_found, new_count


# ---------------------------------------------------------------------------
# Strategy 3: Full channel (reactions + linked group)
# ---------------------------------------------------------------------------

async def scrape_channel_full(handle: str) -> tuple[int, int]:
    """
    Combine reaction scraping with linked-group member scraping.

    Returns combined (total_found, new_members) deduplicated by user_id.
    """
    handle = _clean_handle(handle)
    client = await get_client()

    entity = await client.get_entity(handle)

    target_id = await _get_or_create_target(
        handle,
        "channel",
        getattr(entity, "title", handle),
    )

    seen_user_ids: set[int] = set()
    total_found = 0
    new_count = 0

    # --- Part A: reactions ---
    posts_limit = settings.reaction_posts_limit
    messages = await client.get_messages(entity, limit=posts_limit)

    for message in messages:
        if message is None or not hasattr(message, "id"):
            continue

        offset_id = ""
        while True:
            try:
                result = await client(
                    GetMessageReactionsListRequest(
                        peer=entity,
                        id=message.id,
                        reaction=None,
                        limit=100,
                        offset=offset_id,
                    )
                )
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds + 1)
                result = await client(
                    GetMessageReactionsListRequest(
                        peer=entity,
                        id=message.id,
                        reaction=None,
                        limit=100,
                        offset=offset_id,
                    )
                )

            for user in result.users:
                if getattr(user, "deleted", False):
                    continue

                total_found += 1
                is_new = await storage.upsert_member(
                    target_id=target_id,
                    user_id=user.id,
                    username=getattr(user, "username", None),
                    first_name=getattr(user, "first_name", None),
                    last_name=getattr(user, "last_name", None),
                    phone=getattr(user, "phone", None),
                    is_bot=bool(getattr(user, "bot", False)),
                    scraped_via="reaction",
                )
                if is_new and user.id not in seen_user_ids:
                    new_count += 1
                seen_user_ids.add(user.id)

            if not result.next_offset:
                break
            offset_id = result.next_offset

        await _rate_sleep()

    # --- Part B: linked group members ---
    try:
        full = await client(GetFullChannelRequest(entity))
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 1)
        full = await client(GetFullChannelRequest(entity))

    linked_chat_id = getattr(full.full_chat, "linked_chat_id", None)
    if linked_chat_id:
        try:
            linked_entity = await client.get_entity(linked_chat_id)
            participants = await client.get_participants(linked_entity, aggressive=True)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 1)
            linked_entity = await client.get_entity(linked_chat_id)
            participants = await client.get_participants(linked_entity, aggressive=True)

        batch_counter = 0
        for user in participants:
            if getattr(user, "deleted", False):
                continue

            total_found += 1
            batch_counter += 1

            is_new = await storage.upsert_member(
                target_id=target_id,
                user_id=user.id,
                username=getattr(user, "username", None),
                first_name=getattr(user, "first_name", None),
                last_name=getattr(user, "last_name", None),
                phone=getattr(user, "phone", None),
                is_bot=bool(getattr(user, "bot", False)),
                scraped_via="group_members",
            )
            if is_new and user.id not in seen_user_ids:
                new_count += 1
            seen_user_ids.add(user.id)

            if batch_counter % 100 == 0:
                await _rate_sleep()

    await storage.update_last_scraped(target_id)
    return total_found, new_count
