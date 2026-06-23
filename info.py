import re
from os import environ, getenv
from Script import script 

id_pattern = re.compile(r'^-?\d+$')

def is_enabled(value, default):
    if value.lower() in ["true", "yes", "1", "enable", "y"]:
        return True
    elif value.lower() in ["false", "no", "0", "disable", "n"]:
        return False
    else:
        return default

def fix_channel_id(ch):
    """
    Accepts numeric ID (-1001234567890), bare ID (1001234567890),
    @username, or plain username — returns correct format for Pyrogram.
    """
    ch = str(ch).strip()
    if not ch:
        return None
    if ch.startswith('@'):
        return ch
    try:
        cid = int(ch)
        if cid < 0:
            return cid
        if cid > 1_000_000_000:
            return int(f"-100{cid}")
        return cid
    except (ValueError, TypeError):
        # Plain username without @
        return f"@{ch}"

def parse_single(env_key, default=''):
    """Parse a single channel/chat — returns int ID or @username or None."""
    val = environ.get(env_key, default).strip()
    if not val:
        return None
    return fix_channel_id(val)

def parse_positive_number(env_key, default, number_type=float):
    """Parse a numeric env var (int or float), falling back to `default`
    and logging a clear warning instead of crashing the bot on bad input."""
    raw = environ.get(env_key, '').strip()
    if not raw:
        return number_type(default)
    try:
        value = number_type(raw)
    except (TypeError, ValueError):
        print(f"[info.py] Invalid value for {env_key}={raw!r}, expected a {number_type.__name__} — using default {default}")
        return number_type(default)
    if value <= 0:
        print(f"[info.py] {env_key}={raw!r} must be greater than 0 — using default {default}")
        return number_type(default)
    return value

# Bot information
SESSION = environ.get('SESSION', 'Media_search')
API_ID = int(environ.get('API_ID', '0') or '0')
API_HASH = environ.get('API_HASH', '')
BOT_TOKEN = environ.get('BOT_TOKEN', "")

# Stream link shortener
STREAM_SITE = environ.get('STREAM_SITE', '')
STREAM_API = environ.get('STREAM_API', '')

# Premium logs channel — accepts ID or username
PREMIUM_LOGS = parse_single('PREMIUM_LOGS')

SUBSCRIPTION = environ.get('SUBSCRIPTION', 'https://graph.org/file/a36b4b70f61796cfb8d5d.jpg')
CODE = environ.get('CODE', 'https://graph.org/file/2790ba63079bbee6b473f.jpg')

# Bot settings
CACHE_TIME = int(environ.get('CACHE_TIME', '300') or '300')
USE_CAPTION_FILTER = bool(environ.get('USE_CAPTION_FILTER', True))

PICS = (environ.get('PICS', 'https://graph.org/file/31b69f67e6f085a61fb92-8bbd37b80eb61b11b2.jpg')).split()
NOR_IMG = environ.get("NOR_IMG", "https://te.legra.ph/file/a27dc8fe434e6b846b0f8.jpg")
MELCOW_VID = environ.get("MELCOW_VID", "https://graph.org/file/ca0f3a822fa09df4a6663-b956c564a73bf7d1db.jpg")
SPELL_IMG = environ.get("SPELL_IMG", "https://te.legra.ph/file/15c1ad448dfe472a5cbb8.jpg")

# Admins, Channels & Users
USERNAME = environ.get("USERNAME", "https://t.me/Muja_tg18")
ADMINS = [int(admin) for admin in environ.get('ADMINS', '').split() if id_pattern.search(admin)]

# All channel/group IDs — accept numeric ID or username
CHANNELS = [fix_channel_id(ch) for ch in (environ.get('CHANNELS', '') or '').split() if ch.strip()]

auth_users = [int(user) if id_pattern.search(user) else user for user in environ.get('AUTH_USERS', '').split()]
AUTH_USERS = (auth_users + ADMINS) if auth_users else []
PREMIUM_USER = [int(user) if id_pattern.search(user) else user for user in environ.get('PREMIUM_USER', '').split()]

AUTH_CHANNEL = parse_single('AUTH_CHANNEL')
auth_grp = environ.get('AUTH_GROUP', '')
AUTH_GROUPS = [fix_channel_id(ch) for ch in auth_grp.split() if ch.strip()] if auth_grp else None

SUPPORT_CHAT_ID = parse_single('SUPPORT_CHAT_ID')
REQST_CHANNEL = parse_single('REQST_CHANNEL_ID')

NO_RESULTS_MSG = bool(environ.get("NO_RESULTS_MSG", False))

# MongoDB information
DATABASE_URI = environ.get('DATABASE_URI', '')
DATABASE_NAME = environ.get('DATABASE_NAME', 'Telegram_Bot')
COLLECTION_NAME = environ.get('COLLECTION_NAME', 'files')



#====================[       For Dual Verification      ]===========================#
VERIFY = is_enabled((environ.get('VERIFY', 'False')), False)
TIMEZONE = environ.get("TIMEZONE", "Asia/Kolkata")
VERIFY_TIME2 = int(environ.get('VERIFY_TIME2', '1800') or '1800')
VERIFY_URL = environ.get('VERIFY_URL', '')
VERIFY_API = environ.get('VERIFY_API', '')
VERIFY_URL2 = environ.get('VERIFY_URL2', '')
VERIFY_API2 = environ.get('VERIFY_API2', '')
VERIFY_IMG = environ.get("VERIFY_IMG", "https://graph.org/file/d208da11507ba55fe7e2b.jpg")
TUTORIAL_LINK_1 = environ.get('TUTORIAL_LINK_1', '')
TUTORIAL_LINK_2 = environ.get('TUTORIAL_LINK_2', '')
#====================================================================================#

SHORTLINK_URL = environ.get('SHORTLINK_URL', '')
SHORTLINK_API = environ.get('SHORTLINK_API', '')
IS_SHORTLINK = bool(environ.get('IS_SHORTLINK', False))
DELETE_CHANNELS = [fix_channel_id(dch) for dch in (environ.get('DELETE_CHANNELS', '') or '').split() if dch.strip()]
MAX_B_TN = environ.get("MAX_B_TN", "5")
MAX_BTN = is_enabled((environ.get('MAX_BTN', "True")), True)
GRP_LNK = environ.get('GRP_LNK', 'https://t.me/+K5mivDTeP9lkYjk1')
CHNL_LNK = environ.get('CHNL_LNK', 'https://t.me/rioupdates1')
TUTORIAL = environ.get('TUTORIAL', 'https://t.me/muja_tg18')
IS_TUTORIAL = bool(environ.get('IS_TUTORIAL', True))
MSG_ALRT = environ.get('MSG_ALRT', 'Men Are Brave')

# LOG_CHANNEL — optional, accepts ID or username
LOG_CHANNEL = parse_single('LOG_CHANNEL')

# STREAM_CHANNEL — fallback if LOG_CHANNEL not set, accepts ID or username
STREAM_CHANNEL = parse_single('STREAM_CHANNEL')

SUPPORT_CHAT = environ.get('SUPPORT_CHAT', 'TEAMRIO_SUPPORT_GROUP')
P_TTI_SHOW_OFF = is_enabled((environ.get('P_TTI_SHOW_OFF', "False")), False)
IMDB = is_enabled((environ.get('IMDB', "True")), True)
# PM_IMDB — when True, PM search results include TMDB movie info (poster, rating, cast …)
# Set PM_IMDB=False in env to get plain file-list results in PM (faster, no API call)
PM_IMDB = is_enabled((environ.get('PM_IMDB', "True")), True)
TMDB_API_KEY = environ.get('TMDB_API_KEY', '2da4293666e16b404379924b7045344c')


AUTO_FFILTER = is_enabled((environ.get('AUTO_FFILTER', "True")), True)
AUTO_DELETE = is_enabled((environ.get('AUTO_DELETE', "True")), True)
SINGLE_BUTTON = is_enabled((environ.get('SINGLE_BUTTON', "True")), True)
CUSTOM_FILE_CAPTION = environ.get("CUSTOM_FILE_CAPTION", f"{script.CAPTION}")
BATCH_FILE_CAPTION = environ.get("BATCH_FILE_CAPTION", CUSTOM_FILE_CAPTION)
IMDB_TEMPLATE = environ.get("IMDB_TEMPLATE", f"{script.IMDB_TEMPLATE_TXT}")
LONG_IMDB_DESCRIPTION = is_enabled(environ.get("LONG_IMDB_DESCRIPTION", "True"), True)
SPELL_CHECK_REPLY = is_enabled(environ.get("SPELL_CHECK_REPLY", "True"), True)
MAX_LIST_ELM = environ.get("MAX_LIST_ELM", None)

index_req_channel = environ.get('INDEX_REQ_CHANNEL', '').strip()
if index_req_channel:
    INDEX_REQ_CHANNEL = fix_channel_id(index_req_channel)
else:
    INDEX_REQ_CHANNEL = LOG_CHANNEL

FILE_STORE_CHANNEL = [fix_channel_id(ch) for ch in (environ.get('FILE_STORE_CHANNEL', '') or '').split() if ch.strip()]
MELCOW_NEW_USERS = is_enabled((environ.get('MELCOW_NEW_USERS', "True")), True)
PROTECT_CONTENT = is_enabled((environ.get('PROTECT_CONTENT', "False")), False)
PUBLIC_FILE_STORE = is_enabled((environ.get('PUBLIC_FILE_STORE', "False")), False)

LANGUAGES = ["malayalam", "mal", "tamil", "tam", "english", "eng", "hindi", "hin", "telugu", "tel", "kannada", "kan"]
SEASONS = ["season 1", "season 2", "season 3", "season 4", "season 5", "season 6", "season 7", "season 8", "season 9", "season 10"]
QUALITIES = ["480p", "720p", "1080p", "2160p"]
RELEASEYEAR = ["2006", "2007", "2008", "2009", "2010", "2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "", "2026"]



# PM Text Filter - YES: show file results in PM | NO: show PM warning
TEXT_FILTER = is_enabled(environ.get('TEXT_FILTER', 'Yes'), False)

# Online Stream and Download
PORT = int(environ.get('PORT', '8080') or '8080')
NO_PORT = bool(environ.get('NO_PORT', False))
APP_NAME = None
if 'DYNO' in environ:
    ON_HEROKU = True
    APP_NAME = environ.get('APP_NAME')
else:
    ON_HEROKU = False
BIND_ADRESS = str(getenv('WEB_SERVER_BIND_ADDRESS', '0.0.0.0'))

# ==============================
# KOYEB / DEPLOYMENT URL CONFIG
# ==============================
# Your Koyeb URL is set here directly — change this if your URL changes
KOYEB_URL = ""

_env_url  = getenv('URL',  '').strip()
_env_fqdn = getenv('FQDN', '').strip()

def _valid_url(u):
    return bool(u) and '0.0.0.0' not in u and u.startswith('http')

if _valid_url(_env_url):
    # Priority 1: URL env variable
    URL  = _env_url if _env_url.endswith('/') else _env_url + '/'
    FQDN = URL.replace('https://', '').replace('http://', '').rstrip('/')
elif _valid_url(_env_fqdn):
    # Priority 2: FQDN env variable
    FQDN = _env_fqdn
    URL  = "https://{}/".format(FQDN)
elif ON_HEROKU and APP_NAME:
    # Priority 3: Heroku
    FQDN = APP_NAME + '.herokuapp.com'
    URL  = "https://{}/".format(FQDN)
else:
    # Priority 4: Use hardcoded Koyeb URL above
    URL  = KOYEB_URL
    FQDN = URL.replace('https://', '').replace('http://', '').rstrip('/')
SLEEP_THRESHOLD = int(environ.get('SLEEP_THRESHOLD', '60') or '60')
WORKERS = int(environ.get('WORKERS', '4') or '4')
SESSION_NAME = str(environ.get('SESSION_NAME', 'Levii'))
MULTI_CLIENT = False
name = str(environ.get('name', 'Levii'))
PING_INTERVAL = int(environ.get("PING_INTERVAL", "1200") or "1200")
if 'DYNO' in environ:
    ON_HEROKU = True
    APP_NAME = str(getenv('APP_NAME'))
else:
    ON_HEROKU = False

HAS_SSL = bool(getenv('HAS_SSL', False))
# URL is already set correctly above — do not overwrite it here

# Configuration logging
LOG_STR = "Current Customized Configurations are:-\n"
LOG_STR += ("IMDB Results are enabled.\n" if IMDB else "IMDB Results are disabled.\n")
LOG_STR += ("PM IMDB (TMDB info in PM search) enabled.\n" if PM_IMDB else "PM IMDB disabled — plain file list in PM.\n")
LOG_STR += (f"TMDB_API_KEY is set ✅\n" if TMDB_API_KEY else "⚠️  TMDB_API_KEY not set — IMDB/movie info will not work.\n")
LOG_STR += ("P_TTI_SHOW_OFF enabled.\n" if P_TTI_SHOW_OFF else "P_TTI_SHOW_OFF disabled.\n")
LOG_STR += ("SINGLE_BUTTON enabled.\n" if SINGLE_BUTTON else "SINGLE_BUTTON disabled.\n")
LOG_STR += (f"CUSTOM_FILE_CAPTION: {CUSTOM_FILE_CAPTION}\n" if CUSTOM_FILE_CAPTION else "No CUSTOM_FILE_CAPTION.\n")
LOG_STR += ("Long IMDB storyline enabled.\n" if LONG_IMDB_DESCRIPTION else "LONG_IMDB_DESCRIPTION disabled.\n")

LOG_STR += (f"MAX_LIST_ELM: {MAX_LIST_ELM}\n" if MAX_LIST_ELM else "Full cast/crew list enabled.\n")
LOG_STR += f"IMDB template: {IMDB_TEMPLATE}\n"
if not LOG_CHANNEL:
    LOG_STR += "\n⚠️  LOG_CHANNEL not set — using STREAM_CHANNEL for streaming.\n" if STREAM_CHANNEL else "\n⚠️  WARNING: Neither LOG_CHANNEL nor STREAM_CHANNEL is set. Streaming will not work.\n"