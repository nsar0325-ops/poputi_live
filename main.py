import asyncio
import sqlite3
from datetime import datetime
import os
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes
)

# === ԿԱՐԳԱՎՈՐՈՒՄՆԵՐ ===
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMINS = [int(x) for x in os.environ.get("ADMINS", "6517716621").split(",")]
SHORT_BASE = "https://short.poputi.am"
bot = Bot(token=BOT_TOKEN)

# === ՏՎՅԱԼՆԵՐԻ ԲԱԶԱ ===
def init_db():
    for name in ["visits.db", "clicks.db"]:
        conn = sqlite3.connect(name)
        cur = conn.cursor()
        if name == "visits.db":
            cur.execute("""
                CREATE TABLE IF NOT EXISTS visits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    start_param TEXT,
                    timestamp TEXT
                )
            """)
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS clicks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uid TEXT,
                    ip TEXT,
                    ua TEXT,
                    timestamp TEXT
                )
            """)
        conn.commit()
        conn.close()

init_db()

# === FASTAPI (redirect մաս) ===
app = FastAPI()

@app.get("/")
async def redirect_user(request: Request, uid: str = None):
    ip = request.client.host
    ua = request.headers.get("user-agent", "unknown")
    ts = datetime.utcnow().isoformat()

    conn = sqlite3.connect("clicks.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO clicks (uid, ip, ua, timestamp) VALUES (?, ?, ?, ?)",
                (uid, ip, ua, ts))
    conn.commit()
    conn.close()

    msg = f"🔔 Նոր հղման սեղմում!\nUser ID: {uid}\nIP: {ip}\nTime: {ts}"
    for admin in ADMINS:
        try:
            await bot.send_message(chat_id=admin, text=msg)
        except Exception as e:
            print("Can't notify admin:", e)

    return RedirectResponse(url="https://play.google.com/store/apps/details?id=poputi.app")


# === TELEGRAM ԲՈՏ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    start_param = context.args[0] if context.args else None

    conn = sqlite3.connect("visits.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO visits (user_id, username, first_name, last_name, start_param, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user.id,
        user.username,
        user.first_name,
        user.last_name,
        start_param,
        datetime.utcnow().isoformat(),
    ))
    conn.commit()
    conn.close()

    text = f"Բարև {user.first_name or user.username or 'օգտատեր'} 👋\nՀավելվածը ներբեռնելու համար սեղմիր 👉 {SHORT_BASE}"
    await update.message.reply_text(text)


async def run_bot():
    app_builder = ApplicationBuilder().token(BOT_TOKEN).build()
    app_builder.add_handler(CommandHandler("start", start))
    await app_builder.initialize()
    await app_builder.start()
    await app_builder.updater.start_polling()
    await asyncio.Event().wait()  # keep running


# === ԳԼԽԱՎՈՐ ===
if __name__ == "__main__":
    import uvicorn
    async def main():
        # Միաժամանակ բոտը + redirect սերվերը
        bot_task = asyncio.create_task(run_bot())
        server_task = asyncio.create_task(uvicorn.Server(
            uvicorn.Config(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
        ).serve())
        await asyncio.gather(bot_task, server_task)

    asyncio.run(main())
