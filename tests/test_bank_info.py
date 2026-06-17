"""
Integration tests for the bank info flow (KAA-44).
Requires: RabbitMQ + FastAPI running, user TEST_USERNAME present in DB.
"""
from tests.conftest import (
    bot, make_command, make_callback, make_text, process, sent_texts,
)


async def _sign_in(bot, base_id: int = 0):
    await process(bot, make_command("start", update_id=base_id + 1))
    await process(bot, make_callback("sign_in", update_id=base_id + 2), wait=1.5)


def _all_button_datas(bale_bot) -> set:
    """Collect every callback_data from all inline keyboard buttons sent so far."""
    datas = set()
    for c in bale_bot.mock_reply.call_args_list:
        markup = c.kwargs.get("reply_markup")
        if markup and hasattr(markup, "inline_keyboard"):
            for row in markup.inline_keyboard:
                for btn in row:
                    datas.add(btn.callback_data)
    return datas


class TestBankInfoMenu:
    async def test_personal_menu_contains_bank_info_button(self, bot):
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=700)
        await process(bot, make_callback("personal_menu", update_id=703))

        assert "bank_info" in _all_button_datas(bot), (
            "Expected 'اطلاعات بانکی' (bank_info) button in personal menu"
        )

    async def test_bank_info_menu_shows_view_and_update_buttons(self, bot):
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=710)
        await process(bot, make_callback("personal_menu", update_id=713))
        await process(bot, make_callback("bank_info", update_id=714))

        buttons = _all_button_datas(bot)
        assert "bank_info_view" in buttons
        assert "bank_info_update" in buttons

    async def test_bank_info_update_menu_shows_card_and_iban_buttons(self, bot):
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=720)
        await process(bot, make_callback("personal_menu", update_id=723))
        await process(bot, make_callback("bank_info", update_id=724))
        await process(bot, make_callback("bank_info_update", update_id=725))

        buttons = _all_button_datas(bot)
        assert "bank_info_update_card" in buttons
        assert "bank_info_update_iban" in buttons


class TestBankInfoView:
    async def test_bank_info_view_returns_response(self, bot):
        """Viewing bank info returns either current info or 'not registered' message."""
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=730)
        await process(bot, make_callback("personal_menu", update_id=733))
        await process(bot, make_callback("bank_info", update_id=734))
        await process(bot, make_callback("bank_info_view", update_id=735), wait=1.5)

        texts = sent_texts(bot)
        assert any(
            "اطلاعات بانکی" in t or "ثبت نشده" in t
            for t in texts
        ), f"Expected bank info response, got: {texts}"


class TestBankInfoUpdateCard:
    async def test_update_card_asks_for_16_digits(self, bot):
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=740)
        await process(bot, make_callback("personal_menu", update_id=743))
        await process(bot, make_callback("bank_info", update_id=744))
        await process(bot, make_callback("bank_info_update", update_id=745))
        await process(bot, make_callback("bank_info_update_card", update_id=746))

        texts = sent_texts(bot)
        assert any("کارت" in t for t in texts), (
            f"Expected card number prompt, got: {texts}"
        )

    async def test_invalid_card_shows_validation_error(self, bot):
        """Input shorter than 16 digits is rejected with a validation message."""
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=750)
        await process(bot, make_callback("personal_menu", update_id=753))
        await process(bot, make_callback("bank_info", update_id=754))
        await process(bot, make_callback("bank_info_update", update_id=755))
        await process(bot, make_callback("bank_info_update_card", update_id=756))
        await process(bot, make_text("123456789012", update_id=757))

        texts = sent_texts(bot)
        assert any("۱۶ رقم" in t for t in texts), (
            f"Expected 16-digit validation error, got: {texts}"
        )

    async def test_valid_card_saves_successfully(self, bot):
        """A valid 16-digit card number is saved and the bot confirms."""
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=760)
        await process(bot, make_callback("personal_menu", update_id=763))
        await process(bot, make_callback("bank_info", update_id=764))
        await process(bot, make_callback("bank_info_update", update_id=765))
        await process(bot, make_callback("bank_info_update_card", update_id=766))
        await process(bot, make_text("6037991234567890", update_id=767), wait=1.5)

        texts = sent_texts(bot)
        assert any("ذخیره شد" in t for t in texts), (
            f"Expected save confirmation, got: {texts}"
        )


class TestBankInfoUpdateIban:
    async def test_update_iban_asks_for_sheba(self, bot):
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=770)
        await process(bot, make_callback("personal_menu", update_id=773))
        await process(bot, make_callback("bank_info", update_id=774))
        await process(bot, make_callback("bank_info_update", update_id=775))
        await process(bot, make_callback("bank_info_update_iban", update_id=776))

        texts = sent_texts(bot)
        assert any("شبا" in t or "IBAN" in t for t in texts), (
            f"Expected IBAN/Sheba prompt, got: {texts}"
        )

    async def test_invalid_iban_shows_validation_error(self, bot):
        """A short value that doesn't match IR + 24 digits is rejected."""
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=780)
        await process(bot, make_callback("personal_menu", update_id=783))
        await process(bot, make_callback("bank_info", update_id=784))
        await process(bot, make_callback("bank_info_update", update_id=785))
        await process(bot, make_callback("bank_info_update_iban", update_id=786))
        await process(bot, make_text("IR12345", update_id=787))

        texts = sent_texts(bot)
        assert any("شبا" in t or "IBAN" in t or "۲۶" in t for t in texts), (
            f"Expected IBAN format error, got: {texts}"
        )

    async def test_valid_iban_saves_successfully(self, bot):
        """A valid IR + 24-digit IBAN is saved and the bot confirms."""
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=790)
        await process(bot, make_callback("personal_menu", update_id=793))
        await process(bot, make_callback("bank_info", update_id=794))
        await process(bot, make_callback("bank_info_update", update_id=795))
        await process(bot, make_callback("bank_info_update_iban", update_id=796))
        await process(bot, make_text("IR062170000000109202965164", update_id=797), wait=1.5)

        texts = sent_texts(bot)
        assert any("ذخیره شد" in t for t in texts), (
            f"Expected save confirmation, got: {texts}"
        )

    async def test_lowercase_iban_is_accepted(self, bot):
        """Lowercase 'ir' prefix is auto-uppercased and saved successfully."""
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=800)
        await process(bot, make_callback("personal_menu", update_id=803))
        await process(bot, make_callback("bank_info", update_id=804))
        await process(bot, make_callback("bank_info_update", update_id=805))
        await process(bot, make_callback("bank_info_update_iban", update_id=806))
        await process(bot, make_text("ir062170000000109202965164", update_id=807), wait=1.5)

        texts = sent_texts(bot)
        assert any("ذخیره شد" in t for t in texts), (
            f"Expected save confirmation for lowercase 'ir' IBAN, got: {texts}"
        )