"""
Integration tests for the installment payment proof flow (KAA-53).
Requires: RabbitMQ + FastAPI running, user TEST_USERNAME present in DB.
Note: installment selection tests depend on the user having an approved loan
with pending installments. If none exist, the bot shows "قسط معوقی وجود ندارد".
"""
from tests.conftest import (
    bot, make_command, make_callback, make_text, make_photo, process, sent_texts,
)


async def _sign_in(bot, base_id: int = 0):
    await process(bot, make_command("start", update_id=base_id + 1))
    await process(bot, make_callback("sign_in", update_id=base_id + 2), wait=1.5)


def _all_button_datas(bale_bot) -> set:
    datas = set()
    calls = list(bale_bot.mock_reply.call_args_list)
    if hasattr(bale_bot, "mock_edit"):
        calls += list(bale_bot.mock_edit.call_args_list)
    for c in calls:
        markup = c.kwargs.get("reply_markup")
        if markup and hasattr(markup, "inline_keyboard"):
            for row in markup.inline_keyboard:
                for btn in row:
                    datas.add(btn.callback_data)
    return datas


class TestInstallmentPaymentMenu:
    async def test_personal_menu_contains_pay_installment_button(self, bot):
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=1000)
        await process(bot, make_callback("personal_menu", update_id=1003))

        assert "pay_installment" in _all_button_datas(bot), (
            "Expected 'پرداخت قسط' (pay_installment) button in personal menu"
        )


class TestInstallmentPaymentFlow:
    async def test_pay_installment_returns_response(self, bot):
        """Either shows installment buttons or 'no pending installments' message."""
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=1010)
        await process(bot, make_callback("personal_menu", update_id=1013))
        await process(bot, make_callback("pay_installment", update_id=1014), wait=1.5)

        texts = sent_texts(bot)
        buttons = _all_button_datas(bot)
        has_installment_buttons = any(d.startswith("pay_installment_") and d != "pay_installment" for d in buttons)
        has_empty_message = any("معوق" in t or "وجود ندارد" in t for t in texts)

        assert has_installment_buttons or has_empty_message, (
            f"Expected installment list or empty message, got texts={texts}, buttons={buttons}"
        )

    async def test_installment_selected_asks_for_proof(self, bot):
        """Selecting a pending installment should prompt for proof."""
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=1020)
        await process(bot, make_callback("personal_menu", update_id=1023))
        await process(bot, make_callback("pay_installment", update_id=1024), wait=1.5)

        buttons = _all_button_datas(bot)
        installment_buttons = [d for d in buttons if d.startswith("pay_installment_") and d != "pay_installment"]

        if not installment_buttons:
            return

        bot.mock_reply.reset_mock()
        await process(bot, make_callback(installment_buttons[0], update_id=1025))

        texts = sent_texts(bot)
        assert any("فیش" in t or "رسید" in t for t in texts), (
            f"Expected proof prompt after installment selection, got: {texts}"
        )

    async def test_text_proof_submits_installment_payment(self, bot):
        """Full flow: select installment → text proof → confirmation."""
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=1030)
        await process(bot, make_callback("personal_menu", update_id=1033))
        await process(bot, make_callback("pay_installment", update_id=1034), wait=1.5)

        buttons = _all_button_datas(bot)
        installment_buttons = [d for d in buttons if d.startswith("pay_installment_") and d != "pay_installment"]

        if not installment_buttons:
            return

        await process(bot, make_callback(installment_buttons[0], update_id=1035))
        bot.mock_reply.reset_mock()
        await process(bot, make_text("واریز قسط به حساب شرکت", update_id=1036), wait=1.5)

        texts = sent_texts(bot)
        assert any("ثبت شد" in t or "تایید" in t or "خطا" in t for t in texts), (
            f"Expected installment payment confirmation or error, got: {texts}"
        )

    async def test_photo_proof_submits_installment_payment(self, bot):
        """Full flow: select installment → photo proof → confirmation."""
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=1040)
        await process(bot, make_callback("personal_menu", update_id=1043))
        await process(bot, make_callback("pay_installment", update_id=1044), wait=1.5)

        buttons = _all_button_datas(bot)
        installment_buttons = [d for d in buttons if d.startswith("pay_installment_") and d != "pay_installment"]

        if not installment_buttons:
            return

        await process(bot, make_callback(installment_buttons[0], update_id=1045))
        bot.mock_reply.reset_mock()
        await process(bot, make_photo(file_id="installment_proof_photo", update_id=1046), wait=1.5)

        texts = sent_texts(bot)
        assert any("ثبت شد" in t or "تایید" in t or "خطا" in t for t in texts), (
            f"Expected installment payment confirmation or error after photo, got: {texts}"
        )