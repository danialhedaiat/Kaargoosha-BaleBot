from telegram import BotCommand, Update, InlineKeyboardButton, InlineKeyboardMarkup

import os

from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

from core.settings import logger

load_dotenv()


class BaleBot():
    def __init__(self):
        logger.info("Init Bale Bot")
        self.app = ApplicationBuilder()
        self.app.base_url(os.getenv("BASE_URL"))
        self.app.token(os.getenv("BOT_TOKEN"))
        self.app = self.app.build()

        self.add_handler()

    def add_handler(self):
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("join", self.join_command))
        self.app.add_handler(CallbackQueryHandler(self.join_command, pattern="join"))
        self.app.add_handler(CallbackQueryHandler(self.join_command, pattern="cancel"))

    def run(self):

        logger.info("Run Bale Bot")
        self.app.run_polling()

    async def set_button_command(self, application):
        await application.bot.set_my_commands([
            BotCommand("start", "شروع"),
            BotCommand("join", "عضویت در میز"),
        ])

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.username

        keyboard = [
            [InlineKeyboardButton("Join", callback_data="join")],
            [InlineKeyboardButton("Cancel", callback_data="cancel")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Choose an option:",
            reply_markup=reply_markup
        )

    async def join_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"update {update}")
        query = update.callback_query
        await query.answer()
        try:
            await update.effective_message.reply_text("joined!")
        except Exception as e:
            logger.error(e)


if __name__ == "__main__":
    app = BaleBot()
    app.run()
    logger.info("Shutdown Bale Bot")
