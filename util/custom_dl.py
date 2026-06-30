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
        # Use provided chat_id or resolve LOG_CHANNEL/STREAM_CHANNEL
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

        # Concurrent pipeline window — fetch PIPELINE_SIZE chunks in parallel.
        # Telegram MTProto supports multiple in-flight requests per session;
        # 4 concurrent fetches saturates a typical connection without overloading the DC.
        PIPELINE_SIZE = 4

        async def fetch_chunk(off: int) -> bytes:
            for attempt in range(3):
                try:
                    r = await media_session.send(
                        raw.functions.upload.GetFile(
                            location=location, offset=off, limit=chunk_size
                        ),
                    )
                    if isinstance(r, raw.types.upload.File):
                        return r.bytes
                    return b""
                except TimeoutError:
                    if attempt == 2:
                        logging.warning(f"Chunk timeout after 3 attempts at offset {off}")
                        return b""
                    await asyncio.sleep(0.3)
            return b""

        try:
            # Pre-launch up to PIPELINE_SIZE fetches before we even yield the first chunk.
            # Tasks are ordered: tasks[0] is always the next chunk to yield.
            tasks = []
            for i in range(min(PIPELINE_SIZE, part_count)):
                tasks.append(asyncio.create_task(fetch_chunk(offset + i * chunk_size)))

            current_part = 0
            current_offset = offset

            while tasks:
                chunk = await tasks.pop(0)

                if not chunk:
                    # Cancel remaining in-flight fetches cleanly
                    for t in tasks:
                        t.cancel()
                    break

                current_part += 1

                # Launch the next fetch to keep the pipeline full
                next_fetch_part = current_part - 1 + len(tasks) + 1
                if next_fetch_part < part_count:
                    next_offset = offset + next_fetch_part * chunk_size
                    tasks.append(asyncio.create_task(fetch_chunk(next_offset)))

                # Apply byte cuts on first and last parts
                if part_count == 1:
                    yield chunk[first_part_cut:last_part_cut]
                elif current_part == 1:
                    yield chunk[first_part_cut:]
                elif current_part == part_count:
                    yield chunk[:last_part_cut]
                else:
                    yield chunk

                current_offset += chunk_size

        except (AttributeError, ConnectionResetError):
            pass
        except TimeoutError:
            logging.warning("Stream timed out on initial chunk request")
        finally:
            logging.debug(f"Finished yielding file with {current_part} parts.")
            work_loads[index] -= 1

    async def clean_cache(self) -> None:
        while True:
            await asyncio.sleep(self.clean_timer)
            self.cached_file_ids.clear()
            logging.debug("Cleaned the cache")