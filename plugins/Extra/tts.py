import traceback
from asyncio import get_running_loop
from io import BytesIO

from gtts import gTTS
from googletrans import Translator  # ✅ Fixed: Translator was used but never imported
from pyrogram import Client, filters
from pyrogram.types import Message


def convert(text):
    audio = BytesIO()
    translator = Translator()  # ✅ Fixed: instantiate properly
    detected = translator.detect(text)
    lang = detected.lang if detected and detected.lang else "en"
    tts = gTTS(text, lang=lang)
    audio.name = lang + ".mp3"
    tts.write_to_fp(audio)
    audio.seek(0)
    return audio
#this repo created and maintained by @muja_tg18


@Client.on_message(filters.command("tts") & (filters.private | filters.group))
async def text_to_speech(_, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("❌ Reply to a text message to convert it to speech.")
    if not message.reply_to_message.text:
        return await message.reply_text("❌ The replied message has no text.")

    m = await message.reply_text("🔊 Processing...")
    text = message.reply_to_message.text
    try:
        loop = get_running_loop()
        audio = await loop.run_in_executor(None, convert, text)
        await message.reply_audio(audio, title="TTS Audio", performer="Bot TTS")
        await m.delete()
        audio.close()
    except Exception as e:
        await m.edit(f"❌ Error: `{str(e)}`")
        print(traceback.format_exc())
