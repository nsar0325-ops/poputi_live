import asyncio
import sqlite3
from datetime import datetime
import os
import pytz
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import uvicorn

# === ԿԱՐԳԱՎՈՐՈՒՄՆԵՐ ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8542625753:AAFS4Hd7gNCm8_KbjX-biMAf2HIkN-pApc4")
ADMINS = [int(x) for x in os.environ.get("ADMINS", "6517716621,1105827301").split(",")]
BASE_URL = "https://poputi-live.onrender.com"

bot = Bot(token=BOT_TOKEN)
AM_TZ = pytz.timezone("Asia/Yerevan")

def get_armenia_time():
    """Բերում է Հայաստանի ժամային գոտու ընթացիկ ժամանակը"""
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

# === FASTAPI APP ===
app = FastAPI()

@app.get("/")
async def redirect_user(request: Request, uid: str = None):
    """Գրանցում է հղման սեղմումը և բացում Poputi հավելվածը կամ store-ը"""
    ip = request.client.host
    ua = request.headers.get("user-agent", "").lower()
    ts = get_armenia_time()

    # Բազայում պահպանում ենք սեղմումը
    conn = sqlite3.connect("main.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO clicks (uid, ip, ua, timestamp) VALUES (?, ?, ?, ?)", (uid, ip, ua, ts))
    conn.commit()
    conn.close()

    msg = f"🔔 Նոր հղման սեղմում!\n🆔 User ID: {uid or 'Չկա'}\n🌍 IP: {ip}\n🕒 Ժամանակ՝ {ts}"
    for admin in ADMINS:
        try:
            await bot.send_message(chat_id=admin, text=msg)
        except Exception as e:
            print(f"Can't notify admin {admin}: {e}")

    # Device detection
    if "android" in ua:
        app_link = "poputi://open"
        fallback = "https://play.google.com/store/apps/details?id=com.poputi.share4car"
    elif "iphone" in ua or "ipad" in ua:
        app_link = "poputi://open"
        fallback = "https://apps.apple.com/am/app/poputi-am/id6478853444"
    else:
        app_link = "https://poputi.am"
        fallback = "https://poputi.am"

    # HTML պատասխան՝ բացելու փորձ հավելվածը
    html = f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Poputi</title>
        <script>
            function openApp() {{
                window.location = "{app_link}?uid={uid or '0'}";
                setTimeout(function() {{
                    window.location = "{fallback}";
                }}, 1500);
            }}
            window.onload = openApp;
        </script>
    </head>
    <body style="text-align:center; font-family:Arial; margin-top:60px;">
        <h2>Բացում ենք Poputi հավելվածը...</h2>
        <p>Եթե ավտոմատ չբացվի, սեղմիր <a href="{fallback}">այստեղ</a>.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


# === TELEGRAM ԲՈՏ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Գրանցում է օգտատիրոջ մուտքը և ուղարկում է հղումը"""
    user = update.effective_user
    ts = get_armenia_time()

    conn = sqlite3.connect("main.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO visits (user_id, username, first_name, last_name, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (user.id, user.username, user.first_name, user.last_name, ts))
    conn.commit()
    conn.close()

    msg = (
        f"🟢 Նոր մուտք Telegram բոտում\n"
        f"👤 @{user.username or 'առանց username'} (ID: {user.id})\n"
        f"Անուն: {user.first_name or ''} {user.last_name or ''}\n"
        f"🕒 Ժամանակ՝ {ts}"
    )
    for admin in ADMINS:
        try:
            await bot.send_message(chat_id=admin, text=msg)
        except Exception as e:
            print(f"Can't notify admin {admin}: {e}")

    text = (
        f"Բարև {user.first_name or user.username or 'օգտատեր'} 👋\n\n"
        f"Poputi հավելվածը բացելու համար սեղմիր 👉 {BASE_URL}?uid={user.id}"
    )
    await update.message.reply_text(text)


# === ԳԼԽԱՎՈՐ ===
async def run_bot():
    app_builder = ApplicationBuilder().token(BOT_TOKEN).build()
    app_builder.add_handler(CommandHandler("start", start))
    await app_builder.run_polling(close_loop=False)

if __name__ == "__main__":
    async def main():
        bot_task = asyncio.create_task(run_bot())
        server_task = asyncio.create_task(
            uvicorn.Server(
                uvicorn.Config(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
            ).serve()
        )
        await asyncio.gather(bot_task, server_task)
    asyncio.run(main())
