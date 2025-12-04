import asyncio
import sqlite3
from datetime import datetime
import os
import pytz
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import uvicorn

# === ԿԱՐԳԱՎՈՐՈՒՄՆԵՐ ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8542625753:AAFS4Hd7gNCm8_KbjX-biMAf2HIkN-pApc4")
ADMINS = [int(x) for x in os.environ.get("ADMINS", "6517716621,1105827301").split(",")]
REDIRECT_URL = "https://poputi.am"
BASE_URL = "https://poputi-live.onrender.com"

bot = Bot(token=BOT_TOKEN)
AM_TZ = pytz.timezone("Asia/Yerevan")


def get_armenia_time():
    """Վերադարձնում է Հայաստանի ընթացիկ ժամը ձևաչափով YYYY-MM-DD HH:MM:SS"""
    now_am = datetime.now(AM_TZ)
    return now_am.strftime("%Y-%m-%d %H:%M:%S")


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
    """Գրանցում է հղման սեղմումը և բացում Poputi հավելվածը կամ կայքը"""
    ip = request.client.host
    ua = request.headers.get("user-agent", "unknown").lower()
    ts = get_armenia_time()

    conn = sqlite3.connect("main.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO clicks (uid, ip, ua, timestamp) VALUES (?, ?, ?, ?)", (uid, ip, ua, ts))
    conn.commit()
    conn.close()

    msg = f"🔗 Նոր հղման սեղմում\n🆔 UID: {uid or 'Չկա'}\n🌍 IP: {ip}\n🕒 Ժամանակ՝ {ts}"
    for admin in ADMINS:
        try:
            await bot.send_message(chat_id=admin, text=msg)
        except Exception as e:
            print(f"Can't notify admin {admin}: {e}")

    # === սարքի տեսակն ենք որոշում
    if "android" in ua:
        # Android deep link intent
        deeplink = (
            "intent://open?uid={uid}#Intent;"
            "scheme=poputi;"
            "package=com.poputi.share4car;"
            "S.browser_fallback_url=https://play.google.com/store/apps/details?id=com.poputi.share4car;"
            "end"
        ).format(uid=uid or "0")
        return RedirectResponse(url=deeplink)

    elif "iphone" in ua or "ipad" in ua:
        # iOS Universal Link — redirect + fallback
        deeplink = f"poputi://open?uid={uid or '0'}"
        html = f"""
        <html>
        <head>
            <meta http-equiv="refresh" content="0; url={deeplink}" />
            <script>
                setTimeout(function(){{
                    window.location.href = "https://apps.apple.com/am/app/poputi-am/id6478853444";
                }}, 1500);
            </script>
        </head>
        <body style='font-family:Arial; text-align:center; margin-top:50px;'>
            <h3>Բացում ենք Poputi հավելվածը...</h3>
        </body>
        </html>
        """
        return HTMLResponse(content=html)

    else:
        # Եթե desktop է կամ անճանաչելի սարք՝ բացում է կայքը
        return RedirectResponse(url="https://poputi.am")


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

    # Ծանուցում ադմիններին
    msg = (
        f"👤 Նոր օգտատեր\n"
        f"🆔 ID: {user.id}\n"
        f"👨‍💻 Username: @{user.username}\n"
        f"🕒 Ժամանակ՝ {ts}"
    )
    for admin in ADMINS:
        try:
            await bot.send_message(chat_id=admin, text=msg)
        except Exception as e:
            print(f"Can't notify admin {admin}: {e}")

    # ✅ Հղումը դեպի հավելված / կայք
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
