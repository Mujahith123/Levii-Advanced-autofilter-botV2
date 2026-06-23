from __future__ import unicode_literals

import os
import asyncio
import logging
import requests
from pyrogram import filters, Client
from pyrogram.types import Message
from youtube_search import YoutubeSearch
from youtubesearchpython import SearchVideos
from yt_dlp import YoutubeDL

try:
    from info import COOKIES_FILE_PATH as _CONFIGURED_COOKIES_PATH, LOG_CHANNEL
except ImportError:
    _CONFIGURED_COOKIES_PATH, LOG_CHANNEL = "", None

logger = logging.getLogger(__name__)

# Path to a cookies.txt file (Netscape format) exported from a logged-in
# YouTube browser session. Required because YouTube blocks most server /
# datacenter IPs with "Sign in to confirm you're not a bot" unless valid
# cookies are sent. Configure via the COOKIES_FILE_PATH env var (see
# info.py / .env.example), or just drop a file named cookies.txt in the
# project root.
_CANDIDATE_COOKIE_PATHS = [
    _CONFIGURED_COOKIES_PATH,
    os.environ.get("COOKIES_FILE_PATH", ""),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt"),
    os.path.join(os.getcwd(), "cookies.txt"),
]

NO_COOKIES_MSG = (
    "❌ **YouTube is blocking this server (bot-check).**\n\n"
    "This needs a valid `cookies.txt` from a logged-in browser. "
    "Set the `COOKIES_FILE_PATH` env var to its path, or place "
    "`cookies.txt` in the project root, then restart the bot."
)

EXPIRED_COOKIES_MSG = (
    "❌ **YouTube rejected the saved login (cookies expired).**\n\n"
    "Export a fresh `cookies.txt` from a logged-in browser and replace "
    "the existing file (or update `COOKIES_FILE_PATH`), then restart the bot."
)

_warned_missing_cookies = False  # only nag the log channel once per process


def _validate_cookie_file(path):
    """A cookies.txt that's empty, truncated, or not actually Netscape
    cookie-jar format will make yt-dlp behave as if no cookies were passed
    at all, but with a much more confusing error. Catch that here so we can
    tell the operator exactly what's wrong instead of a generic bot-check
    failure."""
    try:
        if os.path.getsize(path) == 0:
            return False
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(4096)
        if "# Netscape HTTP Cookie File" not in head and "\tyoutube.com\t" not in head and ".youtube.com" not in head:
            return False
        return True
    except OSError:
        return False


def _resolve_cookies_file():
    for path in _CANDIDATE_COOKIE_PATHS:
        if path and os.path.isfile(path):
            if _validate_cookie_file(path):
                return path
            logger.warning("yt_dl: cookies file at %s exists but failed validation (empty/malformed)", path)
    return None


async def _warn_log_channel_once(client):
    global _warned_missing_cookies
    if _warned_missing_cookies or not LOG_CHANNEL:
        return
    _warned_missing_cookies = True
    try:
        await client.send_message(
            LOG_CHANNEL,
            "⚠️ **/song or /video was used but no valid `cookies.txt` is configured.**\n"
            "YouTube downloads will keep failing with a bot-check error until "
            "`COOKIES_FILE_PATH` points to a fresh, valid cookies.txt.",
        )
    except Exception:
        pass  # never let a notification failure break the user-facing flow


def base_ydl_opts():
    """Common yt-dlp options, with cookies + a real browser User-Agent
    attached automatically when a valid cookies file is available. Without
    this, YouTube responds to most cloud-hosted IPs with a bot-check error
    and every download command fails."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        # A modern desktop UA reduces the odds of triggering the bot check
        # even when cookies aren't set.
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        },
        # Retry transient failures instead of giving up on the first hiccup.
        "retries": 3,
        "fragment_retries": 3,
    }
    cookies_file = _resolve_cookies_file()
    if cookies_file:
        opts["cookiefile"] = cookies_file
    return opts


def _is_bot_check_error(err: str) -> bool:
    err = err.lower()
    return "sign in to confirm" in err or "not a bot" in err


def _is_expired_cookie_error(err: str) -> bool:
    err = err.lower()
    return any(
        phrase in err
        for phrase in (
            "cookies are no longer valid",
            "failed to extract any player response",
            "use --cookies-from-browser",
            "http error 403",
        )
    )


@Client.on_message(filters.command(['song', 'mp3']) & (filters.private | filters.group))
async def song(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("❌ Example: `/song Believer Imagine Dragons`")

    user_id = message.from_user.id
    user_name = message.from_user.first_name
    rpk = f"[{user_name}](tg://user?id={user_id})"
    query = " ".join(message.command[1:])

    m = await message.reply(f"🔍 **Searching:** `{query}`")

    try:
        results = YoutubeSearch(query, max_results=1).to_dict()
        if not results:
            return await m.edit("❌ No results found. Try a different song name.")
        link = f"https://youtube.com{results[0]['url_suffix']}"
        title = results[0]["title"][:40]
        thumbnail = results[0]["thumbnails"][0]
        thumb_name = f'thumb_{message.id}.jpg'
        thumb = requests.get(thumbnail, allow_redirects=True, timeout=10)
        open(thumb_name, 'wb').write(thumb.content)
        performer = "[RIO NETWORKS™]"
        duration = results[0]["duration"]
    except Exception as e:
        print(str(e))
        return await m.edit("❌ Could not find the song. Try: `/song vaa vaathi`")

    await m.edit("⬇️ **Downloading your song...**")

    ydl_opts = base_ydl_opts()
    ydl_opts.update({
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": f"%(title)s_{message.id}.%(ext)s",
    })

    try:
        # ✅ Fixed: use download=True directly instead of process_info workaround
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(link, download=True)
            audio_file = ydl.prepare_filename(info_dict)

        # Calculate duration in seconds
        secmul, dur, dur_arr = 1, 0, duration.split(':')
        for i in range(len(dur_arr) - 1, -1, -1):
            dur += int(dur_arr[i]) * secmul
            secmul *= 60

        cap = "**BY›› [RIO NETWORKS™](https://t.me/muja_tg18)**"
        await message.reply_audio(
            audio_file,
            caption=cap,
            quote=False,
            title=title,
            duration=dur,
            performer=performer,
            thumb=thumb_name
        )
        await m.delete()
    except Exception as e:
        err = str(e)
        if _is_bot_check_error(err):
            await m.edit(NO_COOKIES_MSG if not _resolve_cookies_file() else EXPIRED_COOKIES_MSG)
            await _warn_log_channel_once(client)
        elif _is_expired_cookie_error(err) and _resolve_cookies_file():
            await m.edit(EXPIRED_COOKIES_MSG)
            await _warn_log_channel_once(client)
        else:
            await m.edit(f"❌ **Download Failed:** `{err}`")
        print(e)
    finally:
        for f in [audio_file if 'audio_file' in locals() else None, thumb_name]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass


def get_text(message: Message):
    if not message.text or " " not in message.text:
        return None
    try:
        return message.text.split(None, 1)[1]
    except IndexError:
        return None


@Client.on_message(filters.command(["video", "mp4"]) & (filters.private | filters.group))
async def vsong(client, message: Message):
    urlissed = get_text(message)
    if not urlissed:
        return await message.reply("❌ Example: `/video Alan Walker Faded`")

    pablo = await message.reply(f"🔍 **Finding video:** `{urlissed}`")

    try:
        search = SearchVideos(f"{urlissed}", offset=1, mode="dict", max_results=1)
        mi = search.result()
        mio = mi["search_result"]
        mo = mio[0]["link"]
        thum = mio[0]["title"]
        fridayz = mio[0]["id"]
        kekme = f"https://img.youtube.com/vi/{fridayz}/hqdefault.jpg"
    except Exception as e:
        return await pablo.edit(f"❌ Search failed: `{str(e)}`")

    await asyncio.sleep(0.6)

    # ✅ Fixed: replaced wget with requests to avoid extra dependency
    thumb_path = f"thumb_vid_{message.id}.jpg"
    try:
        thumb_data = requests.get(kekme, timeout=10)
        with open(thumb_path, 'wb') as f:
            f.write(thumb_data.content)
    except Exception:
        thumb_path = None

    opts = base_ydl_opts()
    opts.update({
        "format": "best[ext=mp4]/best",
        "outtmpl": f"%(id)s_{message.id}.%(ext)s",
    })

    file_stark = None
    try:
        with YoutubeDL(opts) as ytdl:
            ytdl_data = ytdl.extract_info(mo, download=True)
        file_stark = f"{ytdl_data['id']}_{message.id}.mp4"
    except Exception as e:
        err = str(e)
        if _is_bot_check_error(err):
            await _warn_log_channel_once(client)
            return await pablo.edit(NO_COOKIES_MSG if not _resolve_cookies_file() else EXPIRED_COOKIES_MSG)
        elif _is_expired_cookie_error(err) and _resolve_cookies_file():
            await _warn_log_channel_once(client)
            return await pablo.edit(EXPIRED_COOKIES_MSG)
        return await pablo.edit(f"❌ **Download Failed:** `{err}`")

    capy = f"**𝚃𝙸𝚃𝙻𝙴:** [{thum}]({mo})\n**𝚁𝙴𝚀𝚄𝙴𝚂𝚃𝙴𝙳 𝙱𝚈:** {message.from_user.mention}"

    try:
        await client.send_video(
            message.chat.id,
            video=open(file_stark, "rb"),
            duration=int(ytdl_data.get("duration", 0)),
            file_name=str(ytdl_data.get("title", "video")),
            thumb=thumb_path,
            caption=capy,
            supports_streaming=True,
            reply_to_message_id=message.id
        )
        await pablo.delete()
    except Exception as e:
        await pablo.edit(f"❌ Upload failed: `{str(e)}`")
    finally:
        for f in [file_stark, thumb_path]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass