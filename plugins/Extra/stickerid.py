import os
import glob
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ✅ Fixed: Removed standalone Client() creation and hardcoded credentials
# ✅ Fixed: Use your main bot's Client via @Client.on_message decorators

DOWNLOAD_LOCATION = os.environ.get("DOWNLOAD_LOCATION", "./DOWNLOADS/")
os.makedirs(DOWNLOAD_LOCATION, exist_ok=True)

JOIN_BUTTON = InlineKeyboardMarkup(
    [[InlineKeyboardButton('↗ Join Here ↗', url='https://t.me/riouptades1')]]
)


@Client.on_message(filters.command(["start_sticker"]) & (filters.private | filters.group))  # ✅ Fixed: | not &
async def start_sticker(bot, update):
    text = f"Hi {update.from_user.mention}, I'm Sticker Bot.\n\nI can Provide all Kind of Sticker Options Here 😊"
    await update.reply_text(
        text=text,
        disable_web_page_preview=True,
        reply_markup=JOIN_BUTTON,
        quote=True
    )


@Client.on_message(filters.command(["ping"]) & (filters.private | filters.group))
async def ping(bot, message):
    start_t = time.time()
    rm = await message.reply_text("Checking...")
    end_t = time.time()
    time_taken_s = (end_t - start_t) * 1000
    await rm.edit(f"🏓 Pong!\n`{time_taken_s:.3f} ms`")


@Client.on_message(filters.command(["getsticker"]) & (filters.private | filters.group))
async def getstickerasfile(bot, message):
    if not message.reply_to_message or not message.reply_to_message.sticker:
        return await message.reply_text("❌ Reply to a sticker to use this command.")
    try:
        tx = await message.reply_text("⬇️ Downloading...")
        file_path = DOWNLOAD_LOCATION + f"{message.chat.id}.WEBM"
        await message.reply_to_message.download(file_path)
        await tx.edit("📤 Uploading...")
        await message.reply_document(file_path, caption="©NASRANI_UPDATE")
        await tx.delete()
        os.remove(file_path)
    except Exception as error:
        print(error)
        await message.reply_text(f"❌ Error: `{str(error)}`")


@Client.on_message(filters.command(["clearcache"]) & (filters.private | filters.group))  # ✅ Fixed: | not &
async def clearcache(bot, message):
    txt = await message.reply_text("🔍 Checking Cache...")
    await txt.edit("🗑️ Clearing cache...")
    dir_path = DOWNLOAD_LOCATION
    filelist = glob.glob(os.path.join(dir_path, "*"))
    count = 0  # ✅ Fixed: initialize count to avoid UnboundLocalError when filelist is empty
    for f in filelist:
        os.remove(f)
        count += 1
    await txt.edit(f"✅ Cleared {count} file(s)")
    await txt.delete()


@Client.on_message(filters.command(["stickerid"]) & (filters.private | filters.group))
async def stickerid(bot, message):
    if not message.reply_to_message:
        return await message.reply("❌ Reply to a sticker.")
    if message.reply_to_message.sticker:
        await message.reply(
            f"**Sticker ID:**\n`{message.reply_to_message.sticker.file_id}`\n\n"
            f"**Unique ID:**\n`{message.reply_to_message.sticker.file_unique_id}`",
            quote=True
        )
    else:
        await message.reply("❌ Oops! That's not a sticker.")


@Client.on_message(filters.command(["findsticker"]) & (filters.private | filters.group))  # ✅ Fixed: | not &
async def findsticker(bot, message):
    if not message.reply_to_message or not message.reply_to_message.text:
        return await message.reply_text("❌ Reply to a message containing a sticker file ID.")
    try:
        txt = await message.reply_text("🔍 Validating Sticker ID...")
        sticker_id = str(message.reply_to_message.text)
        chat_id = str(message.chat.id)
        await txt.delete()
        await bot.send_sticker(chat_id, sticker_id)
    except Exception as error:
        await message.reply_text(f"❌ Not a Valid File ID: `{str(error)}`")
