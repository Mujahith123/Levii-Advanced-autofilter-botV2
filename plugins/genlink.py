import re
import asyncio
from pyrogram import filters, Client, enums
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, UsernameInvalid, UsernameNotModified
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import ADMINS, LOG_CHANNEL, FILE_STORE_CHANNEL, PUBLIC_FILE_STORE
from database.ia_filterdb import unpack_new_file_id
from utils import temp
import os
import json
import base64
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Tracks active interactive batch sessions: {user_id: {"files": [], "cancelled": bool}}
_batch_sessions = {}

# Supported media types for batch collection
_MEDIA_TYPES = (
    enums.MessageMediaType.VIDEO,
    enums.MessageMediaType.AUDIO,
    enums.MessageMediaType.DOCUMENT,
    enums.MessageMediaType.PHOTO,
    enums.MessageMediaType.STICKER,
    enums.MessageMediaType.ANIMATION,
    enums.MessageMediaType.VOICE,
    enums.MessageMediaType.VIDEO_NOTE,
)

async def allowed(_, __, message):
    if PUBLIC_FILE_STORE:
        return True
    if message.from_user and message.from_user.id in ADMINS:
        return True
    return False

@Client.on_message(filters.command(['link', 'plink']) & filters.create(allowed))
async def gen_link_s(bot, message):
    replied = message.reply_to_message
    if not replied:
        return await message.reply('Reply to a message to get a shareable link.')
    file_type = replied.media
    if file_type not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
        return await message.reply("Reply to a supported media")
    if message.has_protected_content and message.chat.id not in ADMINS:
        return await message.reply("okDa")
    file_id, ref = unpack_new_file_id((getattr(replied, file_type.value)).file_id)
    string = 'filep_' if message.text.lower().strip() == "/plink" else 'file_'
    string += file_id
    outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
    await message.reply(f"Here is your Link:\nhttps://t.me/{temp.U_NAME}?start={outstr}")


def _extract_file_entry(message, protect: bool) -> dict | None:
    """
    Extract a file entry dict from a Pyrogram message.
    Returns None if the message contains no supported media.
    """
    file_type = message.media
    if file_type is None or file_type not in _MEDIA_TYPES:
        return None
    try:
        media_obj = getattr(message, file_type.value, None)
        if media_obj is None:
            return None
        file_id = getattr(media_obj, "file_id", None)
        if not file_id:
            return None
        caption = ""
        if message.caption:
            try:
                caption = message.caption.html
            except Exception:
                caption = str(message.caption)
        return {
            "file_id": file_id,
            "caption": caption,
            "title": getattr(media_obj, "file_name", "") or "",
            "size": getattr(media_obj, "file_size", 0) or 0,
            "protect": protect,
        }
    except Exception as e:
        logger.warning(f"_extract_file_entry error: {e}")
        return None


# ── Callback: Cancel button during interactive batch session ───────────────
@Client.on_callback_query(filters.regex(r"^cancel_batch_\d+$"))
async def _cancel_batch(bot, callback_query):
    """Handle Cancel button press during an active batch session."""
    if not callback_query.from_user:
        return
    user_id = callback_query.from_user.id
    session = _batch_sessions.get(user_id)
    if session is None:
        await callback_query.answer("No active batch session.", show_alert=False)
        return
    session["cancelled"] = True
    await callback_query.answer("Batch cancelled.", show_alert=False)
    try:
        await callback_query.message.edit_text("❌ <b>Batch process has been cancelled.</b>")
    except Exception:
        pass


# ── Handler: collect files during an active interactive batch session ──────
# IMPORTANT: this filter must only match when the sender has a genuinely
# active /batch session. The filter previously matched ANY private media
# message (forwarded or not), which meant it silently swallowed messages
# — including files forwarded for indexing — before plugins/index.py ever
# got a chance to see them (handlers run in registration/file order within
# the same group, and the first match wins). Checking the session state in
# the filter itself (not just in the handler body) ensures unrelated media
# messages fall through to other handlers, such as the indexing flow.
async def _has_active_batch_session(_, __, message):
    if not message.from_user:
        return False
    session = _batch_sessions.get(message.from_user.id)
    return bool(session and not session.get("cancelled"))

@Client.on_message(
    filters.private
    & filters.incoming
    & filters.media
    & filters.create(_has_active_batch_session)
    & ~filters.command(["batch", "pbatch", "link", "plink", "start", "help"])
)
async def _collect_batch_file(bot, message):
    """Collect any media message sent during an active batch session."""
    if not message.from_user:
        return
    user_id = message.from_user.id
    session = _batch_sessions.get(user_id)
    if session is None or session.get("cancelled"):
        return
    # Only process messages that have supported media
    if message.media is None:
        return
    entry = _extract_file_entry(message, session.get("protect", False))
    if entry is None:
        return
    session["files"].append(entry)
    # Acknowledge receipt so user knows the file was captured
    count = len(session["files"])
    try:
        await message.reply(
            f"✅ File {count} added to batch.",
            quote=True,
        )
    except Exception:
        pass


# ── Main batch command handler ─────────────────────────────────────────────
@Client.on_message(filters.command(['batch', 'pbatch']) & filters.create(allowed))
async def gen_link_batch(bot, message):
    # ── Interactive mode: /batch (no arguments) ────────────────────────────
    if " " not in message.text:
        user_id = message.from_user.id
        cmd = message.text.strip().split()[0].lower()
        protect = (cmd == "/pbatch")

        # Start a new session (overwrite any stale one)
        _batch_sessions[user_id] = {"files": [], "cancelled": False, "protect": protect}

        cancel_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_batch_{user_id}")]
        ])
        prompt = await message.reply(
            "📂 <b>Send your files within 1 minute.</b>\n"
            "Each file will be confirmed with a ✅ reply.",
            reply_markup=cancel_markup,
        )

        # Wait 60 seconds while _collect_batch_file fills the session
        await asyncio.sleep(60)

        session = _batch_sessions.pop(user_id, None)
        if session is None:
            return

        # User pressed Cancel – message already edited by _cancel_batch
        if session.get("cancelled"):
            return

        collected = session.get("files", [])

        # Nothing was sent within the window
        if not collected:
            try:
                await prompt.edit_text(
                    "⏰ <b>Your time has expired. Please try again.</b>",
                    reply_markup=None,
                )
            except Exception:
                pass
            return

        # Build the batch link
        try:
            await prompt.edit_text(
                f"⚙️ <b>Processing {len(collected)} file(s)…</b>",
                reply_markup=None,
            )
        except Exception:
            pass

        json_path = f"batchmode_{user_id}.json"
        with open(json_path, "w+") as out:
            json.dump(collected, out)

        if not LOG_CHANNEL:
            try:
                await prompt.edit_text(
                    "❌ <b>LOG_CHANNEL is not set. Cannot store batch file.</b>\n"
                    "Please set the <code>LOG_CHANNEL</code> env variable."
                )
            except Exception:
                pass
            os.remove(json_path)
            return

        post = await bot.send_document(
            LOG_CHANNEL,
            json_path,
            file_name="Batch.json",
            caption="⚠️ Generated for filestore.",
        )
        os.remove(json_path)

        # Encode as "chat_id:msg_id" — far shorter than a raw file_id string,
        # keeping the ?start= parameter well under Telegram's 64-character limit.
        compact = f"{post.chat.id}:{post.id}"
        encoded = base64.urlsafe_b64encode(compact.encode()).decode().strip("=")
        batch_link = f"https://t.me/{temp.U_NAME}?start=BATCH-{encoded}"
        link_text = (
            f"✅ <b>Batch link created!</b>\n"
            f"Contains <code>{len(collected)}</code> file(s).\n"
            f"🔗 <code>{batch_link}</code>"
        )
        # Always send a fresh message — editing the prompt after 60 s is unreliable
        # because Telegram may have already invalidated it (cancel press, timeout, etc.)
        try:
            await prompt.delete()
        except Exception:
            pass
        await bot.send_message(chat_id=user_id, text=link_text)
        return

    # ── URL-range mode: /batch url1 url2  (original behaviour, unchanged) ──
    links = message.text.strip().split(" ")
    if len(links) != 3:
        return await message.reply("Use correct format.\nExample <code>/batch https://t.me/TeamEvamaria/10 https://t.me/TeamEvamaria/20</code>.")
    cmd, first, last = links
    regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
    match = regex.match(first)
    if not match:
        return await message.reply('Invalid link')
    f_chat_id = match.group(4)
    f_msg_id = int(match.group(5))
    if f_chat_id.isnumeric():
        f_chat_id  = int(("-100" + f_chat_id))

    match = regex.match(last)
    if not match:
        return await message.reply('Invalid link')
    l_chat_id = match.group(4)
    l_msg_id = int(match.group(5))
    if l_chat_id.isnumeric():
        l_chat_id  = int(("-100" + l_chat_id))

    if f_chat_id != l_chat_id:
        return await message.reply("Chat ids not matched.")
    try:
        chat_id = (await bot.get_chat(f_chat_id)).id
    except ChannelInvalid:
        return await message.reply('This may be a private channel / group. Make me an admin over there to index the files.')
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply('Invalid Link specified.')
    except Exception as e:
        return await message.reply(f'Errors - {e}')

    sts = await message.reply("Generating link for your message.\nThis may take time depending upon number of messages")
    if chat_id in FILE_STORE_CHANNEL:
        string = f"{f_msg_id}_{l_msg_id}_{chat_id}_{cmd.lower().strip()}"
        b_64 = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
        return await sts.edit(f"Here is your link https://t.me/{temp.U_NAME}?start=DSTORE-{b_64}")

    FRMT = "Generating Link...\nTotal Messages: `{total}`\nDone: `{current}`\nRemaining: `{rem}`\nStatus: `{sts}`"

    outlist = []

    # file store without db channel
    og_msg = 0
    tot = 0
    async for msg in bot.iter_messages(f_chat_id, l_msg_id, f_msg_id):
        tot += 1
        if msg.empty or msg.service:
            continue
        if not msg.media:
            # only media messages supported.
            continue
        try:
            file_type = msg.media
            file = getattr(msg, file_type.value)
            caption = getattr(msg, 'caption', '')
            if caption:
                caption = caption.html
            if file:
                file = {
                    "file_id": file.file_id,
                    "caption": caption,
                    "title": getattr(file, "file_name", ""),
                    "size": file.file_size,
                    "protect": cmd.lower().strip() == "/pbatch",
                }

                og_msg +=1
                outlist.append(file)
        except:
            pass
        if not og_msg % 20:
            try:
                await sts.edit(FRMT.format(total=l_msg_id-f_msg_id, current=tot, rem=((l_msg_id-f_msg_id) - tot), sts="Saving Messages"))
            except:
                pass
    with open(f"batchmode_{message.from_user.id}.json", "w+") as out:
        json.dump(outlist, out)
    if not LOG_CHANNEL:
        await sts.edit("❌ LOG_CHANNEL is not set. Cannot store batch file. Please set the LOG_CHANNEL env variable.")
        os.remove(f"batchmode_{message.from_user.id}.json")
        return
    post = await bot.send_document(LOG_CHANNEL, f"batchmode_{message.from_user.id}.json", file_name="Batch.json", caption="⚠️Generated for filestore.")
    os.remove(f"batchmode_{message.from_user.id}.json")
    # Encode as "chat_id:msg_id" — far shorter than a raw file_id string,
    # keeping the ?start= parameter well under Telegram's 64-character limit.
    compact = f"{post.chat.id}:{post.id}"
    encoded = base64.urlsafe_b64encode(compact.encode()).decode().strip("=")
    batch_link = f"https://t.me/{temp.U_NAME}?start=BATCH-{encoded}"
    await sts.edit(f"Here is your link\nContains `{og_msg}` files.\n{batch_link}")