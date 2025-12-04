import asyncio
import os
from datetime import datetime
from telegram import Bot
import pytz

# === ԿԱՐԳԱՎՈՐՈՒՄՆԵՐ ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8542625753:AAFS4Hd7gNCm8_KbjX-biMAf2HIkN-pApc4")
ADMINS = [int(x) for x in os.environ.get("ADMINS", "6517716621,1105827301").split(",")]
AM_TZ = pytz.timezone("Asia/Yerevan")

def get_arm_time():
    return datetime.now(pytz.utc).astimezone(AM_TZ).strftime("%Y-%m-%d %H:%M:%S")

async def main():
    bot = Bot(token=BOT_TOKEN)
    ts = get_arm_time()

    for admin in ADMINS:
        try:
            # Բերում ենք ադմինի տվյալները՝ username-ի համար
            admin_info = await bot.get_chat(admin)
            username = admin_info.username or "օգտատեր"

            msg = f"Բարև @{username} 👋\nՀավելվածը բացելու համար սեղմիր 👉 https://short.poputi.am"

            await bot.send_message(chat_id=admin, text=msg)
            print(f"✅ Ծանուցումը ուղարկվեց @{username} ({admin})՝ {ts}")
        except Exception as e:
            print(f"⚠️ Չհաջողվեց ուղարկել admin-ին ({admin}): {e}")

if __name__ == "__main__":
    asyncio.run(main())
