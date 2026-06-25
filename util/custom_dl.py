#Thanks @muja_tg18 for helping in this journey 
import math
import asyncio
import logging
from info import *
from typing import Dict, Union
from leviibot import work_loads, get_stream_channel_id
from pyrogram import Client, utils, raw
from .file_properties import get_file_ids
from pyrogram.session import Session, Auth
from pyrogram.errors import AuthBytesInvalid
from server.exceptions import FIleNotFound
from pyrogram.file_id import FileId, FileType, ThumbnailSource


# ─────────────────────────────────────────────────────────────────────────────
# The ONLY way to increase throughput is to run MORE parallel GetFile requests
# at the same time (pipeline depth). Each in-flight request hides the ~200-400ms
# MTProto round-trip latency of the others.
#
# PIPELINE_SIZE = 16 means 16 MB is being fetched concurrently at all times.
# For a typical movie file over a good connection this keeps the buffer full.
# Raise this further only if the server has plenty of memory and the Telegram
# DC connection can handle it without flood-wait errors.
# ─────────────────────────────────────────────────────────────────────────────
PIPELINE_SIZE = 16


class ByteStreamer:
    def __init__(self, client: Client):
        self.clean_timer = 30 * 60
        self.client: Client = client
        self.cached_file_ids: Dict[int, FileId] = {}
        asyncio.create_task(self.clean_cache())

    async def get_file_properties(self, id: int, chat_id: int = None) -> FileId:
        if id not in self.cached_file_ids:
            await self.generate_file_properties(id, chat_id)
            logging.debug(f"Cached file properties for message with ID {id}")
        return self.cached_file_ids[id]

    async def generate_file_properties(self, id: int, chat_id: int = None) -> FileId:
        effective_chat = chat_id if chat_id else await get_stream_channel_id()
        file_id = await get_file_ids(self.client, effective_chat, id)
        logging.debug(f"Generated file ID and Unique ID for message with ID {id}")
        if not file_id:
            logging.debug(f"Message with ID {id} not found")
            raise FIleNotFound
        self.cached_file_ids[id] = file_id
        logging.debug(f"Cached media message with ID {id}")
        return self.cached_file_ids[id]

    async def generate_media_session(self, client: Client, file_id: FileId) -> Session:
        media_session = client.media_sessions.get(file_id.dc_id, None)

        if media_session is None:
            if file_id.dc_id != await client.storage.dc_id():
                media_session = Session(
                    client,
                    file_id.dc_id,
                    await Auth(
                        client, file_id.dc_id, await client.storage.test_mode()
                    ).create(),
                    await client.storage.test_mode(),
                    is_media=True,
                )
                await media_session.start()

                for _ in range(6):
                    exported_auth = await client.invoke(
                        raw.functions.auth.ExportAuthorization(dc_id=file_id.dc_id)
                    )
                    try:
                        await media_session.send(
                            raw.functions.auth.ImportAuthorization(
                                id=exported_auth.id, bytes=exported_auth.bytes
                            )
                        )
                        break
                    except AuthBytesInvalid:
                        logging.debug(f"Invalid authorization bytes for DC {file_id.dc_id}")
                        continue
                else:
                    await media_session.stop()
                    raise AuthBytesInvalid
            else:
                media_session = Session(
                    client,
                    file_id.dc_id,
                    await client.storage.auth_key(),
                    await client.storage.test_mode(),
                    is_media=True,
                )
                await media_session.start()
            logging.debug(f"Created media session for DC {file_id.dc_id}")
            client.media_sessions[file_id.dc_id] = media_session
        else:
            logging.debug(f"Using cached media session for DC {file_id.dc_id}")
        return media_session

    @staticmethod
    async def get_location(file_id: FileId) -> Union[raw.types.InputPhotoFileLocation,
                                                     raw.types.InputDocumentFileLocation,
                                                     raw.types.InputPeerPhotoFileLocation,]:
        file_type = file_id.file_type

        if file_type == FileType.CHAT_PHOTO:
            if file_id.chat_id > 0:
                peer = raw.types.InputPeerUser(
                    user_id=file_id.chat_id, access_hash=file_id.chat_access_hash
                )
            else:
                if file_id.chat_access_hash == 0:
                    peer = raw.types.InputPeerChat(chat_id=-file_id.chat_id)
                else:
                    peer = raw.types.InputPeerChannel(
                        channel_id=utils.get_channel_id(file_id.chat_id),
                        access_hash=file_id.chat_access_hash,
                    )

            location = raw.types.InputPeerPhotoFileLocation(
                peer=peer,
                volume_id=file_id.volume_id,
                local_id=file_id.local_id,
                big=file_id.thumbnail_source == ThumbnailSource.CHAT_PHOTO_BIG,
            )
        elif file_type == FileType.PHOTO:
            location = raw.types.InputPhotoFileLocation(
                id=file_id.media_id,
                access_hash=file_id.access_hash,
                file_reference=file_id.file_reference,
                thumb_size=file_id.thumbnail_size,
            )
        else:
            location = raw.types.InputDocumentFileLocation(
                id=file_id.media_id,
                access_hash=file_id.access_hash,
                file_reference=file_id.file_reference,
                thumb_size=file_id.thumbnail_size,
            )
        return location

    async def yield_file(
        self,
        file_id: FileId,
        index: int,
        offset: int,
        first_part_cut: int,
        last_part_cut: int,
        part_count: int,
        chunk_size: int,
    ) -> Union[str, None]:
        client = self.client
        work_loads[index] += 1
        logging.debug(f"Starting to yield file with client {index}.")
        media_session = await self.generate_media_session(client, file_id)
        location = await self.get_location(file_id)

        async def fetch_chunk(off: int) -> bytes:
            # Retry up to 5 times with a short progressive back-off.
            # Transient Telegram DC errors (FloodWait excluded — those are handled
            # by Pyrogram's sleep_threshold) usually clear within one retry.
            for attempt in range(5):
                try:
                    r = await media_session.send(
                        raw.functions.upload.GetFile(
                            location=location,
                            offset=off,
                            limit=chunk_size,   # 1 MB — Telegram hard cap, do not change
                        ),
                    )
                    if isinstance(r, raw.types.upload.File):
                        return r.bytes
                    return b""
                except TimeoutError:
                    if attempt == 4:
                        logging.warning(f"Chunk at offset {off} timed out after 5 attempts")
                        return b""
                    await asyncio.sleep(0.2 * (attempt + 1))   # 0.2 / 0.4 / 0.6 / 0.8 s
            return b""

        current_part = 0

        try:
            # ── Pipeline pre-fill ──────────────────────────────────────────────
            # Fire PIPELINE_SIZE GetFile requests before we yield the first chunk.
            # While the caller is consuming chunk N, chunks N+1..N+PIPELINE_SIZE
            # are already being fetched in parallel, hiding round-trip latency.
            # tasks[0] is always the next chunk to yield (ordered).
            tasks = []
            for i in range(min(PIPELINE_SIZE, part_count)):
                tasks.append(asyncio.create_task(fetch_chunk(offset + i * chunk_size)))

            while tasks:
                chunk = await tasks.pop(0)

                if not chunk:
                    # Empty chunk = DC error or EOF — cancel in-flight fetches
                    for t in tasks:
                        t.cancel()
                    break

                current_part += 1

                # Immediately schedule the next chunk to keep the pipeline full
                next_part_index = current_part - 1 + len(tasks) + 1
                if next_part_index < part_count:
                    next_off = offset + next_part_index * chunk_size
                    tasks.append(asyncio.create_task(fetch_chunk(next_off)))

                # Trim the byte range on first and last chunks only
                if part_count == 1:
                    yield chunk[first_part_cut:last_part_cut]
                elif current_part == 1:
                    yield chunk[first_part_cut:]
                elif current_part == part_count:
                    yield chunk[:last_part_cut]
                else:
                    yield chunk

        except (AttributeError, ConnectionResetError):
            pass
        except TimeoutError:
            logging.warning("Stream timed out during initial fetch")
        finally:
            logging.debug(f"Finished yielding file — delivered {current_part} of {part_count} parts.")
            work_loads[index] -= 1

    async def clean_cache(self) -> None:
        while True:
            await asyncio.sleep(self.clean_timer)
            self.cached_file_ids.clear()
            logging.debug("Cleaned the cache")