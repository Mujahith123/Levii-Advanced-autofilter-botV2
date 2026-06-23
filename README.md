> **Credits:** This repo fully created by Telegram [@muja_tg18](https://t.me/muja_tg18)

<p align="center">
  <img src="https://i.postimg.cc/yNRzLHCQ/a8034e0df1c89f502899ae1cd4197924.jpg" width="280"/>
</p>

<h1 align="center">⚡ LEVII AUTO FILTER BOT</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-yellow?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Pyrogram-2.x-orange?style=for-the-badge" alt="Pyrogram"/>
  <img src="https://img.shields.io/badge/MongoDB-Database-47A248?style=for-the-badge&logo=mongodb&logoColor=white" alt="MongoDB"/>
  <img src="https://img.shields.io/badge/License-GPL_v2-green?style=for-the-badge" alt="License"/>
</p>

<p align="center">
  A powerful, feature-rich Telegram Auto Filter Bot built with <b>Pyrogram</b> and <b>MongoDB</b>.<br/>
  Indexes files from Telegram channels, serves them to groups and PM via smart search, supports<br/>
  streaming, shortlink monetization, dual verification, premium plans, IMDB info, content-gap<br/>
  analytics, scheduled broadcasts, and a bundle of fun/utility extras.
</p>

---

## 📑 Table of Contents

- [Features](#-features)
- [Commands](#-commands)
- [BotFather Command List](#-botfather-command-list)
- [Environment Variables](#-environment-variables)
- [Deployment](#-deployment)
- [Credits](#-credits)
- [License](#-disclaimer--license)

---

## ✨ Features

### 🎬 Core — File Search & Indexing

**Auto Filter**
When a user types a movie or file name in a connected group, the bot strips filler words (language tags, "please", "send me", etc.) and searches the database, returning matching results with download/stream buttons. If nothing matches, it can fall back to a Google-assisted suggestion (see **Spell-Check Fallback** below) when that setting is enabled for the group.

**Manual Filters vs Global Filters vs Auto Filter — priority order**
For every group text message, the bot checks in this order: **per-group manual filters** (set with `/filter`) → **bot-wide global filters** (set with `/gfilter`) → **auto filter** (the database search). The first one that matches wins.

**File Indexing (Channel / Link based)**
Admins index an entire channel by forwarding a post from it (or pasting a `t.me/...` link) to the bot in PM. The bot asks for confirmation, then walks every message in that channel, saving every video/audio/document to MongoDB while skipping deleted messages, non-media messages, and duplicates. A live progress counter updates every 20 messages, and indexing can be cancelled mid-run with a **Cancel** button.

**Live Channel Auto-Indexing**
Any file posted directly into a channel listed in `CHANNELS` is saved to the database automatically the moment it's posted — no manual indexing needed.

**Non-Admin Index Requests**
If a non-admin forwards a file/link for indexing, it's sent to `INDEX_REQ_CHANNEL` (or `LOG_CHANNEL`) for an admin to **Accept** or **Reject** via inline buttons, and the requester is notified either way.

**Inline Search**
Search the database inline from any chat with `@yourbotusername <query>`. Supports filtering by file type using `query|filetype` syntax, paginates results, and respects `AUTH_USERS`/`AUTH_CHANNEL` access gates.

**PM Search**
When `TEXT_FILTER` is enabled, users can type a movie name directly in the bot's PM and get the same search experience as in groups — including the shortlink/verification gate for non-premium users.

**Spell-Check Fallback (Google/IMDB-Assisted)**
If a search returns nothing and the group's `spell_check` setting is on, the bot cleans up the query and runs a Google search to suggest the closest-matching title, along with **Google Search** and **📩 Request** buttons. This is a search-engine-assisted suggestion, not fuzzy/edit-distance matching against the file database.

**Content Gap Logging**
Every failed search (no results found) is logged in the background with the query text, user ID, group, and timestamp — this feeds the **Content Gap Analytics** dashboard described further down.

---

### 🔗 Streaming & Links

**Fast Download**
Every file result includes a direct download link served by the bot's own built-in web server (`aiohttp`) — no third-party file host required.

**Watch Online (Stream)**
Files can be streamed straight in the browser via a unique `/watch/<hash><id>` URL with full HTTP byte-range support, so videos can be seeked and played without downloading the whole file first. Audio/video files are served `inline`; everything else is served as an `attachment`.

**Multi-Client Load Balancing**
You can register extra bot tokens as `MULTI_TOKEN1`, `MULTI_TOKEN2`, etc. The bot starts a Pyrogram client for each one and spreads streaming/download requests across whichever client currently has the lightest load — useful for high-traffic deployments hitting Telegram's per-bot file-download rate limits.

**Link Generator**
`/link` (or `/plink` for a forward-protected version) replies to any video/audio/document message and returns a permanent `https://t.me/yourbot?start=...` deep link that re-delivers that exact file on demand.

**Batch Link Generator**
`/batch` (or `/pbatch` for forward-protected files) has two modes:
- **Interactive** — run `/batch` with no arguments and the bot opens a 60-second window where you simply forward/send files one by one (each gets a ✅ confirmation); it then bundles everything into one shareable link with a **Cancel** button available throughout.
- **URL-range** — run `/batch <first_message_link> <last_message_link>` to grab every file between two channel post links in one shot.

---

### 👑 Premium System

**Premium Users**
Admins grant premium access to any user for a chosen duration (e.g. `1 day`, `2 hours`, `1 month`, `1 year`) with `/add_premium`. Premium users skip all shortlink ads and verification gates entirely.

**Permanent Premium**
User IDs listed in the `PREMIUM_USER` env variable get ad-free access with no expiry, no command needed.

**Premium Logs**
Every grant and removal is posted to the `PREMIUM_LOGS` channel and DM'd to the affected user.

**One-Time Free Trial**
New users can tap **🥳 Get 5 Mins Free Trial** (from `/plan` or the "Buy Premium" prompt) once per account for a 5-minute taste of ad-free access.

**Referral System**
`/refer` gives a personal `?start=ref_<id>` link. The first time a genuinely new user starts the bot through that link, the referrer is credited **+1 day of premium**, stacked on top of whatever plan they already have.

---

### ✅ Dual Verification System

A two-step shortlink verification gate for free (non-premium, non-verified) users before they reach files.

- **Step 1** — user completes the first shortlink provider (`VERIFY_URL` / `VERIFY_API`)
- **Step 2** — user completes the second shortlink provider (`VERIFY_URL2` / `VERIFY_API2`)
- **Token Validity** — each verification stays valid for `VERIFY_TIME2` seconds (default 1800s / 30 min); after that the user must verify again
- **Returning Users** — if a user's first-step token has expired, they're routed straight to the second shortener on their next attempt instead of repeating step one
- **Tutorial Buttons** — each step can show a "how to verify" button pointed at `TUTORIAL_LINK_1` / `TUTORIAL_LINK_2`

**Gate priority (PM & group search)** — checked in this exact order for every search result:
1. Premium user → direct results, no gate
2. Already-verified user within their window → direct results
3. `VERIFY=True` → verification gate
4. `IS_SHORTLINK=True` → single shortlink gate
5. None of the above → direct results

---

### 🌐 Global Force Subscribe

`AUTH_CHANNEL` (and optionally `AUTH_GROUP`) lets you require users to join a channel/group before using the bot anywhere. Public channels are handled with a plain join link plus membership re-check on **Try Again**; private channels use Telegram's join-request flow (`creates_join_request=True`) combined with auto-approval once the user is verified — see **Join Request Handling** below.

---

### 👥 Group Management

**Per-Group Settings Panel**
`/settings` opens an inline toggle panel (in-group or routed to PM) controlling: result page style (button vs text), file send mode (auto vs manual start), protect content, IMDB info, spell check, welcome message, auto-delete, auto-filter, max buttons, and the per-group shortlink switch.

**Connect / Disconnect**
`/connect <group_id>` lets an admin manage a group's filters and settings from bot PM without typing commands in the group itself; `/disconnect` and `/connections` round out the flow.

**Join Request Handling**
Pending join requests to `AUTH_CHANNEL` are recorded in the database and auto-approved once the requesting user completes verification — no manual approval needed. `/delreq` clears the stored join-request backlog.

**Welcome Message**
New members get a custom welcome video/caption (configurable per group via the `welcome` setting) with quick links to the support group, updates channel, and bot owner.

**Auto Delete**
Files (and the welcome message, if enabled) are automatically deleted after a countdown to reduce copyright exposure; users are reminded to forward files to Saved Messages first.

**Ban / Unban (Users & Groups)**
Admins can ban individual users (`/ban`, `/unban`) and disable/re-enable entire chats (`/disable`, `/enable`) — disabled chats get a notice and the bot leaves automatically. `/leave <chat_id>` removes the bot from any single chat on demand.

**Maintenance Mode**
`/maintenance on|off` makes the bot respond to admins only — useful during indexing, migrations, or outages.

---

### 📢 Broadcast

**User Broadcast** — `/broadcast` (reply to a message) sends it to every user who has ever started the bot.
**Group Broadcast** — `/grp_broadcast` (reply to a message) sends it to every connected group.
**Broadcast with Buttons** — `/bcast_btn` sends a message with custom inline buttons attached.
**Scheduled Broadcast** — `/schedule_broadcast YYYY-MM-DD HH:MM` (reply to a message, time in IST) queues it with APScheduler; pending jobs survive a bot restart and are re-queued automatically on startup. Manage with `/list_scheduled` and `/cancel_scheduled <id>`.

---

### 🎭 IMDB Integration

**Auto IMDB Info**
File results can be enriched with title, poster, rating, genre, release year, and storyline pulled live from IMDB (via Cinemagoer).

**Separate PM Toggle**
`PM_IMDB` controls IMDB enrichment specifically for PM search results independently of the group-level `imdb` setting — handy if you want faster, plain file lists in PM while keeping rich cards in groups.

**Custom Template**
`/set_template` lets each group define its own Jinja2 template for how IMDB info is rendered.

**Manual IMDB Search**
`/imdb <title>` or `/search <title>` looks up a title directly and returns a tappable list of matches with poster, rating, genre, and storyline.

---

### 📋 Content Gap Analytics

**Not-Found Logging**
Every search that returns zero results is logged with the query, user, group, and timestamp.

**Standard Dashboard** — `/stats` and `/dashboard` show user/group/file counts, today's search activity, top searched titles, and top active groups.
**Gap Dashboard** — `/gapdashboard` adds the content-gap angle specifically: today's searches vs. today's not-found count, the top titles people search for but the bot doesn't have (your real "what to add next" list), all-time most-searched titles, a 7-day search trend, and the most active groups.

---

### 🎯 Smart Request System

**Request Button**
Any "no results found" message shows a **📩 Request** button. Tapping it saves the request and notifies admins via the log channel — no typing required.

**Manual Request Command**
`/request <movie name>` (also works as `#request <movie name>` in groups) formally logs a request and forwards it to the log/request channel.

**Auto-Fulfilment Notification**
The moment a newly indexed file's name or caption matches an open request — from *any* indexing path (channel auto-index, forwarded-file index, or batch) — the requester is automatically DM'd that their file is ready, with no admin action needed.

---

### 🎶 Extra Tools (Fun & Utility)

A grab-bag of additional commands available in both PM and groups, layered on top of the core file-sharing bot:

- **🎵 YouTube Song/Video Downloader** — `/song` (or `/mp3`) and `/video` (or `/mp4`) search YouTube and deliver the top result as an audio file or MP4. Requires a valid `cookies.txt` (see `COOKIES_FILE_PATH`) since YouTube blocks most server IPs without it — the bot detects bot-check / expired-cookie errors and explains exactly what to fix.
- **🌐 Translate** — `/translate <lang> <text>` or `/translate <lang>` as a reply; accepts both language codes (`es`, `fr`, `ta`) and full names (`spanish`, `french`, `tamil`). Falls back to a secondary endpoint automatically if the primary translation call fails.
- **🔊 Text-to-Speech** — `/tts` (reply to a text message) auto-detects the language and replies with an MP3.
- **🎤 Lyrics** — `/lyrics <song name>` (or reply) fetches lyrics from two free providers with automatic fallback.
- **📋 Paste / Telegraph** — `/paste` (or `/tgpaste`, `/pasty`) uploads text/code (typed, replied text, or a replied `.txt` file) to a pastebin and returns shareable + raw links. `/telegraph` (reply to a photo/GIF/MP4 under 5MB) uploads it to telegra.ph.
- **🎲 Dice Games** — `/throw` or `/dart` (🎯), `/roll` or `/dice` (🎲), `/luck` or `/cownd` (🎰 slot machine), `/goal` or `/shoot` (⚽) send Telegram's native animated dice/emoji games.
- **🔐 Password Generator** — `/genpassword` or `/genpw [length]` generates a random alphanumeric+symbol password (default length picked randomly if omitted).
- **🏓 Ping** — `/ping` reports round-trip response time.
- **🌀 Sticker Tools** — `/getsticker` (downloads a replied sticker as a file), `/stickerid` (returns a replied sticker's file ID), `/findsticker` (re-sends a sticker from a replied file ID), `/clearcache` (clears the bot's local sticker download cache).
- **🔤 Aesthetic Text** — `/ae <text>` converts text into fullwidth "aesthetic" Unicode characters.
- **🎭 Random One-Liners** — `/runs` replies with a random joke/quote line.

---

### ⚙️ Miscellaneous

- **Bot Stats** — `/stats` (rich admin view) and `/dashboard` for users, groups, files, DB size, and premium counts
- **Backup & Restore** — `/backup` exports the entire file database as JSON to the log channel; `/restore` re-imports it
- **Protect Content** — prevent users from forwarding files the bot sends (`PROTECT_CONTENT`, or per-group via `/settings`)
- **Shortlink Monetization** — wrap every file/result link in a shortlink provider (`/shortlink`, `/shortlink_info`, `/setshortlinkon`, `/setshortlinkoff`) to earn from ad views
- **Tutorials** — `/set_tutorial <url>` / `/remove_tutorial` lets each group set its own "how to download" link shown alongside shortlinks
- **ID / Info Tools** — `/id` returns chat/user/file IDs; `/info` returns detailed profile info for a user
- **Restart** — `/restart` restarts the bot process in place

---

## 📋 Commands

### 👤 User Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot, get the welcome message (also handles deep links, referral links, and verification callbacks) |
| `/settings` | Open the per-group settings panel (admins only, run in or connected to a group) |
| `/connect <group_id>` | Connect a group to bot PM for filter/settings management |
| `/disconnect` | Disconnect the currently connected group |
| `/connections` | View all groups connected to your account (PM only) |
| `/filter` or `/add` | Add a manual filter in the connected/current group |
| `/filters` or `/viewfilters` | View all active manual filters |
| `/del <keyword>` | Delete a specific manual filter |
| `/delall` | Delete all manual filters in the group |
| `/shortlink <domain> <api>` | Set a custom shortlink domain and API key for your group |
| `/shortlink_info` | View the current shortlink configuration for your group |
| `/set_template` | Set a custom Jinja2 IMDB display template for your group |
| `/set_tutorial <url>` | Set a "how to download" tutorial link for your group |
| `/remove_tutorial` | Remove the group's tutorial link |
| `/request <movie>` or `#request <movie>` | Formally request a movie/file in a group |
| `/myplan` | Check your current premium plan and expiry date |
| `/plan` | View available premium plans, with a one-time free trial option |
| `/refer` | Get your referral link (+1 day premium for the referrer per new user) |
| `/id` | Get the Telegram ID of a user, chat, or replied file |
| `/info` | Get detailed profile information about a user |
| `/imdb <title>` or `/search <title>` | Search IMDB manually for a movie or TV show |
| `/latest` or `/newmovies` | Show the 20 most recently indexed files |
| `/link` | Generate a permanent shareable link for a file (reply to a file) |
| `/plink` | Same as `/link`, but the file is sent with forward-protection |
| `/batch` | Start an interactive batch link session, or use `/batch <link1> <link2>` for a URL range |
| `/pbatch` | Same as `/batch`, but files are sent with forward-protection |

---

### 🎶 Extra / Fun Commands

| Command | Description |
|---------|-------------|
| `/song` or `/mp3 <name>` | Download a song from YouTube as an audio file |
| `/video` or `/mp4 <name>` | Download a video from YouTube as an MP4 |
| `/translate <lang> <text>` or `/tr` | Translate text (code or full language name; also works as a reply) |
| `/tts` | Convert a replied text message to speech (auto-detects language) |
| `/lyrics <song name>` | Fetch lyrics for a song (also works as a reply) |
| `/paste`, `/tgpaste`, `/pasty` | Paste text/code/a replied `.txt` file to a pastebin |
| `/telegraph` | Upload a replied photo/GIF/MP4 (under 5MB) to telegra.ph |
| `/throw` or `/dart` | Send an animated dart throw |
| `/roll` or `/dice` | Send an animated dice roll |
| `/luck` or `/cownd` | Send an animated slot machine |
| `/goal` or `/shoot` | Send an animated football/goal |
| `/runs` | Reply with a random one-liner |
| `/genpassword` or `/genpw [length]` | Generate a random password |
| `/ping` | Check the bot's response time |
| `/getsticker` | Download a replied sticker as a file |
| `/stickerid` | Get the file ID of a replied sticker |
| `/findsticker` | Re-send a sticker from a replied file ID |
| `/clearcache` | Clear the bot's local sticker download cache |
| `/ae <text>` | Convert text to fullwidth "aesthetic" Unicode |

---

### 🔑 Admin Commands

| Command | Description |
|---------|-------------|
| `/channel` | View info about all channels connected to the bot |
| `/logs` | Fetch the bot's latest log file |
| `/delete` | Delete a specific file from the database (reply to the file) |
| `/deleteall` | Delete **all** indexed files from the database |
| `/deletefiles <query>` | Delete multiple files matching a query |
| `/delreq` | Clear the stored join-request backlog |
| `/send <user_id>` | Send a message to a specific user via the bot |
| `/setskip <number>` | Set how many messages to skip at the start of indexing |
| `/stats` | View full bot statistics (users, files, groups, premium count, maintenance status) |
| `/dashboard` | View the standard stats + search-trend dashboard |
| `/gapdashboard` | View the content-gap analytics dashboard |
| `/backup` | Export the full file database as JSON to the log channel |
| `/restore` | Restore the file database from an exported JSON backup |
| `/maintenance on\|off` | Toggle maintenance mode (admins-only access) |
| `/ban <user_id> [reason]` | Ban a user from using the bot |
| `/unban <user_id>` | Unban a previously banned user |
| `/disable <chat_id> [reason]` | Disable the bot in a chat and leave it |
| `/enable <chat_id>` | Re-enable the bot in a previously disabled chat |
| `/leave <chat_id>` | Leave a specific chat immediately |
| `/invite <chat_id>` | Generate an invite link for a chat the bot is in |
| `/users` | List all users saved in the database |
| `/chats` | List all chats saved in the database |
| `/broadcast` | Broadcast a message to all users (reply to message) |
| `/grp_broadcast` | Broadcast a message to all connected groups (reply to message) |
| `/bcast_btn` | Broadcast a message with custom inline buttons |
| `/schedule_broadcast YYYY-MM-DD HH:MM` | Schedule a broadcast (IST, reply to message) |
| `/list_scheduled` | List all pending scheduled broadcasts |
| `/cancel_scheduled <id>` | Cancel a scheduled broadcast |
| `/gfilter` or `/addg` | Add a global filter (active across all groups) |
| `/gfilters` or `/viewgfilters` | View all global filters |
| `/delg <keyword>` | Delete a specific global filter |
| `/delallg` | Delete all global filters |
| `/add_premium <user_id> <amount> <unit>` | Grant premium for a duration, e.g. `/add_premium 12345 1 month` |
| `/remove_premium <user_id>` | Remove premium access from a user |
| `/get_premium <user_id>` | Check the premium status of a user |
| `/premium_users` | List all current premium users and their expiry dates |
| `/setshortlinkon` | Enable the shortlink system globally |
| `/setshortlinkoff` | Disable the shortlink system globally |
| `/restart` | Restart the bot process |

> **Note:** `/ban`, `/unban`, and `/stats` each have two independent implementations in this codebase (one in `commands.py`, one in `p_ttishow.py`) — both are admin-only and do the same job with slightly different output formatting; this is a known duplication rather than two different features.

---

## 🤖 BotFather Command List

Copy and paste this into [@BotFather](https://t.me/BotFather) → **Edit Bot** → **Edit Commands** (BotFather caps lists at a reasonable length, so this covers the core user-facing commands — admin-only and Extra/fun commands are intentionally left out of the public menu):

```
start - Start the bot and get the welcome message
settings - Open group settings panel
connect - Connect a group to bot PM
disconnect - Disconnect the connected group
connections - View all connected groups
filter - Add a manual filter
filters - View all manual filters
del - Delete a manual filter
delall - Delete all manual filters
shortlink - Set shortlink domain and API for your group
shortlink_info - View current shortlink configuration
set_template - Set custom IMDB display template
set_tutorial - Set a tutorial link for verification
remove_tutorial - Remove the tutorial link
request - Request a movie or file
myplan - Check your premium plan and expiry
plan - View available premium plans
refer - Get your referral link
id - Get Telegram ID of a user or chat
info - Get detailed info about a user
imdb - Search IMDB for a movie or show
search - Search IMDB for a movie or show
latest - Show recently indexed files
newmovies - Show recently indexed files
link - Generate a permanent file link
batch - Generate a batch file link
```

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and fill in your values before running the bot. (`.env.example` covers the most common variables — the tables below are the complete, authoritative list straight from `info.py`.)

---

### 🔴 Required

| Variable | Description |
|----------|-------------|
| `API_ID` | Telegram API ID from [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | Telegram API Hash from [my.telegram.org](https://my.telegram.org) |
| `BOT_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) |
| `DATABASE_URI` | MongoDB connection URI (`mongodb+srv://...`) |
| `DATABASE_NAME` | MongoDB database name (default: `Telegram_Bot`) |
| `COLLECTION_NAME` | MongoDB collection name for indexed files (default: `files`) |
| `ADMINS` | Space-separated Telegram user IDs with full admin access |
| `LOG_CHANNEL` | Channel where logs, file copies, batch JSON, and index requests are stored |

---

### 📢 Channels & Groups

| Variable | Description |
|----------|-------------|
| `CHANNELS` | Space-separated channel IDs/usernames auto-indexed live as files are posted |
| `STREAM_CHANNEL` | Fallback channel used for streaming if `LOG_CHANNEL` isn't set |
| `AUTH_CHANNEL` | Global force-subscribe channel (ID or @username) |
| `AUTH_GROUP` | Global force-subscribe group(s) — space-separated |
| `SUPPORT_CHAT_ID` | Support group chat ID/username (searches here are handled differently) |
| `SUPPORT_CHAT` | Support group username (used in links/buttons) |
| `REQST_CHANNEL_ID` | Channel where formal `/request` submissions are forwarded |
| `INDEX_REQ_CHANNEL` | Channel where non-admin index requests are sent for review (falls back to `LOG_CHANNEL`) |
| `FILE_STORE_CHANNEL` | Space-separated channel IDs used for URL-range `/batch` direct file-store mode |
| `DELETE_CHANNELS` | Space-separated channel IDs where files are auto-removed from the DB when deleted there |
| `PREMIUM_LOGS` | Channel where all premium grant/removal activity is logged |

---

### 👤 Users

| Variable | Description |
|----------|-------------|
| `AUTH_USERS` | Extra Telegram user IDs with admin-level bot access (merged with `ADMINS`) |
| `PREMIUM_USER` | Permanent premium user IDs (no expiry, no command needed) |

---

### 🤖 Bot Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSION_NAME` | `Levii` | Pyrogram session file name |
| `USERNAME` | `https://t.me/Muja_tg18` | Bot owner / contact link shown in buttons |
| `GRP_LNK` | — | Support group invite link shown in start/welcome messages |
| `CHNL_LNK` | — | Updates channel invite link shown in start/welcome messages |
| `CACHE_TIME` | `300` | Inline query result cache time in seconds (forced to `0` if `AUTH_USERS`/`AUTH_CHANNEL` is set) |
| `MAX_B_TN` | `5` | Number of result buttons shown when `max_btn` is off |
| `MAX_BTN` | `True` | Default state of the per-group "Max Buttons" setting |
| `MSG_ALRT` | `Men Are Brave` | Alert text shown on certain inline button taps |
| `MULTI_TOKEN1`, `MULTI_TOKEN2`, ... | — | Extra bot tokens for multi-client streaming load balancing |
| `SLEEP_THRESHOLD` | `60` | Pyrogram flood-wait sleep threshold (seconds) |

---

### 🎬 Auto Filter

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTO_FFILTER` | `True` | Enable auto filter (database search) in connected groups |
| `SINGLE_BUTTON` | `True` | Show one combined button per result instead of split download/stream |
| `CUSTOM_FILE_CAPTION` | — | Custom caption template applied to all sent files |
| `BATCH_FILE_CAPTION` | Same as `CUSTOM_FILE_CAPTION` | Caption template used specifically for batch-link file sends |
| `USE_CAPTION_FILTER` | `True` | Include file captions (not just filenames) in search matching |
| `NO_RESULTS_MSG` | `False` | Log a message to `LOG_CHANNEL` whenever a search returns no results |
| `TEXT_FILTER` | `True` | Enable PM text search (users can search directly in bot PM) |

---

### 🗑️ Auto Delete

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTO_DELETE` | `True` | Delete sent files (and welcome messages) automatically after a countdown |

---

### 🎭 IMDB

| Variable | Default | Description |
|----------|---------|-------------|
| `IMDB` | `True` | Fetch and display IMDB info with file results in groups |
| `PM_IMDB` | `True` | Fetch and display IMDB info with file results in PM (independent of `IMDB`) |
| `TMDB_API_KEY` | (built-in default) | API key used for movie/show metadata lookups |
| `IMDB_TEMPLATE` | (built-in default) | Custom Jinja2 template for IMDB output |
| `LONG_IMDB_DESCRIPTION` | `True` | Show the full storyline instead of a short summary |
| `SPELL_CHECK_REPLY` | `True` | Suggest a corrected title when no search results are found |
| `MAX_LIST_ELM` | — | Maximum number of cast/crew members to display (unset = show all) |

---

### 🔗 Stream & Download Server

| Variable | Default | Description |
|----------|---------|-------------|
| `URL` | — | Public URL of the stream server (e.g. `https://yourapp.koyeb.app`) |
| `FQDN` | — | Fully qualified domain name; derived from `URL` if not set directly |
| `PORT` | `8080` | Internal web server port |
| `NO_PORT` | `False` | Omit the port number from stream/download URLs |
| `WORKERS` | `4` | Number of async worker threads |
| `HAS_SSL` | `False` | Use HTTPS (`https://`) for stream and download links |
| `STREAM_SITE` / `STREAM_API` | — | Optional shortlink wrapping specifically for stream/watch links |

---

### 🔗 Shortlink

| Variable | Default | Description |
|----------|---------|-------------|
| `IS_SHORTLINK` | `False` | Wrap file links in a shortlink for monetization |
| `SHORTLINK_URL` | — | Shortlink provider domain (e.g. `bindaaslinks.com`) |
| `SHORTLINK_API` | — | API key from the shortlink provider |
| `TUTORIAL` | `https://t.me/muja_tg18` | Default tutorial link shown alongside shortlinks |
| `IS_TUTORIAL` | `True` | Show a "How to Download" tutorial button |

---

### ✅ Dual Verification

| Variable | Default | Description |
|----------|---------|-------------|
| `VERIFY` | `False` | Enable two-step shortlink verification before file access |
| `VERIFY_TIME2` | `1800` | Seconds a verification token stays valid (default 30 min) |
| `VERIFY_URL` | `krownlinks.com` | First verification shortlink provider domain |
| `VERIFY_API` | (built-in default) | API key for the first verification provider |
| `VERIFY_URL2` | `bindaaslinks.com` | Second verification shortlink provider domain |
| `VERIFY_API2` | (built-in default) | API key for the second verification provider |
| `VERIFY_IMG` | — | Image shown on the verification prompt |
| `TUTORIAL_LINK_1` | — | Tutorial link for verification step 1 |
| `TUTORIAL_LINK_2` | — | Tutorial link for verification step 2 |
| `TIMEZONE` | `Asia/Kolkata` | Timezone used for token expiry and scheduled-broadcast calculations |

---

### 🖼️ Images & Media

| Variable | Description |
|----------|-------------|
| `PICS` | Space-separated image URLs used as the start-message slideshow |
| `NOR_IMG` | Image shown when a search returns no results |
| `MELCOW_VID` | Welcome media sent to new group members |
| `SPELL_IMG` | Image shown alongside spell-check suggestions |
| `SUBSCRIPTION` | Image shown on the force-subscribe prompt |
| `CODE` | Promo image shown in certain responses |

---

### 👑 Premium & Protection

| Variable | Default | Description |
|----------|---------|-------------|
| `P_TTI_SHOW_OFF` | `False` | Enable premium welcome animations |
| `MELCOW_NEW_USERS` | `True` | Send welcome media to new users who start the bot |
| `PROTECT_CONTENT` | `False` | Prevent users from forwarding files sent by the bot |
| `PUBLIC_FILE_STORE` | `False` | Allow anyone (not just admins) to use `/link` and `/batch` |
| `PING_INTERVAL` | `1200` | Keep-alive ping interval in seconds |

---

### 🎶 Extra Tools

| Variable | Description |
|----------|-------------|
| `COOKIES_FILE_PATH` | Path to a Netscape-format `cookies.txt` from a logged-in YouTube session, required for `/song` and `/video` to bypass YouTube's bot-check on server IPs |

---

## 🚀 Deployment

### Prerequisites

- Python 3.10 or higher
- A MongoDB Atlas cluster (free tier is sufficient to start)
- Telegram API credentials from [my.telegram.org](https://my.telegram.org)
- A bot token from [@BotFather](https://t.me/BotFather)

---

### 🖥️ Run Locally

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/yourrepo.git
cd yourrepo

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and configure environment variables
cp .env.example .env
nano .env   # Fill in all required values

# 4. Start the bot
python3 bot.py
```

---

### 🐳 Docker

```bash
# Build the image
docker build -t levii-bot .

# Run with an environment file
docker run --env-file .env levii-bot
```

With Docker Compose:

```bash
docker-compose up -d
```

---

### ☁️ Deploy on Koyeb

1. Fork this repository
2. Go to [koyeb.com](https://www.koyeb.com) and create a new app
3. Connect your GitHub repository
4. Set all required environment variables in the Koyeb dashboard
5. Set the run command to `python3 bot.py`
6. Deploy — Koyeb builds from the `Dockerfile` automatically

> See [`KOYEB_DEPLOYMENT_GUIDE.md`](KOYEB_DEPLOYMENT_GUIDE.md) for a full step-by-step walkthrough.

---

### 🎨 Deploy on Render

1. Fork this repository
2. Go to [render.com](https://render.com) and click **New → Web Service**
3. Connect your GitHub repository — Render auto-detects [`render.yaml`](render.yaml) and pre-fills the build/start commands
4. Set all required environment variables in the Render dashboard (**Environment** tab)
5. Click **Create Web Service** — Render runs `pip3 install -r requirements.txt` then `python3 bot.py`

⚠️ Render's free tier spins down on inactivity. Use a paid `starter` plan (already set in `render.yaml`) for a bot that needs to stay online 24/7.

> See [`RENDER_DEPLOYMENT_GUIDE.md`](RENDER_DEPLOYMENT_GUIDE.md) for a full step-by-step walkthrough.

---

### 🚂 Deploy on Railway

1. Fork this repository
2. Go to [railway.app](https://railway.app) and click **New Project → Deploy from GitHub repo**
3. Select your fork — Railway auto-detects [`railway.json`](railway.json) and builds from the `Dockerfile`
4. Open the service → **Variables** tab and add all required environment variables
5. Railway assigns a `PORT` automatically and redeploys — no extra config needed

⚠️ Railway's free tier includes limited monthly usage hours; check your plan if the bot needs to run continuously.

> See [`RAILWAY_DEPLOYMENT_GUIDE.md`](RAILWAY_DEPLOYMENT_GUIDE.md) for a full step-by-step walkthrough.

---

### 🟣 Deploy on Heroku

```bash
heroku login
heroku create your-app-name

heroku config:set API_ID=your_api_id \
                  API_HASH=your_api_hash \
                  BOT_TOKEN=your_token \
                  DATABASE_URI=your_mongo_uri \
                  DATABASE_NAME=your_db_name \
                  COLLECTION_NAME=files \
                  ADMINS=your_user_id \
                  LOG_CHANNEL=your_channel_id

git push heroku main
```

⭐ Heroku builds with the `stack: container` setting in [`app.json`](app.json), using the same `Dockerfile` as the other platforms.

> See [`HEROKU_DEPLOYMEND_GUIDE.md`](HEROKU_DEPLOYMEND_GUIDE.md) for a full step-by-step walkthrough.

---

## 🙏 Credits

| Developer / Project | Contribution |
|---------------------|-------------|
| [Dan](https://github.com/pyrogram) | [Pyrogram](https://github.com/pyrogram/pyrogram) — the MTProto client library |
| [Mahesh](https://github.com/Mahesh0253) | [Media Search Bot](https://github.com/Mahesh0253/Media-Search-Bot) — original auto filter concept |
| [Trojanz](https://github.com/trojanzex) | [Unlimited Filter Bot](https://github.com/trojanzex/Unlimited-Filter-Bot) — filter system design |
| [EvamariaTG](https://github.com/EvamariaTG) | [EvaMaria](https://github.com/EvamariaTG/EvaMaria) — core bot architecture |
| [Joelkb](https://github.com/Joelkb) | DQ File Donor — file storage and link generation |
| [Ashok](https://github.com/AshokShau) | [Ben Filter Bot](https://github.com/AshokShau/BenFilterBot) — filter management |
| [Lazydeveloper](https://https://github.com/LazyDeveloperr/LazyPrincess) | Streaming feature basic codes |
| [@muja_tg18](https://telegram.dog/muja_tg18) | **Main Developer** — LEVII Bot development, enhancements & maintenance |
| All supporters ❤️ | Everyone who starred, forked, tested, and contributed |

---

## 📞 Contact

| Platform | Link |
|----------|------|
| Telegram | [@muja_tg18](https://telegram.dog/muja_tg18) |
| Instagram | [@mujazxx](https://instagram.com/mujazxx) |
| Updates Channel | [@rioupdates1](https://t.me/rioupdates1) |

---

## ⚠️ Disclaimer & License

This project is licensed under the **[GNU General Public License v2.0](LICENSE)**.

- ✅ You **must** give proper credit if you modify or redistribute this project
- 🚫 Do not remove author credits from the source code or README

> Releasing a modified version with only minor changes does not make you the developer.
> Learn from the code, build genuinely new features, and always credit those who came before you.

---

<p align="center">
  Made with ❤️ by <a href="https://telegram.dog/muja_tg18">@muja_tg18</a>
  <br/><br/>
  <a href="https://t.me/rioupdates1">
    <img src="https://img.shields.io/badge/Join-Updates%20Channel-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" alt="Updates Channel"/>
  </a>
</p>
