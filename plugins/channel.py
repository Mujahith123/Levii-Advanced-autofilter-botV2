from pyrogram import Client, filters
from info import CHANNELS
from database.ia_filterdb import save_file

media_filter = filters.document | filters.video | filters.audio


# Guard: filters.chat([]) raises an error in Pyrogram when CHANNELS is empty
if CHANNELS:
    @Client.on_message(filters.chat(CHANNELS) & media_filter)
    async def media(bot, message):
        """Media Handler"""
        for file_type in ("document", "video", "audio"):
            media = getattr(message, file_type, None)
            if media is not None:
                break
        else:
            return

        media.file_type = file_type
        media.caption = message.caption
        await save_file(media)
else:
    import logging
    logging.warning("⚠️ CHANNELS is empty — media auto-indexing from channels is disabled. Set the CHANNELS env variable with valid channel IDs.")