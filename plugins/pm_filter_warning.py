"""
PM Filter Warning
- TEXT_FILTER = Yes -> search files in PM, shortlink/verify gate for free users
- TEXT_FILTER = No  -> show join group warning

Gate Priority:
  Premium user     → Direct results (no gate)
  Verified user    → Direct results (within verify window)
  VERIFY=True      → Verify gate
  IS_SHORTLINK=True → Shortlink gate (commands.py exact format)
  None             → Direct results
"""

import re
import math
import random
import string
import asyncio
import logging
import sys
import pytz
from datetime import datetime, timedelta

from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty

from info import (
    TEXT_FILTER, LOG_CHANNEL, NO_RESULTS_MSG,
    GRP_LNK, IS_SHORTLINK, VERIFY,
    TUTORIAL_LINK_1, TUTORIAL_LINK_2,
    PREMIUM_USER, AUTO_DELETE,
    PM_IMDB, IMDB_TEMPLATE
)
from database.ia_filterdb import get_search_results
from database.users_chats_db import db
from utils import temp, get_size, get_verify_shortlink, get_shortlink, get_tutorial, get_poster
from Script import script
# Feature integrations
from plugins.new_features import (
    record_not_found,
)

logger = logging.getLogger(__name__)


def _get_fresh():
    mod = sys.modules.get("plugins.pm_filter")
    if mod and hasattr(mod, "FRESH"):
        return mod.FRESH
    return {}


def _get_page_cache():
    mod = sys.modules.get("plugins.pm_filter")
    if mod and hasattr(mod, "PAGE_CACHE"):
        return mod.PAGE_CACHE
    return {}


def _clean_search(raw_text):
    search = raw_text.lower()
    find = search.split(" ")
    search = ""
    removes = ["in", "upload", "series", "full", "horror", "thriller", "mystery", "print", "file"]
    for x in find:
        if x not in removes:
            search = search + x + " "
    search = re.sub(
        r"\b(pl(i|e)*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)"
        r"|movie(s)?|new|latest|bro|bruh|broh|helo|that|find|dubbed|link"
        r"|venum|iruka|pannunga|pannungga|anuppunga|anupunga|anuppungga|anupungga"
        r"|film|undo|kitti|kitty|tharu|kittumo|kittum|movie|any(one)"
        r"|with\ssubtitle(s)?)", "", search, flags=re.IGNORECASE
    )
    search = re.sub(r"\s+", " ", search).strip()
    search = search.replace("-", " ").replace(":", "")
    return search


@Client.on_message(filters.private & filters.incoming & ~filters.bot & ~filters.me)
async def pm_handler(client: Client, message: Message):
    try:
        # Skip forwarded messages — index.py handles them (channel-link indexing flow)
        if getattr(message, "forward_date", None) or getattr(message, "forward_from_chat", None) or getattr(message, "forward_from", None):
            return
        text = message.text or message.caption
        if not text or text.startswith("/"):
            return
        if TEXT_FILTER:
            await pm_text_search(client, message, text)
        else:
            await show_pm_warning(client, message)
    except Exception as e:
        logger.error(f"PM Handler Error: {e}")


async def pm_text_search(client: Client, message: Message, raw_text: str):
    curr_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()

    if len(raw_text) >= 100:
        return

    if re.findall(r"((^\/|^,|^!|^\.|^[\U0001F600-\U000E007F]).*)", raw_text):
        return

    search = _clean_search(raw_text)
    if not search:
        return

    user_id = message.from_user.id

    # ─── GATE CHECK ───────────────────────────────────────────────────────────
    is_premium = await db.has_premium_access(user_id) or user_id in PREMIUM_USER

    if not is_premium:
        try:
            user_verified = await db.is_user_verified(user_id)
            is_second_shortener = await db.use_second_shortener(user_id)
        except Exception:
            user_verified = False
            is_second_shortener = False

        # ── Verify gate ──
        if VERIFY and (not user_verified or is_second_shortener):
            verify_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
            await db.create_verify_id(user_id, verify_id)
            how_to_link = TUTORIAL_LINK_2 if is_second_shortener else TUTORIAL_LINK_1
            verify_url = await get_verify_shortlink(
                f"https://telegram.me/{temp.U_NAME}?start=verify_{user_id}_{verify_id}",
                is_second_shortener
            )
            btn = [[
                InlineKeyboardButton("♻️ ᴄʟɪᴄᴋ ʜᴇʀᴇ ᴛᴏ ᴠᴇʀɪꜰʏ ♻️", url=verify_url)
            ], [
                InlineKeyboardButton("⁉️ ʜᴏᴡ ᴛᴏ ᴠᴇʀɪꜰʏ ⁉️", url=how_to_link)
            ]]
            bin_text = script.SECOND_VERIFICATION_TEXT if is_second_shortener else script.VERIFICATION_TEXT
            dlt = await message.reply_text(
                text=bin_text.format(message.from_user.mention),
                reply_markup=InlineKeyboardMarkup(btn),
                parse_mode=enums.ParseMode.HTML
            )
            await asyncio.sleep(120)
            try:
                await dlt.delete()
                await message.delete()
            except Exception:
                pass
            return

        # ── Shortlink gate — exact commands.py format ──
        elif IS_SHORTLINK and not VERIFY:
            # PM-ல chat_id = user_id → global SHORTLINK_URL/API fallback ✅
            g = await get_shortlink(user_id, f"https://telegram.me/{temp.U_NAME}?start=search")
            # Shortlink-ல get_tutorial use பண்றோம்
            # PM-ல group settings இல்ல → TUTORIAL (info.py) fallback ✅
            # Group-ல owner custom tutorial set பண்ணா → அது வருது ✅
            how_to_link = await get_tutorial(user_id)
            btn = [[
                InlineKeyboardButton('📁 Dᴏᴡɴʟᴏᴀᴅ Lɪɴᴋ 📁', url=g)
            ], [
                InlineKeyboardButton('⁉️ Hᴏᴡ Tᴏ Dᴏᴡɴʟᴏᴀᴅ ⁉️', url=how_to_link)
            ], [
                InlineKeyboardButton('💸 Buy Premium For Adz Free Movies ✅', callback_data='buy_premium')
            ]]
            dlt = await client.send_message(
                chat_id=user_id,
                text=f"<b>📕Nᴀᴍᴇ ➠ : <code>{search}</code>\n\n"
                     f"📂Fɪʟᴇ ʟɪɴᴋ ➠ : {g}\n\n"
                     f"<i>Note: This message is deleted in 20 minutes to avoid copyrights. "
                     f"Save the link to Somewhere else</i></b>",
                reply_markup=InlineKeyboardMarkup(btn)
            )
            await asyncio.sleep(1200)
            try:
                await dlt.edit("<b>Your message is successfully deleted!!!</b>")
            except Exception:
                pass
            return
    # ─── END GATE ─────────────────────────────────────────────────────────────

    m = await message.reply_text(f"<b><i> 𝖲𝖾𝖺𝗋𝖼𝗁𝗂𝗇𝗀 𝖿𝗈𝗋 '{search}' 🔎</i></b>")

    original_search = search

    files, offset, total_results = await get_search_results(
        user_id, search, offset=0, filter=True
    )

    if not files:
        await m.delete()

        # ── Feature 1: log content gap ────────────────────────────────────
        asyncio.create_task(record_not_found(
            original_search,
            user_id=user_id,
            group_id=None,   # PM — no group
            group_title=None,
        ))

        # ── Feature 2: smart Request button (callback, saves to DB) ──────
        req_btn = [
            [
                InlineKeyboardButton(
                    "🔍 Search Google",
                    url="https://www.google.com/search?q=" + search.replace(" ", "+") + "+movie"
                ),
                InlineKeyboardButton(
                    "📩 Request Movie",
                    callback_data=f"autoreq#{search[:50]}"
                )
            ]
        ]

        hint = "\n\nYou can request the movie below!"
        no_res = await message.reply_text(
            "<b>No Results Found for: " + search + "</b>\n\n"
            "Try:\n• Check spelling\n• Search with year\n• Use English name"
            + hint,
            reply_markup=InlineKeyboardMarkup(req_btn)
        )
        if NO_RESULTS_MSG and LOG_CHANNEL:
            try:
                await client.send_message(
                    chat_id=LOG_CHANNEL,
                    text="No PM Results | User: " + str(user_id) + " | Query: " + search
                )
            except Exception:
                pass
        await asyncio.sleep(30)
        try:
            await no_res.delete()
        except Exception:
            pass
        return

    # Build key and store for filter callbacks
    key = f"{message.chat.id}-{message.id}"
    _get_fresh()[key] = search

    if not hasattr(temp, 'GETALL') or temp.GETALL is None:
        temp.GETALL = {}
    if not hasattr(temp, 'SHORT') or temp.SHORT is None:
        temp.SHORT = {}

    temp.GETALL[key] = files
    temp.SHORT[user_id] = message.chat.id

    # ── TMDB / IMDB info fetch ────────────────────────────────────────────────
    imdb = None
    if PM_IMDB:
        try:
            imdb = await get_poster(search, file=files[0].file_name)
        except Exception as e:
            logger.exception(f"TMDB fetch failed in PM: {e}")
            imdb = None

    # ── Build caption ─────────────────────────────────────────────────────────
    if imdb:
        # Rich TMDB caption (same template as group filter)
        cur_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
        time_difference = timedelta(hours=cur_time.hour, minutes=cur_time.minute, seconds=(cur_time.second+(cur_time.microsecond/1000000))) - timedelta(hours=curr_time.hour, minutes=curr_time.minute, seconds=(curr_time.second+(curr_time.microsecond/1000000)))
        remaining_seconds = "{:.2f}".format(time_difference.total_seconds())
        try:
            cap = IMDB_TEMPLATE.format(
                qurey=search,
                requested=message.from_user.mention,
                title=imdb['title'],
                votes=imdb['votes'],
                aka=imdb["aka"],
                seasons=imdb["seasons"],
                box_office=imdb['box_office'],
                localized_title=imdb['localized_title'],
                kind=imdb['kind'],
                imdb_id=imdb["imdb_id"],
                cast=imdb["cast"],
                runtime=imdb["runtime"],
                countries=imdb["countries"],
                certificates=imdb["certificates"],
                languages=imdb["languages"],
                director=imdb["director"],
                writer=imdb["writer"],
                producer=imdb["producer"],
                composer=imdb["composer"],
                cinematographer=imdb["cinematographer"],
                music_team=imdb["music_team"],
                distributors=imdb["distributors"],
                release_date=imdb['release_date'],
                year=imdb['year'],
                genres=imdb['genres'],
                poster=imdb['poster'],
                plot=imdb['plot'],
                rating=imdb['rating'],
                url=imdb['url'],
                remaining_seconds=remaining_seconds,
            )
        except Exception as e:
            logger.exception(f"IMDB_TEMPLATE format error in PM: {e}")
            imdb = None  # fall back to plain cap below
            cap = ""

        if imdb:
            cap += "\n\n<b><u>👇 Your Movie Files 👇</u></b>\n\n"
            for file in files:
                if is_premium:
                    link = f"https://telegram.me/{temp.U_NAME}?start=file_{file.file_id}"
                elif IS_SHORTLINK:
                    link = f"https://telegram.me/{temp.U_NAME}?start=short_{file.file_id}"
                else:
                    link = f"https://telegram.me/{temp.U_NAME}?start=file_{file.file_id}"
                cap += f"📂 <b>{get_size(file.file_size)}</b> ▷ <a href='{link}'>{file.file_name}</a>\n\n"
            cap += f"<b>⚠️ ᴀꜰᴛᴇʀ 5 ᴍɪɴᴜᴛᴇꜱ ᴛʜɪꜱ ᴍᴇꜱꜱᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴅᴇʟᴇᴛᴇᴅ 🗑️</b>"
            temp.IMDB_CAP[message.from_user.id] = cap

    if not imdb:
        # Plain caption (PM_IMDB=False or TMDB returned nothing)
        if is_premium:
            cap = (
                f"<b>HEY PREMIUM USER ⭐\n\n"
                f"Tʜᴇ Rᴇꜱᴜʟᴛꜱ Fᴏʀ ☞ {search}\n\n"
                f"Rᴇǫᴜᴇsᴛᴇᴅ Bʏ ☞ {message.from_user.mention}\n\n"
                f"ᴘᴏᴡᴇʀᴇᴅ ʙʏ ☞ : LEVII AUTO FILTER BOT\n\n"
                f"⚠️ ᴀꜰᴛᴇʀ 5 ᴍɪɴᴜᴛᴇꜱ ᴛʜɪꜱ ᴍᴇꜱꜱᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴅᴇʟᴇᴛᴇᴅ 🗑️\n\n</b>"
            )
        else:
            cap = (
                f"<b>Tʜᴇ Rᴇꜱᴜʟᴛꜱ Fᴏʀ ☞ {search}\n\n"
                f"Rᴇǫᴜᴇsᴛᴇᴅ Bʏ ☞ {message.from_user.mention}\n\n"
                f"ᴘᴏᴡᴇʀᴇᴅ ʙʏ ☞ : LEVII AUTO FILTER BOT\n\n"
                f"⚠️ ᴀꜰᴛᴇʀ 5 ᴍɪɴᴜᴛᴇꜱ ᴛʜɪꜱ ᴍᴇꜱꜱᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴅᴇʟᴇᴛᴇᴅ 🗑️\n\n</b>"
            )
        for file in files:
            if is_premium:
                link = f"https://telegram.me/{temp.U_NAME}?start=file_{file.file_id}"
            elif IS_SHORTLINK:
                link = f"https://telegram.me/{temp.U_NAME}?start=short_{file.file_id}"
            else:
                link = f"https://telegram.me/{temp.U_NAME}?start=file_{file.file_id}"
            cap += f"📂 <b>{get_size(file.file_size)}</b> ▷ <a href='{link}'>{file.file_name}</a>\n\n"

    # Buttons
    btn = []

    # Send All — commands.py exact format (sendfiles flow use ஆகும்)
    btn.append([
        InlineKeyboardButton("📍 𝗦𝗲𝗻𝗱 𝗔𝗹𝗹 𝗙𝗶𝗹𝗲𝘀 𝗜𝗻 𝗢𝗻𝗲 𝗟𝗶𝗻𝗸 📍", callback_data=f"sendfiles#{key}")
    ])
    btn.append([
        InlineKeyboardButton("Qᴜᴀʟɪᴛʏ", callback_data=f"qualities#{key}"),
        InlineKeyboardButton("Lᴀɴɢᴜᴀɢᴇ", callback_data=f"languages#{key}"),
        InlineKeyboardButton("Sᴇᴀsᴏɴ", callback_data=f"seasons#{key}")
    ])
    btn.append([
        InlineKeyboardButton("☞ꜱᴇʟᴇᴄᴛ ʀᴇʟᴇᴀꜱᴇ ʏᴇᴀʀ☜", callback_data=f"releaseyear#{key}")
    ])

    if not is_premium:
        btn.append([
            InlineKeyboardButton('💸 Buy Premium For Adz Free Movies ✅', callback_data='buy_premium')
        ])

    # Pagination
    if offset != "":
        try:
            from info import MAX_B_TN
            total_pages = math.ceil(int(total_results) / int(MAX_B_TN))
        except Exception:
            total_pages = math.ceil(int(total_results) / 10)
        btn.append([
            InlineKeyboardButton("𝐏𝐀𝐆𝐄", callback_data="pages"),
            InlineKeyboardButton(text=f"1/{total_pages}", callback_data="pages"),
            InlineKeyboardButton(text="𝐍𝐄𝐗𝐓 ➪", callback_data=f"next_{user_id}_{key}_{offset}")
        ])
    else:
        btn.append([
            InlineKeyboardButton(text="𝐍𝐎 𝐌𝐎𝐑𝐄 𝐏𝐀𝐆𝐄𝐒 𝐀𝐕𝐀𝐈𝐋𝐀𝐁𝐋𝐄", callback_data="pages")
        ])

    await m.delete()
    _get_page_cache()[(key, 0)] = {"btn": btn, "cap": cap}

    # ── Send result — photo if TMDB poster available, otherwise text ──────────
    if imdb and imdb.get('poster'):
        try:
            result_msg = await message.reply_photo(
                photo=imdb['poster'],
                caption=cap,
                reply_markup=InlineKeyboardMarkup(btn)
            )
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            # Poster URL invalid — retry with resized variant
            poster = imdb['poster'].replace('.jpg', '._V1_UX360.jpg')
            try:
                result_msg = await message.reply_photo(
                    photo=poster,
                    caption=cap,
                    reply_markup=InlineKeyboardMarkup(btn)
                )
            except Exception:
                result_msg = await message.reply_text(
                    cap,
                    reply_markup=InlineKeyboardMarkup(btn),
                    disable_web_page_preview=True
                )
        except Exception:
            result_msg = await message.reply_text(
                cap,
                reply_markup=InlineKeyboardMarkup(btn),
                disable_web_page_preview=True
            )
    else:
        result_msg = await message.reply_text(
            cap,
            reply_markup=InlineKeyboardMarkup(btn),
            disable_web_page_preview=True
        )

    #this repo created and maintained by @muja_tg18
    if AUTO_DELETE:
        await asyncio.sleep(300)
        try:
            await result_msg.delete()
            await message.delete()
        except Exception:
            pass


async def show_pm_warning(client: Client, message: Message):
    buttons = [
        [InlineKeyboardButton("🎬 Join Movie Search Group", url=GRP_LNK)],
        [InlineKeyboardButton("❌ Close", callback_data="close_pm_warning")]
    ]
    await message.reply_text(
        "⚠️ <b>SORRY I CAN'T WORK IN PM</b>\n\nSearch movies in our <b>MOVIE SEARCH GROUP</b>.",
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True
    )


@Client.on_callback_query(filters.regex("^close_pm_warning$"))
async def close_pm_warning(client, callback_query):
    try:
        await callback_query.message.delete()
    except Exception as e:
        logger.error(f"Close Button Error: {e}")