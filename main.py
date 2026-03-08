# =============================
# Main.py - Cleaner Bot
# =============================

import asyncio
import os
import time
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
# START / WELCOME (basic)
# =============================
@dp.message_handler(commands=["start"])
async def start_cmd(msg: types.Message):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("➕ Add me in a group", url="https://t.me/AutoDelete_ccbot?startgroup=true"),
        InlineKeyboardButton("💬 Support", url="https://t.me/CarelessxWorld"),
        InlineKeyboardButton("👤 Owner", url="https://t.me/CarelessxOwner")
    )
    await msg.reply("Hi! I am Cleaner Bot.\nClick buttons to add me in your group.", reply_markup=kb)

# =============================
# CONFIG / CONTROL / TIMING
# =============================
# Example Control / Timing inline buttons handler (simplified)
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
    await msg.reply("⚙ Cleaner Settings", reply_markup=kb)

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
# START BOT
# =============================
async def on_startup(dp):
    asyncio.create_task(cleaner())

if __name__=="__main__":
    executor.start_polling(dp, on_startup=on_startup)
