import re
import logging
from pyrogram import Client, filters
from info import DELETE_CHANNELS
from database.ia_filterdb import unpack_new_file_id, delete_one_across_dbs, delete_many_across_dbs

logger = logging.getLogger(__name__)

media_filter = filters.document | filters.video | filters.audio

# Guard: filters.chat([]) raises an error in Pyrogram when DELETE_CHANNELS is empty
if DELETE_CHANNELS:
    @Client.on_message(filters.chat(DELETE_CHANNELS) & media_filter)
    async def deletemultiplemedia(bot, message):
        """Delete Multiple files from database"""

        for file_type in ("document", "video", "audio"):
            media = getattr(message, file_type, None)
            if media is not None:
                break
        else:
            return

        file_id, file_ref = unpack_new_file_id(media.file_id)

        result = await delete_one_across_dbs({
            '_id': file_id,
        })
        if result.deleted_count:
            logger.info('File is successfully deleted from database.')
        else:
            file_name = re.sub(r"(_|\-|\.|\\+)", " ", str(media.file_name))
            deleted = await delete_many_across_dbs({
                'file_name': file_name,
                'file_size': media.file_size,
                'mime_type': media.mime_type
                })
            if deleted:
                logger.info('File is successfully deleted from database.')
            else:
                deleted = await delete_many_across_dbs({
                    'file_name': media.file_name,
                    'file_size': media.file_size,
                    'mime_type': media.mime_type
                })
                if deleted:
                    logger.info('File is successfully deleted from database.')
                else:
                    logger.info('File not found in database.')
