import asyncio
import os
import sqlite3
from datetime import datetime
import pytz
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import uvicorn

# === ԿԱՐԳԱՎՈՐՈՒՄՆԵՐ ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8542625753:AAFS4Hd7gNCm8_KbjX-biMAf2HIkN-pApc4")
ADMINS = [int(x) for x in os.environ.get("ADMINS", "6517716621,1105827301").split(",")]
BASE_URL = "https://short.poputi.am"
AM_TZ = pytz.timezone("Asia/Yerevan")

bot = Bot(token=BOT_TOKEN)

# === ԺԱՄԱՆԱԿ ===
def get_armenia_time():
    return datetime.now(pytz.utc).astimezone(AM_TZ).strftime("%Y-%m-%d %H:%M:%S")

# === ՏՎՅԱԼՆԵՐԻ ԲԱԶԱ ===
def init_db():
    conn = sqlite3.connect("main.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# === FASTAPI APP ===
app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse("""
    <html>
    <head><title>Poputi Live</title></head>
    <body style='text-align:center; font-family:Arial; margin-top:60px;'>
        <h2>✅ Poputi Bot Live է</h2>
        <p>Բոտը հաջողությամբ աշխատում է Render-ի վրա։</p>
    </body>
    </html>
    """)

# === TELEGRAM ԲՈՏ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ts = get_armenia_time()

    # Գրանցում բազայում
    conn = sqlite3.connect("main.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO visits (user_id, username, first_name, last_name, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (user.id, user.username, user.first_name, user.last_name, ts))
    conn.commit()
    conn.close()

    # Ծանուցում ադմիններին
    admin_msg = (
        f"🟢 Նոր մուտք Telegram բոտում\n"
        f"👤 @{user.username or 'առանց username'} (ID: {user.id})\n"
        f"Անուն: {user.first_name or ''} {user.last_name or ''}\n"
        f"🕒 Ժամանակ՝ {ts}"
    )
    for admin in ADMINS:
        try:
            await bot.send_message(chat_id=admin, text=admin_msg)
        except Exception as e:
            print(f"Can't notify admin {admin}: {e}")

    # Պատասխան օգտատիրոջը
    text = (
        f"Բարև {user.first_name or 'օգտատեր'} 👋\n\n"
        f"Հավելվածը բացելու համար սեղմիր 👉 {BASE_URL}"
    )
    await update.message.reply_text(text)

# === ԳԼԽԱՎՈՐ ՖՈՒՆԿՑԻԱ ===
async def run_bot():
    app_builder = ApplicationBuilder().token(BOT_TOKEN).build()
    app_builder.add_handler(CommandHandler("start", start))
    await app_builder.run_polling()

async def main():
    bot_task = asyncio.create_task(run_bot())
    server_task = asyncio.create_task(
        uvicorn.Server(
            uvicorn.Config(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
        ).serve()
    )
    await asyncio.gather(bot_task, server_task)

if __name__ == "__main__":
    asyncio.run(main())


