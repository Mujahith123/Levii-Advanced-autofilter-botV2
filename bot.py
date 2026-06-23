import logging
import logging.config

# Get logging configurations
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("imdbpy").setLevel(logging.ERROR)

from pyrogram import Client, __version__
from pyrogram.raw.all import layer
from database.ia_filterdb import Media
from database.users_chats_db import db
from info import SESSION, API_ID, API_HASH, BOT_TOKEN, LOG_STR, LOG_CHANNEL, PORT
from utils import temp
from typing import Union, Optional, AsyncGenerator
from pyrogram import types
from Script import script
import levii_credits  # Attribution & integrity — built by @muja_tg18
from datetime import date, datetime
import pytz
import asyncio
from aiohttp import web
from plugins import web_server


class Bot(Client):

    def __init__(self):
        super().__init__(
            name=SESSION,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=50,
            plugins={"root": "plugins"},
            sleep_threshold=5,
        )

    async def start(self):
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats
        await super().start()
        await Media.ensure_indexes()
        # ── Feature indexes — created once at startup, idempotent ─────────────
        try:
            await db.not_found_logs.create_index([("query", 1), ("ts", -1)])
            await db.not_found_logs.create_index([("ts", -1)])
            await db.group_activity.create_index([("group_id", 1)], unique=True)
            logging.info("Feature indexes ensured.")
        except Exception as _idx_err:
            logging.warning(f"Index creation warning (non-fatal): {_idx_err}")
        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        temp.BOT = self  # Store running bot for streaming
        self.username = '@' + me.username
        # Register self as the primary streaming client
        from leviibot import multi_clients, work_loads
        multi_clients[0] = self
        work_loads[0] = 0
        logging.info(f"{me.first_name} with for Pyrogram v{__version__} (Layer {layer}) started on {me.username}.")
        logging.info(LOG_STR)
        logging.info(script.LOGO)
        levii_credits.startup_check()  # Verify attribution integrity

        # Send startup message only if LOG_CHANNEL is set
        if LOG_CHANNEL:
            try:
                tz = pytz.timezone('Asia/Kolkata')
                today = date.today()
                now = datetime.now(tz)
                time = now.strftime("%H:%M:%S %p")
                await self.send_message(chat_id=LOG_CHANNEL, text=script.RESTART_TXT.format(today, time))
            except Exception as e:
                logging.warning(f"Could not send startup message to LOG_CHANNEL: {e}")
        else:
            logging.warning("LOG_CHANNEL not set, skipping startup message.")

        # Start web server with retry - handles port-in-use during Koyeb restarts
        for attempt in range(10):
            try:
                runner = web.AppRunner(await web_server())
                await runner.setup()
                await web.TCPSite(runner, "0.0.0.0", PORT, reuse_port=True).start()
                logging.info(f"Web server started on port {PORT}")
                break
            except OSError as port_err:
                if attempt < 9:
                    logging.warning(f"Port {PORT} busy, retrying in 3s... ({attempt+1}/10)")
                    await asyncio.sleep(3)
                else:
                    raise port_err

    async def stop(self, *args):
        await super().stop()
        logging.info("Bot stopped. Bye.")

    async def iter_messages(
        self,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 0,
    ) -> Optional[AsyncGenerator["types.Message", None]]:
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(chat_id, list(range(current, current + new_diff + 1)))
            for message in messages:
                yield message
                current += 1


# Run bot 24/7 with auto-restart on crash
if __name__ == "__main__":
    while True:
        try:
            app = Bot()
            app.run()
        except KeyboardInterrupt:
            logging.info("Bot stopped by user.")
            break
        except Exception as e:
            err_msg = str(e).lower()
            # Wait longer for port/db lock errors - these need time to release
            if "address already in use" in err_msg or "database is locked" in err_msg:
                sleep_time = 15
            else:
                sleep_time = 5
            logging.error(f"Bot crashed: {e}. Restarting in {sleep_time} seconds...")
            asyncio.get_event_loop().run_until_complete(asyncio.sleep(sleep_time))