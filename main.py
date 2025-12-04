import os
import sqlite3
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# === ԿԱՐԳԱՎՈՐՈՒՄՆԵՐ ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8542625753:AAFS4Hd7gNCm8_KbjX-biMAf2HIkN-pApc4")  # այստեղ դիր քո բոտի token-ը
ADMINS = [int(x) for x in os.environ.get("ADMINS", "6517716621,1105827301").split(",")]
SHORT_BASE = "https://poputi-live.onrender.com"

# ✅ ԱՅՍԵՐԸ փոխիր իրական հղումներով
ANDROID_URL = "https://play.google.com/store/apps/details?id=com.poputi.passenger"
IOS_URL = "https://apps.apple.com/am/app/poputi/id654321987"
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


# === REDIRECT ՄԱՍ ===
@app.get("/")
async def redirect_user(request: Request, uid: str = None):
    ua = (request.headers.get("user-agent") or "").lower()
    ip = request.client.host or "unknown"
    ts = datetime.utcnow().isoformat()

    # պահում ենք click-ը բազայում
    conn = sqlite3.connect("clicks.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO clicks (uid, ip, ua, timestamp) VALUES (?, ?, ?, ?)",
                (uid, ip, ua, ts))
    conn.commit()
    conn.close()

    # սարքի ստուգում
    if "android" in ua:
        final_url = ANDROID_URL
    elif "iphone" in ua or "ipad" in ua:
        final_url = IOS_URL
    else:
        final_url = WEB_URL

    # ծանուցում ադմիններին
    msg = f"🔔 Նոր հղման սեղմում\nUID: {uid}\nIP: {ip}\nTime: {ts}"
    for admin_id in ADMINS:
        try:
            await bot.send_message(chat_id=admin_id, text=msg)
        except Exception:
            pass

    return RedirectResponse(url=final_url)


# === ԲՈՏԻ ՄԱՍ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # պահպանում ենք բազայում
    conn = sqlite3.connect("visits.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO visits (user_id, username, first_name, last_name, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (user.id, user.username, user.first_name, user.last_name, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

    # ադմինին ծանուցում
    for admin_id in ADMINS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"🟢 Նոր user մուտք գործեց բոտ\n@{user.username or '—'} (ID: {user.id})"
            )
        except Exception:
            pass

    # ուղարկում ենք հղումը
    link = f"{SHORT_BASE}?uid={user.id}"
    await update.message.reply_text(
        f"Բարև {user.first_name or user.username or 'օգտատեր'} 👋\n"
        f"Հավելվածը ներբեռնելու կամ բացելու համար սեղմիր 👉 {link}"
    )


# === ԳԼԽԱՎՈՐ ===
def main():
    import uvicorn
    app_tg = ApplicationBuilder().token(BOT_TOKEN).build()
    app_tg.add_handler(CommandHandler("start", start))

    # asyncio չօգտագործող պարզ տարբերակ
    from threading import Thread

    def run_tg():
        app_tg.run_polling()

    Thread(target=run_tg).start()
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))


if __name__ == "__main__":
    main()





