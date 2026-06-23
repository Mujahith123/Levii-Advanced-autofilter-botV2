═══════════════════════════════════════════════════════════════════════════════ TELEGRAM AUTOFILTER BOT - RENDER DEPLOYMENT READY ═══════════════════════════════════════════════════════════════════════════════

WHY RENDER: ═══════════

✓ Native render.yaml support — Render reads the build/start commands straight from the repo, no manual configuration needed ✓ Free HTTPS, auto-restarts on crash, and a web dashboard for logs ✓ Builds with Python directly (env: python in render.yaml) — no Docker layer needed, so builds are faster than container-based platforms

═════════════════════════════════════════════════════════════════════════════

WHAT'S ALREADY CONFIGURED FOR YOU (render.yaml): ═════════════════════════════════════════════════

services:

type: web name: THALAPATHY-FILTER-BOT env: python startCommand: python3 bot.py buildCommand: pip3 install --no-cache-dir -U -r requirements.txt region: fra plan: starter numInstances: 1 healthCheckPath: /
This means: Render will automatically

Detect render.yaml in the repo root
Install dependencies with pip3
Start the bot with python3 bot.py
Health-check the bot's web server on "/" (served by bot.py)
You only need to add environment variables — everything else is already wired up.

═════════════════════════════════════════════════════════════════════════════

REQUIRED ENVIRONMENT VARIABLES FOR RENDER: ═══════════════════════════════════════════

TELEGRAM CREDENTIALS: API_ID - Get from https://my.telegram.org API_HASH - Get from https://my.telegram.org BOT_TOKEN - Get from @BotFather on Telegram SESSION - Session name (default: Media_search)

DATABASE: DATABASE_URI - MongoDB connection string with credentials DATABASE_NAME - Database name (default: Telegram_Bot) COLLECTION_NAME - Collection name (default: files)

CHANNELS & GROUPS: ADMINS - Space-separated admin IDs CHANNELS - Space-separated channel IDs for file storage LOG_CHANNEL - Channel ID for bot logs SUPPORT_CHAT_ID - Support group/channel ID AUTH_CHANNEL - Channel ID for authentication AUTH_GROUP - Group ID for authentication PREMIUM_LOGS - Premium user logs channel REQST_CHANNEL_ID - Request channel ID

OPTIONAL SETTINGS: PORT - Render injects this automatically, do not set manually OPENAI_API - OpenAI API key for GPT features VERIFY - Enable verification (True/False) IMDB - Enable IMDB info (True/False) AUTO_DELETE - Auto delete messages (True/False) PROTECT_CONTENT - Protect file content (True/False) COOKIES_FILE_PATH - Path to a YouTube cookies.txt (for /song, /video) And many more...

═════════════════════════════════════════════════════════════════════════════

DEPLOYMENT STEPS FOR RENDER: ═════════════════════════════

Push your repository to GitHub git init git add . git commit -m "Bot ready for deployment" git push -u origin main

Login to Render Dashboard (https://dashboard.render.com)

Click "New +" → "Web Service"

Select "Build and deploy from a Git repository" → connect GitHub and choose your repo

Render detects render.yaml automatically and pre-fills:

Name: THALAPATHY-FILTER-BOT
Environment: Python
Build Command: pip3 install --no-cache-dir -U -r requirements.txt
Start Command: python3 bot.py
Region: Frankfurt (fra)
Plan: Starter
(You can change the region/plan if you want, but leave the build and start commands as detected.)

Add Environment Variables: Scroll to the "Environment" section and click "Add Environment Variable" for each one:

API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
DATABASE_URI=your_mongodb_uri
ADMINS=your_admin_id
CHANNELS=channel_id
LOG_CHANNEL=log_channel_id (And any other required variables)
Click "Create Web Service" Render builds the image and starts the bot automatically

View Logs: Go to your service → "Logs" tab (live-streamed)

═════════════════════════════════════════════════════════════════════════════

RENDER SPECIFIC NOTES: ═══════════════════════

✓ Builds with the Python environment directly — no Docker required (env: python in render.yaml), so deploys are quick ✓ healthCheckPath: / matches the route bot.py's aiohttp web server already serves, so Render's health checks pass out of the box ✓ Auto-restarts the service if the process crashes ✓ MongoDB Atlas works fine with Render — just whitelist 0.0.0.0/0 (or Render's published egress IPs) in Atlas Network Access ✓ Free tier services spin down after 15 minutes of inactivity and take ~30-60s to wake up on the next request — use the paid Starter plan (already set in render.yaml) if the bot needs to stay online 24/7 for groups that rely on it constantly

═════════════════════════════════════════════════════════════════════════════

TESTING LOCALLY BEFORE DEPLOYMENT: ═══════════════════════════════════

Create .env file with your variables: API_ID=12345 API_HASH=abcdef BOT_TOKEN=your_token DATABASE_URI=your_mongodb_uri etc...

Load environment: export $(cat .env | xargs)

Run the bot: python3 bot.py

═════════════════════════════════════════════════════════════════════════════

TROUBLESHOOTING: ═════════════════

• Build fails with "render.yaml not found"? → Make sure render.yaml is committed at the repo root, not in a subfolder

• Bot not starting? → Check all required environment variables are set in the "Environment" tab → Check DATABASE_URI is correct → Check BOT_TOKEN is valid

• Health check failing / service marked "unhealthy"? → Confirm the bot's web server actually started — check logs for "Web server started on port" — bot.py binds to $PORT automatically → healthCheckPath is "/" by default; don't change this unless you also add a matching route

• Database connection error? → Verify MongoDB URI is correct → Whitelist Render's egress IPs (or 0.0.0.0/0 for simplicity) in MongoDB Atlas Network Access

• Service keeps spinning down / slow to respond? → That's expected on Render's free tier; upgrade to Starter or higher for an always-on bot

• Import errors? → All dependencies are in requirements.txt — Render installs them automatically on every deploy

═════════════════════════════════════════════════════════════════════════════

STATUS: ✓ READY FOR DEPLOYMENT ═════════════════════════════════════════════════════════════════════════════

render.yaml is already configured. Simply connect the repo, set the environment variables, and deploy. Good luck!