import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from telegraph import Telegraph

# Telegraph only accepts these extensions
ALLOWED_EXT = {'.jpg', '.jpeg', '.png', '.gif', '.mp4'}


def get_file_id(message):
    """Extract file info from a message. Returns file_id or None."""
    if message.photo:
        return message.photo.file_id
    elif message.video:
        return message.video.file_id
    elif message.document:
        return message.document.file_id
    elif message.animation:
        return message.animation.file_id
    return None


@Client.on_message(filters.command("telegraph") & (filters.private | filters.group))
async def telegraph_upload(bot, update):
    replied = update.reply_to_message

    if not replied:
        await update.reply_text(
            "📎 Reply to a **photo, GIF, or MP4 video** (under 5 MB) to upload it to Telegraph."
        )
        return

    file_id = get_file_id(replied)
    if not file_id:
        await update.reply_text("❌ Not supported! Reply to a photo, GIF, video (mp4), or document.")
        return

    text = await update.reply_text(
        "<code>⬇️ Downloading to server...</code>", disable_web_page_preview=True
    )

    media = await update.reply_to_message.download()

    # ── Validate file extension before attempting upload ────────────────────
    _, ext = os.path.splitext(media)
    if ext.lower() not in ALLOWED_EXT:
        await text.edit_text(
            f"❌ Telegraph only supports: <code>.jpg .jpeg .png .gif .mp4</code>\n"
            f"Your file has extension <code>{ext or 'none'}</code>.",
            disable_web_page_preview=True
        )
        if os.path.exists(media):
            os.remove(media)
        return

    await text.edit_text(
        "<code>✅ Downloaded. Uploading to telegra.ph...</code>", disable_web_page_preview=True
    )

    try:
        # Use Telegraph().upload_file() — the modern non-deprecated API.
        # Returns a list of dicts: [{'src': '/file/xxxxxx.jpg'}]
        t = Telegraph()
        response = t.upload_file(media)
        src_path = response[0]['src']             # '/file/xxxxxx.jpg'
    except Exception as error:
        print(error)
        await text.edit_text(
            f"❌ Upload Error: <code>{error}</code>", disable_web_page_preview=True
        )
        if os.path.exists(media):
            os.remove(media)
        return
    finally:
        if os.path.exists(media):
            try:
                os.remove(media)
            except Exception as e:
                print(e)

    graph_url = f"https://telegra.ph{src_path}"
    await text.edit_text(
        text=f"<b>✅ Uploaded!</b>\n\n<code>{graph_url}</code>",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(text="🔗 Open Link", url=graph_url),
            InlineKeyboardButton(text="📤 Share Link",
                                 url=f"https://telegram.me/share/url?url={graph_url}")
        ], [
            InlineKeyboardButton(text="✗ Close ✗", callback_data="close")
        ]])
    )