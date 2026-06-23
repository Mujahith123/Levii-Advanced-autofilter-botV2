import logging
import asyncio
from struct import pack
import re
import base64
from pyrogram.file_id import FileId
from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields

from marshmallow.exceptions import ValidationError
from motor.motor_asyncio import AsyncIOMotorClient
from info import (
    DATABASE_URI, DATABASE_NAME, COLLECTION_NAME, USE_CAPTION_FILTER, MAX_B_TN,
)
from utils import get_settings, save_group_settings, temp
from database.users_chats_db import db as users_db

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


client = AsyncIOMotorClient(DATABASE_URI)
db = client[DATABASE_NAME]
instance = Instance.from_db(db)


@instance.register
class Media(Document):
    file_id = fields.StrField(attribute='_id')
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)

    class Meta:
        indexes = ('$file_name',)
        collection_name = COLLECTION_NAME


async def save_file(media):
    """Save file in database."""

    if not getattr(media, "file_id", None):
        logger.warning("save_file called with media that has no file_id – skipping")
        return False, 2

    file_id, file_ref = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"@(\w+)", r"\1", str(media.file_name))
    file_name = re.sub(r"(_|\(|\)\-|\.|\+)", " ", file_name)

    try:
        file = Media(
            file_id=file_id,
            file_ref=file_ref,
            file_name=file_name,
            file_size=media.file_size,
            file_type=media.file_type,
            mime_type=media.mime_type,
            caption=media.caption.html if media.caption else None,
        )
    except ValidationError:
        logger.exception('Error occurred while saving file in database')
        return False, 2

    try:
        await file.commit()
    except DuplicateKeyError:
        logger.warning(
            f'{getattr(media, "file_name", "NO_FILE")} is already saved in database'
        )
        return False, 0
    except Exception:
        logger.exception('Error occurred while saving file in database')
        return False, 2

    logger.info(f'{getattr(media, "file_name", "NO_FILE")} is saved to database')
    asyncio.create_task(_notify_request_matches(file_name, file.caption))
    return True, 1


def _pattern_for_request(query):
    """Word-boundary AND-of-words pattern used for request matching."""
    query = (query or "").strip()
    if not query:
        return None
    if ' ' not in query:
        raw_pattern = r'(\b|[\.+\-_])' + re.escape(query) + r'(\b|[\.+\-_])'
    else:
        words = query.split()
        raw_pattern = ''.join([r'(?=.*' + re.escape(w) + r')' for w in words])
    try:
        return re.compile(raw_pattern, flags=re.IGNORECASE)
    except re.error:
        return None


async def _notify_request_matches(file_name, caption=None):
    """Auto Request Notify: DM anyone whose /request matches this newly-indexed file."""
    try:
        haystacks = [file_name or ""]
        if caption:
            haystacks.append(caption)
        open_requests = await users_db.get_open_requests()
        async for req in open_requests:
            regex = _pattern_for_request(req.get("query"))
            if not regex or not any(regex.search(h) for h in haystacks):
                continue
            try:
                if temp.BOT:
                    await temp.BOT.send_message(
                        req["user_id"],
                        f"🎬 Good news! The movie/file you requested — <b>{req['query']}</b> — has just been added.\nSearch for it now to get your file."
                    )
            except Exception as e:
                logger.warning(f"Auto Request Notify: failed to DM {req.get('user_id')}: {e}")
            await users_db.mark_request_notified(req["_id"])
    except Exception as e:
        logger.warning(f"Auto Request Notify failed: {e}")


async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):
    """For given query return (results, next_offset, total_results)."""
    if chat_id is not None:
        settings = await get_settings(int(chat_id))
        try:
            if settings['max_btn']:
                max_results = 10
            else:
                max_results = int(MAX_B_TN)
        except KeyError:
            await save_group_settings(int(chat_id), 'max_btn', False)
            settings = await get_settings(int(chat_id))
            if settings['max_btn']:
                max_results = 10
            else:
                max_results = int(MAX_B_TN)
    query = query.strip()
    if offset == 0 and query:
        asyncio.create_task(users_db.log_search(query))
        if chat_id and int(chat_id) < 0:
            asyncio.create_task(users_db.log_group_activity(int(chat_id), None))
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.+\-_])' + re.escape(query) + r'(\b|[\.+\-_])'
    else:
        words = query.split()
        raw_pattern = ''.join([r'(?=.*' + re.escape(w) + r')' for w in words])

    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except re.error:
        return []

    if USE_CAPTION_FILTER:
        mongo_filter = {'$or': [{'file_name': regex}, {'caption': regex}]}
    else:
        mongo_filter = {'file_name': regex}

    if file_type:
        mongo_filter['file_type'] = file_type

    total_results = await Media.count_documents(mongo_filter)
    next_offset = offset + max_results

    if next_offset > total_results:
        next_offset = ''

    cursor = Media.find(mongo_filter)
    cursor.sort('$natural', -1)
    cursor.skip(offset).limit(max_results)
    files = await cursor.to_list(length=max_results)

    return files, next_offset, total_results


async def get_recent_files(limit=20):
    """Return the most recently indexed files."""
    cursor = Media.find({})
    cursor.sort("$natural", -1)
    cursor.limit(limit)
    return await cursor.to_list(length=limit)


async def get_bad_files(query, file_type=None, filter=False):
    """For given query return (results, total_results)"""
    query = query.strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.+\-_])' + re.escape(query) + r'(\b|[\.+\-_])'
    else:
        words = query.split()
        raw_pattern = ''.join([r'(?=.*' + re.escape(w) + r')' for w in words])

    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except re.error:
        return []

    if USE_CAPTION_FILTER:
        filter = {'$or': [{'file_name': regex}, {'caption': regex}]}
    else:
        filter = {'file_name': regex}

    if file_type:
        filter['file_type'] = file_type

    total_results = await Media.count_documents(filter)
    cursor = Media.find(filter)
    cursor.sort('$natural', -1)
    files = await cursor.to_list(length=total_results)
    return files, total_results


async def get_file_details(query):
    """Look up a single file by file_id."""
    filter = {'file_id': query}
    cursor = Media.find(filter)
    filedetails = await cursor.to_list(length=1)
    return filedetails


async def delete_one_across_dbs(mongo_filter):
    """Delete a single matching document from the database."""
    return await Media.collection.delete_one(mongo_filter)


async def delete_many_across_dbs(mongo_filter):
    """Delete all matching documents from the database. Returns deleted_count."""
    result = await Media.collection.delete_many(mongo_filter)
    return result.deleted_count


def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0

    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0

            r += bytes([i])

    return base64.urlsafe_b64encode(r).decode().rstrip("=")


def encode_file_ref(file_ref: bytes) -> str:
    return base64.urlsafe_b64encode(file_ref).decode().rstrip("=")


def unpack_new_file_id(new_file_id):
    """Return file_id, file_ref"""
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    file_ref = encode_file_ref(decoded.file_reference)
    return file_id, file_ref
