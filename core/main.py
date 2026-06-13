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

from core.consumer import BotConsumer
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
        self.consumer = BotConsumer(app=self)

        self.add_handler()

    def add_handler(self):
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("join", self.join_command))

        self.app.add_handler(CallbackQueryHandler(self.sign_in_command, pattern="^sign_in$"))
        self.app.add_handler(CallbackQueryHandler(self.sign_up_command, pattern="^sign_up$"))
        self.app.add_handler(CallbackQueryHandler(self.join_command, pattern="^join$"))
        self.app.add_handler(CallbackQueryHandler(self.create_command, pattern="^create$"))
        self.app.add_handler(CallbackQueryHandler(self.start_command, pattern="^start$"))
        self.app.add_handler(CallbackQueryHandler(self.check_admin_menu_permission, pattern="^admin_menu$"))
        self.app.add_handler(CallbackQueryHandler(self.role_settings, pattern="^role_settings$"))
        self.app.add_handler(CallbackQueryHandler(self.create_role, pattern="^createـrole$"))
        self.app.add_handler(CallbackQueryHandler(self.get_roles, pattern="^select_role$"))
        self.app.add_handler(CallbackQueryHandler(self.assign_role, pattern="^assign_role$"))
        self.app.add_handler(CallbackQueryHandler(self.user_role_list, pattern="^list_role$"))
        self.app.add_handler(CallbackQueryHandler(self.delete_user_role, pattern="^delete_role$"))
        self.app.add_handler(
            CallbackQueryHandler(self.selected_delete_user_role, pattern=r"^select_delete_user_role_(\d+)$"))
        self.app.add_handler(CallbackQueryHandler(self.selected_role, pattern=r"^select_role_\d+$"))
        self.app.add_handler(CallbackQueryHandler(self.check_role_permissions, pattern=r"^check_role_permissions_\d+$"))
        self.app.add_handler(CallbackQueryHandler(self.add_role_permission, pattern=r"^add_role_permission_\d+$"))
        self.app.add_handler(
            CallbackQueryHandler(self.revoke_role_permission, pattern=r"^revoke_role_permission_(\d+)$"))
        self.app.add_handler(CallbackQueryHandler(self.delete_role_permission, pattern=r"^delete_role_(\d+)$"))
        self.app.add_handler(
            CallbackQueryHandler(self.add_selected_permission, pattern=r"^add_selected_permission_(\d+)_([A-Z_]+)$"))
        self.app.add_handler(CallbackQueryHandler(self.revoke_selected_permission,
                                                  pattern=r"^revoke_selected_permission_(\d+)_([A-Z_]+)$"))
        self.app.add_handler(CallbackQueryHandler(self.selected_assign_role,
                                                  pattern=r"^select_assign_role_(\d+)$"))
        self.app.add_handler(CallbackQueryHandler(self.personal_menu, pattern="^personal_menu$"))
        self.app.add_handler(CallbackQueryHandler(self.apply_for_loan, pattern="^apply_for_loan$"))
        self.app.add_handler(CallbackQueryHandler(self.loan_duration_selected, pattern=r"^loan_duration_(\d+)$"))
        self.app.add_handler(CallbackQueryHandler(self.loan_confirm, pattern="^loan_confirm$"))
        self.app.add_handler(CallbackQueryHandler(self.loan_cancel, pattern="^loan_cancel$"))
        self.app.add_handler(CallbackQueryHandler(self.loan_approve, pattern=r"^loan_approve_(\d+)$"))
        self.app.add_handler(CallbackQueryHandler(self.loan_reject, pattern=r"^loan_reject_(\d+)$"))
        self.app.add_handler(CallbackQueryHandler(self.loan_client_history, pattern=r"^loan_history_(\d+)_(\d+)$"))
        self.app.add_handler(CallbackQueryHandler(self.loan_history_back, pattern=r"^loan_history_back_(\d+)_(\d+)$"))

        self.app.add_handler(MessageHandler(filters.CONTACT, self.contact_listener))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_message_listener))

    def run(self):
        logger.info("Run Bale Bot")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        self.consumer.start_consuming(loop)

        try:
            loop.run_until_complete(self.app.run_polling())
        finally:
            loop.close()

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            context.user_data["username"] = update.effective_user.username or str(update.effective_user.id)
            context.user_data["chat_id"] = update.effective_chat.id
            context.user_data["phone_number_create_user_flag"] = None
            context.user_data["phone_number_join_user_flag"] = None
            context.user_data["firstname_flag"] = None
            context.user_data["lastname_flag"] = None
            context.user_data["role_name_flag"] = None
            context.user_data["assign_role_flag"] = None
            context.user_data["user_role_list_flag"] = None
            context.user_data["delete_user_role_flag"] = None
            context.user_data["loan_flow"] = None
            context.user_data["loan_amount"] = None
            context.user_data["loan_duration"] = None
            context.user_data["loan_approve_flag"] = None
            context.user_data["loan_reject_flag"] = None

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

            if response is None or "error" in response:
                keyboard = [
                    [InlineKeyboardButton("بازگشت به شروع", callback_data="start")],
                ]

                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.effective_message.reply_text("اکانت شما یافت نشد",
                                                          reply_markup=reply_markup)
                return
            context.user_data["roles"] = response["roles"]
            context.user_data["social_media"] = response["social_media"]
            context.user_data["first_name"] = response["first_name"]
            context.user_data["last_name"] = response["last_name"]
            context.user_data["phone_number"] = response["phone_number"]
            context.user_data["user_id"] = response["id"]
            context.user_data["chat_id"] = update.effective_chat.id

            self.publisher.update_chat_id({
                "user_id": response["id"],
                "chat_id": update.effective_chat.id,
            })

            admin_perm_response = self.publisher.check_admin_menu_permission(context.user_data)
            has_admin_permission = admin_perm_response.get("status") == True

            if has_admin_permission:
                context.bot_data["admin_chat_id"] = update.effective_chat.id

            keyboard = [[InlineKeyboardButton("منوی شخصی", callback_data="personal_menu")]]
            if has_admin_permission:
                keyboard.append([InlineKeyboardButton("منوی ادمین", callback_data="admin_menu")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_message.reply_text(
                f"{context.user_data['first_name']} عزیز به کارگشا خوش آمدی\nلطفا یکی از منو های زیر را انتخاب کن",
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
        try:
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

            elif context.user_data["role_name_flag"] and context.user_data["flow"] == "create_role":
                body = {"name": update.message.text, "requested_by": context.user_data["user_id"]}
                self.publisher.create_role(body=body, callback=self.role_created,
                                           callback_kwargs={"update": update, "context": context})

            elif context.user_data["assign_role_flag"]:
                phone_number = update.message.text

                if not phone_number or not phone_number.isdigit():
                    await update.effective_message.reply_text("لطفا مقدار صحیح وارد کنید")
                    return

                context.chat_data["phone_number"] = phone_number
                await self.select_assign_role(update, context)

            elif context.user_data["user_role_list_flag"]:
                phone_number = update.message.text

                if not phone_number or not phone_number.isdigit():
                    await update.effective_message.reply_text("لطفا مقدار صحیح وارد کنید")
                    return
                context.user_data["user_role_list_flag"] = False
                body = {"phone_number": phone_number, "requested_by": context.user_data["user_id"]}
                self.publisher.get_user_roles(body=body, callback=self.recived_user_roles,
                                              callback_kwargs={"update": update, "context": context})

            elif context.user_data["delete_user_role_flag"]:
                phone_number = update.message.text

                if not phone_number or not phone_number.isdigit():
                    await update.effective_message.reply_text("لطفا مقدار صحیح وارد کنید")
                    return
                context.user_data["delete_user_role_flag"] = False
                context.chat_data["delete_target_phone"] = phone_number
                body = {"phone_number": phone_number, "requested_by": context.user_data["user_id"]}
                self.publisher.get_user_roles(body=body, callback=self.show_user_roles_for_delete,
                                              callback_kwargs={"update": update, "context": context})

            elif context.user_data.get("loan_approve_flag"):
                amount_text = update.message.text.strip()
                if not amount_text.isdigit():
                    await update.effective_message.reply_text("لطفا یک عدد صحیح وارد کنید")
                    return
                loan_id = context.user_data["loan_approve_flag"]
                context.user_data["loan_approve_flag"] = None
                body = {
                    "loan_id": loan_id,
                    "requested_by": context.user_data["user_id"],
                    "amount": int(amount_text),
                }
                self.publisher.approve_loan(
                    body=body,
                    callback=self.after_loan_approve,
                    callback_kwargs={"update": update, "context": context},
                )

            elif context.user_data.get("loan_reject_flag"):
                reason = update.message.text.strip()
                loan_id = context.user_data["loan_reject_flag"]
                context.user_data["loan_reject_flag"] = None
                body = {
                    "loan_id": loan_id,
                    "requested_by": context.user_data["user_id"],
                    "rejection_reason": reason,
                }
                self.publisher.reject_loan(
                    body=body,
                    callback=self.after_loan_reject,
                    callback_kwargs={"update": update, "context": context},
                )

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def check_phone_number_create_user_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                                     response):

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

    async def check_admin_menu_permission(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            await update.effective_message.reply_text("درحال چک کردن دسترسی شما...")
            response = self.publisher.check_admin_menu_permission(context.user_data)
            await self.admin_menu(update, context, response)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, response):
        try:
            if response["status"] == True:
                context.user_data["flow"] = "admin_menu"
                keyboard = [
                    [InlineKeyboardButton("تنظیمات رول", callback_data="role_settings")],
                    [InlineKeyboardButton("بازگشت", callback_data="sign_in")],
                ]

                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.effective_message.reply_text("پلن ادمین",
                                                          reply_markup=reply_markup)
            else:
                keyboard = [
                    [InlineKeyboardButton("بازگشت", callback_data="sign_in")],
                ]

                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.effective_message.reply_text("شما به این منو دسترسی ندارید", reply_markup=reply_markup)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def role_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            query = update.callback_query
            await query.answer()
            keyboard = [
                [InlineKeyboardButton("ساخت رول جدید", callback_data="createـrole")],
                [InlineKeyboardButton("انتخاب رول", callback_data="select_role")],
                [InlineKeyboardButton("لیست رول های کاربر", callback_data="list_role")],
                [InlineKeyboardButton("اضافه کردن رول به کاربر", callback_data="assign_role")],
                [InlineKeyboardButton("حذف کردن رول کاربر", callback_data="delete_role")],
                [InlineKeyboardButton("بازگشت", callback_data="admin_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_message.reply_text("تنظیمات رول", reply_markup=reply_markup)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def personal_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            has_loan_permission = False
            try:
                perm_response = self.publisher.check_loan_create_permission(context.user_data)
                has_loan_permission = perm_response.get("status") == True
            except Exception:
                pass

            keyboard = []
            if has_loan_permission:
                keyboard.append([InlineKeyboardButton("درخواست وام", callback_data="apply_for_loan")])
            keyboard.append([InlineKeyboardButton("بازگشت", callback_data="sign_in")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_message.reply_text("منوی شخصی", reply_markup=reply_markup)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def apply_for_loan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            context.user_data["loan_flow"] = "duration"
            context.user_data["loan_amount"] = None
            context.user_data["loan_duration"] = None
            keyboard = [
                [
                    InlineKeyboardButton("۶ ماه", callback_data="loan_duration_6"),
                    InlineKeyboardButton("۱۲ ماه", callback_data="loan_duration_12"),
                    InlineKeyboardButton("۱۵ ماه", callback_data="loan_duration_15"),
                ],
                [InlineKeyboardButton("انصراف", callback_data="personal_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_message.reply_text(
                "مدت زمان بازپرداخت وام را انتخاب کنید:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def loan_duration_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            query = update.callback_query
            await query.answer()

            match = re.match(r"^loan_duration_(\d+)$", query.data)
            duration = int(match.group(1))

            context.user_data["loan_duration"] = duration
            context.user_data["loan_flow"] = "confirm"

            summary = (
                f"درخواست وام\n"
                f"مدت بازپرداخت: {duration} ماه\n\n"
                f"آیا مطمئن هستید؟"
            )
            keyboard = [
                [
                    InlineKeyboardButton("✅ تایید و ارسال", callback_data="loan_confirm"),
                    InlineKeyboardButton("❌ انصراف", callback_data="loan_cancel"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_message.reply_text(summary, reply_markup=reply_markup)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def loan_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            body = {
                "user_id": context.user_data["user_id"],
                "duration_months": context.user_data["loan_duration"],
                "member_chat_id": context.user_data.get("chat_id"),
            }
            self.publisher.create_loan_request(
                body=body,
                callback=self.loan_request_saved,
                callback_kwargs={"update": update, "context": context}
            )
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def loan_request_saved(self, update: Update, context: ContextTypes.DEFAULT_TYPE, response):
        try:
            context.user_data["loan_flow"] = None
            keyboard = [[InlineKeyboardButton("بازگشت به منوی شخصی", callback_data="personal_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            if "error" in response:
                await update.effective_message.reply_text(
                    f"متاسفانه درخواست ثبت نشد:\n{response['error']}",
                    reply_markup=reply_markup
                )
                return

            await update.effective_message.reply_text(
                "درخواست شما ثبت شد و در انتظار بررسی است ✅",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def loan_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            context.user_data["loan_flow"] = None
            context.user_data["loan_duration"] = None
            keyboard = [[InlineKeyboardButton("بازگشت به منوی شخصی", callback_data="personal_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_message.reply_text("درخواست وام لغو شد.", reply_markup=reply_markup)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def handle_notify_loan_approved(self, data: dict):
        try:
            member_chat_id = data.get("member_chat_id")
            amount = data.get("amount")
            monthly_amount = data.get("monthly_amount")
            first_due_date = data.get("first_due_date")

            text = (
                f"✅ وام شما تایید شد\n"
                f"مبلغ: {amount:,} تومان\n"
                f"قسط ماهانه: {monthly_amount:,} تومان\n"
                f"اولین قسط: {first_due_date}"
            )
            await self.app.bot.send_message(chat_id=member_chat_id, text=text)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def handle_notify_loan_rejected(self, data: dict):
        try:
            member_chat_id = data.get("member_chat_id")
            rejection_reason = data.get("rejection_reason", "")
            text = f"❌ درخواست وام شما رد شد\nدلیل: {rejection_reason}"
            await self.app.bot.send_message(chat_id=member_chat_id, text=text)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def handle_notify_loan_request(self, data: dict):
        try:
            recipients = data.get("recipients", [])
            chat_ids = [
                r["chat_id"] for r in recipients
                if r.get("social_media") == settings.SOCIAL_MEDIA
            ]
            loan_id = data.get("loan_id")
            user_id = data.get("user_id")
            user_name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
            duration_months = data.get("duration_months")

            text = (
                f"درخواست وام جدید:\n"
                f"کاربر: {user_name}\n"
                f"مدت بازپرداخت: {duration_months} ماه\n\n"
                f"لطفا یکی از گزینه های زیر را انتخاب کنید:"
            )
            keyboard = [
                [
                    InlineKeyboardButton("✅ تایید", callback_data=f"loan_approve_{loan_id}"),
                    InlineKeyboardButton("❌ رد کردن", callback_data=f"loan_reject_{loan_id}"),
                ],
                [
                    InlineKeyboardButton("📋 سابقه مشتری", callback_data=f"loan_history_{loan_id}_{user_id}"),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            for chat_id in chat_ids:
                await self.app.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def loan_approve(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            query = update.callback_query
            await query.answer()
            match = re.match(r"^loan_approve_(\d+)$", query.data)
            loan_id = int(match.group(1))
            context.user_data["loan_approve_flag"] = loan_id
            await update.effective_message.reply_text(
                f"درخواست وام شماره {loan_id}\nلطفا مبلغ وام را به تومان وارد کنید:"
            )
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def after_loan_approve(self, update: Update, context: ContextTypes.DEFAULT_TYPE, response):
        try:
            if response is None or "error" in response:
                error_msg = response.get("error", "خطای ناشناخته") if response else "پاسخی دریافت نشد"
                await update.effective_message.reply_text(f"❌ خطا در تایید وام: {error_msg}")
                return
            loan_id = response.get("id")
            amount = response.get("amount")
            await update.effective_message.reply_text(
                f"✅ وام شماره {loan_id} با مبلغ {amount:,} تومان تایید شد"
            )
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def loan_reject(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            query = update.callback_query
            await query.answer()
            match = re.match(r"^loan_reject_(\d+)$", query.data)
            loan_id = int(match.group(1))
            context.user_data["loan_reject_flag"] = loan_id
            await update.effective_message.reply_text(
                f"درخواست وام شماره {loan_id}\nلطفا دلیل رد کردن وام را وارد کنید:"
            )
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def after_loan_reject(self, update: Update, context: ContextTypes.DEFAULT_TYPE, response):
        try:
            if response is None or "error" in response:
                error_msg = response.get("error", "خطای ناشناخته") if response else "پاسخی دریافت نشد"
                await update.effective_message.reply_text(f"❌ خطا در رد وام: {error_msg}")
                return
            await update.effective_message.reply_text("✅ وام رد شد")
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def loan_client_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            query = update.callback_query
            await query.answer()
            match = re.match(r"^loan_history_(\d+)_(\d+)$", query.data)
            loan_id = int(match.group(1))
            user_id = int(match.group(2))
            self.publisher.get_client_history(
                body={"user_id": user_id},
                callback=self.after_loan_client_history,
                callback_kwargs={"update": update, "context": context, "loan_id": loan_id, "user_id": user_id},
            )
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def after_loan_client_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE, response, loan_id: int, user_id: int):
        try:
            if response is None or "error" in response:
                error_msg = response.get("error", "خطای ناشناخته") if response else "پاسخی دریافت نشد"
                await update.effective_message.reply_text(f"❌ خطا در دریافت سابقه: {error_msg}")
                return

            total_loans = response.get("total_loans", 0)
            payment_rate = response.get("payment_rate")
            loans = response.get("loans", [])

            lines = ["📋 سابقه وام مشتری\n"]
            lines.append(f"تعداد کل درخواست‌ها: {total_loans}")
            if payment_rate is not None:
                lines.append(f"نرخ پرداخت به موقع: {payment_rate}%")

            status_map = {"pending": "در انتظار", "approved": "تایید شده", "rejected": "رد شده"}
            for loan in loans:
                status_fa = status_map.get(loan.get("status"), loan.get("status"))
                line = f"\n• وام {loan['id']}: {status_fa}"
                if loan.get("amount"):
                    line += f" | {loan['amount']:,} تومان"
                if loan.get("installments_count"):
                    line += f"\n  اقساط: {loan['paid_count']}/{loan['installments_count']} پرداخت شده"
                    if loan.get("overdue_count"):
                        line += f" | {loan['overdue_count']} معوق"
                if loan.get("rejection_reason"):
                    line += f"\n  دلیل رد: {loan['rejection_reason']}"
                lines.append(line)

            text = "\n".join(lines)
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data=f"loan_history_back_{loan_id}_{user_id}")]]
            await update.effective_message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def loan_history_back(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            query = update.callback_query
            await query.answer()
            match = re.match(r"^loan_history_back_(\d+)_(\d+)$", query.data)
            loan_id = int(match.group(1))
            user_id = int(match.group(2))
            text = (
                f"درخواست وام شماره {loan_id}\n"
                f"لطفا یکی از گزینه های زیر را انتخاب کنید:"
            )
            keyboard = [
                [
                    InlineKeyboardButton("✅ تایید", callback_data=f"loan_approve_{loan_id}"),
                    InlineKeyboardButton("❌ رد کردن", callback_data=f"loan_reject_{loan_id}"),
                ],
                [
                    InlineKeyboardButton("📋 سابقه مشتری", callback_data=f"loan_history_{loan_id}_{user_id}"),
                ],
            ]
            await update.effective_message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def create_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data["flow"] = "create_role"
        context.user_data["role_name_flag"] = True
        await update.effective_message.reply_text("لطفا نام رول جدید را ارسال کنید:")

    async def role_created(self, update: Update, context: ContextTypes.DEFAULT_TYPE, response):
        keyboard = [
            [InlineKeyboardButton("ساخت رول جدید", callback_data="create_role")],
            [InlineKeyboardButton("انتخاب رول", callback_data="select_role")],
            [InlineKeyboardButton("بازگشت", callback_data="admin_menu")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.effective_message.reply_text(
            f"رول جدید شما با نام\n{response["name"]}\n با موفقیت ساخته شد\nدر ادامه یکی از گزینه های زیر را انتخاب کنید",
            reply_markup=reply_markup)

    async def get_roles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            body = {"requested_by": context.user_data["user_id"]}
            response = self.publisher.get_roles(body=body)
            if "error" in response:
                logger.error(response["error"])
                pass
            keyboard = [
                [InlineKeyboardButton(role["name"], callback_data=f"select_role_{role['id']}")] for role in
                response
            ]
            keyboard += [[InlineKeyboardButton("بازگشت", callback_data="admin_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_message.reply_text("لطفا رول مورد نظر خود را انتخاب کنید", reply_markup=reply_markup)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def selected_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            query = update.callback_query
            await query.answer()

            pattern = r"^select_role_(\d+)$"
            match = re.match(pattern, query.data)

            role_id = match.group(1)

            keyboard = [
                [InlineKeyboardButton("مشاهده دسترسی ها", callback_data=f"check_role_permissions_{role_id}")],
                [InlineKeyboardButton("اضافه کردن دسترسی جدید", callback_data=f"add_role_permission_{role_id}")],
                [InlineKeyboardButton("حذف کردن دسترسی", callback_data=f"revoke_role_permission_{role_id}")],
                [InlineKeyboardButton("حذف کردن رول", callback_data=f"delete_role_{role_id}")],
                [InlineKeyboardButton("بازگشت", callback_data="select_role")],
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_message.reply_text(
                f"منو تنظیمات رول",
                reply_markup=reply_markup)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def check_role_permissions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            query = update.callback_query
            await query.answer()

            pattern = r"^check_role_permissions_(\d+)$"
            match = re.match(pattern, query.data)

            role_id = match.group(1)

            body = {"requested_by": context.user_data["user_id"], "role_id": role_id}

            response = self.publisher.get_role_permissions(
                body=body)

            if not response:
                keyboard = [
                    [InlineKeyboardButton("بازگشت", callback_data=f"select_role_{role_id}")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.effective_message.reply_text(f"دسترسی برای این رول پیدا نشد", reply_markup=reply_markup)
                return

            keyboard = [
                [InlineKeyboardButton("بازگشت", callback_data=f"select_role_{role_id}")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            logger.info(response)

            message = f"دسترسی هایی که برای این رول {response[0]["role"]["name"]} پیدا شد به این ترتیب است:\n" + "\n".join(
                permission["codename"]
                for permission in response
            )
            await update.effective_message.reply_text(message, reply_markup=reply_markup)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def add_role_permission(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        pattern = r"^add_role_permission_(\d+)$"
        match = re.match(pattern, query.data)

        role_id = match.group(1)

        body = {"requested_by": context.user_data["user_id"]}

        response = self.publisher.get_all_permissions(body=body)
        keyboard = [
            [InlineKeyboardButton(key, callback_data=f"add_selected_permission_{role_id}_{value}")] for
            key, value in response.items()
        ]
        keyboard += [
            [InlineKeyboardButton("بازگشت", callback_data=f"select_role_{role_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.effective_message.reply_text("دسترسی مورد نظر را انتخاب کنید", reply_markup=reply_markup)

    async def add_selected_permission(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            query = update.callback_query
            await query.answer()

            pattern = r"^add_selected_permission_(\d+)_([A-Z_]+)$"
            match = re.match(pattern, query.data)

            role_id = match.group(1)
            permission = match.group(2)

            body = {"requested_by": context.user_data["user_id"], "role_id": role_id, "codename": permission}

            response = self.publisher.add_role_permission(body=body)

            if "error" in response and response["error"].startswith("(sqlite3.IntegrityError) UNIQUE constraint"):
                keyboard = [
                    [InlineKeyboardButton("بازگشت", callback_data=f"add_role_permission_{role_id}")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.effective_message.reply_text("این دسترسی قبلا یه رول داده شده است",
                                                          reply_markup=reply_markup)
                return

            keyboard = [
                [InlineKeyboardButton("بازگشت", callback_data=f"select_role_{role_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_message.reply_text("دسترسی به رول داده شد", reply_markup=reply_markup)

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def revoke_role_permission(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            query = update.callback_query
            await query.answer()

            pattern = r"^revoke_role_permission_(\d+)$"
            match = re.match(pattern, query.data)

            role_id = match.group(1)

            body = {"requested_by": context.user_data["user_id"], "role_id": role_id}

            response = self.publisher.get_role_permissions(
                body=body)
            keyboard = [
                [InlineKeyboardButton(permission["codename"],
                                      callback_data=f"revoke_selected_permission_{role_id}_{permission["codename"]}")]
                for
                permission in response
            ]
            keyboard += [
                [InlineKeyboardButton("بازگشت", callback_data=f"select_role_{role_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_message.reply_text("دسترسی مورد نظر را انتخاب کنید", reply_markup=reply_markup)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def revoke_selected_permission(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            query = update.callback_query
            await query.answer()

            pattern = r"^revoke_selected_permission_(\d+)_([A-Z_]+)$"
            match = re.match(pattern, query.data)

            role_id = match.group(1)
            permission = match.group(2)

            body = {"requested_by": context.user_data["user_id"], "role_id": role_id, "codename": permission}

            response = self.publisher.revoke_role_permission(body=body)

            if "error" in response:
                keyboard = [
                    [InlineKeyboardButton("بازگشت", callback_data=f"add_role_permission_{role_id}")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.effective_message.reply_text("این دسترسی پیدا نشد",
                                                          reply_markup=reply_markup)
                return

            keyboard = [
                [InlineKeyboardButton("بازگشت", callback_data=f"select_role_{role_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_message.reply_text("دسترسی با موفقیت حذف شد",
                                                      reply_markup=reply_markup)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def delete_role_permission(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            query = update.callback_query
            await query.answer()

            pattern = r"^delete_role_(\d+)$"
            match = re.match(pattern, query.data)

            role_id = match.group(1)

            body = {"requested_by": context.user_data["user_id"], "role_id": role_id}

            response = self.publisher.delete_role(body=body)

            if "error" in response:
                keyboard = [
                    [InlineKeyboardButton("بازگشت", callback_data=f"select_role_{role_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                logger.info(type(response))
                logger.info(response)
                await update.effective_message.reply_text(
                    f"در انجام عملیات با یک مشکل مواجه شدیم به پشتیبانی پیام دهید:\n{response}",
                    reply_markup=reply_markup)
                return

            keyboard = [
                [InlineKeyboardButton("بازگشت", callback_data=f"select_role")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_message.reply_text("رول با موفقیت حذف شد", reply_markup=reply_markup)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def assign_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            context.user_data["assign_role_flag"] = True

            await update.effective_message.reply_text("لطفا شماره تلفن کاربر مورد نظر را ارسال کنید:")

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def select_assign_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            phone_number = context.chat_data["phone_number"]
            body = {"requested_by": context.user_data["user_id"], "phone_number": phone_number}
            response = self.publisher.get_roles(body=body)

            if "error" in response:
                logger.error(response["error"])
                pass
            keyboard = [
                [InlineKeyboardButton(role["name"], callback_data=f"select_assign_role_{role['id']}")] for role in
                response
            ]
            keyboard += [[InlineKeyboardButton("بازگشت", callback_data="admin_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_message.reply_text("لطفا رول مورد نظر خود را انتخاب کنید", reply_markup=reply_markup)

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def selected_assign_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            query = update.callback_query
            await query.answer()

            pattern = r"^select_assign_role_(\d+)$"

            match = re.match(pattern, query.data)

            role_id = match.group(1)

            phone_number = context.chat_data["phone_number"]

            body = {"requested_by": context.user_data["user_id"], "phone_number": phone_number, "role_id": role_id}

            self.publisher.assign_user_role(body=body, callback=self.assigned_role, callback_kwargs={"update": update,
                                                                                                     "context": context})


        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def assigned_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE, response):
        try:
            if "error" in response:
                keyboard = [
                    [InlineKeyboardButton("بازگشت", callback_data=f"assign_role")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.effective_message.reply_text(f"متاسفانه با مشکل مواجه شد:\n{response["error"]}",
                                                          reply_markup=reply_markup)
                return
            keyboard = [
                [InlineKeyboardButton("بازگشت", callback_data=f"admin_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_message.reply_text(
                f"رول با موفقیت به یوزر {response["first_name"]} {response["last_name"]} اضافه شد.\nرول های این کاربر:\n" + "\n".join(
                    role["name"] for role in response["roles"]
                ),
                reply_markup=reply_markup)

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def user_role_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data["user_role_list_flag"] = True

        keyboard = [
            [InlineKeyboardButton("بازگشت", callback_data="admin_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.effective_message.reply_text("برای مشاهده لیست رول ها ابتدا شماره کاربر مورد نظر را وارد نمایید:",
                                                  reply_markup=reply_markup)

    async def recived_user_roles(self, update: Update, context: ContextTypes.DEFAULT_TYPE, response):
        try:
            keyboard = [
                [InlineKeyboardButton("بازگشت", callback_data="admin_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            if not response or "error" in response:
                await update.effective_message.reply_text("کاربری با این شماره یافت نشد", reply_markup=reply_markup)
                return

            if not response.get("roles"):
                await update.effective_message.reply_text("این کاربر هیچ رولی ندارد", reply_markup=reply_markup)
                return

            message = f"رول های کاربر {response["first_name"]} {response["last_name"]}:\n" + "\n".join(
                role["name"] for role in response["roles"]
            )
            await update.effective_message.reply_text(message, reply_markup=reply_markup)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def delete_user_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            context.user_data["delete_user_role_flag"] = True

            keyboard = [
                [InlineKeyboardButton("بازگشت", callback_data="admin_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_message.reply_text(
                "برای حذف رول از کاربر، شماره تلفن کاربر مورد نظر را وارد کنید:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def show_user_roles_for_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE, response):
        try:
            keyboard_back = [
                [InlineKeyboardButton("بازگشت", callback_data="admin_menu")],
            ]
            reply_markup_back = InlineKeyboardMarkup(keyboard_back)

            if not response or "error" in response:
                await update.effective_message.reply_text("کاربری با این شماره یافت نشد",
                                                          reply_markup=reply_markup_back)
                return

            if not response.get("roles"):
                await update.effective_message.reply_text("این کاربر هیچ رولی ندارد", reply_markup=reply_markup_back)
                return

            context.chat_data["delete_target_user_id"] = response["id"]

            keyboard = [
                [InlineKeyboardButton(role["name"], callback_data=f"select_delete_user_role_{role['id']}")]
                for role in response["roles"]
            ]
            keyboard += [[InlineKeyboardButton("بازگشت", callback_data="admin_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_message.reply_text(
                f"رول مورد نظر برای حذف از کاربر {response['first_name']} {response['last_name']} را انتخاب کنید:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def selected_delete_user_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            query = update.callback_query
            await query.answer()

            pattern = r"^select_delete_user_role_(\d+)$"
            match = re.match(pattern, query.data)
            role_id = match.group(1)

            user_id = context.chat_data["delete_target_user_id"]
            body = {"requested_by": context.user_data["user_id"], "user_id": user_id, "role_id": role_id}

            self.publisher.revoke_user_role(body=body, callback=self.user_role_revoked,
                                            callback_kwargs={"update": update, "context": context})
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

    async def user_role_revoked(self, update: Update, context: ContextTypes.DEFAULT_TYPE, response):
        try:
            keyboard = [
                [InlineKeyboardButton("بازگشت", callback_data="admin_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            if "error" in response:
                await update.effective_message.reply_text(
                    f"متاسفانه با مشکل مواجه شدیم:\n{response['error']}",
                    reply_markup=reply_markup
                )
                return

            await update.effective_message.reply_text("رول با موفقیت از این کاربر حذف شد", reply_markup=reply_markup)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)


if __name__ == "__main__":
    app = BaleBot()
    app.run()
    logger.info("Shutdown Bale Bot")
