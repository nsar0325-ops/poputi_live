import os
import sqlite3
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# === ԿԱՐԳԱՎՈՐՈՒՄՆԵՐ ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8542625753:AAFS4Hd7gNCm8_KbjX-biMAf2HIkN-pApc4")
ADMINS = [int(x) for x in os.environ.get("ADMINS", "6517716621,1105827301").split(",")]

# Redirect base link
SHORT_BASE = "https://poputi-live.onrender.com"

# Հղումներ ըստ սարքի
ANDROID_URL = "https://play.google.com/store/apps/details?id=poputi.app"
IOS_URL = "https://apps.apple.com/app/idXXXXXXXX"  # փոխիր իրական iOS հղմամբ
WEB_URL = "https://poputi.am"

bot = Bot(token=BOT_TOKEN)
app = FastAPI()

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


# === FASTAPI - Redirect logic ===
@app.get("/")
async def redirect_user(request: Request, uid: str | None = None):
    ua = (request.headers.get("user-agent") or "").lower()
    ip = request.client.host or "unknown"
    ts = datetime.utcnow().isoformat()

    conn = sqlite3.connect("clicks.db")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO clicks (uid, ip, ua, timestamp) VALUES (?, ?, ?, ?)",
        (uid, ip, ua, ts),
    )
    conn.commit()
    conn.close()

    # սարքից կախված URL
    if "android" in ua:
        final_url = ANDROID_URL
    elif "iphone" in ua or "ipad" in ua or "ios" in ua:
        final_url = IOS_URL
    else:
        final_url = WEB_URL

    msg = (
        f"🔔 Նոր հղման սեղմում\n"
        f"UID: {uid}\n"
        f"IP: {ip}\n"
        f"UA: {ua}\n"
        f"Time(UTC): {ts}"
    )
    for admin_id in ADMINS:
        try:
            await bot.send_message(chat_id=admin_id, text=msg)
        except Exception as e:
            print(f"Can't notify admin {admin_id}: {e}")

    return RedirectResponse(url=final_url, status_code=302)


# === TELEGRAM ԲՈՏ (Webhook տարբերակ) ===
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

    admin_msg = (
        f"🟢 Նոր մուտք բոտում\n"
        f"👤 @{user.username or '—'} (ID: {user.id})\n"
        f"Անուն: {user.first_name or ''} {user.last_name or ''}\n"
        f"Time(UTC): {datetime.utcnow().isoformat()}"
    )
    for admin in ADMINS:
        try:
            await context.bot.send_message(chat_id=admin, text=admin_msg)
        except Exception as e:
            print(f"Can't notify admin {admin}: {e}")

    text = (
        f"Բարև {user.first_name or user.username or 'օգտատեր'} 👋\n"
        f"Հավելվածը բացելու համար սեղմիր 👉 {SHORT_BASE}?uid={user.id}"
    )
    await update.message.reply_text(text)


def setup_webhook_app() -> Application:
    """Ստեղծում է Telegram բոտը webhook ռեժիմով"""
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    return application


telegram_app = setup_webhook_app()


@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Telegram-ի update-ները գալիս են այստեղ"""
    body = await request.json()
    update = Update.de_json(body, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}


@app.on_event("startup")
async def on_startup():
    """Միացնում է webhook-ը Telegram-ում"""
    webhook_url = f"{SHORT_BASE}/webhook"
    await bot.set_webhook(webhook_url)
    print(f"✅ Webhook set: {webhook_url}")


# === ԳԼԽԱՎՈՐ ===
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))




