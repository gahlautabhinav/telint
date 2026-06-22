"""
Scraping strategies for telint.

All public functions return (members_found: int, new_members: int).
"""

import asyncio

from telethon.errors import FloodWaitError
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import (
    ChannelParticipantsAdmins,
    ChannelParticipantCreator,
    MessageMediaPhoto,
    MessageMediaDocument,
)
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


def _detect_media_type(media) -> str | None:
    """Detect media type string from a Telethon media object."""
    if media is None:
        return None
    if isinstance(media, MessageMediaPhoto):
        return 'photo'
    if isinstance(media, MessageMediaDocument):
        return 'document'
    return type(media).__name__.replace('MessageMedia', '').lower() or None


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
    try:
        participants = await client.get_participants(entity, aggressive=True)
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 1)
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


# ---------------------------------------------------------------------------
# Strategy 4: Admins
# ---------------------------------------------------------------------------

async def scrape_admins(handle: str) -> tuple[int, int]:
    """
    Scrape admin participants of a group/channel.

    Returns (admins_found, new_members).
    """
    handle = _clean_handle(handle)
    client = await get_client()

    entity = await client.get_entity(handle)
    type_ = "group" if getattr(entity, 'megagroup', False) else "channel"

    target_id = await _get_or_create_target(handle, type_, getattr(entity, "title", handle))

    try:
        admins = await client.get_participants(entity, filter=ChannelParticipantsAdmins())
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 1)
        admins = await client.get_participants(entity, filter=ChannelParticipantsAdmins())

    total_found = 0
    new_count = 0

    for user in admins:
        if getattr(user, "deleted", False):
            continue

        participant = getattr(user, "participant", None)
        admin_title = None
        if participant is not None:
            admin_title = getattr(participant, "title", None) or None
            if isinstance(participant, ChannelParticipantCreator) and not admin_title:
                admin_title = "Creator"

        total_found += 1

        is_new = await storage.upsert_member(
            target_id=target_id,
            user_id=user.id,
            username=getattr(user, "username", None),
            first_name=getattr(user, "first_name", None),
            last_name=getattr(user, "last_name", None),
            phone=getattr(user, "phone", None),
            is_bot=bool(getattr(user, "bot", False)),
            scraped_via='group_members',
            is_admin=False,
            admin_title=None,
        )
        await storage.set_member_admin(target_id, user.id, True, admin_title)

        if is_new:
            new_count += 1

    await storage.update_last_scraped(target_id)
    return total_found, new_count


# ---------------------------------------------------------------------------
# Strategy 5: Messages
# ---------------------------------------------------------------------------

async def scrape_messages(handle: str, limit: int = None) -> tuple[int, int]:
    """
    Scrape recent messages from a group/channel.

    Returns (messages_saved, new_senders).
    """
    if limit is None:
        limit = settings.message_scrape_limit

    handle = _clean_handle(handle)
    client = await get_client()

    entity = await client.get_entity(handle)
    type_ = "group" if getattr(entity, 'megagroup', False) else "channel"

    target_id = await _get_or_create_target(handle, type_, getattr(entity, "title", handle))

    try:
        messages = await client.get_messages(entity, limit=limit)
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 1)
        messages = await client.get_messages(entity, limit=limit)

    messages_saved = 0
    new_senders = 0
    seen_sender_ids: set[int] = set()

    for message in messages:
        if message is None or not hasattr(message, "id"):
            continue

        sender = getattr(message, "sender", None)
        sender_user_id = None
        sender_username = None
        sender_first_name = None
        sender_last_name = None
        sender_phone = None
        sender_is_bot = False

        if sender is not None and hasattr(sender, 'first_name'):
            sender_user_id = getattr(sender, "id", None)
            sender_username = getattr(sender, "username", None)
            sender_first_name = getattr(sender, "first_name", None)
            sender_last_name = getattr(sender, "last_name", None)
            sender_phone = getattr(sender, "phone", None)
            sender_is_bot = bool(getattr(sender, "bot", False))
        elif message.sender_id is not None:
            sid = message.sender_id
            if hasattr(sid, "user_id"):
                sender_user_id = sid.user_id
            else:
                try:
                    sender_user_id = int(sid)
                except (TypeError, ValueError):
                    sender_user_id = None

        text = getattr(message, "text", None)
        date = message.date.replace(tzinfo=None).isoformat() if message.date else None
        media_type = _detect_media_type(getattr(message, "media", None))
        reply_to = getattr(message.reply_to, "reply_to_msg_id", None) if message.reply_to else None

        is_new_msg = await storage.upsert_message(
            target_id, message.id, sender_user_id, sender_username,
            sender_first_name, sender_last_name, text, date, media_type, reply_to,
        )
        if is_new_msg:
            messages_saved += 1

        if sender is not None and hasattr(sender, 'first_name') and sender_user_id is not None:
            if not getattr(sender, "deleted", False):
                is_new_sender = await storage.upsert_member(
                    target_id=target_id,
                    user_id=sender_user_id,
                    username=sender_username,
                    first_name=sender_first_name,
                    last_name=sender_last_name,
                    phone=sender_phone,
                    is_bot=sender_is_bot,
                    scraped_via='messages',
                )
                if is_new_sender and sender_user_id not in seen_sender_ids:
                    new_senders += 1
                seen_sender_ids.add(sender_user_id)

    await storage.update_last_scraped(target_id)
    return messages_saved, new_senders
