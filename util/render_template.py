#Thanks @muja_tg18 helping this journey 

import jinja2
from info import *
from leviibot import get_stream_channel_id
from utils import temp
from util.human_readable import humanbytes
from util.file_properties import get_file_ids
from server.exceptions import InvalidHash
import urllib.parse
import logging
import aiohttp


async def render_page(id, secure_hash, src=None):
    channel_id = await get_stream_channel_id()
    file_data = await get_file_ids(temp.BOT, channel_id, int(id))
    if file_data.unique_id[:6] != secure_hash:
        logging.debug(f"link hash: {secure_hash} - {file_data.unique_id[:6]}")
        logging.debug(f"Invalid hash for message with - ID {id}")
        raise InvalidHash

    src = urllib.parse.urljoin(
        URL,
        f"{id}/{urllib.parse.quote_plus(file_data.file_name)}?hash={secure_hash}",
    )

    tag = file_data.mime_type.split("/")[0].strip() if file_data.mime_type else ""
    file_size = humanbytes(file_data.file_size)

    # Fallback: check file extension if MIME type doesn't say video/audio
    VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".3gp", ".ts", ".m2ts"}
    AUDIO_EXTS = {".mp3", ".flac", ".aac", ".ogg", ".wav", ".m4a", ".opus", ".wma"}
    file_ext = ""
    if file_data.file_name:
        import os
        file_ext = os.path.splitext(file_data.file_name)[1].lower()

    is_video = tag == "video" or file_ext in VIDEO_EXTS
    is_audio = tag == "audio" or file_ext in AUDIO_EXTS

    if is_video or is_audio:
        template_file = "template/dl.html"   # full player with VLC/MX/PLAYit/KM
    else:
        template_file = "template/req.html"  # download page for docs/other
        async with aiohttp.ClientSession() as s:
            async with s.get(src) as u:
                file_size = humanbytes(int(u.headers.get("Content-Length")))

    with open(template_file) as f:
        template = jinja2.Template(f.read())

    file_name = file_data.file_name.replace("_", " ")

    return template.render(
        file_name=file_name,
        file_url=src,
        file_size=file_size,
        file_unique_id=file_data.unique_id,
    )