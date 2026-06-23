═══════════════════════════════════════════════════════════════════════════════ TELEGRAM AUTOFILTER BOT - RAILWAY DEPLOYMENT READY ═══════════════════════════════════════════════════════════════════════════════

WHY RAILWAY: ═════════════

✓ Native railway.json support — Railway reads the build/deploy config straight from the repo, no manual configuration needed ✓ Builds from the existing Dockerfile, so the environment is identical to Koyeb and Render's Docker-based deploys ✓ Automatic PORT injection, auto-restart on failure, and a clean web dashboard for logs and metrics

═══════════════════════════════════════════════════════════════════════════════

WHAT'S ALREADY CONFIGURED FOR YOU (railway.json): ═════════════════════════════════════════════════

{ "$schema": "https://railway.app/railway.schema.json", "build": { "builder": "DOCKERFILE", "dockerfilePath": "Dockerfile" }, "deploy": { "startCommand": "python3 bot.py", "healthcheckPath": "/", "healthcheckTimeout": 100, "restartPolicyType": "ON_FAILURE", "restartPolicyMaxRetries": 10 } }

This means: Railway will automatically

Detect railway.json in the repo root
Build the image from the existing Dockerfile (includes ffmpeg, deno, and all system dependencies the bot needs)
Start the bot with python3 bot.py
Health-check the bot's web server on "/" (served by bot.py)
Restart automatically (up to 10 times) if the process crashes
You only need to add environment variables — everything else is already wired up.

═══════════════════════════════════════════════════════════════════════════════

REQUIRED ENVIRONMENT VARIABLES FOR RAILWAY: ═══════════════════════════════════════════

TELEGRAM CREDENTIALS: API_ID - Get from https://my.telegram.org API_HASH - Get from https://my.telegram.org BOT_TOKEN - Get from @BotFather on Telegram SESSION - Session name (default: Media_search)

DATABASE: DATABASE_URI - MongoDB connection string with credentials DATABASE_NAME - Database name (default: Telegram_Bot) COLLECTION_NAME - Collection name (default: files)

CHANNELS & GROUPS: ADMINS - Space-separated admin IDs CHANNELS - Space-separated channel IDs for file storage LOG_CHANNEL - Channel ID for bot logs SUPPORT_CHAT_ID - Support group/channel ID AUTH_CHANNEL - Channel ID for authentication AUTH_GROUP - Group ID for authentication PREMIUM_LOGS - Premium user logs channel REQST_CHANNEL_ID - Request channel ID

OPTIONAL SETTINGS: PORT - Railway injects this automatically, do not set it manually OPENAI_API - OpenAI API key for GPT features VERIFY - Enable verification (True/False) IMDB - Enable IMDB info (True/False) AUTO_DELETE - Auto delete messages (True/False) PROTECT_CONTENT - Protect file content (True/False) COOKIES_FILE_PATH - Path to a YouTube cookies.txt (for /song, /video) And many more — see .env.example for the full list

═══════════════════════════════════════════════════════════════════════════════

DEPLOYMENT STEPS FOR RAILWAY: ═══════════════════════════════

Push your repository to GitHub git init git add . git commit -m "Bot ready for deployment" git push -u origin main

Login to Railway (https://railway.app)

Click "New Project" → "Deploy from GitHub repo"

Authorize Railway to access GitHub (if not already done) and select your repository

Railway detects railway.json automatically and configures:

Builder: Dockerfile
Start Command: python3 bot.py
Health Check Path: /
Restart Policy: ON_FAILURE (up to 10 retries)
Open the deployed service → click the "Variables" tab → "New Variable" for each one:

API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
DATABASE_URI=your_mongodb_uri
ADMINS=your_admin_id
CHANNELS=channel_id
LOG_CHANNEL=log_channel_id (And any other required variables)
Tip: use the "Raw Editor" in the Variables tab to paste multiple KEY=VALUE lines at once instead of adding them one by one.

Railway automatically redeploys whenever you add or change a variable — no separate "deploy" button needed

Go to the "Deployments" tab → click the active deployment → "View Logs" to watch the build and runtime output live

═══════════════════════════════════════════════════════════════════════════════

RAILWAY SPECIFIC NOTES: ══════════════════════════

✓ Builds from the same Dockerfile as Koyeb, so behavior is consistent across both platforms (ffmpeg and deno are included) ✓ healthcheckPath: "/" matches the route bot.py's aiohttp web server already serves, so Railway's health checks pass out of the box ✓ Auto-restarts the service on crash, capped at 10 retries (restartPolicyMaxRetries in railway.json) ✓ PORT is injected automatically by Railway at runtime — bot.py already reads it via the PORT env var, so no changes are needed ✓ MongoDB Atlas works fine with Railway — just whitelist 0.0.0.0/0 (or Railway's published egress IPs) in Atlas Network Access ✓ Railway's free/trial tier includes a limited number of usage hours per month — check your plan if the bot needs to run continuously without interruption

═══════════════════════════════════════════════════════════════════════════════

TESTING LOCALLY BEFORE DEPLOYMENT: ═══════════════════════════════════

Create .env file with your variables: API_ID=12345 API_HASH=abcdef BOT_TOKEN=your_token DATABASE_URI=your_mongodb_uri etc...

Load environment: export $(cat .env | xargs)

Run the bot: python3 bot.py

Or test the exact container Railway will build: docker build -t levii-bot . docker run --env-file .env levii-bot

═══════════════════════════════════════════════════════════════════════════════

TROUBLESHOOTING: ═════════════════

• Build fails with "Dockerfile not found" or wrong builder detected? → Make sure railway.json is committed at the repo root, not in a subfolder — the dockerfilePath in railway.json is relative to the repo root

• Bot not starting / crash loop? → Open "Deployments" → "View Logs" for the Python traceback → Check all required environment variables are set in the Variables tab → After 10 failed restarts (restartPolicyMaxRetries), Railway stops retrying — fix the underlying error, then redeploy manually

• Health check failing / deployment marked unhealthy? → Confirm the bot's web server actually started — check logs for "Web server started on port" — bot.py binds to $PORT automatically → healthcheckPath is "/" in railway.json; don't change this unless you also add a matching route in plugins/route.py

• Database connection error? → Verify MongoDB URI is correct → Whitelist Railway's egress IPs (or 0.0.0.0/0 for simplicity) in MongoDB Atlas Network Access

• Running out of usage hours / service stops unexpectedly? → Check your Railway plan's monthly usage limit in account billing

• Import errors? → All dependencies are in requirements.txt — the Dockerfile installs them automatically on every build

═══════════════════════════════════════════════════════════════════════════════

STATUS: ✓ READY FOR DEPLOYMENT ═══════════════════════════════════════════════════════════════════════════════

railway.json is already configured. Simply connect the repo, set your environment variables, and deploy. Good luck!