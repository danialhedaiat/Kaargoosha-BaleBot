"""
Integration tests for authentication flows.
Requires: RabbitMQ + FastAPI running, user TEST_USERNAME present in DB.
"""
import datetime
from telegram import CallbackQuery, Chat, Message, Update, User

from tests.conftest import (
    bot, make_command, make_callback, make_contact, process, sent_texts, _now,
    TEST_TELEGRAM_USER_ID, TEST_CHAT_ID,
)


class TestStartCommand:
    async def test_start_shows_welcome_text(self, bot):
        await process(bot, make_command("start", update_id=1))

        texts = sent_texts(bot)
        assert texts, "Expected at least one message after /start"
        assert any("کارگشا" in t for t in texts)

    async def test_start_sends_sign_in_and_sign_up_buttons(self, bot):
        bot.mock_reply.reset_mock()
        await process(bot, make_command("start", update_id=10))

        bot.mock_reply.assert_called_once()
        kwargs = bot.mock_reply.call_args.kwargs
        markup = kwargs.get("reply_markup")
        assert markup is not None
        button_data = [btn.callback_data for row in markup.inline_keyboard for btn in row]
        assert "sign_in" in button_data
        assert "sign_up" in button_data


class TestSignInFlow:
    async def test_sign_in_found_sends_welcome_menu(self, bot):
        """Happy path: existing user → welcome message + personal/admin menu."""
        bot.mock_reply.reset_mock()
        await process(bot, make_command("start", update_id=20))
        await process(bot, make_callback("sign_in", update_id=21), wait=1.5)

        texts = sent_texts(bot)
        assert any("عزیز" in t or "منو" in t or "خوش" in t for t in texts), (
            f"Expected welcome/menu text, got: {texts}"
        )

    async def test_sign_in_not_found_shows_error(self, bot):
        """Unknown username → 'account not found' message."""
        unknown_id = 777666555
        user = User(id=unknown_id, first_name="Ghost", is_bot=False, username="nobody_xyz_abc")
        chat = Chat(id=unknown_id, type=Chat.PRIVATE)

        start_msg = Message(message_id=30, date=_now(), chat=chat, from_user=user, text="/start")
        start_upd = Update(update_id=30, message=start_msg)

        from telegram import MessageEntity
        start_msg2 = Message(
            message_id=30, date=_now(), chat=chat, from_user=user, text="/start",
            entities=(MessageEntity(type=MessageEntity.BOT_COMMAND, offset=0, length=6),),
        )
        start_upd2 = Update(update_id=30, message=start_msg2)

        cb_msg = Message(message_id=31, date=_now(), chat=chat, from_user=user)
        cb = CallbackQuery(id="31", from_user=user, chat_instance=str(unknown_id), data="sign_in", message=cb_msg)
        sign_in_upd = Update(update_id=31, callback_query=cb)

        bot.mock_reply.reset_mock()
        await process(bot, start_upd2)
        await process(bot, sign_in_upd, wait=1.5)

        texts = sent_texts(bot)
        assert any("یافت نشد" in t for t in texts), (
            f"Expected 'not found' message, got: {texts}"
        )


class TestSignUpFlow:
    async def test_sign_up_shows_platform_options(self, bot):
        bot.mock_reply.reset_mock()
        await process(bot, make_command("start", update_id=40))
        await process(bot, make_callback("sign_up", update_id=41))

        texts = sent_texts(bot)
        assert any("ثبت نام" in t or "پلتفرم" in t for t in texts)

    async def test_create_new_account_asks_for_phone(self, bot):
        bot.mock_reply.reset_mock()
        await process(bot, make_command("start", update_id=50))
        await process(bot, make_callback("sign_up", update_id=51))
        await process(bot, make_callback("create", update_id=52))

        texts = sent_texts(bot)
        assert any("شماره" in t for t in texts)