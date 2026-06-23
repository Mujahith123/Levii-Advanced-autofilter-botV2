═══════════════════════════════════════════════════════════════════════════════
    TELEGRAM AUTOFILTER BOT - HEROKU DEPLOYMENT READY
═══════════════════════════════════════════════════════════════════════════════

WHY HEROKU:
═════════════

✓ Native app.json + heroku.yml support — Heroku reads the build config
  straight from the repo, no manual configuration needed
✓ Builds from the existing Dockerfile via "stack": "container" in
  app.json, so the environment is identical to Koyeb and Railway's
  Docker-based deploys
✓ One-command deploys with the Heroku CLI, plus a "Deploy to Heroku"
  button workflow if you prefer the dashboard

═══════════════════════════════════════════════════════════════════════════════

WHAT'S ALREADY CONFIGURED FOR YOU (app.json + heroku.yml):
═════════════════════════════════════════════════════════════

heroku.yml:
    build:
      docker:
          worker: Dockerfile

app.json (relevant parts):
    {
      "stack": "container",
      "formation": {
        "worker": {
          "quantity": 1,
          "size": "eco"
        }
      }
    }

   This means: Heroku will automatically
   1. Detect "stack": "container" in app.json and heroku.yml
   2. Build the image from the existing Dockerfile (includes ffmpeg,
      deno, and all system dependencies the bot needs)
   3. Run the container as a worker process (size: eco)
   4. Restart automatically if the process crashes

   Note: app.json's "formation" block is set to "worker", not "web" —
   that's correct for this bot since Pyrogram connects outbound to
   Telegram and doesn't need Heroku's router to receive traffic. The
   bot's own aiohttp server (for streaming/downloads) still binds to
   $PORT internally and works fine on a worker dyno.

═══════════════════════════════════════════════════════════════════════════════

REQUIRED ENVIRONMENT VARIABLES FOR HEROKU:
═══════════════════════════════════════════

TELEGRAM CREDENTIALS:
    API_ID              - Get from https://my.telegram.org
    API_HASH            - Get from https://my.telegram.org
    BOT_TOKEN           - Get from @BotFather on Telegram
    SESSION             - Session name (default: Media_search)

DATABASE:
    DATABASE_URI        - MongoDB connection string with credentials
    DATABASE_NAME       - Database name (default: Telegram_Bot)
    COLLECTION_NAME     - Collection name (default: files)

CHANNELS & GROUPS:
    ADMINS              - Space-separated admin IDs
    CHANNELS            - Space-separated channel IDs for file storage
    LOG_CHANNEL         - Channel ID for bot logs
    SUPPORT_CHAT_ID     - Support group/channel ID
    AUTH_CHANNEL        - Channel ID for authentication
    AUTH_GROUP          - Group ID for authentication
    PREMIUM_LOGS        - Premium user logs channel
    REQST_CHANNEL_ID    - Request channel ID

OPTIONAL SETTINGS:
    PORT                - Heroku injects this automatically, do not set
                          it manually
    OPENAI_API          - OpenAI API key for GPT features
    VERIFY              - Enable verification (True/False)
    IMDB                - Enable IMDB info (True/False)
    AUTO_DELETE         - Auto delete messages (True/False)
    PROTECT_CONTENT     - Protect file content (True/False)
    COOKIES_FILE_PATH   - Path to a YouTube cookies.txt (for /song, /video)
    And many more — see .env.example for the full list

═══════════════════════════════════════════════════════════════════════════════

DEPLOYMENT STEPS FOR HEROKU (CLI):
═════════════════════════════════════

1. Install the Heroku CLI if you don't have it:
   https://devcenter.heroku.com/articles/heroku-cli

2. Push your repository to GitHub (recommended, optional for CLI deploy)
   git init
   git add .
   git commit -m "Bot ready for deployment"
   git push -u origin main

3. Login and create the app:
   heroku login
   heroku create your-app-name

4. Set the stack to container (required — this app deploys via Dockerfile,
   not Heroku's default buildpacks):
   heroku stack:set container -a your-app-name

5. Set environment variables:
   heroku config:set API_ID=your_api_id \
                     API_HASH=your_api_hash \
                     BOT_TOKEN=your_token \
                     DATABASE_URI=your_mongo_uri \
                     DATABASE_NAME=your_db_name \
                     COLLECTION_NAME=files \
                     ADMINS=your_user_id \
                     LOG_CHANNEL=your_channel_id \
                     -a your-app-name

   (Add any other required variables the same way)

6. Deploy:
   git push heroku main

   Heroku builds the Docker image and starts the worker dyno
   automatically using heroku.yml

7. Scale the worker dyno on (containers deploy "off" by default):
   heroku ps:scale worker=1 -a your-app-name

8. View Logs:
   heroku logs --tail -a your-app-name

═══════════════════════════════════════════════════════════════════════════════

DEPLOYMENT STEPS FOR HEROKU (Dashboard / Deploy Button):
═════════════════════════════════════════════════════════

1. Push your repository to GitHub

2. Go to https://dashboard.heroku.com/new-app and create a new app,
   or use a "Deploy to Heroku" button if you've added one to your README
   pointing at app.json

3. On the "Deploy" tab, connect to GitHub and select your repository

4. Heroku reads app.json and automatically sets the stack to "container"

5. Fill in the environment variables listed in app.json's "env" block
   when prompted (API_ID, API_HASH, BOT_TOKEN, ADMINS, LOG_CHANNEL,
   DATABASE_URI, etc.)

6. Click "Deploy App" — Heroku builds from the Dockerfile and launches
   the worker dyno

7. Go to "Resources" tab and confirm the worker dyno is switched ON
   (containers can deploy with dynos off by default)

═══════════════════════════════════════════════════════════════════════════════

HEROKU SPECIFIC NOTES:
═════════════════════════

✓ Builds from the same Dockerfile as Koyeb and Railway, so behavior is
  consistent across all three platforms (ffmpeg and deno are included)
✓ Uses a worker dyno, not a web dyno — this bot doesn't need Heroku's
  HTTP router since Pyrogram connects outbound to Telegram directly
✓ The bot's own aiohttp server still binds to $PORT for streaming/
  download links; Heroku injects PORT automatically and bot.py already
  reads it
✓ Heroku no longer offers a free tier — the "eco" dyno size in app.json
  is the cheapest paid option suitable for this bot
✓ MongoDB Atlas works fine with Heroku — just whitelist 0.0.0.0/0 (or
  Heroku's published egress IPs) in Atlas Network Access
✓ Heroku dynos restart automatically on crash and also cycle once every
  ~24 hours ("dyno restart") — this is normal and the bot's auto-restart
  loop in bot.py handles reconnecting cleanly

═══════════════════════════════════════════════════════════════════════════════

TESTING LOCALLY BEFORE DEPLOYMENT:
═══════════════════════════════════

1. Create .env file with your variables:
   API_ID=12345
   API_HASH=abcdef
   BOT_TOKEN=your_token
   DATABASE_URI=your_mongodb_uri
   etc...

2. Load environment:
   export $(cat .env | xargs)

3. Run the bot:
   python3 bot.py

   Or test the exact container Heroku will build:
   docker build -t levii-bot .
   docker run --env-file .env levii-bot

═══════════════════════════════════════════════════════════════════════════════

TROUBLESHOOTING:
═════════════════

• "App not compatible with buildpack" or it tries to use Python
  buildpacks instead of Docker?
  → Run heroku stack:set container -a your-app-name before pushing —
    app.json sets this for new apps created via the Deploy button, but
    CLI-created apps need it set explicitly first

• Worker dyno shows "off" / nothing happens after deploy?
  → Containers can deploy with the worker dyno scaled to 0 — run
    heroku ps:scale worker=1 -a your-app-name

• Bot not starting / crashing on boot?
  → heroku logs --tail -a your-app-name for the Python traceback
  → Check all required environment variables are set with
    heroku config -a your-app-name

• Database connection error?
  → Verify DATABASE_URI is correct
  → Whitelist Heroku's egress IPs (or 0.0.0.0/0 for simplicity) in
    MongoDB Atlas Network Access

• Build fails / times out?
  → Heroku's container builds run the same Dockerfile as Koyeb/Railway;
    if it works on one it should work on Heroku too — check
    heroku builds:output -a your-app-name for the failing step

• Import errors?
  → All dependencies are in requirements.txt — the Dockerfile installs
    them automatically on every build

═══════════════════════════════════════════════════════════════════════════════

STATUS: ✓ READY FOR DEPLOYMENT
═══════════════════════════════════════════════════════════════════════════════

app.json and heroku.yml are already configured for container deploys.
Just set the stack, add your environment variables, and push. Good luck!