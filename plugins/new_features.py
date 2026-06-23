
import asyncio
import logging
import aiohttp
from datetime import datetime

from pyrogram import Client, filters, enums
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, Message,
)
from pyrogram.errors import FloodWait, UserIsBlocked, PeerIdInvalid

from info import ADMINS, TMDB_API_KEY, LOG_CHANNEL
from database.users_chats_db import db
from database.ia_filterdb import get_search_results
from utils import get_size, get_settings, temp

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ══════════════════════════════════════════════════════════════════════════════
#  Feature 1 – Content Gap Analytics Dashboard (enhanced /dashboard)
# ══════════════════════════════════════════════════════════════════════════════

@Client.on_message(filters.command("gapdashboard") & filters.user(ADMINS))
async def gap_dashboard_cmd(bot, message: Message):
    """Admin command: /gapdashboard — full analytics including content gaps."""
    sts = await message.reply_text("⏳ Gathering analytics data...")
    try:
        (
            today_searches,
            new_users_today,
            top_searches,
            top_not_found,
            top_groups,
            weekly_trend,
            today_nf,
        ) = await asyncio.gather(
            db.get_today_search_count(),
            db.get_new_users_today_count(),
            db.get_top_searches(limit=5),
            db.get_top_not_found(limit=8),
            db.get_top_active_groups(limit=5),
            db.get_search_trend(days=7, limit=5),
            db.get_today_not_found_count(),
        )

        def _list(items, fmt):
            return "\n".join(fmt(i, item) for i, item in enumerate(items)) if items else "  —"

        text = (
            "📊 <b>Content Gap Analytics Dashboard</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔎 Today's Searches: <code>{today_searches}</code>\n"
            f"❌ Today's Not-Found: <code>{today_nf}</code>\n"
            f"🆕 New Users Today: <code>{new_users_today}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎬 <b>Top Requested (Not Found)</b> — content gaps:\n"
            + _list(top_not_found, lambda i, x: f"  {i+1}. {x[0].title()} — <code>{x[1]}x</code>") + "\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🏆 <b>Most Searched (all time)</b>:\n"
            + _list(top_searches, lambda i, x: f"  {i+1}. {x[0].title()} — <code>{x[1]}x</code>") + "\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📈 <b>Search Trend (last 7 days)</b>:\n"
            + _list(weekly_trend, lambda i, x: f"  {i+1}. {x[0].title()} — <code>{x[1]}x</code>") + "\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🏘️ <b>Most Active Groups</b>:\n"
            + _list(top_groups, lambda i, x: f"  {i+1}. {x[0]} — <code>{x[2]} searches</code>")
        )
        await sts.edit(text)
    except Exception as e:
        logger.exception(e)
        await sts.edit(f"❌ Error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  Feature 1 (hook) – record_not_found helper (called from pm_filter / pm_filter_warning)
# ══════════════════════════════════════════════════════════════════════════════

async def record_not_found(query: str, user_id=None, group_id=None, group_title=None):
    """Background task: record a failed search for content gap analytics."""
    try:
        await db.log_not_found(query, user_id=user_id, group_id=group_id, group_title=group_title)
    except Exception as e:
        logger.warning(f"record_not_found failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  Feature 2 – Smart Auto Request (callback handler for "Request" button)
# ══════════════════════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^autoreq#(.+)"))
async def auto_request_callback(bot, query: CallbackQuery):
    """User taps the '📩 Request' button on a not-found message."""
    movie_name = query.data.split("#", 1)[1]
    user = query.from_user

    try:
        await db.add_movie_request(user.id, movie_name)
    except Exception as e:
        logger.warning(f"Auto request save failed: {e}")

    if LOG_CHANNEL:
        try:
            chat_type = query.message.chat.type
            group_name = (
                query.message.chat.title
                if chat_type in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP)
                else "Private"
            )
            text = (
                "📩 <b>Auto Movie Request</b>\n\n"
                f"🎬 Movie: <b>{movie_name}</b>\n"
                f"👤 User: {user.mention} (<code>{user.id}</code>)\n"
                f"💬 From: {group_name}"
            )
            await bot.send_message(chat_id=LOG_CHANNEL, text=text)
        except Exception as e:
            logger.warning(f"Auto request admin notify failed: {e}")

    await query.answer(
        f"✅ '{movie_name}' has been requested! You'll get a DM when it's added.",
        show_alert=True
)
