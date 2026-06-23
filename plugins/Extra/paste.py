import os
import json
import requests
from pyrogram import Client, filters

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.104 Safari/537.36",
    "content-type": "application/json",
}


async def p_paste(message, extension=None):
    siteurl = "https://pasty.lus.pm/api/v1/pastes"
    data = {"content": message}
    try:
        response = requests.post(url=siteurl, data=json.dumps(data), headers=headers)
    except Exception as e:
        return {"error": str(e)}
    if response.ok:
        response = response.json()
        purl = (
            f"https://pasty.lus.pm/{response['id']}.{extension}"
            if extension
            else f"https://pasty.lus.pm/{response['id']}.txt"
        )
        return {
            "url": purl,
            "raw": f"https://pasty.lus.pm/{response['id']}/raw",
            "bin": "Pasty",
        }
    return {"error": "Unable to reach pasty.lus.pm"}


@Client.on_message(filters.command(["tgpaste", "pasty", "paste"]) & (filters.private | filters.group))
async def pasty(client, message):
    pablo = await message.reply_text("`Please wait...`")

    message_s = None  # ✅ Fixed: initialize to avoid NameError

    # Priority 1: inline text after command
    if len(message.command) > 1:
        message_s = message.text.split(" ", 1)[1]

    # Priority 2: replied message
    elif message.reply_to_message:
        if message.reply_to_message.text:
            message_s = message.reply_to_message.text
        elif message.reply_to_message.document:
            # Download and read file content
            file = await message.reply_to_message.download()
            try:
                with open(file, "r", encoding="utf-8") as f:
                    message_s = f.read()
            except Exception:
                await pablo.edit("`Could not read the file. Only text files supported.`")
                return
            finally:
                if os.path.exists(file):
                    os.remove(file)
        else:
            await pablo.edit("`Only text and documents are supported.`")
            return
    else:
        # ✅ Fixed: added return so message_s is never undefined
        await pablo.edit("`No input. Reply to a message or use /paste <text>`")
        return

    ext = "py"
    x = await p_paste(message_s, ext)

    if "error" in x:
        await pablo.edit(f"❌ Error: `{x['error']}`")
        return

    p_link = x["url"]
    p_raw = x["raw"]
    pasted = (
        f"**✅ Successfully Pasted to Pasty**\n\n"
        f"**Link:** • [Click here]({p_link})\n\n"
        f"**Raw Link:** • [Click here]({p_raw})"
    )
    await pablo.edit(pasted, disable_web_page_preview=True)
