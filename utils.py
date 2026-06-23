# Credits: This repo fully created by Telegram @muja_tg18
import logging
from pyrogram.errors import InputUserDeactivated, FloodWait, UserIsBlocked, PeerIdInvalid
from info import *
from imdb import Cinemagoer
import asyncio
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid
from pyrogram import enums
from typing import Union
from Script import script
import pytz
import random 
import re
import os
from datetime import datetime, date
import string
from typing import List
from database.users_chats_db import db
from bs4 import BeautifulSoup
import requests
import aiohttp
from shortzy import Shortzy
import http.client
import json

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BTN_URL_REGEX = re.compile(
    r"(\[([^\[]+?)\]\((buttonurl|buttonalert):(?:/{0,2})(.+?)(:same)?\))"
)

imdb = Cinemagoer() 
TOKENS = {}
VERIFIED = {}
BANNED = {}
SECOND_SHORTENER = {}
SMART_OPEN = '“'
SMART_CLOSE = '”'
START_CHAR = ('\'', '"', SMART_OPEN)

# temp db for banned 
class temp(object):
    BANNED_USERS = []
    BANNED_CHATS = []
    ME = None
    BOT = None  # Holds the actual running Bot instance
    MAINTENANCE = False  # Maintenance mode flag
    CURRENT=int(os.environ.get("SKIP", 2))
    CANCEL = False
    MELCOW = {}
    U_NAME = None
    B_NAME = None
    GETALL = {}
    SHORT = {}
    SETTINGS = {}
    IMDB_CAP = {}

def is_support_chat(chat):
    """Check whether `chat` (a Pyrogram Chat, or anything with .id/.username
    attributes) is the configured SUPPORT_CHAT_ID.

    SUPPORT_CHAT_ID can be set as a numeric chat ID or as a @username
    (see info.fix_channel_id) — a plain `SUPPORT_CHAT_ID == chat.id`
    comparison only works for the numeric case and silently always returns
    False when a username is configured, since chat.id is always an int.
    This checks both forms so either configuration works.
    """
    if SUPPORT_CHAT_ID is None or chat is None:
        return False
    if isinstance(SUPPORT_CHAT_ID, str):
        configured_username = SUPPORT_CHAT_ID.lstrip('@').lower()
        chat_username = (getattr(chat, "username", None) or "").lower()
        return bool(chat_username) and chat_username == configured_username
    return SUPPORT_CHAT_ID == chat.id


async def is_req_subscribed(bot, query):
    # For private channels: check DB first (join request was recorded by join_req.py)
    # For public channels: join_req.py never fires, so skip DB and check membership directly
    try:
        auth_chat = await bot.get_chat(AUTH_CHANNEL)
        is_public = bool(auth_chat.username)
    except Exception:
        is_public = False

    if not is_public:
        # Private channel — check join request DB first
        if await db.find_join_req(query.from_user.id):
            return True

    # Always check actual membership (works for both public and private)
    try:
        user = await bot.get_chat_member(AUTH_CHANNEL, query.from_user.id)
    except UserNotParticipant:
        return False
    except Exception as e:
        logger.exception(e)
        return False
    else:
        if user.status != enums.ChatMemberStatus.BANNED:
            return True
    return False

async def get_poster(query, bulk=False, id=False, file=None):
    """Fetch movie info from TMDB API (works on all cloud servers)."""
    try:
        import aiohttp

        if not TMDB_API_KEY:
            logger.warning("TMDB_API_KEY not set. IMDB/TMDB results disabled.")
            return None

        BASE = "https://api.themoviedb.org/3"
        IMG_BASE = "https://image.tmdb.org/t/p/w500"

        query = query.strip()
        title = query

        # Extract year from query or filename
        year = None
        year_match = re.findall(r'[1-2]\d{3}', query)
        if year_match:
            year = year_match[-1]
            title = query.replace(year, "").strip()
        elif file:
            year_match = re.findall(r'[1-2]\d{3}', file)
            if year_match:
                year = year_match[-1]

        async with aiohttp.ClientSession() as session:
            # Search TMDB
            params = {
                "api_key": TMDB_API_KEY,
                "query": title,
                "language": "en-US",
                "page": 1
            }
            if year:
                params["year"] = year

            async with session.get(f"{BASE}/search/multi", params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    logger.warning(f"TMDB search failed: HTTP {resp.status}")
                    return None
                data = await resp.json()

            results = data.get("results", [])
            if not results:
                # Try without year
                params.pop("year", None)
                async with session.get(f"{BASE}/search/multi", params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await resp.json()
                results = data.get("results", [])

            if not results:
                return None

            if bulk:
                return [r.get("title") or r.get("name") for r in results[:10]]

            # Pick best result - prefer movies and tv series
            result = None
            for r in results:
                if r.get("media_type") in ["movie", "tv"]:
                    result = r
                    break
            if not result:
                result = results[0]

            media_type = result.get("media_type", "movie")
            tmdb_id = result.get("id")

            # Fetch full details
            endpoint = "movie" if media_type == "movie" else "tv"
            async with session.get(
                f"{BASE}/{endpoint}/{tmdb_id}",
                params={"api_key": TMDB_API_KEY, "language": "en-US", "append_to_response": "credits,release_dates"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    return None
                movie = await resp.json()

            # Extract crew
            credits = movie.get("credits", {})
            cast_list = [c["name"] for c in credits.get("cast", [])[:5]]
            crew = credits.get("crew", [])
            directors = [c["name"] for c in crew if c.get("job") == "Director"]
            writers = [c["name"] for c in crew if c.get("job") in ["Writer", "Screenplay", "Story"]]
            producers = [c["name"] for c in crew if c.get("job") == "Producer"]
            composers = [c["name"] for c in crew if c.get("department") == "Sound"]
            cinematographers = [c["name"] for c in crew if c.get("job") == "Director of Photography"]

            # Title and year
            title_str = movie.get("title") or movie.get("name") or query
            release = movie.get("release_date") or movie.get("first_air_date") or ""
            release_year = release[:4] if release else year or "N/A"

            # Genres
            genres = ", ".join([g["name"] for g in movie.get("genres", [])])

            # Languages
            languages = ", ".join([l.get("english_name", l.get("name", "")) for l in movie.get("spoken_languages", [])])

            # Countries
            countries = ", ".join([c["name"] for c in movie.get("production_countries", [])])

            # Runtime
            runtime = str(movie.get("runtime") or movie.get("episode_run_time", [0])[0] if movie.get("episode_run_time") else "N/A")

            # Plot
            plot = movie.get("overview", "N/A")
            if plot and len(plot) > 800:
                plot = plot[:800] + "..."

            # Poster
            poster_path = movie.get("poster_path")
            poster_url = f"{IMG_BASE}{poster_path}" if poster_path else None

            # Rating
            rating = str(round(movie.get("vote_average", 0), 1))
            votes = str(movie.get("vote_count", "N/A"))

            # IMDB URL (use TMDB page if no imdb_id)
            imdb_id = movie.get("imdb_id") or f"tmdb_{tmdb_id}"
            url = f"https://www.imdb.com/title/{imdb_id}" if movie.get("imdb_id") else f"https://www.themoviedb.org/{endpoint}/{tmdb_id}"

            # Box office
            revenue = movie.get("revenue", 0)
            box_office = f"${revenue:,}" if revenue else "N/A"

            # Seasons (for TV)
            seasons = str(movie.get("number_of_seasons", "N/A"))

            return {
                "title": title_str,
                "votes": votes,
                "aka": movie.get("original_title") or movie.get("original_name") or title_str,
                "seasons": seasons,
                "box_office": box_office,
                "localized_title": title_str,
                "kind": "tv series" if media_type == "tv" else "movie",
                "imdb_id": imdb_id,
                "cast": ", ".join(cast_list),
                "runtime": runtime,
                "countries": countries,
                "certificates": "N/A",
                "languages": languages,
                "director": ", ".join(directors),
                "writer": ", ".join(writers),
                "producer": ", ".join(producers),
                "composer": ", ".join(composers),
                "cinematographer": ", ".join(cinematographers),
                "music_team": "N/A",
                "distributors": "N/A",
                "release_date": release,
                "year": release_year,
                "genres": genres,
                "poster": poster_url,
                "plot": plot,
                "rating": rating,
                "url": url
            }

    except asyncio.TimeoutError:
        logger.warning(f"TMDB timeout for query: {query}")
        return None
    except Exception as e:
        logger.error(f"TMDB get_poster error: {e}", exc_info=True)
        return None


async def broadcast_messages(user_id, message):
    try:
        m = await message.copy(chat_id=user_id)
        try:
            await m.pin(both_sides=True)
        except:
            pass
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await broadcast_messages(user_id, message)
    except InputUserDeactivated:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id}-Removed from Database, since deleted account.")
        return False, "Deleted"
    except UserIsBlocked:
        logging.info(f"{user_id} -Blocked the bot.")
        return False, "Blocked"
    except PeerIdInvalid:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id} - PeerIdInvalid")
        return False, "Error"
    except Exception as e:
        return False, "Error"


async def broadcast_messages_group(chat_id, message):
    try:
        kd = await message.copy(chat_id=chat_id)
        try:
            await kd.pin()
        except:
            pass
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await broadcast_messages_group(chat_id, message)
    except Exception as e:
        return False, "Error"

async def search_gagala(text):
    usr_agent = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/61.0.3163.100 Safari/537.36'
        }
    text = text.replace(" ", '+')
    url = f'https://www.google.com/search?q={text}'
    response = requests.get(url, headers=usr_agent)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    titles = soup.find_all( 'h3' )
    return [title.getText() for title in titles]

async def get_settings(group_id):
    settings = temp.SETTINGS.get(group_id)
    if not settings:
        settings = await db.get_settings(group_id)
        temp.SETTINGS[group_id] = settings
    return settings

async def save_group_settings(group_id, key, value):
    current = await get_settings(group_id)
    current[key] = value
    temp.SETTINGS[group_id] = current
    await db.update_settings(group_id, current)

def get_size(size):
    """Get size in readable format"""

    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])

def split_list(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]  

def get_file_id(msg: Message):
    if msg.media:
        for message_type in (
            "photo",
            "animation",
            "audio",
            "document",
            "video",
            "video_note",
            "voice",
            "sticker"
        ):
            obj = getattr(msg, message_type)
            if obj:
                setattr(obj, "message_type", message_type)
                return obj

def extract_user(message: Message) -> Union[int, str]:
    """extracts the user from a message"""
    # https://github.com/SpEcHiDe/PyroGramBot/blob/f30e2cca12002121bad1982f68cd0ff9814ce027/pyrobot/helper_functions/extract_user.py#L7
    user_id = None
    user_first_name = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        user_first_name = message.reply_to_message.from_user.first_name

    elif len(message.command) > 1:
        if (
            len(message.entities) > 1 and
            message.entities[1].type == enums.MessageEntityType.TEXT_MENTION
        ):

            required_entity = message.entities[1]
            user_id = required_entity.user.id
            user_first_name = required_entity.user.first_name
        else:
            user_id = message.command[1]
            # don't want to make a request -_-
            user_first_name = user_id
        try:
            user_id = int(user_id)
        except ValueError:
            pass
    else:
        user_id = message.from_user.id
        user_first_name = message.from_user.first_name
    return (user_id, user_first_name)

def list_to_str(k):
    if not k:
        return "N/A"
    elif len(k) == 1:
        return str(k[0])
    elif MAX_LIST_ELM:
        k = k[:int(MAX_LIST_ELM)]
        return ' '.join(f'{elem}, ' for elem in k)
    else:
        return ' '.join(f'{elem}, ' for elem in k)

def last_online(from_user):
    time = ""
    if from_user.is_bot:
        time += "🤖 Bot :("
    elif from_user.status == enums.UserStatus.RECENTLY:
        time += "Recently"
    elif from_user.status == enums.UserStatus.LAST_WEEK:
        time += "Within the last week"
    elif from_user.status == enums.UserStatus.LAST_MONTH:
        time += "Within the last month"
    elif from_user.status == enums.UserStatus.LONG_AGO:
        time += "A long time ago :("
    elif from_user.status == enums.UserStatus.ONLINE:
        time += "Currently Online"
    elif from_user.status == enums.UserStatus.OFFLINE:
        time += from_user.last_online_date.strftime("%a, %d %b %Y, %H:%M:%S")
    return time


def split_quotes(text: str) -> List:
    if not any(text.startswith(char) for char in START_CHAR):
        return text.split(None, 1)
    counter = 1  # ignore first char -> is some kind of quote
    while counter < len(text):
        if text[counter] == "\\":
            counter += 1
        elif text[counter] == text[0] or (text[0] == SMART_OPEN and text[counter] == SMART_CLOSE):
            break
        counter += 1
    else:
        return text.split(None, 1)

    # 1 to avoid starting quote, and counter is exclusive so avoids ending
    key = remove_escapes(text[1:counter].strip())
    # index will be in range, or `else` would have been executed and returned
    rest = text[counter + 1:].strip()
    if not key:
        key = text[0] + text[0]
    return list(filter(None, [key, rest]))

def gfilterparser(text, keyword):
    if "buttonalert" in text:
        text = (text.replace("\n", "\\n").replace("\t", "\\t"))
    buttons = []
    note_data = ""
    prev = 0
    i = 0
    alerts = []
    for match in BTN_URL_REGEX.finditer(text):
        # Check if btnurl is escaped
        n_escapes = 0
        to_check = match.start(1) - 1
        while to_check > 0 and text[to_check] == "\\":
            n_escapes += 1
            to_check -= 1

        # if even, not escaped -> create button
        if n_escapes % 2 == 0:
            note_data += text[prev:match.start(1)]
            prev = match.end(1)
            if match.group(3) == "buttonalert":
                # create a thruple with button label, url, and newline status
                if bool(match.group(5)) and buttons:
                    buttons[-1].append(InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"gfilteralert:{i}:{keyword}"
                    ))
                else:
                    buttons.append([InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"gfilteralert:{i}:{keyword}"
                    )])
                i += 1
                alerts.append(match.group(4))
            elif bool(match.group(5)) and buttons:
                buttons[-1].append(InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                ))
            else:
                buttons.append([InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                )])

        else:
            note_data += text[prev:to_check]
            prev = match.start(1) - 1
    else:
        note_data += text[prev:]

    try:
        return note_data, buttons, alerts
    except:
        return note_data, buttons, None

def parser(text, keyword):
    if "buttonalert" in text:
        text = (text.replace("\n", "\\n").replace("\t", "\\t"))
    buttons = []
    note_data = ""
    prev = 0
    i = 0
    alerts = []
    for match in BTN_URL_REGEX.finditer(text):
        # Check if btnurl is escaped
        n_escapes = 0
        to_check = match.start(1) - 1
        while to_check > 0 and text[to_check] == "\\":
            n_escapes += 1
            to_check -= 1

        # if even, not escaped -> create button
        if n_escapes % 2 == 0:
            note_data += text[prev:match.start(1)]
            prev = match.end(1)
            if match.group(3) == "buttonalert":
                # create a thruple with button label, url, and newline status
                if bool(match.group(5)) and buttons:
                    buttons[-1].append(InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"alertmessage:{i}:{keyword}"
                    ))
                else:
                    buttons.append([InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"alertmessage:{i}:{keyword}"
                    )])
                i += 1
                alerts.append(match.group(4))
            elif bool(match.group(5)) and buttons:
                buttons[-1].append(InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                ))
            else:
                buttons.append([InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                )])

        else:
            note_data += text[prev:to_check]
            prev = match.start(1) - 1
    else:
        note_data += text[prev:]

    try:
        return note_data, buttons, alerts
    except:
        return note_data, buttons, None

def remove_escapes(text: str) -> str:
    res = ""
    is_escaped = False
    for counter in range(len(text)):
        if is_escaped:
            res += text[counter]
            is_escaped = False
        elif text[counter] == "\\":
            is_escaped = True
        else:
            res += text[counter]
    return res


def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'

async def get_shortlink(chat_id, link):
    settings = await get_settings(chat_id) #fetching settings for group
    if 'shortlink' in settings.keys():
        URL = settings['shortlink']
        API = settings['shortlink_api']
    else:
        URL = SHORTLINK_URL
        API = SHORTLINK_API
    if URL.startswith("shorturllink") or URL.startswith("terabox.in") or URL.startswith("urlshorten.in"):
        URL = SHORTLINK_URL
        API = SHORTLINK_API
    if URL == "api.shareus.io":
        # method 1:
        # https = link.split(":")[0] #splitting https or http from link
        # if "http" == https: #if https == "http":
        #     https = "https"
        #     link = link.replace("http", https) #replacing http to https
        # conn = http.client.HTTPSConnection("api.shareus.io")
        # payload = json.dumps({
        #   "api_key": "4c1YTBacB6PTuwogBiEIFvZN5TI3",
        #   "monetization": True,
        #   "destination": link,
        #   "ad_page": 3,
        #   "category": "Entertainment",
        #   "tags": ["trendinglinks"],
        #   "monetize_with_money": False,
        #   "price": 0,
        #   "currency": "INR",
        #   "purchase_note":""

        # })
        # headers = {
        #   'Keep-Alive': '',
        #   'Content-Type': 'application/json'
        # }
        # conn.request("POST", "/generate_link", payload, headers)
        # res = conn.getresponse()
        # data = res.read().decode("utf-8")
        # parsed_data = json.loads(data)
        # if parsed_data["status"] == "success":
        #   return parsed_data["link"]
    #method 2
        url = f'https://{URL}/easy_api'
        params = {
            "key": API,
            "link": link,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, raise_for_status=True, ssl=False) as response:
                    data = await response.text()
                    return data
        except Exception as e:
            logger.error(e)
            return link
    else:
        shortzy = Shortzy(api_key=API, base_site=URL)
        link = await shortzy.convert(link)
        return link

async def get_tutorial(chat_id):
    settings = await get_settings(chat_id) #fetching settings for group
    if 'tutorial' in settings.keys():
        if settings['is_tutorial']:
            TUTORIAL_URL = settings['tutorial']
        else:
            TUTORIAL_URL = TUTORIAL
    else:
        TUTORIAL_URL = TUTORIAL
    return TUTORIAL_URL

#=================== Dual Verify Shortlink Genrate ===================#
async def get_verify_shortlink(url, is_second_shortener=False):
    if is_second_shortener:
        api, site = VERIFY_API2, VERIFY_URL2
    else:
        api, site = VERIFY_API, VERIFY_URL

    shortzy = Shortzy(api, site)
    try:
        url = await shortzy.convert(url)
    except Exception as e:
        url = await shortzy.get_quick_link(url)
    return url
#=========================================================================#

async def send_all(bot, userid, files, ident, chat_id, user_name, query):
    settings = await get_settings(chat_id)
    if 'is_shortlink' in settings.keys():
        ENABLE_SHORTLINK = settings['is_shortlink']
    else:
        await save_group_settings(message.chat.id, 'is_shortlink', False)
        ENABLE_SHORTLINK = False
    try:
        if ENABLE_SHORTLINK:
            for file in files:
                title = file.file_name
                size = get_size(file.file_size)
                await bot.send_message(chat_id=userid, text=f"<b>Hᴇʏ ᴛʜᴇʀᴇ {user_name} 👋🏽 \n\n✅ Sᴇᴄᴜʀᴇ ʟɪɴᴋ ᴛᴏ ʏᴏᴜʀ ғɪʟᴇ ʜᴀs sᴜᴄᴄᴇssғᴜʟʟʏ ʙᴇᴇɴ ɢᴇɴᴇʀᴀᴛᴇᴅ ᴘʟᴇᴀsᴇ ᴄʟɪᴄᴋ ᴅᴏᴡɴʟᴏᴀᴅ ʙᴜᴛᴛᴏɴ\n\n🗃️ Fɪʟᴇ Nᴀᴍᴇ : {title}\n🔖 Fɪʟᴇ Sɪᴢᴇ : {size}</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 Dᴏᴡɴʟᴏᴀᴅ 📥", url=await get_shortlink(chat_id, f"https://telegram.me/{temp.U_NAME}?start=files_{file.file_id}"))]]))
        else:
            for file in files:
                    f_caption = file.caption
                    title = file.file_name
                    size = get_size(file.file_size)
                    if CUSTOM_FILE_CAPTION:
                        try:
                            f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                                    file_size='' if size is None else size,
                                                                    file_caption='' if f_caption is None else f_caption)
                        except Exception as e:
                            print(e)
                            f_caption = f_caption
                    if f_caption is None:
                        f_caption = f"{title}"
                    await bot.send_cached_media(
                        chat_id=userid,
                        file_id=file.file_id,
                        caption=f_caption,
                        protect_content=True if ident == "filep" else False,
                        reply_markup=InlineKeyboardMarkup(
                            [
                                [
                                InlineKeyboardButton('Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ', url=GRP_LNK),
                                InlineKeyboardButton('Uᴘᴅᴀᴛᴇs Cʜᴀɴɴᴇʟ', url=CHNL_LNK)
                            ],[
                                InlineKeyboardButton("Bᴏᴛ Oᴡɴᴇʀ", url=USERNAME)
                                ]
                            ]
                        )
                    )
    except UserIsBlocked:
        await query.answer('Uɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ ᴍᴀʜɴ !', show_alert=True)
    except PeerIdInvalid:
        await query.answer('Hᴇʏ, Sᴛᴀʀᴛ Bᴏᴛ Fɪʀsᴛ Aɴᴅ Cʟɪᴄᴋ Sᴇɴᴅ Aʟʟ', show_alert=True)
    except Exception as e:
        await query.answer('Hᴇʏ, Sᴛᴀʀᴛ Bᴏᴛ Fɪʀsᴛ Aɴᴅ Cʟɪᴄᴋ Sᴇɴᴅ Aʟʟ', show_alert=True)

async def get_cap(settings, remaining_seconds, files, query, total_results, search):
    if settings["imdb"]:
        IMDB_CAP = temp.IMDB_CAP.get(query.from_user.id)
        if IMDB_CAP:
            cap = IMDB_CAP
            cap+="<b>\n\n<u>👇 Your Movie Files 👇</u></b>\n\n"
            for file in files:
                cap += f"""<b>‼️ <a href='https://telegram.me/{temp.U_NAME}?start=files_{file.file_id}'>[{get_size(file.file_size)}] {file.file_name}\n\n</a></b>"""
            cap  += f"<b>\n⚠️ ᴀꜰᴛᴇʀ 5 ᴍɪɴᴜᴛᴇꜱ ᴛʜɪꜱ ᴍᴇꜱꜱᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛꜱ 🗑️\n</b>"
        else:
            imdb = await get_poster(search, file=(files[0]).file_name) if settings["imdb"] else None
            if imdb:
                TEMPLATE = script.IMDB_TEMPLATE_TXT
                cap = TEMPLATE.format(
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
                    **locals()
                )
                cap+="<b>\n\n<u>👇 Your Movie Files 👇</u></b>\n\n"
                for file in files:
                    cap += f"""<b>‼️ <a href='https://telegram.me/{temp.U_NAME}?start=files_{file.file_id}'>[{get_size(file.file_size)}] {file.file_name}\n\n</a></b>"""
                cap  += f"<b>\n⚠️ ᴀꜰᴛᴇʀ 5 ᴍɪɴᴜᴛᴇꜱ ᴛʜɪꜱ ᴍᴇꜱꜱᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛꜱ 🗑️\n</b>"
            else:
                cap = f"<b>Hᴇʏ {query.from_user.mention}, Fᴏᴜɴᴅ {total_results} Rᴇsᴜʟᴛs ғᴏʀ Yᴏᴜʀ Qᴜᴇʀʏ {search}\n\n</b>"
                cap+="<b><u>👇 Your Movie  Files 👇</u></b>\n\n"
                for file in files:
                    cap += f"""<b>‼️ <a href='https://telegram.me/{temp.U_NAME}?start=files_{file.file_id}'>[{get_size(file.file_size)}] {file.file_name}\n\n</a></b>"""
                cap  += f"<b>\n⚠️ ᴀꜰᴛᴇʀ 5 ᴍɪɴᴜᴛᴇꜱ ᴛʜɪꜱ ᴍᴇꜱꜱᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛꜱ 🗑️\n</b>"
    else:
        cap = f"<b>Hᴇʏ {query.from_user.mention}, Fᴏᴜɴᴅ {total_results} Rᴇsᴜʟᴛs ғᴏʀ Yᴏᴜʀ Qᴜᴇʀʏ {search}\n\n</b>"
        cap+="<b><u>👇 Your Movie  Files 👇</u></b>\n\n"
        for file in files:
            cap += f"""<b>‼️ <a href='https://telegram.me/{temp.U_NAME}?start=files_{file.file_id}'>[{get_size(file.file_size)}] {file.file_name}\n\n</a></b>"""
        cap  += f"<b>\n⚠️ ᴀꜰᴛᴇʀ 5 ᴍɪɴᴜᴛᴇꜱ ᴛʜɪꜱ ᴍᴇꜱꜱᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛꜱ 🗑️\n</b>"
    return cap


async def get_seconds(time_string):
    def extract_value_and_unit(ts):
        value = ""
        unit = ""

        index = 0
        while index < len(ts) and ts[index].isdigit():
            value += ts[index]
            index += 1

        unit = ts[index:].lstrip()

        if value:
            value = int(value)

        return value, unit

    value, unit = extract_value_and_unit(time_string)

    if unit == 's':
        return value
    elif unit == 'min':
        return value * 60
    elif unit == 'hour':
        return value * 3600
    elif unit == 'day':
        return value * 86400
    elif unit == 'month':
        return value * 86400 * 30
    elif unit == 'year':
        return value * 86400 * 365
    else:
        return 0
