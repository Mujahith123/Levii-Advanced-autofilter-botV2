import traceback
from asyncio import get_running_loop

import requests
from googletrans import Translator, LANGUAGES
from pyrogram import Client, filters
from pyrogram.types import Message

# Reverse lookup so people can type the language name instead of the code,
# e.g. "/translate spanish hello" works the same as "/translate es hello".
_NAME_TO_CODE = {name.lower(): code for code, name in LANGUAGES.items()}

# A few common aliases / casual spellings that don't match the googletrans
# language names exactly.
_ALIASES = {
    "chinese": "zh-cn",
    "mandarin": "zh-cn",
    "farsi": "fa",
    "burmese": "my",
    "filipino": "tl",
    "tagalog": "tl",
    "myanmar": "my",
}


def resolve_lang(raw: str):
    """Turn user input like 'es', 'ES', 'Spanish', or 'spanish' into a
    valid googletrans language code. Returns None if it can't be resolved."""
    key = raw.strip().lower()
    if key in LANGUAGES:
        return key
    if key in _ALIASES:
        return _ALIASES[key]
    if key in _NAME_TO_CODE:
        return _NAME_TO_CODE[key]
    # Handle codes like "zh_cn" or "zh CN" typed with the wrong separator
    normalized = key.replace("_", "-").replace(" ", "-")
    if normalized in LANGUAGES:
        return normalized
    return None


def _translate_sync(text: str, dest: str):
    """Runs in a thread executor since googletrans 4.0.0rc1 makes a
    blocking HTTP call under the hood."""
    translator = Translator()
    result = translator.translate(text, dest=dest)
    return result.text, result.src


def _translate_fallback(text: str, dest: str):
    """Free, key-free REST fallback used only if googletrans itself fails
    (the unofficial Google endpoint it wraps occasionally rate-limits or
    blocks server IPs). Uses the same public translate.googleapis.com
    endpoint that many lightweight translate tools rely on."""
    try:
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": "auto",
                "tl": dest,
                "dt": "t",
                "q": text,
            },
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            translated = "".join(chunk[0] for chunk in data[0] if chunk[0])
            detected_src = data[2] if len(data) > 2 else "auto"
            return translated, detected_src
    except Exception:
        pass
    return None, None


def do_translate(text: str, dest: str):
    try:
        translated, src = _translate_sync(text, dest)
        if translated:
            return translated, src, None
    except Exception:
        print(traceback.format_exc())
    translated, src = _translate_fallback(text, dest)
    if translated:
        return translated, src, None
    return None, None, "Translation service is unavailable right now. Try again in a bit."


@Client.on_message(filters.command(["translate", "tr"]) & (filters.private | filters.group))
async def translate_cmd(client, message: Message):
    args = message.text.split(None, 2)  # ["/translate", "<lang>", "<text>"]

    lang_code = None
    text = None

    if message.reply_to_message and (message.reply_to_message.text or message.reply_to_message.caption):
        # /translate <lang>  (as a reply to the message to translate)
        if len(args) >= 2:
            lang_code = resolve_lang(args[1])
        text = message.reply_to_message.text or message.reply_to_message.caption
    else:
        # /translate <lang> <text>
        if len(args) < 3:
            return await message.reply_text(
                "❌ **Usage:**\n"
                "• `/translate <lang> <text>` — e.g. `/translate es Hello there`\n"
                "• Reply to a message with `/translate <lang>` — e.g. `/translate fr`\n\n"
                "You can use a language code (`es`, `fr`, `hi`, `ja`...) or the full "
                "name (`spanish`, `french`, `hindi`...). Works in groups and DMs.",
                quote=True
            )
        lang_code = resolve_lang(args[1])
        text = args[2]

    if not lang_code:
        return await message.reply_text(
            f"❌ Unknown language: `{args[1] if len(args) > 1 else ''}`\n\n"
            "Use a language code (`es`, `fr`, `hi`, `ta`...) or full name "
            "(`spanish`, `french`, `hindi`, `tamil`...).",
            quote=True
        )

    if not text or not text.strip():
        return await message.reply_text("❌ No text found to translate.", quote=True)

    m = await message.reply_text("🌐 **Translating...**", quote=True)

    try:
        loop = get_running_loop()
        translated, src, error = await loop.run_in_executor(None, do_translate, text, lang_code)
    except Exception as e:
        print(traceback.format_exc())
        return await m.edit(f"❌ **Translation failed:** `{str(e)}`")

    if error or not translated:
        return await m.edit(f"❌ **Translation failed:** {error}")

    src_name = LANGUAGES.get((src or "").lower(), src or "auto").title()
    dest_name = LANGUAGES.get(lang_code, lang_code).title()

    out = (
        f"🌐 **Translated** ({src_name} → {dest_name})\n\n"
        f"{translated}"
    )
    await m.edit(out)