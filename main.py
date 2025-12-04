import asyncio
import os
import sqlite3
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# === ԿԱՐԳԱՎՈՐՈՒՄՆԵՐ ===
# Token-ը Render-ում պարտադիր դիր ENV-ում որպես BOT_TOKEN
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8542625753:AAFS4Hd7gNCm8_KbjX-biMAf2HIkN-pApc4")

# Ադմինների ID-ները ENV-ում՝ ADMINS="6517716621,1105827301"
ADMINS = [int(x) for x in os.environ.get("ADMINS", "6517716621,1105827301").split(",")]

# Սա հղումն է, որը բոտը կտա user-ին
SHORT_BASE = "https://poputi-live.onrender.com"

# Սարքերից կախված ուղղություններ
ANDROID_URL = "https://play.google.com/store/apps/details?id=poputi.app"
IOS_URL = "https://apps.apple.com/app/idXXXXXXXX"  # TODO: փոխիր իրական iOS App Store լինքով
WEB_URL = "https://poputi.am"

# Գլոբալ bot օբյեկտ՝ redirect-ի ծանուցումների համար
bot = Bot(token=BOT_TOKEN)

# === ՏՎՅԱԼՆԵՐԻ ԲԱԶԱ ===
def init_db():
    """Ստեղծում է visits.db և clicks.db, եթե չկան"""
    for name in ["visits.db", "clicks.db"]:
        conn = sqlite3.connect(name)
        cur = conn.cursor()
        if name == "visits.db":
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS visits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    start_param TEXT,
                    timestamp TEXT
                )
                """
            )
        else:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS clicks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uid TEXT,
                    ip TEXT,
                    ua TEXT,
                    timestamp TEXT
                )
                """
            )
        conn.commit()
        conn.close()


init_db()

# === FASTAPI (redirect մաս) ===
app = FastAPI()


@app.get("/")
async def redirect_user(request: Request, uid: str | None = None):
    """
    Գրանցում է հղման սեղմումը և տանում է Poputi app/store/վեբ՝ սարքից կախված
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
    if "iphone" in ua or "ipad" in ua or "ios" in ua:
        final_url = IOS_URL
    elif "android" in ua:
        final_url = ANDROID_URL
    else:
        final_url = WEB_URL

    # Կարող ես, եթե շատ չի, ծանուցում ուղարկել ադմիններին նաև click-ի մասին
    text = (
        f"🔔 Նոր հղման սեղմում\n"
        f"UID: {uid}\n"
        f"IP: {ip}\n"
        f"UA: {ua}\n"
        f"Time(UTC): {ts}"
    )
    for admin_id in ADMINS:
        try:
            await bot.send_message(chat_id=admin_id, text=text)
        except Exception as e:
            print(f"Can't notify admin {admin_id}: {e}")

    return RedirectResponse(url=final_url)


# === ՕԳՆԱԿԱՆ՝ ծանուցում ադմիններին բոտի կողմից ===
async def notify_admins_from_bot(context: ContextTypes.DEFAULT_TYPE, text: str):
    for admin_id in ADMINS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=text)
        except Exception as e:
            print(f"Can't notify admin {admin_id}: {e}")


# === TELEGRAM ԲՈՏ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start հրաման — գրանցում է user-ին և ծանուցում ադմիններին
    """
    user = update.effective_user
    start_param = context.args[0] if context.args else None

    # Պահպանում ենք visits.db-ում
    conn = sqlite3.connect("visits.db")
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO visits (user_id, username, first_name, last_name, start_param, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user.id,
            user.username,
            user.first_name,
            user.last_name,
            start_param,
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()

    # Ծանուցում ադմիններին բոտի կողմից
    admin_msg = (
        "🟢 Նոր մուտք բոտում\n"
        f"👤 @{user.username or '—'} (ID: {user.id})\n"
        f"Անուն: {user.first_name or ''} {user.last_name or ''}\n"
        f"start_param: {start_param}\n"
        f"Time(UTC): {datetime.utcnow().isoformat()}"
    )
    await notify_admins_from_bot(context, admin_msg)

    # User-ին ուղարկվող հաղորդագրություն
    text = (
        f"Բարև {user.first_name or user.username or 'օգտատեր'} 👋\n"
        f"Հավելվածը բացելու համար սեղմիր 👉 {SHORT_BASE}"
    )
    await update.message.reply_text(text)


async def run_bot():
    """
    Գործարկում է Telegram բոտը async ռեժիմով
    """
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))

    # initialize + start + run_polling համակցված async տարբերակ
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    # պահում ենք, որ process-ը չփակվի
    await asyncio.Event().wait()


# === ԳԼԽԱՎՈՐ ===
if __name__ == "__main__":
    import uvicorn

    async def main():
        # Միաժամանակ բոտը + FastAPI սերվերը
        bot_task = asyncio.create_task(run_bot())
        server_task = asyncio.create_task(
            uvicorn.Server(
                uvicorn.Config(
                    app,
                    host="0.0.0.0",
                    port=int(os.environ.get("PORT", 8000)),
                )
            ).serve()
        )
        await asyncio.gather(bot_task, server_task)

    asyncio.run(main())
