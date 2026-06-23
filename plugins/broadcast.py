from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import datetime
import time
import re
import pytz
from bson import ObjectId
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from database.users_chats_db import db
from info import ADMINS
from utils import broadcast_messages, broadcast_messages_group, temp
import asyncio
import logging

logger = logging.getLogger(__name__)


def parse_buttons(text):
    """Parse button markup from message text.
    Format: [Button Text](url) on same line = same row
    Each line = new row
    Example:
    [Join Channel](https://t.me/xxx) [Updates](https://t.me/yyy)
    [Website](https://example.com)
    """
    buttons = []
    lines = text.strip().split('\n')
    clean_text = []
    for line in lines:
        matches = re.findall(r'\[(.+?)\]\((https?://[^\)]+)\)', line)
        if matches:
            row = [InlineKeyboardButton(text=btn_text, url=url) for btn_text, url in matches]
            buttons.append(row)
        else:
            clean_text.append(line)
    markup = InlineKeyboardMarkup(buttons) if buttons else None
    return '\n'.join(clean_text).strip(), markup


@Client.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast_users(bot, message):
    b_msg = message.reply_to_message
    sts = await message.reply_text("Broadcasting to users...")
    start_time = time.time()
    total_users = await db.total_users_count()
    done = 0
    blocked = 0
    deleted = 0
    failed = 0
    success = 0
    users = await db.get_all_users()
    async for user in users:
        pti, sh = await broadcast_messages(int(user['id']), b_msg)
        if pti:
            success += 1
        elif pti == False:
            if sh == "Blocked":
                blocked += 1
            elif sh == "Deleted":
                deleted += 1
            elif sh == "Error":
                failed += 1
        done += 1
        await asyncio.sleep(2)
        if not done % 20:
            await sts.edit(
                f"Broadcast in progress:\n\n"
                f"Total: {total_users} | Done: {done}\n"
                f"Success: {success} | Blocked: {blocked} | Deleted: {deleted}"
            )
    time_taken = datetime.timedelta(seconds=int(time.time() - start_time))
    await sts.edit(
        f"Broadcast Completed in {time_taken}!\n\n"
        f"Total: {total_users} | Done: {done}\n"
        f"Success: {success} | Blocked: {blocked} | Deleted: {deleted} | Failed: {failed}"
    )


@Client.on_message(filters.command("grp_broadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast_groups(bot, message):
    b_msg = message.reply_to_message
    sts = await message.reply_text("Broadcasting to groups...")
    start_time = time.time()
    total_groups = await db.total_chat_count()
    done = 0
    failed = 0
    success = 0
    groups = await db.get_all_chats()
    async for group in groups:
        pti, sh = await broadcast_messages_group(int(group['id']), b_msg)
        if pti:
            success += 1
        elif sh == "Error":
            failed += 1
        done += 1
        if not done % 20:
            await sts.edit(
                f"Group Broadcast in progress:\n\n"
                f"Total: {total_groups} | Done: {done}\n"
                f"Success: {success} | Failed: {failed}"
            )
    time_taken = datetime.timedelta(seconds=int(time.time() - start_time))
    await sts.edit(
        f"Group Broadcast Completed in {time_taken}!\n\n"
        f"Total: {total_groups} | Done: {done}\n"
        f"Success: {success} | Failed: {failed}"
    )


@Client.on_message(filters.command("bcast_btn") & filters.user(ADMINS))
async def broadcast_with_buttons(bot, message):
    """Broadcast a message with custom buttons.
    Usage: Reply to a message OR write message after command.
    Add buttons in format: [Button Name](url)
    
    Example:
    /bcast_btn
    Your announcement text here
    [Join Channel](https://t.me/xxx) [Updates](https://t.me/yyy)
    [Website](https://example.com)
    """
    if message.reply_to_message:
        b_msg = message.reply_to_message
        # Check if replied message has caption with buttons
        raw_text = b_msg.caption or b_msg.text or ""
        clean_text, markup = parse_buttons(raw_text)
    elif len(message.command) > 1:
        raw_text = message.text.split(None, 1)[1]
        clean_text, markup = parse_buttons(raw_text)
        b_msg = None
    else:
        return await message.reply_text(
            "Usage: /bcast_btn\nYour message text\n[Button 1](https://t.me/xxx) [Button 2](url)\n[Button 3](url)"
        )

    sts = await message.reply_text("Broadcasting with buttons...")
    start_time = time.time()
    total_users = await db.total_users_count()
    done = 0
    success = 0
    blocked = 0
    failed = 0

    users = await db.get_all_users()
    async for user in users:
        try:
            if b_msg and b_msg.photo:
                await bot.send_photo(
                    chat_id=int(user['id']),
                    photo=b_msg.photo.file_id,
                    caption=clean_text,
                    reply_markup=markup
                )
            else:
                await bot.send_message(
                    chat_id=int(user['id']),
                    text=clean_text,
                    reply_markup=markup,
                    disable_web_page_preview=True
                )
            success += 1
        except Exception as e:
            err = str(e).lower()
            if "blocked" in err:
                blocked += 1
            else:
                failed += 1
        done += 1
        await asyncio.sleep(0.05)
        if not done % 20:
            await sts.edit(
                f"Broadcast in progress:\n\nTotal: {total_users} | Done: {done}\n"
                f"Success: {success} | Blocked: {blocked} | Failed: {failed}"
            )

    time_taken = datetime.timedelta(seconds=int(time.time() - start_time))
    await sts.edit(
        f"Broadcast Completed in {time_taken}!\n\nTotal: {total_users} | Done: {done}\n"
        f"Success: {success} | Blocked: {blocked} | Failed: {failed}"
    )


#===================================[ Scheduled Broadcast ]================================#
scheduler = AsyncIOScheduler()
scheduler.start()

IST = pytz.timezone("Asia/Kolkata")


def _queue_broadcast_job(broadcast_id, run_date_naive):
    scheduler.add_job(
        _run_scheduled_broadcast,
        trigger=DateTrigger(run_date=run_date_naive),
        args=[broadcast_id],
        id=str(broadcast_id),
        replace_existing=True,
    )


async def _run_scheduled_broadcast(broadcast_id):
    bot = temp.BOT
    if bot is None:
        # Bot isn't fully up yet — try again shortly instead of dropping the job.
        scheduler.add_job(
            _run_scheduled_broadcast,
            trigger=DateTrigger(run_date=datetime.datetime.now() + datetime.timedelta(seconds=30)),
            args=[broadcast_id],
        )
        return

    record = await db.scheduled_broadcasts.find_one({"_id": broadcast_id})
    if not record or record.get("status") != "pending":
        return

    try:
        b_msg = await bot.get_messages(record["chat_id"], record["message_id"])
    except Exception as e:
        logger.error(f"Scheduled broadcast {broadcast_id}: could not fetch source message: {e}")
        await db.mark_broadcast_status(broadcast_id, "failed")
        return

    success = blocked = deleted = failed = 0
    users = await db.get_all_users()
    async for user in users:
        pti, sh = await broadcast_messages(int(user['id']), b_msg)
        if pti:
            success += 1
        elif sh == "Blocked":
            blocked += 1
        elif sh == "Deleted":
            deleted += 1
        else:
            failed += 1
        await asyncio.sleep(0.05)

    await db.mark_broadcast_status(broadcast_id, "sent")
    try:
        await bot.send_message(
            record["created_by"],
            f"📢 Your scheduled broadcast (ID <code>{broadcast_id}</code>) just went out!\n\n"
            f"Total: {success + blocked + deleted + failed} | Success: {success} | "
            f"Blocked: {blocked} | Deleted: {deleted} | Failed: {failed}"
        )
    except Exception:
        pass


async def _requeue_pending_broadcasts():
    """Re-attach scheduler jobs for broadcasts still pending from before the last restart."""
    try:
        pending = await db.get_pending_scheduled_broadcasts()
    except Exception as e:
        logger.error(f"Could not load pending scheduled broadcasts: {e}")
        return
    now = datetime.datetime.now()
    for record in pending:
        run_date = record["scheduled_time"]
        if run_date <= now:
            # Was due while the bot was offline — fire it shortly instead of silently skipping it.
            run_date = now + datetime.timedelta(seconds=15)
        _queue_broadcast_job(record["_id"], run_date)


# Deferred a few seconds so it only runs once the event loop is actually pumping.
scheduler.add_job(_requeue_pending_broadcasts, trigger=DateTrigger(run_date=datetime.datetime.now() + datetime.timedelta(seconds=5)))


@Client.on_message(filters.command("schedule_broadcast") & filters.user(ADMINS) & filters.reply)
async def schedule_broadcast_cmd(bot, message):
    """Usage: /schedule_broadcast YYYY-MM-DD HH:MM  (24h time, IST) — reply to the message to send."""
    if len(message.command) < 3:
        return await message.reply_text(
            "Usage: /schedule_broadcast YYYY-MM-DD HH:MM (time in IST)\n"
            "Reply to the message you want broadcast.\n\n"
            "Example: /schedule_broadcast 2026-06-20 09:00"
        )
    date_str, time_str = message.command[1], message.command[2]
    try:
        naive_input = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        scheduled_ist = IST.localize(naive_input)
    except ValueError:
        return await message.reply_text("❌ Invalid date/time. Use format: YYYY-MM-DD HH:MM")

    if scheduled_ist <= datetime.datetime.now(IST):
        return await message.reply_text("❌ That time is in the past. Pick a future date/time.")

    run_date_naive = scheduled_ist.astimezone(pytz.utc).replace(tzinfo=None)
    b_msg = message.reply_to_message

    broadcast_id = await db.add_scheduled_broadcast(
        chat_id=b_msg.chat.id,
        message_id=b_msg.id,
        scheduled_time=run_date_naive,
        created_by=message.from_user.id,
    )
    _queue_broadcast_job(broadcast_id, run_date_naive)

    await message.reply_text(
        "✅ <b>Broadcast Scheduled</b>\n\n"
        f"🕐 Will be sent: <code>{scheduled_ist.strftime('%d-%m-%Y %I:%M %p')} IST</code>\n"
        f"🆔 ID: <code>{broadcast_id}</code>\n\n"
        "/list_scheduled to view pending broadcasts, /cancel_scheduled <id> to cancel this one."
    )


@Client.on_message(filters.command("list_scheduled") & filters.user(ADMINS))
async def list_scheduled_cmd(bot, message):
    pending = await db.get_pending_scheduled_broadcasts()
    if not pending:
        return await message.reply_text("No scheduled broadcasts pending.")
    lines = []
    for record in pending:
        when_ist = record["scheduled_time"].replace(tzinfo=pytz.utc).astimezone(IST)
        lines.append(f"🆔 <code>{record['_id']}</code> — {when_ist.strftime('%d-%m-%Y %I:%M %p')} IST")
    await message.reply_text("<b>📅 Pending Scheduled Broadcasts</b>\n\n" + "\n".join(lines))


@Client.on_message(filters.command("cancel_scheduled") & filters.user(ADMINS))
async def cancel_scheduled_cmd(bot, message):
    if len(message.command) != 2:
        return await message.reply_text("Usage: /cancel_scheduled <id>  (copy the id from /list_scheduled)")
    try:
        broadcast_id = ObjectId(message.command[1])
    except Exception:
        return await message.reply_text("❌ That doesn't look like a valid ID.")
    try:
        scheduler.remove_job(str(broadcast_id))
    except Exception:
        pass
    await db.mark_broadcast_status(broadcast_id, "cancelled")
    await message.reply_text("✅ Scheduled broadcast cancelled.")