import asyncio
import sqlite3
from datetime import datetime
import os
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# === ԿԱՐԳԱՎՈՐՈՒՄՆԵՐ ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8542625753:AAFS4Hd7gNCm8_KbjX-biMAf2HIkN-pApc4")
ADMINS = [int(x) for x in os.environ.get("ADMINS", "6517716621,1105827301").split(",")]
SHORT_BASE = "https://poputi-live.onrender.com"

ANDROID_URL = "https://play.google.com/store/apps/details?id=poputi.app"
IOS_URL = "https://apps.apple.com/app/idXXXXXXXX"  # փոխիր քո իրական App Store հղումով
WEB_URL = "https://poputi.am"

# === ՏՎՅԱԼՆԵՐԻ ԲԱԶԱ ===
def init_db():
    for name in ["visits.db", "clicks.db", "installs.db"]:
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
        elif name == "clicks.db":
            cur.execute("""
                CREATE TABLE IF NOT EXISTS clicks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uid TEXT,
                    ip TEXT,
                    ua TEXT,
                    timestamp TEXT
                )
            """)
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS installs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uid TEXT,
                    timestamp TEXT
                )
            """)
        conn.commit()
        conn.close()

init_db()

app = FastAPI()

# === ՀԱՂՈՐԴԱԳՐՈՒԹՅՈՒՆ ԱԴՄԻՆՆԵՐԻՆ ===
async def notify_admins(context, text):
    for admin in ADMINS:
        try:
            await context.bot.send_message(chat_id=admin, text=text)
        except Exception as e:
            print(f"Can't notify admin {admin}: {e}")

# === REDIRECT ===
@app.get("/")
async def redirect_user(request: Request, uid: str = None):
    ua = request.headers.get("user-agent", "").lower()
    ip = request.client.host
    ts = datetime.utcnow().isoformat()

    conn = sqlite3.connect("clicks.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO clicks (uid, ip, ua, timestamp) VALUES (?, ?, ?, ?)", (uid, ip, ua, ts))
    conn.commit()
    conn.close()

    # սարքի ստուգում
    if "iphone" in ua or "ios" in ua or "ipad" in ua:
        final_url = IOS_URL
    elif "android" in ua:
        final_url = ANDROID_URL
    else:
        final_url = WEB_URL

    msg = f"🔔 Նոր հղման սեղմում!\nUser ID: {uid}\nIP: {ip}\nTime: {ts}\nUA: {ua}"
    print(msg)  # Render log-ում երևա

    return RedirectResponse(url=final_url)

# === INSTALL ԾԱՆՈՒՑՈՒՄ (եթե հավելվածից ուղարկվի) ===
@app.post("/installed")
async def installed(request: Request):
    data = await request.json()
    uid = data.get("uid")
    ts = datetime.utcnow().isoformat()

    conn = sqlite3.connect("installs.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO installs (uid, timestamp) VALUES (?, ?)", (uid, ts))
    conn.commit()
    conn.close()

    text = f"✅ Նոր հավելվածի ներբեռնում!\nUser ID: {uid}\nTime: {ts}"
    for admin in ADMINS:
        try:
            from telegram import Bot
            bot = Bot(token=BOT_TOKEN)
            await bot.send_message(chat_id=admin, text=text)
        except Exception as e:
            print("Can't send install notification:", e)

    return JSONResponse({"status": "ok"})

# === TELEGRAM ԲՈՏ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    start_param = context.args[0] if context.args else None

    conn = sqlite3.connect("visits.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO visits (user_id, username, first_name, last_name, start_param, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user.id, user.username, user.first_name, user.last_name, start_param, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

    admin_msg = (
        f"🟢 Նոր մուտք բոտում\n"
        f"👤 @{user.username or '—'} (ID: {user.id})\n"
        f"Անուն: {user.first_name or ''} {user.last_name or ''}\n"
        f"Ժամանակ: {datetime.utcnow().isoformat()}"
    )
    await notify_admins(context, admin_msg)

    await update.message.reply_text(
        f"Բարև {user.first_name or user.username or 'օգտատեր'} 👋\n"
        f"Հավելվածը բացելու համար սեղմիր 👉 {SHORT_BASE}"
    )

async def run_bot():
    app_builder = ApplicationBuilder().token(BOT_TOKEN).build()
    app_builder.add_handler(CommandHandler("start", start))
    await app_builder.initialize()
    await app_builder.start()
    await app_builder.updater.start_polling()
    await asyncio.Event().wait()

# === ԳԼԽԱՎՈՐ ===
if __name__ == "__main__":
    import uvicorn
    async def main():
        bot_task = asyncio.create_task(run_bot())
        server_task = asyncio.create_task(
            uvicorn.Server(
                uvicorn.Config(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
            ).serve()
        )
        await asyncio.gather(bot_task, server_task)

    asyncio.run(main())
