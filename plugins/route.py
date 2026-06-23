from aiohttp import web
import re
import math
import logging
import secrets
import time
import mimetypes
from aiohttp.http_exceptions import BadStatusLine
from leviibot import multi_clients, work_loads, LeviiBot
from server.exceptions import FIleNotFound, InvalidHash
from zzint import StartTime, __version__
from util.custom_dl import ByteStreamer
from util.time_format import get_readable_time
from util.render_template import render_page
from pyrogram.types import Update
from info import *


routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response("BenFilterBot")


@routes.post("/webhook")
async def webhook_handler(request):
    """Handle incoming Telegram webhook updates"""
    try:
        data = await request.json()
        logging.info(f"Webhook received: update_id {data.get('update_id')}")
        
        # Process update through Pyrogram
        update = Update(data)
        
        # Handle the update
        if hasattr(LeviiBot, '_handle_update'):
            await LeviiBot._handle_update(update)
        else:
            # Fallback: directly process through dispatcher
            await LeviiBot.dispatcher.handler(LeviiBot, update)
            
        logging.info(f"Update {data.get('update_id')} processed successfully")
        return web.Response(status=200, text="OK")
        
    except Exception as e:
        logging.error(f"Webhook error: {e}", exc_info=True)
        # Return 200 to prevent Telegram from retrying
        return web.Response(status=200, text="OK")


@routes.get("/webhook")
async def webhook_check(request):
    """Health check for webhook"""
    return web.json_response({"status": "webhook_active", "ok": True})



@routes.get(r"/watch/{path:\S+}", allow_head=True)
async def stream_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)
        if match:
            secure_hash = match.group(1)
            id = int(match.group(2))
        else:
            id = int(re.search(r"(\d+)(?:\/\S+)?", path).group(1))
            secure_hash = request.rel_url.query.get("hash")
        return web.Response(text=await render_page(id, secure_hash), content_type='text/html')
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logging.critical(e.with_traceback(None))
        raise web.HTTPInternalServerError(text=str(e))

@routes.get(r"/{path:\S+}", allow_head=True)
async def path_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)
        if match:
            secure_hash = match.group(1)
            id = int(match.group(2))
        else:
            id = int(re.search(r"(\d+)(?:\/\S+)?", path).group(1))
            secure_hash = request.rel_url.query.get("hash")
        return await media_streamer(request, id, secure_hash)
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logging.critical(e.with_traceback(None))
        raise web.HTTPInternalServerError(text=str(e))

class_cache = {}

async def media_streamer(request: web.Request, id: int, secure_hash: str):
    range_header = request.headers.get("Range", 0)
    
    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]
    
    if MULTI_CLIENT:
        logging.info(f"Client {index} is now serving {request.remote}")

    if faster_client in class_cache:
        tg_connect = class_cache[faster_client]
        logging.debug(f"Using cached ByteStreamer object for client {index}")
    else:
        logging.debug(f"Creating new ByteStreamer object for client {index}")
        tg_connect = ByteStreamer(faster_client)
        class_cache[faster_client] = tg_connect
    logging.debug("before calling get_file_properties")
    stream_chat_id = request.rel_url.query.get("chat_id")
    stream_chat_id = int(stream_chat_id) if stream_chat_id else None
    file_id = await tg_connect.get_file_properties(id, chat_id=stream_chat_id)
    logging.debug("after calling get_file_properties")
    
    if file_id.unique_id[:6] != secure_hash:
        logging.debug(f"Invalid hash for message with ID {id}")
        raise InvalidHash
    
    file_size = file_id.file_size or 0  # Guard against None file_size

    if range_header:
        from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
        from_bytes = int(from_bytes)
        until_bytes = int(until_bytes) if until_bytes else (file_size - 1 if file_size else 0)
    else:
        from_bytes = request.http_range.start or 0
        until_bytes = ((request.http_range.stop or file_size) - 1) if file_size else 0

    if file_size and ((until_bytes > file_size) or (from_bytes < 0) or (until_bytes < from_bytes)):
        return web.Response(
            status=416,
            body="416: Range not satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    chunk_size = 1024 * 1024  # 1 MB — Telegram GetFile hard limit (must be multiple of 4096)
    until_bytes = min(until_bytes, file_size - 1)

    offset = from_bytes - (from_bytes % chunk_size)
    first_part_cut = from_bytes - offset
    last_part_cut = until_bytes % chunk_size + 1

    req_length = until_bytes - from_bytes + 1
    part_count = math.ceil(until_bytes / chunk_size) - math.floor(offset / chunk_size)
    body = tg_connect.yield_file(
        file_id, index, offset, first_part_cut, last_part_cut, part_count, chunk_size
    )

    mime_type = file_id.mime_type
    file_name = file_id.file_name

    # Use inline for video/audio so browsers can play directly instead of downloading
    if mime_type and mime_type.startswith(("video/", "audio/")):
        disposition = "inline"
    else:
        disposition = "attachment"

    if mime_type:
        if not file_name:
            try:
                file_name = f"{secrets.token_hex(2)}.{mime_type.split('/')[1]}"
            except (IndexError, AttributeError):
                file_name = f"{secrets.token_hex(2)}.unknown"
    else:
        if file_name:
            mime_type = mimetypes.guess_type(file_id.file_name)[0] or "application/octet-stream"
        else:
            mime_type = "application/octet-stream"
            file_name = f"{secrets.token_hex(2)}.unknown"

    return web.Response(
        status=206 if range_header else 200,
        body=body,
        headers={
            "Content-Type": mime_type,
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Length": str(req_length),
            "Content-Disposition": f'{disposition}; filename="{file_name}"',
            "Accept-Ranges": "bytes",
        },
    )