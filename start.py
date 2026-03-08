# =============================
# Main.py - Cleaner Bot + Start.py merge
# =============================

import os
import time
import random
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from motor.motor_asyncio import AsyncIOMotorClient

# =============================
# LOAD ENV
# =============================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
OWNER_ID = int(os.getenv("OWNER_ID"))
LOGGER_GROUP_ID = int(os.getenv("LOGGER_GROUP_ID", -1003748226916))

# =============================
# BOT & DISPATCHER
# =============================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# =============================
# MONGO DB
# =============================
mongo = AsyncIOMotorClient(MONGO_URI)
db = mongo.cleanerbot
groups = db.groups

# =============================
# MEMORY
# =============================
messages = {}
waiting_custom = {}

# =============================
# IMAGES
# =============================
IMG = [
    "https://files.catbox.moe/vqk2m1.jpg",
    "https://files.catbox.moe/9fqgen.jpg",
    "https://files.catbox.moe/et8fz6.jpg",
    "https://files.catbox.moe/ow4v71.jpg",
    "https://files.catbox.moe/nqzk5h.jpg"
]

# =============================
# START / WELCOME MESSAGE
# =============================
STBUTTON = [
    [
        InlineKeyboardButton(
            text="✙ ʌᴅᴅ ϻє ɪη ʏσυʀ ɢʀσυᴘ ✙",
            url=f"https://t.me/AutoDelete_ccbot?startgroup=true",
        ),
    ],
    [
        InlineKeyboardButton(text="⌯ ❍ᴡɴᴇʀ ⌯", url="https://t.me/CarelessxOwner"),
        InlineKeyboardButton(text="⌯ ᴧʙσᴜᴛ ⌯", callback_data="ABOUT"),
    ],
    [
        InlineKeyboardButton(text="⌯ ʜєʟᴘ ᴧηᴅ ᴄσϻϻᴧηᴅs ⌯", callback_data="HELP_MAIN"),
    ],
]

START = f"""**❖ ʜᴇʏ! I am Cleaner Bot 🥳

I can auto delete messages in groups according to timers.

Click 'Help' to see all commands.**"""

HELP = """**❖ This is the help message.

Commands:
/start - Start bot
/config - Configure cleaner
/activate - Activate deletion
/deactivate - Stop deletion**"""

HELP_ABOUT = """**About Cleaner Bot
- Delete messages automatically
- Custom minute/hour timer
- Admin only control
- Powered by: Carelessx**"""

# =============================
# START HANDLER
# =============================
@dp.message_handler(commands=["start"])
async def start_cmd(msg: types.Message):
    kb = InlineKeyboardMarkup(row_width=1)
    for row in STBUTTON:
        kb.row(*row)
    msg_reply = await msg.reply_photo(
        photo=random.choice(IMG),
        caption=START,
        reply_markup=kb
    )
    # Track bot message
    messages.setdefault(msg.chat.id, []).append({
        "id": msg_reply.message_id,
        "user": bot.id,
        "bot": True,
        "time": time.time()
    })

# =============================
# HELP HANDLER
# =============================
@dp.message_handler(commands=["help"])
async def help_cmd(msg: types.Message):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("💬 Support", url="https://t.me/CarelessxWorld")
    )
    msg_reply = await msg.reply_photo(
        photo=random.choice(IMG),
        caption=HELP,
        reply_markup=kb
    )
    messages.setdefault(msg.chat.id, []).append({
        "id": msg_reply.message_id,
        "user": bot.id,
        "bot": True,
        "time": time.time()
    })

# =============================
# CONFIG PANEL
# =============================
@dp.message_handler(commands=["config"])
async def config(msg: types.Message):
    if msg.chat.type not in ["group","supergroup"]: return
    member = await bot.get_chat_member(msg.chat.id,msg.from_user.id)
    if member.status not in ["administrator","creator"]: return
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🧹 Control", callback_data="control"),
        InlineKeyboardButton("⏱ Timing", callback_data="timing")
    )
    msg_reply = await msg.reply("⚙ Cleaner Settings", reply_markup=kb)
    messages.setdefault(msg.chat.id, []).append({
        "id": msg_reply.message_id,
        "user": bot.id,
        "bot": True,
        "time": time.time()
    })

# =============================
# ACTIVATE / DEACTIVATE
# =============================
@dp.message_handler(commands=["activate"])
async def activate(msg: types.Message):
    member = await bot.get_chat_member(msg.chat.id,msg.from_user.id)
    if member.status not in ["administrator","creator"]: return
    await groups.update_one({"chat_id": msg.chat.id}, {"$set": {"enabled": True}}, upsert=True)
    await msg.reply("✅ Cleaner activated.")

@dp.message_handler(commands=["deactivate"])
async def deactivate(msg: types.Message):
    member = await bot.get_chat_member(msg.chat.id,msg.from_user.id)
    if member.status not in ["administrator","creator"]: return
    await groups.update_one({"chat_id": msg.chat.id}, {"$set": {"enabled": False}})
    await msg.reply("❌ Cleaner deactivated.")

# =============================
# MESSAGE TRACKER
# =============================
@dp.message_handler(content_types=types.ContentType.ANY)
async def tracker(msg: types.Message):
    messages.setdefault(msg.chat.id, [])
    messages[msg.chat.id].append({
        "id": msg.message_id,
        "user": msg.from_user.id,
        "bot": msg.from_user.is_bot,
        "time": time.time()
    })

# =============================
# CLEANER ENGINE
# =============================
async def cleaner():
    while True:
        async for group in groups.find({"enabled": True}):
            chat_id = group["chat_id"]
            timer = group.get("timer", 5)
            mode = group.get("mode", "all")
            if chat_id not in messages: continue
            new_list = []
            for m in messages[chat_id]:
                if time.time() - m["time"] >= timer * 60:
                    try:
                        member = await bot.get_chat_member(chat_id, m["user"])
                        delete = False
                        if mode=="admin" and member.status in ["administrator","creator"]: delete=True
                        elif mode=="members" and member.status not in ["administrator","creator"]: delete=True
                        elif mode=="all": delete=True
                        if delete: await bot.delete_message(chat_id, m["id"])
                        else: new_list.append(m)
                    except: new_list.append(m)
                else: new_list.append(m)
            messages[chat_id] = new_list
        await asyncio.sleep(15)

# =============================
# STARTUP
# =============================
async def on_startup(dp):
    asyncio.create_task(cleaner())

# =============================
# RUN BOT
# =============================
if __name__=="__main__":
    executor.start_polling(dp, on_startup=on_startup)
