import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# 🧩 Ադմինների ID-ներ
ADMIN_IDS = [6517716621, 1105827301]

# 🔐 Քո բոտի Token
BOT_TOKEN = "8542625753:AAFS4Hd7gNCm8_KbjX-biMAf2HIkN-pApc4"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """start հրամանի հիմնական ֆունկցիա"""
    user = update.effective_user
    first_name = user.first_name or ""
    username = user.username or "առանց նիկնեյմի"

    # ✅ Նամակ օգտվողին
    text = f'Բարև {first_name} 👋\n\n' \
           f'Ներբեռնելու համար սեղմիր կոճակը 👇'

    keyboard = [
        [InlineKeyboardButton("Ներբեռնել short.poputi.am", url="https://short.poputi.am")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, reply_markup=reply_markup)

    # 📨 Ծանուցում ադմիններին
    admin_message = (
        f"▶️ Նոր /start սեղմում\n\n"
        f"👤 Անուն: {first_name}\n"
        f"🔗 Username: @{username}\n"
        f"🆔 User ID: {user.id}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=admin_message)
        except Exception as e:
            print(f"❌ Չստացվեց ուղարկել ադմինին {admin_id}: {e}")


def main():
    """Բոտի հիմնական գործարկում"""
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))

    # Render-ի համար (webhook)
    port = int(os.getenv("PORT", "8443"))
    base_url = os.getenv("RENDER_EXTERNAL_URL")

    if base_url:
        webhook_path = f"/{BOT_TOKEN}"
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=BOT_TOKEN,
            webhook_url=f"{base_url}{webhook_path}",
        )
    else:
        # Եթե տեղային ես աշխատացնում՝ polling-ով
        application.run_polling()


if __name__ == "__main__":
    main()
