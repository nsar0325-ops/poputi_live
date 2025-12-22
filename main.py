import os
import logging
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes



load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN չկա (.env ֆայլում ավելացրու)")

ADMIN_IDS = [6517716621, 1105827301]

DOWNLOAD_URL = "https://short.poputi.am"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message

    first_name = user.first_name or "ընկեր"
    username = user.username

   
    text = (
        f"Բարև {first_name} 👋\n\n"
        f"Ներբեռնելու համար սեղմիր կոճակը 👇"
    )

    keyboard = [
        [InlineKeyboardButton("Ներբեռնել short.poputi.am", url=DOWNLOAD_URL)]
    ]

    await message.reply_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


    username_text = f"@{username}" if username else "չկա"

    admin_text = (
        "▶️ Նոր /start\n\n"
        f"👤 Անուն: {first_name}\n"
        f"🔗 Username: {username_text}\n"
        f"🆔 User ID: {user.id}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=admin_text)
        except Exception as e:
            logger.error(f"Չստացվեց ուղարկել ադմինին {admin_id}: {e}")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "🤖 Հրամաններ\n\n"
        "/start — սկսել\n"
        "/help — օգնություն"
    )



def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))

    logger.info("Bot started (polling)")
    app.run_polling()


if __name__ == "__main__":
    main()
