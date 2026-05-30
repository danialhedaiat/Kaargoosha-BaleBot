import asyncio
import re
import json
import traceback

from telegram import BotCommand, Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, \
    ReplyKeyboardMarkup, ReplyKeyboardRemove

import os

from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, ConversationHandler, \
    MessageHandler, filters

from core.publisher import BotPublisher
from core.settings import logger, settings

load_dotenv()


class BaleBot():
    def __init__(self):
        logger.info("Init Bale Bot")
        self.app = ApplicationBuilder()
        self.app.base_url(settings.BASE_URL)
        self.app.token(settings.BOT_TOKEN)
        self.app = self.app.build()

        self.publisher = BotPublisher()

        self.add_handler()

    def add_handler(self):
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("join", self.join_command))

        self.app.add_handler(CallbackQueryHandler(self.sign_in_command, pattern="sign_in"))
        self.app.add_handler(CallbackQueryHandler(self.sign_up_command, pattern="sign_up"))
        self.app.add_handler(CallbackQueryHandler(self.join_command, pattern="join"))
        self.app.add_handler(CallbackQueryHandler(self.create_command, pattern="create"))
        self.app.add_handler(CallbackQueryHandler(self.start_command, pattern="start"))

        self.app.add_handler(MessageHandler(filters.CONTACT, self.contact_listener))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_message_listener))

    def run(self):
        logger.info("Run Bale Bot")
        self.app.run_polling()

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            context.user_data["username"] = update.effective_user.username
            context.user_data["phone_number_create_user_flag"] = None
            context.user_data["phone_number_join_user_flag"] = None
            context.user_data["firstname_flag"] = None
            context.user_data["lastname_flag"] = None

            keyboard = [
                [InlineKeyboardButton("ورود به حساب کاربری", callback_data="sign_in")],
                [InlineKeyboardButton("ثبت نام در ربات بله", callback_data="sign_up")]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_message.reply_text(
                "به ربات کارگشا خوش امدید\nاگر قبلا در پلتفرم های دیگه ما ثبت نام کرده‌اید کافیست از منو زیر ثبت نام در بله رو انتخاب کنید",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(e)

    async def sign_in_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data["flow"] = "sign_in"
        try:
            self.publisher.get_user_by_username(body=context.user_data,
                                                callback=self.after_sign_in,
                                                callback_kwargs={"update": update, "context": context})

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def after_sign_in(self, update: Update, context: ContextTypes.DEFAULT_TYPE, response):
        try:

            if "error" in response:
                keyboard = [
                    [InlineKeyboardButton("بازگشت به شروع", callback_data="start")],
                ]

                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.effective_message.reply_text("اکانت شما یافت نشد",
                                                          reply_markup=reply_markup)
                return
            context.user_data["role"] = response["role_permission"]
            context.user_data["social_media"] = response["social_media"]
            context.user_data["first_name"] = response["first_name"]
            context.user_data["last_name"] = response["last_name"]
            context.user_data["phone_number"] = response["phone_number"]
            context.user_data["user_id"] = response["id"]
            if context.user_data["phone_number"] == settings.GOD:
                keyboard = [
                    [InlineKeyboardButton("منوی شخصی", callback_data="personal_menu")],
                    [InlineKeyboardButton("منوی ادمین", callback_data="admin_menu")],
                ]

                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.effective_message.reply_text(
                    f"{context.user_data["first_name"]} عزیز به کارگشا خوش آمدی\nلطفا یکی از منو های زیر را انتخاب کن",
                    reply_markup=reply_markup)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def sign_up_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data["flow"] = "sign_up"
        try:
            keyboard = [
                [InlineKeyboardButton("با پلتفرم دیگری ثبت نام کردم", callback_data="join")],
                [InlineKeyboardButton("ثبت نام برای اولین بار", callback_data="create")]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_message.reply_text(
                "اگر قبلا با پلتفرم دیگری در صندوق ما ثبت نام کردید میتوانید از این پلتفرم هم با همان حساب استفاده کنید",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def create_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.callback_query.from_user
        context.user_data["flow"] = "create"
        if user.is_bot:
            return
        try:
            query = update.callback_query
            await query.answer()
            keyboard = [
                [KeyboardButton("ارسال شماره 📱", request_contact=True)]
            ]

            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            await update.effective_message.reply_text(
                "لطفاً شماره خود را ارسال کنید:",
                reply_markup=reply_markup
            )
            context.user_data["phone_number_create_user_flag"] = True
        except Exception as e:
            logger.error(e)

    async def contact_listener(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            phone = update.message.contact.phone_number

            context.user_data["phone_number"] = "0" + phone[-10:]
            if context.user_data["phone_number_create_user_flag"] and context.user_data["flow"] == "create":

                self.publisher.user_phone_number_check(body=context.user_data,
                                                       callback=self.check_phone_number_create_user_handler,
                                                       callback_kwargs={"update": update, "context": context})

            elif context.user_data["phone_number_join_user_flag"] or context.user_data["flow"] == "join":

                self.publisher.user_phone_number_check(body=context.user_data,
                                                       callback=self.check_phone_number_join_user_handler,
                                                       callback_kwargs={"update": update, "context": context})
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def text_message_listener(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        if context.user_data["phone_number_create_user_flag"] and context.user_data["flow"] == " create":
            phone = update.message.text
            context.user_data["phone_number"] = "0" + phone[-10:]

            if not re.fullmatch(r"\+?\d{11}", context.user_data["phone_number"]):
                await update.effective_message.reply_text(
                    "لطفاً شماره معتبر وارد کنید یا از دکمه ارسال شماره استفاده کنید 📱",
                )

            self.publisher.user_phone_number_check(body=context.user_data,
                                                   callback=self.check_phone_number_create_user_handler,
                                                   callback_kwargs={"update": update, "context": context})
            context.user_data["phone_number_create_user_flag"] = False

        elif context.user_data["phone_number_join_user_flag"] or context.user_data["flow"] == "join":
            phone = update.message.text
            context.user_data["phone_number"] = "0" + phone[-10:]

            if not re.fullmatch(r"\+?\d{11}", context.user_data["phone_number"]):
                await update.effective_message.reply_text(
                    "لطفاً شماره معتبر وارد کنید یا از دکمه ارسال شماره استفاده کنید 📱",
                )

            self.publisher.user_phone_number_check(body=context.user_data,
                                                   callback=self.check_phone_number_join_user_handler,
                                                   callback_kwargs={"update": update, "context": context})

        elif context.user_data["firstname_flag"]:
            context.user_data["first_name"] = update.message.text
            context.user_data["firstname_flag"] = False
            context.user_data["lastname_flag"] = True

            await update.message.reply_text("لطفا نام خانوادگی خود را وارد کنید ⬇️")

        elif context.user_data["lastname_flag"]:
            context.user_data["last_name"] = update.message.text
            context.user_data["lastname_flag"] = False
            self.publisher.user_create(body=context.user_data, callback=self.user_created,
                                       callback_kwargs={"update": update, "context": context})

    async def check_phone_number_create_user_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, response):

        msg = await update.message.reply_text("درحال چک کردن شماره تلفن شما", reply_markup=ReplyKeyboardRemove())


        if "error" in response and not response["error"] == "User does not exist":
            keyboard = [
                [InlineKeyboardButton("بازگشت به شروع", callback_data="start")],
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_message.reply_text("حساب با این شماره ساخته شده است",
                                                      reply_markup=reply_markup)
            return

        context.user_data["firstname_flag"] = True

        await update.effective_message.reply_text(
            "لطفا نام کوچک خود را وارد کنید ⬇️",
            reply_markup=ReplyKeyboardRemove()
        )

        context.user_data["phone_number_create_user_flag"] = False

    async def user_created(self, update: Update, context: ContextTypes.DEFAULT_TYPE, response):
        try:
            if "error" in response:
                keyboard = [
                    [InlineKeyboardButton("بازگشت", callback_data="start")],
                ]

                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.effective_message.reply_text("شما در این پلتفرم با شماره تلفن همراه دیگری حساب ساخته اید.",
                                                          reply_markup=reply_markup)
                return

            message = "user created:\n" + "\n".join(
                f"{field}: {response[field]}" for field in response
            )
            await update.message.reply_text(message)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def join_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.callback_query.from_user
        if user.is_bot:
            return
        try:
            context.user_data["sign_in_status"] = "join"
            query = update.callback_query
            await query.answer()
            keyboard = [
                [KeyboardButton("ارسال شماره 📱", request_contact=True)]
            ]

            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            await update.effective_message.reply_text(
                "لطفاً شماره خود را ارسال کنید:",
                reply_markup=reply_markup
            )

            context.user_data["phone_number_join_user_flag"] = True

        except Exception as e:
            logger.error(e)

    async def check_phone_number_join_user_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE, response):

        msg = await update.message.reply_text("درحال چک کردن شماره تلفن شما", reply_markup=ReplyKeyboardRemove())

        if "error" in response and response["error"] == "User does not exist":
            keyboard = [
                [InlineKeyboardButton("بازگشت به شروع", callback_data="start")],
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_message.reply_text(
                "حساب با این شماره پیدا ساخته نشده است.\nگزینه بازگشت را زده و حساب جدید برای خودتان ایجاد کنید",
                reply_markup=reply_markup)
            return

        self.publisher.user_join_from_different_platform(body=context.user_data, callback=self.user_joined,
                                                         callback_kwargs={"update": update, "context": context})

    async def user_joined(self, update: Update, context: ContextTypes.DEFAULT_TYPE, response):
        try:
            if "error" in response:
                keyboard = [
                    [InlineKeyboardButton("بازگشت به شروع", callback_data="start")],
                ]

                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.effective_message.reply_text("شما در این پلتفرم با شماره تلفن همراه دیگری حساب ساخته اید.",
                                                          reply_markup=reply_markup)
                return

            message = "اکانت بله شما با موفقیت به حساب کاربری شما متصل گردید\nحساب کاربری شما:\n" + "\n".join(
                f"{field}: {response[field]}" for field in response
            )
            await update.message.reply_text(message)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)


if __name__ == "__main__":
    app = BaleBot()
    app.run()
    logger.info("Shutdown Bale Bot")
