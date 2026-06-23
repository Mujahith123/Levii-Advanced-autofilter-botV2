import re
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# apis.xditya.me has been discontinued (now returns 403 for every request),
# which is why /lyrics always failed with "API error". Switched to two
# free, key-free APIs that are currently active:
#   1. lyrics.ovh   - simple, needs separate artist/title
#   2. lrclib.net   - fallback, searches by a single free-text query
LYRICS_OVH_API = "https://api.lyrics.ovh/v1/{artist}/{title}"
LRCLIB_SEARCH_API = "https://lrclib.net/api/search"


def _split_artist_title(song: str):
    """Best-effort split of a free-text query into (artist, title).
    Accepts 'artist - title' or 'artist title'; falls back to using
    the whole string as the title with an empty artist."""
    song = song.strip()
    for sep in (" - ", " – ", ":"):
        if sep in song:
            artist, title = song.split(sep, 1)
            return artist.strip(), title.strip()
    return "", song


def _try_lyrics_ovh(song: str):
    artist, title = _split_artist_title(song)
    query_title = title or song
    try:
        if artist:
            url = LYRICS_OVH_API.format(artist=requests.utils.quote(artist), title=requests.utils.quote(query_title))
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get("lyrics"):
                    return data["lyrics"]
        # If no artist guess, or that lookup failed, try the whole string as title
        # with no artist isn't supported by lyrics.ovh (it needs both), so skip.
    except Exception:
        pass
    return None


def _try_lrclib(song: str):
    try:
        r = requests.get(LRCLIB_SEARCH_API, params={"q": song}, timeout=10)
        if r.status_code == 200:
            results = r.json()
            if results:
                top = results[0]
                text = top.get("plainLyrics") or top.get("syncedLyrics")
                if text:
                    # Strip LRC timestamps like [00:12.34] if synced lyrics came back
                    text = re.sub(r"\[\d{2}:\d{2}\.\d{2,3}\]", "", text).strip()
                    return text
    except Exception:
        pass
    return None


def get_lyrics(song):
    lyrics = _try_lyrics_ovh(song) or _try_lrclib(song)
    if not lyrics:
        return None, "Lyrics not found for this song."
    text = f"**🎶 Successfully Extracted Lyrics Of {song}**\n\n"
    text += f"`{lyrics}`"
    text += '\n\n**Made By Artificial Intelligence**'
    return text, None


@Client.on_message(filters.command(["lyrics"]) & (filters.private | filters.group))
async def sng(bot, message):
    # Get song name from command args or reply
    if len(message.command) > 1:
        song = message.text.split(" ", 1)[1]
    elif message.reply_to_message and message.reply_to_message.text:
        song = message.reply_to_message.text
    else:
        return await message.reply_text(
            "Usage:\n• `/lyrics <song name>`\n• Or reply to a message with the song name",
            quote=True
        )

    mee = await message.reply_text("`Searching 🔎`")

    lyrics_text, error = get_lyrics(song)

    await mee.delete()  # ✅ Fixed: only delete once

    update_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Updates", url="https://t.me/mkn_bots_updates")]]
    )

    if error or not lyrics_text:
        await message.reply_text(
            f"❌ Couldn't find lyrics for `{song}`\n\nError: {error}",
            quote=True,
            reply_markup=update_button
        )
        return

    # Send in chunks if too long
    max_len = 4000
    if len(lyrics_text) <= max_len:
        await message.reply_text(
            text=lyrics_text,
            reply_markup=update_button,
            quote=True
        )
    else:
        for i in range(0, len(lyrics_text), max_len):
            await bot.send_message(
                message.chat.id,
                text=lyrics_text[i:i + max_len],
                reply_to_message_id=message.id if i == 0 else None,
                reply_markup=update_button if i + max_len >= len(lyrics_text) else None
            )