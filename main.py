import asyncio
import os
import pytz
import sqlite3
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from telegram import Bot

# === ԿԱՐԳԱՎՈՐՈՒՄՆԵՐ ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8542625753:AAFS4Hd7gNCm8_KbjX-biMAf2HIkN-pApc4")
ADMINS = [int(x) for x in os.environ.get("ADMINS", "6517716621,1105827301").split(",")]
BASE_URL = "https://short.poputi.am"
AM_TZ = pytz.timezone("Asia/Yerevan")

bot = Bot(token=BOT_TOKEN)

def get_time():
    return datetime.now(pytz.utc).astimezone(AM_TZ).strftime("%Y-%m-%d %H:%M:%S")

# === ՏՎՅԱԼՆԵՐԻ ԲԱԶԱ ===
def init_db():
    conn = sqlite3.connect("clicks.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT,
            username TEXT,
            ip TEXT,
            ua TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# === FASTAPI ===
app = FastAPI()

@app.get("/")
async def handle_click(request: Request, uid: str = None, username: str = None):
    """Գրանցում է սեղմումը և ուղարկում է ծանուցում ադմինին"""
    ip = request.client.host
    ua = request.headers.get("user-agent", "")
    ts = get_time()

    conn = sqlite3.connect("clicks.db")
    c = conn.cursor()
    c.execute("INSERT INTO clicks (uid, username, ip, ua, timestamp) VALUES (?, ?, ?, ?, ?)",
              (uid, username, ip, ua, ts))
    conn.commit()
    conn.close()

    user_text = f"@{username}" if username else f"ID {uid or 'անհայտ'}"
    msg = f"🔔 Նոր սեղմում!\n👤 {user_text}\n🌍 IP: {ip}\n🕒 Ժամանակ՝ {ts}"

    # ուղարկում ենք ադմինին մեկ անգամ
    for admin in ADMINS:
        try:
            await bot.send_message(chat_id=admin, text=msg)
        except Exception as e:
            print(f"Can't notify admin {admin}: {e}")

    # վերադարձնում ենք redirect էջ
    html = f"""
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="text-align:center; font-family:Arial; margin-top:60px;">
        <h2>Բացում ենք Poputi հավելվածը...</h2>
        <p>Եթե ավտոմատ չբացվի, սեղմիր <a href="https://poputi.am">այստեղ</a>.</p>
        <script>
            setTimeout(() => {{
                window.location = "https://poputi.am";
            }}, 1000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


# === ԳԼԽԱՎՈՐ ===
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🌐 Server running on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

