import random
from pyrogram import Client, filters


# AESTHETIC
def aesthetify(string):
    PRINTABLE_ASCII = range(0x21, 0x7f)
    for c in string:
        c = ord(c)
        if c in PRINTABLE_ASCII:
            c += 0xFF00 - 0x20
        elif c == ord(" "):
            c = 0x3000
        yield chr(c)


@Client.on_message(filters.command(["ae"]) & (filters.private | filters.group))
async def aesthetic(client, message):
    text = "".join(str(e) for e in message.command[1:])
    if not text:
        return await message.reply_text("Usage: `/ae your text`")
    text = "".join(aesthetify(text))
    await message.reply_text(text)


# DART
@Client.on_message(filters.command(["throw", "dart"]) & (filters.private | filters.group))
async def throw_dart(client, message):
    rep_mesg_id = message.id  # ✅ Fixed: .id not .message_id
    if message.reply_to_message:
        rep_mesg_id = message.reply_to_message.id
    await client.send_dice(
        chat_id=message.chat.id,
        emoji="🎯",
        disable_notification=True,
        reply_to_message_id=rep_mesg_id
    )


# DICE
@Client.on_message(filters.command(["roll", "dice"]) & (filters.private | filters.group))
async def roll_dice(client, message):
    rep_mesg_id = message.id  # ✅ Fixed: .id not .message_id
    if message.reply_to_message:
        rep_mesg_id = message.reply_to_message.id
    await client.send_dice(
        chat_id=message.chat.id,
        emoji="🎲",
        disable_notification=True,
        reply_to_message_id=rep_mesg_id
    )


# LUCK / SLOT MACHINE
@Client.on_message(filters.command(["luck", "cownd"]) & (filters.private | filters.group))
async def luck_cownd(client, message):
    rep_mesg_id = message.id  # ✅ Fixed: .id not .message_id
    if message.reply_to_message:
        rep_mesg_id = message.reply_to_message.id
    await client.send_dice(
        chat_id=message.chat.id,
        emoji="🎰",
        disable_notification=True,
        reply_to_message_id=rep_mesg_id
    )


# GOAL / FOOTBALL  ✅ Fixed: renamed from roll_dice to goal_shoot (was duplicate function name)
@Client.on_message(filters.command(["goal", "shoot"]) & (filters.private | filters.group))
async def goal_shoot(client, message):
    rep_mesg_id = message.id  # ✅ Fixed: .id not .message_id
    if message.reply_to_message:
        rep_mesg_id = message.reply_to_message.id
    await client.send_dice(
        chat_id=message.chat.id,
        emoji="⚽",
        disable_notification=True,
        reply_to_message_id=rep_mesg_id
    )


# RANDOM STRINGS
RUN_STRINGS = (
    "A broken heart filled with darkness... Why have you come to remind it?",
    "We have become the lives to be the underwater that we do not know.",
    "You want the bad call... but you need good thunder....",
    "Oh Bloody Grama Virtues!",
    "Sea MUGGie I Am Going to Pay The Bill.",
    "Want with me!",
    "You are not a male chaff!!",
    "I locked it, and the good beach is done by the good beach.",
    "Kindi... Kindi...!",
    "Giving the stems and then showing one and show the ISI Mark",
    "Dayveyeese, Kingfisher... Childe...!.",
    "You have made your father for half of the midnight?",
    "This is the King of our work.",
    "I'm fetts to feed....",
    "Mumak is every Bearby Kachyo...",
    "Oh it moves it.... When we moves it...",
    "The self of carpenter is the virtue of a carpenter.",
    "Why not feel this intelligence in Da Vijaya...!",
    "Where was this time... Save me only....",
    "I know his father's name is Bhavaniami....",
    "Da Dasa...",
    "Uppukam's English Salt Mongo Tree.....",
    "Children..",
    "Your father to Paul....",
    "Car Engine Out Completely.....",
    "This is the eye or magnety...",
    "Before falling in the 4th pegging, I will arrive there.",
    "The drunk rains and wast.... To tell me I love Yo....",
    "No, the Meenaka of Verbapur is not....",
)


@Client.on_message(filters.command("runs") & (filters.private | filters.group))
async def runs(_, message):
    effective_string = random.choice(RUN_STRINGS)
    if message.reply_to_message:
        await message.reply_to_message.reply_text(effective_string)
    else:
        await message.reply_text(effective_string)
