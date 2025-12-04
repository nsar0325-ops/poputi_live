import asyncio
import os
import sqlite3
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# === ԿԱՐԳԱՎՈՐՈՒՄՆԵՐ ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8542625753:AAFS4Hd7gNCm8_KbjX-biMAf2HIkN-pApc4")
ADMINS = [int(x) for x in os.environ.get("ADMINS", "6517716621,1105827301").split(",")]

# Լինքը, որը բոտը կտա (Redirect-ը գնում է հենց այս սերվերին)
SHORT_BASE = "https://poputi-live.onrender.com"

# Բացման ուղղությունները ըստ սարքի
ANDROID_URL = "https://play.google.com/store/apps/details?id=poputi.app"
IOS_URL = "https://apps.apple.com/app/idXXXXXXXX"  # Փոխիր իրական iOS հղմամբ
WEB_URL = "https://poputi.am"

bot = Bot(token=BOT_TOKEN)

# === ՏՎՅԱԼՆԵՐԻ ԲԱԶԱ ===
def init_db():
    """Ստեղծում է SQLite բազաներ visits.db և clicks.db"""
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

# === FASTAPI Redirect սերվեր ===
app = FastAPI()


@app.get("/")
async def redirect_user(request: Request, uid: str | None = None):
    """
    Գրանցում է հղման սեղմումը և տանում է ըստ սարքի՝
    Android → Play Market
    iOS → App Store
    Այլ → Poputi.am
    """
    ua = (request.headers.get("user-agent") or "").lower()
    ip = request.client.host or "unknown"
    ts = datetime.utcnow().isoformat()

    # Գրանցում ենք click-ը
    conn = sqlite3.connect("clicks.db")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO clicks (uid, ip, ua, timestamp) VALUES (?, ?, ?, ?)",
        (uid, ip, ua, ts),
    )
    conn.commit()
    conn.close()

    # Ընտրում ենք ուր տանել user-ին
    if "android" in ua:
        final_url = ANDROID_URL
    elif "iphone" in ua or "ipad" in ua or "ios" in ua:
        final_url = IOS_URL
    else:
        final_url = WEB_URL

    # Տպում ենք Render logs-ում հարմար debug-ի համար
    print(f"[Redirect] {ip} → {final_url}")

    # Ծանուցում ադմիններին Telegram-ով
    msg = (
        f"🔔 Նոր հղման սեղմում\n"
        f"UID: {uid}\n"
        f"IP: {ip}\n"
        f"UA: {ua}\n"
        f"Time(UTC): {ts}"
    )
    for admin in ADMINS:
        try:
            await bot.send_message(chat_id=admin, text=msg)
        except Exception as e:
            print(f"Can't notify admin {admin}: {e}")

    return RedirectResponse(url=final_url, status_code=302)


# === ՕԳՆԱԿԱՆ՝ ծանուցում ադմիններին բոտի կողմից ===
async def notify_admins(context: ContextTypes.DEFAULT_TYPE, text: str):
    for admin in ADMINS:
        try:
            await context.bot.send_message(chat_id=admin, text=text)
        except Exception as e:
            print(f"Can't notify admin {admin}: {e}")


# === TELEGRAM ԲՈՏ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start հրաման՝ պահպանում է user-ին բազայում, ծանուցում ադմիններին
    """
    user = update.effective_user
    start_param = context.args[0] if context.args else None

    # Պահպանում ենք visits.db-ում
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

    # Ծանուցում ադմիններին
    admin_msg = (
        f"🟢 Նոր մուտք բոտում\n"
        f"👤 @{user.username or '—'} (ID: {user.id})\n"
        f"Անուն: {user.first_name or ''} {user.last_name or ''}\n"
        f"Time(UTC): {datetime.utcnow().isoformat()}"
    )
    await notify_admins(context, admin_msg)

    # User-ին հաղորդագրություն
    text = (
        f"Բարև {user.first_name or user.username or 'օգտատեր'} 👋\n"
        f"Հավելվածը բացելու համար սեղմիր 👉 {SHORT_BASE}?uid={user.id}"
    )
    await update.message.reply_text(text)


async def run_bot():
    """
    Գործարկում է Telegram բոտը async ռեժիմով
    """
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await asyncio.Event().wait()


# === ԳԼԽԱՎՈՐ ===
if __name__ == "__main__":
    import uvicorn

    async def main():
        # Միաժամանակ գործարկում ենք բոտը + redirect սերվերը
        bot_task = asyncio.create_task(run_bot())
        server_task = asyncio.create_task(
            uvicorn.Server(
                uvicorn.Config(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
            ).serve()
        )
        await asyncio.gather(bot_task, server_task)

    asyncio.run(main())



