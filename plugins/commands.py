import os
import logging
import random
import asyncio
from datetime import datetime
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.errors import ChatAdminRequired, FloodWait, UserNotParticipant
from pyrogram.types import *
from database.ia_filterdb import (
    Media, get_file_details, unpack_new_file_id,
    get_bad_files, delete_one_across_dbs, delete_many_across_dbs,
)
from pymongo.errors import DuplicateKeyError
from database.users_chats_db import db
from info import *
from utils import get_settings, get_size, is_req_subscribed, save_group_settings, temp, get_verify_shortlink, get_shortlink, get_tutorial, is_support_chat
from database.connections_mdb import active_connection
import re, sys
import json
import base64
import string
import pytz
logger = logging.getLogger(__name__)

BATCH_FILES = {}

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    if len(message.command) == 2 and message.command[1].startswith('verify'):
        user_id = int(message.command[1].split("_")[1])
        verify_id = message.command[1].split("_")[2]
            
        verify_id_info = await db.get_verify_id_info(user_id, verify_id)
        if not verify_id_info or verify_id_info["verified"]:
            await message.reply("Lɪɴᴋ Exᴘɪʀᴇᴅ Tʀʏ Aɢᴀɪɴ...")
            return
        
        ist_timezone = pytz.timezone(TIMEZONE)     
        key = "second_time_verified" if await db.is_user_verified(user_id) else "last_verified"        
        current_time = datetime.now(tz=ist_timezone)
        result = await db.update_verify_user(user_id, {key:current_time})
        await db.update_verify_id_info(user_id, verify_id, {"verified":True})      
        buttons = [[
            InlineKeyboardButton("Search Again", callback_data="close_data")
        ]]            
        txt = script.SECOND_VERIFY_COMPLETE_TEXT if key == "second_time_verified" else script.VERIFY_COMPLETE_TEXT
        vrfy = 2 if key == "second_time_verified" else 1
        if LOG_CHANNEL:
            await client.send_message(LOG_CHANNEL, script.VERIFIED_TXT.format(message.from_user.mention, user_id, datetime.now(pytz.timezone(TIMEZONE)).strftime('%d_%B_%Y'), vrfy))
        await message.reply_photo(
            photo=VERIFY_IMG, 
            caption=txt.format(message.from_user.mention), 
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )
        return
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        buttons = [[
                    InlineKeyboardButton('⤬ Aᴅᴅ Mᴇ Tᴏ Yᴏᴜʀ Gʀᴏᴜᴘ ⤬', url=f'http://t.me/{temp.U_NAME}?startgroup=true')
                ],[
                    InlineKeyboardButton('Aᴅᴢ Fʀᴇᴇ Mᴏᴠɪᴇꜱ ✅', callback_data='buy_premium'),
                    InlineKeyboardButton('✇ Jᴏɪɴ Oᴜʀ Cʜᴀɴɴᴇʟꜱ ✇', callback_data='main_channel')
                  ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        m=await message.reply_text("<i><b>ʜᴇʟʟᴏ. ʜᴏᴡ ᴀʀᴇ ʏᴏᴜ \nᴡᴀɪᴛ ᴀ ᴍᴏᴍᴇɴᴛ ʙʀᴏ . . .</b></i>")
        await m.edit_text("<b><i>ꜱᴛᴀʀᴛɪɴɢ...</i></b>")
        await asyncio.sleep(0.4)
        await m.delete()
        m=await message.reply_sticker("CAACAgUAAxkBAAERVl9qItjuSfXZh4oaNmNYVHq5_-HE5wAC8B0AAqYccFQ5JoWWh1zXOzsE")
        await asyncio.sleep(1)
        await m.delete()
        await message.reply(script.START_TXT.format(message.from_user.mention if message.from_user else message.chat.title, temp.U_NAME, temp.B_NAME), reply_markup=reply_markup, disable_web_page_preview=True)
        await asyncio.sleep(2) # 😢 https://github.com/EvamariaTG/EvaMaria/blob/master/plugins/p_ttishow.py#L17 😬 wait a bit, before checking.
        if not await db.get_chat(message.chat.id):
            total=await client.get_chat_members_count(message.chat.id)
            await client.send_message(LOG_CHANNEL, script.LOG_TEXT_G.format(message.chat.title, message.chat.id, total, "Unknown")) if LOG_CHANNEL else None
            await db.add_chat(message.chat.id, message.chat.title)
        return 
    is_new_user = not await db.is_user_exist(message.from_user.id)
    if is_new_user:
        await db.add_user(message.from_user.id, message.from_user.first_name)
        if LOG_CHANNEL:
            await client.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(message.from_user.id, message.from_user.mention))

    is_referral_link = len(message.command) == 2 and message.command[1].startswith("ref_")
    if is_referral_link:
        # Referral System: credit the referrer once, only for genuinely new users.
        try:
            referrer_id = int(message.command[1].split("_", 1)[1])
            if is_new_user and await db.set_referrer(message.from_user.id, referrer_id):
                await db.add_referral_credit(referrer_id)
                try:
                    await client.send_message(
                        referrer_id,
                        f"🎉 Referral success! {message.from_user.mention} just joined using your link.\n+1 day of premium added — thanks for sharing!"
                    )
                except Exception:
                    pass
        except (ValueError, IndexError):
            pass

    if len(message.command) != 2 or is_referral_link:
        buttons = [[
            InlineKeyboardButton('⤬ Aᴅᴅ Mᴇ Tᴏ Yᴏᴜʀ Gʀᴏᴜᴘ ⤬', url=f'http://t.me/{temp.U_NAME}?startgroup=true')
        ],[
            InlineKeyboardButton('Eᴀʀɴ Mᴏɴᴇʏ 💸', callback_data="shortlink_info"),
            
            InlineKeyboardButton('〄 Hᴇʟᴘ', callback_data='help')
        ],[
            InlineKeyboardButton('⍟ Aʙᴏᴜᴛ', callback_data='about'),
            InlineKeyboardButton('☞ Uᴘᴅᴀᴛᴇꜱ', callback_data='main_channel') 
        ],[
            InlineKeyboardButton('💰 Buy Premium for adz Free Movies ✅', callback_data='buy_premium')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        m=await message.reply_text("<i><b>ʜᴇʟʟᴏ. ʜᴏᴡ ᴀʀᴇ ʏᴏᴜ \nᴡᴀɪᴛ ᴀ ᴍᴏᴍᴇɴᴛ ʙʀᴏ . . .</b></i>")
        await m.edit_text("<b><i>ꜱᴛᴀʀᴛɪɴɢ...</i></b>")
        await asyncio.sleep(0.4)
        await m.delete()
        m=await message.reply_sticker("CAACAgUAAxkBAAERVl9qItjuSfXZh4oaNmNYVHq5_-HE5wAC8B0AAqYccFQ5JoWWh1zXOzsE")
        await asyncio.sleep(1)
        await m.delete()
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return

    if len(message.command) == 2 and message.command[1] == "request":
        btn = [[
            InlineKeyboardButton('📩 Request in Support Group', url=f'https://t.me/{SUPPORT_CHAT}')
        ],[
            InlineKeyboardButton('🗑 Cancel', callback_data='close_data')
        ]]
        await message.reply_text(
            "<b>🎬 Request a Movie</b>\n\n"
            "Use the command below to request:\n"
            "<code>/request Movie Name Year</code>\n\n"
            "<b>Example:</b> <code>/request Pushpa 2 2024</code>\n\n"
            "Or tap below to request in our support group!",
            reply_markup=InlineKeyboardMarkup(btn)
        )
        return

    if len(message.command) == 2 and message.command[1] in ["subscribe", "error", "okay", "help", "buy_premium"]:
        if message.command[1] == "buy_premium":
            btn = [[
                InlineKeyboardButton('💸 ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ 💸', url=USERNAME)
            ],[
                InlineKeyboardButton('🥳 𝙲𝚕𝚒𝚌𝚔 𝙷𝚎𝚛𝚎 𝚃𝚘 𝙶𝚎𝚝 𝟻𝙼𝚒𝚗𝚜 𝙵𝚛𝚎𝚎 𝚃𝚛𝚒𝚊𝚕 🎉', callback_data='give_trial')
            ],[
                InlineKeyboardButton('🗑 ᴄᴀɴᴄᴇʟ ᴘʀᴇᴍɪᴜᴍ 🗑', callback_data='close_data')
            ]]            
            await message.reply_text(
                text=script.PREMIUM_TXT.format(message.from_user.mention),
                reply_markup=InlineKeyboardMarkup(btn),
            )
            return
    
    if AUTH_CHANNEL and not await is_req_subscribed(client, message):
        try:
            auth_chat = await client.get_chat(AUTH_CHANNEL)
            auth_chat_id = auth_chat.id
            is_public = bool(auth_chat.username)
        except Exception as e:
            logger.error(f"Failed to get AUTH_CHANNEL info: {e}")
            return

        if is_public:
            # Telegram ignores creates_join_request=True for public channels —
            # the client just opens/joins the channel directly regardless.
            # For public channels we use a direct join link and verify membership
            # via get_chat_member() when the user clicks Try Again.
            channel_url = f"https://t.me/{auth_chat.username}"
            btn = [
                [
                    InlineKeyboardButton(
                        "📢 JOIN OUR CHANNEL 📢", url=channel_url
                    )
                ]
            ]
            msg_text = (
                "**Yᴏᴜ ʜᴀᴠᴇ ɴᴏᴛ ᴊᴏɪɴᴇᴅ ᴏᴜʀ Bᴀᴄᴋ-ᴜᴘ Cʜᴀɴɴᴇʟ...**\n\n"
                "Pʟᴇᴀꜱᴇ ᴊᴏɪɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ ʙʏ ᴄʟɪᴄᴋɪɴɢ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ,\n"
                "ᴛʜᴇɴ ᴄʟɪᴄᴋ **🔃 TRY AGAIN 🔃** ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ғɪʟᴇ."
            )
        else:
            # Private channel — join-request invite links work correctly here
            try:
                invite_link = await client.create_chat_invite_link(
                    auth_chat_id,
                    creates_join_request=True
                )
            except ChatAdminRequired:
                logger.error("Make sure Bot is admin in Forcesub channel")
                return
            except Exception as e:
                logger.error(f"Failed to create invite link for AUTH_CHANNEL: {e}")
                return
            btn = [
                [
                    InlineKeyboardButton(
                        "📢 REQUEST TO JOIN CHANNEL 📢", url=invite_link.invite_link
                    )
                ]
            ]
            msg_text = (
                "**Yᴏᴜ ᴀʀᴇ ɴᴏᴛ ɪɴ ᴏᴜʀ Bᴀᴄᴋ-ᴜᴘ ᴄʜᴀɴɴᴇʟ...**\n\n"
                "Cʟɪᴄᴋ **📢 REQUEST TO JOIN CHANNEL 📢** ʙᴇʟᴏᴡ ᴀɴᴅ ꜱᴇɴᴅ ᴀ ᴊᴏɪɴ ʀᴇQᴜᴇꜱᴛ,\n"
                "ᴛʜᴇɴ ᴄʟɪᴄᴋ **🔃 TRY AGAIN 🔃** ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ғɪʟᴇ."
            )

        if message.command[1] != "subscribe":
            # BATCH links use "BATCH-<encoded>" format (dash separator, not underscore).
            # Always use a URL-based TRY AGAIN for them so the format is preserved
            # exactly when the user clicks — the checksub callback rebuilds with "_"
            # which would corrupt "BATCH-xxx" into "BATCH_xxx".
            start_param = message.command[1]
            if start_param.startswith("BATCH-"):
                btn.append([InlineKeyboardButton("🔃 TRY AGAIN 🔃", url=f"https://t.me/{temp.U_NAME}?start={start_param}")])
            else:
                try:
                    kk, file_id = start_param.split("_", 1)
                    btn.append([InlineKeyboardButton("🔃 TRY AGAIN 🔃", callback_data=f"checksub#{kk}#{file_id}")])
                except (IndexError, ValueError):
                    btn.append([InlineKeyboardButton("🔃 TRY AGAIN 🔃", url=f"https://t.me/{temp.U_NAME}?start={start_param}")])
        await client.send_message(
            chat_id=message.from_user.id,
            text=msg_text,
            reply_markup=InlineKeyboardMarkup(btn),
            parse_mode=enums.ParseMode.MARKDOWN
            )
        return
    if len(message.command) == 2 and message.command[1] in ["subscribe", "error", "okay", "help"]:
        buttons = [[
            InlineKeyboardButton('⤬ Aᴅᴅ Mᴇ Tᴏ Yᴏᴜʀ Gʀᴏᴜᴘ ⤬', url=f'http://t.me/{temp.U_NAME}?startgroup=true')
        ],[
            InlineKeyboardButton('Eᴀʀɴ Mᴏɴᴇʏ 💸', callback_data="shortlink_info"),
            
            InlineKeyboardButton('〄 Hᴇʟᴘ', callback_data='help')
        ],[
            InlineKeyboardButton('⍟ Aʙᴏᴜᴛ', callback_data='about'),
            InlineKeyboardButton('☞ Uᴘᴅᴀᴛᴇꜱ', callback_data='main_channel') 
        ],[
            InlineKeyboardButton('💰 Buy Premium for adz Free Movies ✅', callback_data='buy_premium')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)      
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return
    data = message.command[1]
    try:
        pre, file_id = data.split('_', 1)
    except:
        file_id = data
        pre = ""
    if data.split("-", 1)[0] == "BATCH":
        sts = await message.reply("<b>Please wait...</b>")
        encoded_file_id = data.split("-", 1)[1]
        # Decode the base64-encoded payload.
        # New format (genlink.py ≥ this fix): "chat_id:msg_id"  → fetch message → download
        # Old format (legacy links):          raw Telegram file_id string → download directly
        try:
            padding = '=' * (-len(encoded_file_id) % 4)
            decoded_str = base64.urlsafe_b64decode(encoded_file_id + padding).decode()
        except Exception:
            decoded_str = encoded_file_id  # last-resort fallback

        # Detect new compact format "chat_id:msg_id"
        if ":" in decoded_str:
            try:
                batch_chat_id, batch_msg_id = decoded_str.split(":", 1)
                batch_msg = await client.get_messages(int(batch_chat_id), int(batch_msg_id))
                file_id = batch_msg.document.file_id
            except Exception as e:
                logger.error(f"BATCH get_messages failed: {e}")
                await sts.edit("<b>Failed to locate batch file. The link may have expired.</b>")
                if LOG_CHANNEL:
                    await client.send_message(LOG_CHANNEL, f"BATCH get_messages FAILED: {e}")
                return
        else:
            # Legacy: decoded_str is the raw file_id
            file_id = decoded_str
        msgs = BATCH_FILES.get(file_id)
        if not msgs:
            try:
                file = await client.download_media(file_id)
            except Exception as e:
                logger.error(f"BATCH download_media failed: {e}")
                await sts.edit("<b>Failed to fetch batch file. The link may have expired.</b>")
                if LOG_CHANNEL:
                    await client.send_message(LOG_CHANNEL, f"BATCH download_media FAILED: {e}")
                return
            if not file:
                await sts.edit("<b>Failed to download batch file. Please regenerate the link.</b>")
                return
            try:
                with open(file, encoding='utf-8') as file_data:
                    msgs = json.loads(file_data.read())
            except Exception as e:
                logger.error(f"BATCH open/parse failed: {e}")
                await sts.edit("<b>Failed to read batch file.</b>")
                if LOG_CHANNEL:
                    await client.send_message(LOG_CHANNEL, f"BATCH OPEN FAILED: {e}")
                return
            finally:
                try:
                    os.remove(file)
                except Exception:
                    pass
            BATCH_FILES[file_id] = msgs
        sent_messages = []
        for msg in msgs:
            title = msg.get("title")
            size=get_size(int(msg.get("size", 0)))
            f_caption=msg.get("caption", "")
            if BATCH_FILE_CAPTION:
                try:
                    f_caption=BATCH_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
                except Exception as e:
                    logger.exception(e)
                    f_caption=f_caption
            if f_caption is None:
                f_caption = f"{title}"
            try:
                # Create the inline keyboard button with callback_data
                sent = await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=msg.get("file_id"),
                    caption=f_caption,
                    protect_content=msg.get('protect', False),
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton('Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ', url=f'https://t.me/{SUPPORT_CHAT}'),
                                InlineKeyboardButton('Uᴘᴅᴀᴛᴇs Cʜᴀɴɴᴇʟ', url=CHNL_LNK)
                            ],[
                                InlineKeyboardButton('𝗕𝗢𝗧 𝗢𝗪𝗡𝗘𝗥', url=USERNAME)
                            ]
                        ]
                    )
                )
                sent_messages.append(sent)
            except FloodWait as e:
                await asyncio.sleep(e.value)
                logger.warning(f"Floodwait of {e.value} sec.")
                sent = await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=msg.get("file_id"),
                    caption=f_caption,
                    protect_content=msg.get('protect', False),
                    reply_markup=InlineKeyboardMarkup(
                        [
                         [
                          InlineKeyboardButton('Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ', url=f'https://t.me/{SUPPORT_CHAT}'),
                          InlineKeyboardButton('Uᴘᴅᴀᴛᴇs Cʜᴀɴɴᴇʟ', url=CHNL_LNK)
                       ],[
                          InlineKeyboardButton("𝗕𝗢𝗧 𝗢𝗪𝗡𝗘𝗥", url=USERNAME)
                            ]
                        ]
                    )
                )
                sent_messages.append(sent)
            except Exception as e:
                logger.warning(e, exc_info=True)
                continue
            await asyncio.sleep(1) 
        await sts.delete()
        warning = await client.send_message(
            chat_id=message.from_user.id,
            text=(
                "⚠️ <b>Important:</b>\n\n"
                "All Messages will be deleted after <b>20 minutes</b>. "
                "Please save or forward these messages to your personal saved messages "
                "or share with your friends to avoid losing them!"
            )
        )
        sent_messages.append(warning)
        # Auto-delete all sent messages after 20 minutes (non-blocking)
        async def _delete_batch(msgs, uid):
            await asyncio.sleep(1200)
            for m in msgs:
                try:
                    await m.delete()
                except Exception:
                    pass
            try:
                await client.send_message(
                    chat_id=uid,
                    text=(
                        "🗑️ Your files have been automatically deleted due to copyright © reasons.\n\n"
                        "Please use the link again to re-access the files."
                    )
                )
            except Exception:
                pass
        asyncio.create_task(_delete_batch(sent_messages, message.from_user.id))
        return
    
    elif data.split("-", 1)[0] == "DSTORE":
        sts = await message.reply("<b>Please wait...</b>")
        b_string = data.split("-", 1)[1]
        decoded = (base64.urlsafe_b64decode(b_string + "=" * (-len(b_string) % 4))).decode("ascii")
        try:
            f_msg_id, l_msg_id, f_chat_id, protect = decoded.split("_", 3)
        except:
            f_msg_id, l_msg_id, f_chat_id = decoded.split("_", 2)
            protect = "/pbatch" if PROTECT_CONTENT else "batch"
        diff = int(l_msg_id) - int(f_msg_id)
        async for msg in client.iter_messages(int(f_chat_id), int(l_msg_id), int(f_msg_id)):
            if msg.media:
                media = getattr(msg, msg.media.value)
                if BATCH_FILE_CAPTION:
                    try:
                        f_caption=BATCH_FILE_CAPTION.format(file_name=getattr(media, 'file_name', ''), file_size=getattr(media, 'file_size', ''), file_caption=getattr(msg, 'caption', ''))
                    except Exception as e:
                        logger.exception(e)
                        f_caption = getattr(msg, 'caption', '')
                else:
                    media = getattr(msg, msg.media.value)
                    file_name = getattr(media, 'file_name', '')
                    f_caption = getattr(msg, 'caption', file_name)
                try:
                    await msg.copy(message.chat.id, caption=f_caption, protect_content=True if protect == "/pbatch" else False)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    await msg.copy(message.chat.id, caption=f_caption, protect_content=True if protect == "/pbatch" else False)
                except Exception as e:
                    logger.exception(e)
                    continue
            elif msg.empty:
                continue
            else:
                try:
                    await msg.copy(message.chat.id, protect_content=True if protect == "/pbatch" else False)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    await msg.copy(message.chat.id, protect_content=True if protect == "/pbatch" else False)
                except Exception as e:
                    logger.exception(e)
                    continue
            await asyncio.sleep(1) 
        return await sts.delete()
    if data.startswith("sendfiles"):
        chat_id = int("-" + file_id.split("-")[1])
        userid = message.from_user.id if message.from_user else None
        g = await get_shortlink(chat_id, f"https://telegram.me/{temp.U_NAME}?start=allfiles_{file_id}")
        k = await client.send_message(chat_id=message.from_user.id,text=f"<b>Get All Files in a Single Click!!!\n\n📂 ʟɪɴᴋ ➠ : {g}\n\n<i>Note: This message is deleted in 20 minutes to avoid copyrights. Save the link to Somewhere else</i></b>", reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton('📂 Dᴏᴡɴʟᴏᴀᴅ Lɪɴᴋ 📂', url=g)
                    ], [
                        InlineKeyboardButton('⁉️ Hᴏᴡ Tᴏ Dᴏᴡɴʟᴏᴀᴅ ⁉️', url=await get_tutorial(chat_id))
                    ], [
                        InlineKeyboardButton('💸 Buy Premium For Adz Free Movies ✅', callback_data='buy_premium')
                    ]
                ]
            )
        )                                             
        async def _delete_sendfiles(msg, uid):
            await asyncio.sleep(1200)
            try:
                await msg.edit("<b>Your message is successfully deleted!!!</b>")
            except Exception:
                pass
        asyncio.create_task(_delete_sendfiles(k, message.from_user.id))
        return
        
    
    elif data.startswith("short"):        
        user_id = message.from_user.id
        chat_id = temp.SHORT.get(user_id)
        files_ = await get_file_details(file_id)
        files = files_[0]
        g = await get_shortlink(chat_id, f"https://telegram.me/{temp.U_NAME}?start=file_{file_id}")
        button = [[
            InlineKeyboardButton('📂 Dᴏᴡɴʟᴏᴀᴅ Lɪɴᴋ 📂', url=g)
        ], [
            InlineKeyboardButton('⁉️ Hᴏᴡ Tᴏ Dᴏᴡɴʟᴏᴀᴅ ⁉️', url=await get_tutorial(chat_id))
        ], [
            InlineKeyboardButton('💸 Buy Premium For Adz Free Movies ✅', callback_data="buy_premium")
        ]]
        k = await client.send_message(
            chat_id=user_id,
            text=f"<b>📕Nᴀᴍᴇ ➠ : <code>{files.file_name}</code> \n\n🔗Sɪᴢᴇ ➠ : {get_size(files.file_size)}\n\n📂Fɪʟᴇ ʟɪɴᴋ ➠ : {g}\n\n<i>Note: This message is deleted in 20 minutes to avoid copyrights. Save the link to Somewhere else</i></b>",
            reply_markup=InlineKeyboardMarkup(button)
        )
        async def _delete_short(msg):
            await asyncio.sleep(1200)
            try:
                await msg.edit("<b>Your message is successfully deleted!!!</b>")
            except Exception:
                pass
        asyncio.create_task(_delete_short(k))
        return
        
    elif data.startswith("all"):
        files = temp.GETALL.get(file_id)
        if not files:
            return await message.reply('<b><i>No such file exist.</b></i>')
        filesarr = []
        for file in files:
            file_id = file.file_id
            files_ = await get_file_details(file_id)
            files1 = files_[0]
            title = ' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@'), files1.file_name.split()))
            size=get_size(files1.file_size)
            f_caption=files1.caption
            if CUSTOM_FILE_CAPTION:
                try:
                    f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
                except Exception as e:
                    logger.exception(e)
                    f_caption=f_caption
            if f_caption is None:
                f_caption = f"{' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@'), files1.file_name.split()))}"
            user_id = message.from_user.id
            user_verified = await db.is_user_verified(user_id)
            is_second_shortener = await db.use_second_shortener(user_id)
            how_to_download_link = TUTORIAL_LINK_2 if is_second_shortener else TUTORIAL_LINK_1
            if not await db.has_premium_access(user_id):
                if VERIFY and not user_verified or is_second_shortener:
                    verify_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
                    await db.create_verify_id(user_id, verify_id)
                    btn = [[
                        InlineKeyboardButton(text="♻️ ᴄʟɪᴄᴋ ʜᴇʀᴇ ᴛᴏ ᴠᴇʀɪꜰʏ ♻️", url=await get_verify_shortlink(f"https://telegram.me/{temp.U_NAME}?start=verify_{user_id}_{verify_id}", is_second_shortener))
                    ], [
                        InlineKeyboardButton(text="⁉️ ʜᴏᴡ ᴛᴏ ᴠᴇʀɪꜰʏ ⁉️", url=how_to_download_link)
                    ]]
                    bin_text = script.SECOND_VERIFICATION_TEXT if is_second_shortener else script.VERIFICATION_TEXT
                    reply_markup = InlineKeyboardMarkup(btn)
                    dlt = await message.reply_text(
                        text=bin_text.format(message.from_user.mention),
                        reply_markup=reply_markup,
                        parse_mode=enums.ParseMode.HTML
                    )
                    await asyncio.sleep(120)
                    await dlt.delete()
                    await message.delete()
                    return
            else:
                pass
            msg = await client.send_cached_media(
                chat_id=message.from_user.id,
                file_id=file_id,
                caption=f_caption,
                protect_content=True if pre == 'filep' else False,
                reply_markup=(
                    InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton("𝗕𝗢𝗧 𝗢𝗪𝗡𝗘𝗥", url=USERNAME)
                            ],[
                                InlineKeyboardButton('Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ', url=f'https://t.me/{SUPPORT_CHAT}'),
                                InlineKeyboardButton('Uᴘᴅᴀᴛᴇs Cʜᴀɴɴᴇʟ', url=CHNL_LNK)
                            ],[
                                InlineKeyboardButton('🚀 Fast Download / Watch Online🖥️', callback_data=f'generate_stream_link:{file_id}') #Don't change anything without contacting me bot owner
                            ]
                        ]
                    )
                )
            )
            filesarr.append(msg)
        k = await client.send_message(chat_id = message.from_user.id, text=f"<b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\nThis Movie Files/Videos will be deleted in <b><u>20 minutes</u> 🫥 <i></b>(Due to Copyright Issues)</i>.\n\n<b><i>Please forward this ALL Files/Videos to your Saved Messages and Start Download there</i></b>")
        async def _delete_all(msgs, warn_msg):
            await asyncio.sleep(1200)
            for x in msgs:
                try:
                    await x.delete()
                except Exception:
                    pass
            try:
                await warn_msg.edit_text("<b>Your All Files/Videos is successfully deleted!!!</b>")
            except Exception:
                pass
        asyncio.create_task(_delete_all(filesarr, k))
        return    
        
    elif data.startswith("files"):        
        user_id = message.from_user.id
        if temp.SHORT.get(user_id)==None:
            await message.reply_text(text="<b>Please Search Again in Group</b>")
        else:
            chat_id = temp.SHORT.get(user_id)
        settings = await get_settings(chat_id)
        if not await db.has_premium_access(user_id) and settings['is_shortlink']:
            files_ = await get_file_details(file_id)
            files = files_[0]
            g = await get_shortlink(chat_id, f"https://telegram.me/{temp.U_NAME}?start=file_{file_id}")
            k = await client.send_message(chat_id=message.from_user.id,text=f"<b>📕Nᴀᴍᴇ ➠ : <code>{files.file_name}</code> \n\n🔗Sɪᴢᴇ ➠ : {get_size(files.file_size)}\n\n📂Fɪʟᴇ ʟɪɴᴋ ➠ : {g}\n\n<i>Note: This message is deleted in 20 minutes to avoid copyrights. Save the link to Somewhere else</i></b>", reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton('📁 Dᴏᴡɴʟᴏᴀᴅ Lɪɴᴋ 📁', url=g)
                        ], [
                            InlineKeyboardButton('⁉️ Hᴏᴡ Tᴏ Dᴏᴡɴʟᴏᴀᴅ ⁉️', url=await get_tutorial(chat_id))
                        ], [
                            InlineKeyboardButton('💸 Buy Premium For Adz Free Movies ✅', callback_data='buy_premium')                            
                        ]
                    ]
                )
            )
            async def _delete_files_short(msg):
                await asyncio.sleep(1199)
                try:
                    await msg.edit("<b>Your message is successfully deleted!!!</b>")
                except Exception:
                    pass
            asyncio.create_task(_delete_files_short(k))
            return

    user = message.from_user.id
    files_ = await get_file_details(file_id)           
    if not files_:
        pre, file_id = ((base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))).decode("ascii")).split("_", 1)
        try:
            user_id = message.from_user.id
            user_verified = await db.is_user_verified(user_id)
            is_second_shortener = await db.use_second_shortener(user_id)
            how_to_download_link = TUTORIAL_LINK_2 if is_second_shortener else TUTORIAL_LINK_1
            if not await db.has_premium_access(user_id):
                if VERIFY == True:
                    verify_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
                    await db.create_verify_id(user_id, verify_id)
                    btn = [[
                        InlineKeyboardButton(text="♻️ ᴄʟɪᴄᴋ ʜᴇʀᴇ ᴛᴏ ᴠᴇʀɪꜰʏ ♻️", url=await get_verify_shortlink(f"https://telegram.me/{temp.U_NAME}?start=verify_{user_id}_{verify_id}", is_second_shortener))
                    ], [
                        InlineKeyboardButton(text="⁉️ ʜᴏᴡ ᴛᴏ ᴠᴇʀɪꜰʏ ⁉️", url=how_to_download_link)
                    ]]
                    reply_markup = InlineKeyboardMarkup(btn)
                    bin_text = script.SECOND_VERIFICATION_TEXT if is_second_shortener else script.VERIFICATION_TEXT
                    dlt = await message.reply_text(
                        text=bin_text.format(message.from_user.mention),
                        reply_markup=reply_markup,
                        parse_mode=enums.ParseMode.HTML
                    )
                    await asyncio.sleep(120)
                    await dlt.delete()
                    await message.delete()
                    return
            else:
                pass
            msg = await client.send_cached_media(
                chat_id=message.from_user.id,
                file_id=file_id,
                protect_content=True if pre == 'filep' else False,
                reply_markup=(
                    InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton("𝗕𝗢𝗧 𝗢𝗪𝗡𝗘𝗥", url=USERNAME)
                            ],[
                                InlineKeyboardButton('Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ', url=f'https://t.me/{SUPPORT_CHAT}'),
                                InlineKeyboardButton('Uᴘᴅᴀᴛᴇs Cʜᴀɴɴᴇʟ', url=CHNL_LNK)
                            ],[
                                InlineKeyboardButton('🚀 Fast Download / Watch Online🖥️', callback_data=f'generate_stream_link:{file_id}') #Don't change anything without contacting me owner
                            ]
                        ]
                    )
                )
            )

            filetype = msg.media
            file = getattr(msg, filetype.value)
            title = '@rioupdates1  ' + ' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@'), file.file_name.split()))
            size=get_size(file.file_size)
            f_caption = f"<code>{title}</code>"
            if CUSTOM_FILE_CAPTION:
                try:
                    f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='')
                except:
                    return
            await msg.edit_caption(f_caption)
            btn = [[
                InlineKeyboardButton("Get File Again", callback_data=f'delfile#{file_id}')
            ]]
            k = await msg.reply("<b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\nThis Movie File/Video will be deleted in <b><u>20 minutes</u> 🫥 <i></b>(Due to Copyright Issues)</i>.\n\n<b><i>Please forward this File/Video to your Saved Messages and Start Download there</i></b>",quote=True)
            async def _delete_decoded(file_msg, warn_msg, buttons):
                await asyncio.sleep(1200)
                try:
                    await file_msg.delete()
                except Exception:
                    pass
                try:
                    await warn_msg.edit_text("<b>Your File/Video is successfully deleted!!!\n\nClick below button to get your deleted file 👇</b>", reply_markup=InlineKeyboardMarkup(buttons))
                except Exception:
                    pass
            asyncio.create_task(_delete_decoded(msg, k, btn))
            return
        except:
            pass
        return await message.reply('No such file exist.')
    files = files_[0]
    title = '@rioupdates1  ' + ' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@'), files.file_name.split()))
    size=get_size(files.file_size)
    f_caption=files.caption
    if CUSTOM_FILE_CAPTION:
        try:
            f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
        except Exception as e:
            logger.exception(e)
            f_caption=f_caption
    if f_caption is None:
        f_caption = f"@rioupdates1  {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@'), files.file_name.split()))}"
    user_id = message.from_user.id
    user_verified = await db.is_user_verified(user_id)
    is_second_shortener = await db.use_second_shortener(user_id)
    how_to_download_link = TUTORIAL_LINK_2 if is_second_shortener else TUTORIAL_LINK_1
    if not await db.has_premium_access(user_id):
        if VERIFY and not user_verified or is_second_shortener:
            verify_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
            await db.create_verify_id(user_id, verify_id)
            btn = [[
                InlineKeyboardButton(text="♻️ ᴄʟɪᴄᴋ ʜᴇʀᴇ ᴛᴏ ᴠᴇʀɪꜰʏ ♻️", url=await get_verify_shortlink(f"https://telegram.me/{temp.U_NAME}?start=verify_{user_id}_{verify_id}", is_second_shortener))
            ], [
                InlineKeyboardButton(text="⁉️ ʜᴏᴡ ᴛᴏ ᴠᴇʀɪꜰʏ ⁉️", url=how_to_download_link)
            ]]
            reply_markup = InlineKeyboardMarkup(btn)
            bin_text = script.SECOND_VERIFICATION_TEXT if is_second_shortener else script.VERIFICATION_TEXT
            dlt = await message.reply_text(
                text=bin_text.format(message.from_user.mention),
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
            await asyncio.sleep(120)
            await dlt.delete()
            await message.delete()
            return
    else:
        pass
    msg = await client.send_cached_media(
        chat_id=message.from_user.id,
        file_id=file_id,
        caption=f_caption,
        protect_content=True if pre == 'filep' else False,
        reply_markup=(
            InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("𝗕𝗢𝗧 𝗢𝗪𝗡𝗘𝗥", url=USERNAME)
                    ],[
                        InlineKeyboardButton('Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ', url=f'https://t.me/{SUPPORT_CHAT}'),
                        InlineKeyboardButton('Uᴘᴅᴀᴛᴇs Cʜᴀɴɴᴇʟ', url=CHNL_LNK)
                    ],[
                        InlineKeyboardButton('🚀 Fast Download / Watch Online🖥️', callback_data=f'generate_stream_link:{file_id}') #Don't change anything without contacting me owner
                    ]
                ]
            )
        )
    )
    btn = [[
        InlineKeyboardButton("Get File Again", callback_data=f'delfile#{file_id}')
    ]]
    k = await msg.reply("<b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\nThis Movie File/Video will be deleted in <b><u>20 minutes</u> 🫥 <i></b>(Due to Copyright Issues)</i>.\n\n<b><i>Please forward this File/Video to your Saved Messages and Start Download there</i></b>",quote=True)
    async def _delete_single(file_msg, warn_msg, buttons):
        await asyncio.sleep(1200)
        try:
            await file_msg.delete()
        except Exception:
            pass
        try:
            await warn_msg.edit_text("<b>Your File/Video is successfully deleted!!!\n\nClick below button to get your deleted file 👇</b>", reply_markup=InlineKeyboardMarkup(buttons))
        except Exception:
            pass
    asyncio.create_task(_delete_single(msg, k, btn))
    return   

@Client.on_message(filters.command('channel') & filters.user(ADMINS))
async def channel_info(bot, message):
           
    """Send basic information of channel"""
    if isinstance(CHANNELS, (int, str)):
        channels = [CHANNELS]
    elif isinstance(CHANNELS, list):
        channels = CHANNELS
    else:
        raise ValueError("Unexpected type of CHANNELS")

    text = '📑 **Indexed channels/groups**\n'
    for channel in channels:
        chat = await bot.get_chat(channel)
        if chat.username:
            text += '\n@' + chat.username
        else:
            text += '\n' + chat.title or chat.first_name

    text += f'\n\n**Total:** {len(CHANNELS)}'

    if len(text) < 4096:
        await message.reply(text)
    else:
        file = 'Indexed channels.txt'
        with open(file, 'w') as f:
            f.write(text)
        await message.reply_document(file)
        os.remove(file)


@Client.on_message(filters.command('logs') & filters.user(ADMINS))
async def log_file(bot, message):
    """Send log file"""
    try:
        await message.reply_document('LEVII.LOG')
    except Exception as e:
        await message.reply(str(e))

@Client.on_message(filters.command('delete') & filters.user(ADMINS))
async def delete(bot, message):
    """Delete file from database"""
    reply = message.reply_to_message
    if reply and reply.media:
        msg = await message.reply("Processing...⏳", quote=True)
    else:
        await message.reply('Reply to file with /delete which you want to delete', quote=True)
        return

    for file_type in ("document", "video", "audio"):
        media = getattr(reply, file_type, None)
        if media is not None:
            break
    else:
        await msg.edit('This is not supported file format')
        return
    
    file_id, file_ref = unpack_new_file_id(media.file_id)

    result = await delete_one_across_dbs({
        '_id': file_id,
    })
    if result.deleted_count:
        await msg.edit('File is successfully deleted from database')
    else:
        file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
        deleted = await delete_many_across_dbs({
            'file_name': file_name,
            'file_size': media.file_size,
            'mime_type': media.mime_type
            })
        if deleted:
            await msg.edit('File is successfully deleted from database')
        else:
            # files indexed before https://github.com/EvamariaTG/EvaMaria/commit/f3d2a1bcb155faf44178e5d7a685a1b533e714bf#diff-86b613edf1748372103e94cacff3b578b36b698ef9c16817bb98fe9ef22fb669R39 
            # have original file name.
            deleted = await delete_many_across_dbs({
                'file_name': media.file_name,
                'file_size': media.file_size,
                'mime_type': media.mime_type
            })
            if deleted:
                await msg.edit('File is successfully deleted from database')
            else:
                await msg.edit('File not found in database')


@Client.on_message(filters.command('deleteall') & filters.user(ADMINS))
async def delete_all_index(bot, message):
    await message.reply_text(
        'This will delete all indexed files.\nDo you want to continue??',
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="YES", callback_data="autofilter_delete"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="CANCEL", callback_data="close_data"
                    )
                ],
            ]
        ),
        quote=True,
    )


@Client.on_callback_query(filters.regex(r'^autofilter_delete'))
async def delete_all_index_confirm(bot, message):
    await Media.collection.drop()
    await message.answer('Piracy Is Crime')
    await message.message.edit('Succesfully Deleted All The Indexed Files.')


@Client.on_message(filters.command('settings'))
async def settings(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Use /connect {message.chat.id} in PM")
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                await message.reply_text("Make sure I'm present in your group!!", quote=True)
                return
        else:
            await message.reply_text("I'm not connected to any groups!", quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title

    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if (
            st.status != enums.ChatMemberStatus.ADMINISTRATOR
            and st.status != enums.ChatMemberStatus.OWNER
            and str(userid) not in ADMINS
    ):
        return
    
    settings = await get_settings(grp_id)

    try:
        if settings['max_btn']:
            settings = await get_settings(grp_id)
    except KeyError:
        await save_group_settings(grp_id, 'max_btn', False)
        settings = await get_settings(grp_id)
    if 'is_shortlink' not in settings.keys():
        await save_group_settings(grp_id, 'is_shortlink', False)
    else:
        pass

    if settings is not None:
        buttons = [
            [
                InlineKeyboardButton(
                    'Rᴇsᴜʟᴛ Pᴀɢᴇ',
                    callback_data=f'setgs#button#{settings["button"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    'Bᴜᴛᴛᴏɴ' if settings["button"] else 'Tᴇxᴛ',
                    callback_data=f'setgs#button#{settings["button"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Fɪʟᴇ Sᴇɴᴅ Mᴏᴅᴇ',
                    callback_data=f'setgs#botpm#{settings["botpm"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    'Mᴀɴᴜᴀʟ Sᴛᴀʀᴛ' if settings["botpm"] else 'Aᴜᴛᴏ Sᴇɴᴅ',
                    callback_data=f'setgs#botpm#{settings["botpm"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Pʀᴏᴛᴇᴄᴛ Cᴏɴᴛᴇɴᴛ',
                    callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✔ Oɴ' if settings["file_secure"] else '✘ Oғғ',
                    callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Iᴍᴅʙ',
                    callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✔ Oɴ' if settings["imdb"] else '✘ Oғғ',
                    callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Sᴘᴇʟʟ Cʜᴇᴄᴋ',
                    callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✔ Oɴ' if settings["spell_check"] else '✘ Oғғ',
                    callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Wᴇʟᴄᴏᴍᴇ Msɢ',
                    callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✔ Oɴ' if settings["welcome"] else '✘ Oғғ',
                    callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Aᴜᴛᴏ-Dᴇʟᴇᴛᴇ',
                    callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '10 Mɪɴs' if settings["auto_delete"] else '✘ Oғғ',
                    callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Aᴜᴛᴏ-Fɪʟᴛᴇʀ',
                    callback_data=f'setgs#auto_ffilter#{settings["auto_ffilter"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✔ Oɴ' if settings["auto_ffilter"] else '✘ Oғғ',
                    callback_data=f'setgs#auto_ffilter#{settings["auto_ffilter"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Mᴀx Bᴜᴛᴛᴏɴs',
                    callback_data=f'setgs#max_btn#{settings["max_btn"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '10' if settings["max_btn"] else f'{MAX_B_TN}',
                    callback_data=f'setgs#max_btn#{settings["max_btn"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'ShortLink',
                    callback_data=f'setgs#is_shortlink#{settings["is_shortlink"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✔ Oɴ' if settings["is_shortlink"] else '✘ Oғғ',
                    callback_data=f'setgs#is_shortlink#{settings["is_shortlink"]}#{grp_id}',
                ),
            ],
        ]

        btn = [[
                InlineKeyboardButton("Oᴘᴇɴ Hᴇʀᴇ ↓", callback_data=f"opnsetgrp#{grp_id}"),
                InlineKeyboardButton("Oᴘᴇɴ Iɴ PM ⇲", callback_data=f"opnsetpm#{grp_id}")
              ]]

        reply_markup = InlineKeyboardMarkup(buttons)
        if chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            await message.reply_text(
                text="<b>Dᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴏᴘᴇɴ sᴇᴛᴛɪɴɢs ʜᴇʀᴇ ?</b>",
                reply_markup=InlineKeyboardMarkup(btn),
                disable_web_page_preview=True,
                parse_mode=enums.ParseMode.HTML,
                reply_to_message_id=message.id
            )
        else:
            await message.reply_text(
                text=f"<b>Cʜᴀɴɢᴇ Yᴏᴜʀ Sᴇᴛᴛɪɴɢs Fᴏʀ {title} As Yᴏᴜʀ Wɪsʜ ⚙</b>",
                reply_markup=reply_markup,
                disable_web_page_preview=True,
                parse_mode=enums.ParseMode.HTML,
                reply_to_message_id=message.id
            )



@Client.on_message(filters.command('set_template'))
async def save_template(client, message):
    sts = await message.reply("Checking template")
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Use /connect {message.chat.id} in PM")
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                await message.reply_text("Make sure I'm present in your group!!", quote=True)
                return
        else:
            await message.reply_text("I'm not connected to any groups!", quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title

    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if (
            st.status != enums.ChatMemberStatus.ADMINISTRATOR
            and st.status != enums.ChatMemberStatus.OWNER
            and str(userid) not in ADMINS
    ):
        return

    if len(message.command) < 2:
        return await sts.edit("No Input!!")
    template = message.text.split(" ", 1)[1]
    await save_group_settings(grp_id, 'template', template)
    await sts.edit(f"Successfully changed template for {title} to\n\n{template}")


@Client.on_message((filters.command(["request", "Request"]) | filters.regex("#request") | filters.regex("#Request")) & filters.group)
async def requests(bot, message):
    if REQST_CHANNEL is None or SUPPORT_CHAT_ID is None: return # Must add REQST_CHANNEL and SUPPORT_CHAT_ID to use this feature
    if message.reply_to_message and is_support_chat(message.chat):
        chat_id = message.chat.id
        reporter = str(message.from_user.id)
        mention = message.from_user.mention
        success = True
        content = message.reply_to_message.text
        try:
            if REQST_CHANNEL is not None:
                btn = [[
                        InlineKeyboardButton('View Request', url=f"{message.reply_to_message.link}"),
                        InlineKeyboardButton('Show Options', callback_data=f'show_option#{reporter}')
                      ]]
                reported_post = await bot.send_message(chat_id=REQST_CHANNEL, text=f"<b>𝖱𝖾𝗉𝗈𝗋𝗍𝖾𝗋 : {mention} ({reporter})\n\n𝖬𝖾𝗌𝗌𝖺𝗀𝖾 : {content}</b>", reply_markup=InlineKeyboardMarkup(btn))
                success = True
            elif len(content) >= 3:
                for admin in ADMINS:
                    btn = [[
                        InlineKeyboardButton('View Request', url=f"{message.reply_to_message.link}"),
                        InlineKeyboardButton('Show Options', callback_data=f'show_option#{reporter}')
                      ]]
                    reported_post = await bot.send_message(chat_id=admin, text=f"<b>𝖱𝖾𝗉𝗈𝗋𝗍𝖾𝗋 : {mention} ({reporter})\n\n𝖬𝖾𝗌𝗌𝖺𝗀𝖾 : {content}</b>", reply_markup=InlineKeyboardMarkup(btn))
                    success = True
            else:
                if len(content) < 3:
                    await message.reply_text("<b>You must type about your request [Minimum 3 Characters]. Requests can't be empty.</b>")
            if len(content) < 3:
                success = False
        except Exception as e:
            await message.reply_text(f"Error: {e}")
            pass
        
    elif is_support_chat(message.chat):
        chat_id = message.chat.id
        reporter = str(message.from_user.id)
        mention = message.from_user.mention
        success = True
        content = message.text
        keywords = ["#request", "/request", "#Request", "/Request"]
        for keyword in keywords:
            if keyword in content:
                content = content.replace(keyword, "")
        try:
            if REQST_CHANNEL is not None and len(content) >= 3:
                btn = [[
                        InlineKeyboardButton('View Request', url=f"{message.link}"),
                        InlineKeyboardButton('Show Options', callback_data=f'show_option#{reporter}')
                      ]]
                reported_post = await bot.send_message(chat_id=REQST_CHANNEL, text=f"<b>𝖱𝖾𝗉𝗈𝗋𝗍𝖾𝗋 : {mention} ({reporter})\n\n𝖬𝖾𝗌𝗌𝖺𝗀𝖾 : {content}</b>", reply_markup=InlineKeyboardMarkup(btn))
                success = True
            elif len(content) >= 3:
                for admin in ADMINS:
                    btn = [[
                        InlineKeyboardButton('View Request', url=f"{message.link}"),
                        InlineKeyboardButton('Show Options', callback_data=f'show_option#{reporter}')
                      ]]
                    reported_post = await bot.send_message(chat_id=admin, text=f"<b>𝖱𝖾𝗉𝗈𝗋𝗍𝖾𝗋 : {mention} ({reporter})\n\n𝖬𝖾𝗌𝗌𝖺𝗀𝖾 : {content}</b>", reply_markup=InlineKeyboardMarkup(btn))
                    success = True
            else:
                if len(content) < 3:
                    await message.reply_text("<b>You must type about your request [Minimum 3 Characters]. Requests can't be empty.</b>")
            if len(content) < 3:
                success = False
        except Exception as e:
            await message.reply_text(f"Error: {e}")
            pass

    else:
        success = False
    
    if success:
        '''if isinstance(REQST_CHANNEL, (int, str)):
            channels = [REQST_CHANNEL]
        elif isinstance(REQST_CHANNEL, list):
            channels = REQST_CHANNEL
        for channel in channels:
            chat = await bot.get_chat(channel)
        #chat = int(chat)'''
        link = await bot.create_chat_invite_link(REQST_CHANNEL)
        btn = [[
                InlineKeyboardButton('Join Channel', url=link.invite_link),
                InlineKeyboardButton('View Request', url=f"{reported_post.link}")
              ]]
        await message.reply_text("<b>Your request has been added! Please wait for some time.\n\nJoin Channel First & View Request</b>", reply_markup=InlineKeyboardMarkup(btn))
    
@Client.on_message(filters.command("send") & filters.user(ADMINS))
async def send_msg(bot, message):
    if message.reply_to_message:
        target_id = message.text.split(" ", 1)[1]
        out = "Users Saved In DB Are:\n\n"
        success = False
        try:
            user = await bot.get_users(target_id)
            users = await db.get_all_users()
            async for usr in users:
                out += f"{usr['id']}"
                out += '\n'
            if str(user.id) in str(out):
                await message.reply_to_message.copy(int(user.id))
                success = True
            else:
                success = False
            if success:
                await message.reply_text(f"<b>Your message has been successfully send to {user.mention}.</b>")
            else:
                await message.reply_text("<b>This user didn't started this bot yet !</b>")
        except Exception as e:
            await message.reply_text(f"<b>Error: {e}</b>")
    else:
        await message.reply_text("<b>Use this command as a reply to any message using the target chat id. For eg: /send userid</b>")

@Client.on_message(filters.command("deletefiles") & filters.user(ADMINS))
async def deletemultiplefiles(bot, message):
    chat_type = message.chat.type
    if chat_type != enums.ChatType.PRIVATE:
        return await message.reply_text(f"<b>Hey {message.from_user.mention}, This command won't work in groups. It only works on my PM !</b>")
    else:
        pass
    try:
        keyword = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text(f"<b>Hey {message.from_user.mention}, Give me a keyword along with the command to delete files.</b>")
    k = await bot.send_message(chat_id=message.chat.id, text=f"<b>Fetching Files for your query {keyword} on DB... Please wait...</b>")
    files, total = await get_bad_files(keyword)
    await k.delete()
    #await k.edit_text(f"<b>Found {total} files for your query {keyword} !\n\nFile deletion process will start in 5 seconds !</b>")
    #await asyncio.sleep(5)
    btn = [[
       InlineKeyboardButton("Yes, Continue !", callback_data=f"killfilesdq#{keyword}")
       ],[
       InlineKeyboardButton("No, Abort operation !", callback_data="close_data")
    ]]
    await message.reply_text(
        text=f"<b>Found {total} files for your query {keyword} !\n\nDo you want to delete?</b>",
        reply_markup=InlineKeyboardMarkup(btn),
        parse_mode=enums.ParseMode.HTML
    )

@Client.on_message(filters.command("shortlink"))
async def shortlink(bot, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Turn off anonymous admin and try again this command")
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        return await message.reply_text(f"<b>Hey {message.from_user.mention}, This command only works on groups !\n\n<u>Follow These Steps to Connect Shortener:</u>\n\n1. Add Me in Your Group with Full Admin Rights\n\n2. After Adding in Grp, Set your Shortener\n\nSend this command in your group\n\n—> /shortlink ""{your_shortener_website_name} {your_shortener_api}\n\n#Sample:-\n/shortlink kpslink.in CAACAgUAAxkBAAEJ4GtkyPgEzpIUC_DSmirN6eFWp4KInAACsQoAAoHSSFYub2D15dGHfy8E\n\nThat's it!!! Enjoy Earning Money 💲\n\n[[[ Trusted Earning Site - https://kpslink.in]]]\n\nIf you have any Doubts, Feel Free to Ask me - @creatorrio\n\n(Puriyala na intha contact la message pannunga - @creatorrio)</b>")
    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grpid = message.chat.id
        title = message.chat.title
    else:
        return
    data = message.text
    userid = message.from_user.id
    user = await bot.get_chat_member(grpid, userid)
    if user.status != enums.ChatMemberStatus.ADMINISTRATOR and user.status != enums.ChatMemberStatus.OWNER and str(userid) not in ADMINS:
        return await message.reply_text("<b>You don't have access to use this command!\n\nAdd Me to Your Own Group as Admin and Try This Command\n\nFor More PM Me With This Command</b>")
    else:
        pass
    try:
        command, shortlink_url, api = data.split(" ")
    except:
        return await message.reply_text("<b>Command Incomplete :(\n\nGive me a shortener website link and api along with the command !\n\nFormat: <code>/shortlink kpslink.in e3d82cdf8f9f4783c42170b515d1c271fb1c4500</code></b>")
    reply = await message.reply_text("<b>Please Wait...</b>")
    shortlink_url = re.sub(r"https?://?", "", shortlink_url)
    shortlink_url = re.sub(r"[:/]", "", shortlink_url)
    await save_group_settings(grpid, 'shortlink', shortlink_url)
    await save_group_settings(grpid, 'shortlink_api', api)
    await save_group_settings(grpid, 'is_shortlink', True)
    await reply.edit_text(f"<b>Successfully added shortlink API for {title}.\n\nCurrent Shortlink Website: <code>{shortlink_url}</code>\nCurrent API: <code>{api}</code></b>")
    
@Client.on_message(filters.command("setshortlinkoff") & filters.user(ADMINS))
async def offshortlink(bot, message):
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        return await message.reply_text("I will Work Only in group")
    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grpid = message.chat.id
        title = message.chat.title
    else:
        return
    await save_group_settings(grpid, 'is_shortlink', False)
    # ENABLE_SHORTLINK = False
    return await message.reply_text("Successfully disabled shortlink")
    
@Client.on_message(filters.command("setshortlinkon") & filters.user(ADMINS))
async def onshortlink(bot, message):
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        return await message.reply_text("I will Work Only in group")
    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grpid = message.chat.id
        title = message.chat.title
    else:
        return
    await save_group_settings(grpid, 'is_shortlink', True)
    # ENABLE_SHORTLINK = True
    return await message.reply_text("Successfully enabled shortlink")

@Client.on_message(filters.command("shortlink_info"))
async def showshortlink(bot, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Turn off anonymous admin and try again this command")
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        return await message.reply_text(f"<b>Hey {message.from_user.mention}, This Command Only Works in Group\n\nTry this command in your own group, if you are using me in your group</b>")
    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grpid = message.chat.id
        title = message.chat.title
    else:
        return
    chat_id=message.chat.id
    userid = message.from_user.id
    user = await bot.get_chat_member(grpid, userid)
#     if 'shortlink' in settings.keys():
#         su = settings['shortlink']
#         sa = settings['shortlink_api']
#     else:
#         return await message.reply_text("<b>Shortener Url Not Connected\n\nYou can Connect Using /shortlink command</b>")
#     if 'tutorial' in settings.keys():
#         st = settings['tutorial']
#     else:
#         return await message.reply_text("<b>Tutorial Link Not Connected\n\nYou can Connect Using /set_tutorial command</b>")
    if user.status != enums.ChatMemberStatus.ADMINISTRATOR and user.status != enums.ChatMemberStatus.OWNER and str(userid) not in ADMINS:
        return await message.reply_text("<b>Tʜɪs ᴄᴏᴍᴍᴀɴᴅ Wᴏʀᴋs Oɴʟʏ Fᴏʀ ᴛʜɪs Gʀᴏᴜᴘ Oᴡɴᴇʀ/Aᴅᴍɪɴ\n\nTʀʏ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ʏᴏᴜʀ Oᴡɴ Gʀᴏᴜᴘ, Iғ Yᴏᴜ Aʀᴇ Usɪɴɢ Mᴇ Iɴ Yᴏᴜʀ Gʀᴏᴜᴘ</b>")
    else:
        settings = await get_settings(chat_id) #fetching settings for group
        if 'shortlink' in settings.keys() and 'tutorial' in settings.keys():
            su = settings['shortlink']
            sa = settings['shortlink_api']
            st = settings['tutorial']
            return await message.reply_text(f"<b>Shortlink Website: <code>{su}</code>\n\nApi: <code>{sa}</code>\n\nTutorial: <code>{st}</code></b>")
        elif 'shortlink' in settings.keys() and 'tutorial' not in settings.keys():
            su = settings['shortlink']
            sa = settings['shortlink_api']
            return await message.reply_text(f"<b>Shortener Website: <code>{su}</code>\n\nApi: <code>{sa}</code>\n\nTutorial Link Not Connected\n\nYou can Connect Using /set_tutorial command</b>")
        elif 'shortlink' not in settings.keys() and 'tutorial' in settings.keys():
            st = settings['tutorial']
            return await message.reply_text(f"<b>Tutorial: <code>{st}</code>\n\nShortener Url Not Connected\n\nYou can Connect Using /shortlink command</b>")
        else:
            return await message.reply_text("Shortener url and Tutorial Link Not Connected. Check this commands, /shortlink and /set_tutorial")


@Client.on_message(filters.command("set_tutorial"))
async def settutorial(bot, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Turn off anonymous admin and try again this command")
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        return await message.reply_text("This Command Work Only in group\n\nTry it in your own group")
    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grpid = message.chat.id
        title = message.chat.title
    else:
        return
    userid = message.from_user.id
    user = await bot.get_chat_member(grpid, userid)
    if user.status != enums.ChatMemberStatus.ADMINISTRATOR and user.status != enums.ChatMemberStatus.OWNER and str(userid) not in ADMINS:
        return
    else:
        pass
    if len(message.command) == 1:
        return await message.reply("<b>Give me a tutorial link along with this command\n\nCommand Usage: /set_tutorial your tutorial link</b>")
    elif len(message.command) == 2:
        reply = await message.reply_text("<b>Please Wait...</b>")
        tutorial = message.command[1]
        await save_group_settings(grpid, 'tutorial', tutorial)
        await save_group_settings(grpid, 'is_tutorial', True)
        await reply.edit_text(f"<b>Successfully Added Tutorial\n\nHere is your tutorial link for your group {title} - <code>{tutorial}</code></b>")
    else:
        return await message.reply("<b>You entered Incorrect Format\n\nFormat: /set_tutorial your tutorial link</b>")

@Client.on_message(filters.command("remove_tutorial"))
async def removetutorial(bot, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Turn off anonymous admin and try again this command")
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        return await message.reply_text("This Command Work Only in group\n\nTry it in your own group")
    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grpid = message.chat.id
        title = message.chat.title
    else:
        return
    userid = message.from_user.id
    user = await bot.get_chat_member(grpid, userid)
    if user.status != enums.ChatMemberStatus.ADMINISTRATOR and user.status != enums.ChatMemberStatus.OWNER and str(userid) not in ADMINS:
        return
    else:
        pass
    reply = await message.reply_text("<b>Please Wait...</b>")
    await save_group_settings(grpid, 'is_tutorial', False)
    await reply.edit_text(f"<b>Successfully Removed Your Tutorial Link!!!</b>")

@Client.on_message(filters.command("restart") & filters.user(ADMINS))
async def stop_button(bot, message):
    msg = await bot.send_message(text="**🔄 𝙿𝚁𝙾𝙲𝙴𝚂𝚂𝙴𝚂 𝚂𝚃𝙾𝙿𝙴𝙳. 𝙱𝙾𝚃 𝙸𝚂 𝚁𝙴𝚂𝚃𝙰𝚁𝚃𝙸𝙽𝙶...**", chat_id=message.chat.id)       
    await asyncio.sleep(3)
    await msg.edit("**✅️ 𝙱𝙾𝚃 𝙸𝚂 𝚁𝙴𝚂𝚃𝙰𝚁𝚃𝙴𝙳. 𝙽𝙾𝚆 𝚈𝙾𝚄 𝙲𝙰𝙽 𝚄𝚂𝙴 𝙼𝙴**")
    os.execl(sys.executable, sys.executable, *sys.argv)


@Client.on_message(filters.command("stats") & filters.user(ADMINS))
async def stats_cmd(bot, message):
    sts = await message.reply_text("⏳ Fetching stats...")
    try:
        total_users = await db.total_users_count()
        total_chats = await db.total_chat_count()
        total_files = await Media.count_documents({})
        db_size = await db.get_db_size()
        db_size_mb = round(db_size / (1024 * 1024), 2)
        maintenance = "ON 🔴" if temp.MAINTENANCE else "OFF 🟢"

        # Active users today: users added since midnight IST
        import pytz as _pytz
        tz = _pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(tz)
        midnight_ist = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
        # Count premium users via the uersz collection (expiry_time not None and in future)
        premium_count = await db.users.count_documents({
            "expiry_time": {"$gt": datetime.utcnow()}
        })

        text = (
            "<b>📊 Bot Statistics</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            f"👥 Total Users: <code>{total_users}</code>\n"
            f"💬 Total Groups: <code>{total_chats}</code>\n"
            f"🎬 Total Files: <code>{total_files}</code>\n"
            f"💎 Premium Users: <code>{premium_count}</code>\n"
            "━━━━━━━━━━━━━━━━\n"
            f"🗄️ DB Size: <code>{db_size_mb} MB</code>\n"
            f"🔧 Maintenance: <code>{maintenance}</code>"
        )
        await sts.edit(text)
    except Exception as e:
        await sts.edit("❌ Error: " + str(e))


@Client.on_message(filters.command("dashboard") & filters.user(ADMINS))
async def dashboard_cmd(bot, message):
    sts = await message.reply_text("⏳ Building dashboard...")
    try:
        (
            today_searches,
            new_users_today,
            top_searches,
            top_not_found,
            top_groups,
            today_nf,
        ) = await asyncio.gather(
            db.get_today_search_count(),
            db.get_new_users_today_count(),
            db.get_top_searches(limit=5),
            db.get_top_not_found(limit=5),
            db.get_top_active_groups(limit=3),
            db.get_today_not_found_count(),
        )

        def _fmt(items, fn):
            return "\n".join(fn(i, x) for i, x in enumerate(items)) if items else "  —"

        text = (
            "<b>📈 Stats Dashboard</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            f"🔎 Today's Searches: <code>{today_searches}</code>\n"
            f"❌ Not Found Today: <code>{today_nf}</code>\n"
            f"🆕 New Users Today: <code>{new_users_today}</code>\n"
            "━━━━━━━━━━━━━━━━\n"
            "<b>🏆 Most Searched</b>\n"
            + _fmt(top_searches, lambda i, x: f"  {i+1}. {x[0].title()} — <code>{x[1]}x</code>") + "\n"
            "━━━━━━━━━━━━━━━━\n"
            "<b>🎬 Content Gaps (not found)</b>\n"
            + _fmt(top_not_found, lambda i, x: f"  {i+1}. {x[0].title()} — <code>{x[1]}x</code>") + "\n"
            "━━━━━━━━━━━━━━━━\n"
            "<b>🏘️ Most Active Groups</b>\n"
            + _fmt(top_groups, lambda i, x: f"  {i+1}. {x[0]} — <code>{x[2]} searches</code>") + "\n"
            "━━━━━━━━━━━━━━━━\n"
            "<i>Full analytics: /gapdashboard</i>"
        )
        await sts.edit(text)
    except Exception as e:
        await sts.edit("❌ Error: " + str(e))


@Client.on_message(filters.command("backup") & filters.user(ADMINS))
async def backup_cmd(bot, message):
    """Dump all indexed files from MongoDB and send as a JSON file to LOG_CHANNEL."""
    if not LOG_CHANNEL:
        return await message.reply_text("❌ LOG_CHANNEL is not set. Cannot send backup.")
    sts = await message.reply_text("⏳ Starting DB backup — this may take a while...")
    try:
        cursor = Media.find({})
        all_files = await cursor.to_list(length=None)
        if not all_files:
            return await sts.edit("⚠️ No files found in the database.")

        # Serialise to JSON (convert umongo Document objects to plain dicts)
        records = []
        for doc in all_files:
            records.append({
                "file_id":   doc.file_id,
                "file_ref":  doc.file_ref,
                "file_name": doc.file_name,
                "file_size": doc.file_size,
                "file_type": doc.file_type,
                "mime_type": doc.mime_type,
                "caption":   doc.caption,
            })

        backup_path = f"db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        await sts.edit(f"✅ Backup ready — <code>{len(records)}</code> files. Sending to log channel...")
        await bot.send_document(
            chat_id=LOG_CHANNEL,
            document=backup_path,
            file_name=backup_path,
            caption=(
                f"🗄️ <b>DB Backup</b>\n"
                f"📅 Date: <code>{datetime.now().strftime('%d %B %Y %H:%M:%S')}</code>\n"
                f"🎬 Total Files: <code>{len(records)}</code>"
            ),
        )
        await sts.edit(f"✅ Backup of <code>{len(records)}</code> files sent to the log channel.")
    except Exception as e:
        logger.exception(e)
        await sts.edit(f"❌ Backup failed: {e}")
    finally:
        try:
            os.remove(backup_path)
        except Exception:
            pass


@Client.on_message(filters.command("restore") & filters.user(ADMINS))
async def restore_cmd(bot, message):
    """Restore DB from a JSON backup file. Reply to the backup .json file and send /restore"""
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply_text(
            "❌ <b>How To Use:</b>\n\n"
            "1. Log channel-ல backup JSON file-ஐ forward பண்ணு (bot PM-ல)\n"
            "2. அந்த file-ஐ reply பண்ணி <code>/restore</code> அனுப்பு"
        )

    doc = message.reply_to_message.document
    if not doc.file_name.endswith(".json"):
        return await message.reply_text("❌ JSON file மட்டும் restore பண்ண முடியும்!")

    sts = await message.reply_text("⏳ Backup file download பண்றோம்...")

    # Download the JSON file
    file_path = await message.reply_to_message.download()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            records = json.load(f)

        if not records:
            return await sts.edit("⚠️ Backup file empty-ஆ இருக்கு!")

        await sts.edit(f"⏳ <code>{len(records)}</code> files restore பண்றோம் — wait பண்ணு...")

        inserted = 0
        skipped = 0

        for rec in records:
            try:
                # Already existing file-ஐ skip பண்ணும் (DuplicateKeyError handle)
                target_cls = Media
                file = target_cls(
                    file_id=rec["file_id"],
                    file_ref=rec.get("file_ref", ""),
                    file_name=rec.get("file_name", ""),
                    file_size=rec.get("file_size", 0),
                    file_type=rec.get("file_type", ""),
                    mime_type=rec.get("mime_type", ""),
                    caption=rec.get("caption", None),
                )
                await file.commit()
                inserted += 1
            except DuplicateKeyError:
                skipped += 1
            except Exception as e:
                skipped += 1
                logger.warning(f"Restore skip: {e}")

        await sts.edit(
            f"✅ <b>Restore Complete!</b>\n\n"
            f"📥 Inserted: <code>{inserted}</code> files\n"
            f"⏭️ Already existed (skipped): <code>{skipped}</code> files\n"
            f"📦 Total in backup: <code>{len(records)}</code> files"
        )

    except Exception as e:
        logger.exception(e)
        await sts.edit(f"❌ Restore failed: {e}")
    finally:
        try:
            os.remove(file_path)
        except Exception:
            pass


@Client.on_message(filters.command("maintenance") & filters.user(ADMINS))
async def maintenance_cmd(bot, message):
    args = message.command
    if len(args) < 2:
        status = "ON" if temp.MAINTENANCE else "OFF"
        return await message.reply_text("Maintenance is currently: " + status + "\nUse /maintenance on or /maintenance off")
    mode = args[1].lower()
    if mode == "on":
        temp.MAINTENANCE = True
        await message.reply_text("Maintenance mode ENABLED. Bot will only respond to admins now.")
    elif mode == "off":
        temp.MAINTENANCE = False
        await message.reply_text("Maintenance mode DISABLED. Bot is now live for all users!")
    else:
        await message.reply_text("Usage: /maintenance on or /maintenance off")


@Client.on_message(filters.command("ban") & filters.user(ADMINS))
async def ban_user_cmd(bot, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /ban user_id reason")
    try:
        user_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("Invalid user ID.")
    reason = " ".join(message.command[2:]) if len(message.command) > 2 else "No reason"
    try:
        await db.ban_user(user_id, reason)
        try:
            user = await bot.get_users(user_id)
            name = user.mention
        except Exception:
            name = str(user_id)
        await message.reply_text("Banned " + name + ". Reason: " + reason)
    except Exception as e:
        await message.reply_text("Error: " + str(e))


@Client.on_message(filters.command("unban") & filters.user(ADMINS))
async def unban_user_cmd(bot, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /unban user_id")
    try:
        user_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("Invalid user ID.")
    try:
        await db.remove_ban(user_id)
        try:
            user = await bot.get_users(user_id)
            name = user.mention
        except Exception:
            name = str(user_id)
        await message.reply_text("Unbanned " + name)
    except Exception as e:
        await message.reply_text("Error: " + str(e))


@Client.on_message(filters.command("request"))
async def request_movie(bot, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /request Movie Name\nExample: /request Pushpa 2 2024")
    movie_name = " ".join(message.command[1:])
    user = message.from_user
    chat = message.chat
    try:
        await db.add_movie_request(user.id, movie_name)
    except Exception as e:
        logger.warning(f"Failed to save movie request for auto-notify: {e}")
    if LOG_CHANNEL:
        try:
            text = "<b>New Movie Request</b>\n\n"
            text += "Movie: <b>" + movie_name + "</b>\n"
            text += "User: " + user.mention + " (<code>" + str(user.id) + "</code>)\n"
            text += "Group: " + (chat.title if chat.type != enums.ChatType.PRIVATE else "Private")
            await bot.send_message(chat_id=LOG_CHANNEL, text=text)
        except Exception:
            pass
        await message.reply_text("Your request for <b>" + movie_name + "</b> has been sent! We will upload it soon. You'll get a DM the moment it's added.")
    else:
        await message.reply_text("Request received for <b>" + movie_name + "</b>! We will try to upload it soon. You'll get a DM the moment it's added.")
