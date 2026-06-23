import logging
from pyrogram import Client, filters, enums
from pyrogram.types import ChatJoinRequest
from database.users_chats_db import db
from info import ADMINS, AUTH_CHANNEL

logger = logging.getLogger(__name__)

# Cache the resolved numeric chat ID so we only call get_chat() once.
_auth_channel_id = None

async def _get_auth_channel_id(client):
    """Resolve AUTH_CHANNEL to a numeric ID (works for both @username and -100xxx)."""
    global _auth_channel_id
    if _auth_channel_id is not None:
        return _auth_channel_id
    try:
        chat = await client.get_chat(AUTH_CHANNEL)
        _auth_channel_id = chat.id
    except Exception as e:
        logger.error(f"Could not resolve AUTH_CHANNEL '{AUTH_CHANNEL}': {e}")
        _auth_channel_id = AUTH_CHANNEL  # fallback to raw value
    return _auth_channel_id

if AUTH_CHANNEL:
    # Use no chat filter here — filter manually inside the handler.
    # filters.chat(AUTH_CHANNEL) breaks for public channels because
    # Telegram delivers join-request updates with the numeric chat ID,
    # but AUTH_CHANNEL may be stored as a @username string, causing the
    # filter to never match.
    @Client.on_chat_join_request()
    async def join_reqs(client, message: ChatJoinRequest):
        resolved_id = await _get_auth_channel_id(client)
        if message.chat.id != resolved_id:
            return  # not our channel
        try:
            if not await db.find_join_req(message.from_user.id):
                await db.add_join_req(message.from_user.id)
        except Exception as e:
            logger.error(f"join_reqs DB error for user {message.from_user.id}: {e}")

async def auto_approve_join_request(client, user_id: int):
    """
    Approve a pending join request for user_id in AUTH_CHANNEL.
    Call this after the user completes the verify step so they are admitted
    automatically without any manual intervention.
    """
    if not AUTH_CHANNEL:
        return
    try:
        resolved_id = await _get_auth_channel_id(client)
#this repo created and maintained by @muja_tg18
        await client.approve_chat_join_request(resolved_id, user_id)
        logger.info(f"Auto-approved join request for user {user_id} in {resolved_id}")
    except Exception as e:
        logger.warning(f"auto_approve_join_request failed for user {user_id}: {e}")

@Client.on_message(filters.command("delreq") & filters.private & filters.user(ADMINS))
async def del_requests(client, message):
    await db.del_join_req()
    await message.reply("<b>⚙ ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ᴄʜᴀɴɴᴇʟ ʟᴇғᴛ ᴜꜱᴇʀꜱ ᴅᴇʟᴇᴛᴇᴅ</b>")