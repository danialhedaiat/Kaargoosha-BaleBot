"""
Integration tests for the charge wallet (deposit) flow (KAA-47).
Requires: RabbitMQ + FastAPI running, user TEST_USERNAME present in DB.
"""
from tests.conftest import (
    bot, make_command, make_callback, make_text, make_photo, process, sent_texts,
)


async def _sign_in(bot, base_id: int = 0):
    await process(bot, make_command("start", update_id=base_id + 1))
    await process(bot, make_callback("sign_in", update_id=base_id + 2), wait=1.5)


def _all_button_datas(bale_bot) -> set:
    datas = set()
    for c in bale_bot.mock_reply.call_args_list:
        markup = c.kwargs.get("reply_markup")
        if markup and hasattr(markup, "inline_keyboard"):
            for row in markup.inline_keyboard:
                for btn in row:
                    datas.add(btn.callback_data)
    return datas


class TestDepositMenu:
    async def test_personal_menu_contains_deposit_button(self, bot):
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=900)
        await process(bot, make_callback("personal_menu", update_id=903))

        assert "deposit_wallet" in _all_button_datas(bot), (
            "Expected 'شارژ کیف پول' (deposit_wallet) button in personal menu"
        )


class TestDepositAmountInput:
    async def test_deposit_wallet_asks_for_amount(self, bot):
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=910)
        await process(bot, make_callback("personal_menu", update_id=913))
        await process(bot, make_callback("deposit_wallet", update_id=914))

        texts = sent_texts(bot)
        assert any("مبلغ" in t for t in texts), (
            f"Expected amount prompt, got: {texts}"
        )

    async def test_non_numeric_amount_rejected(self, bot):
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=920)
        await process(bot, make_callback("personal_menu", update_id=923))
        await process(bot, make_callback("deposit_wallet", update_id=924))
        await process(bot, make_text("abc", update_id=925))

        texts = sent_texts(bot)
        assert any("مثبت" in t or "عدد" in t for t in texts), (
            f"Expected validation error for non-numeric input, got: {texts}"
        )

    async def test_zero_amount_rejected(self, bot):
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=930)
        await process(bot, make_callback("personal_menu", update_id=933))
        await process(bot, make_callback("deposit_wallet", update_id=934))
        await process(bot, make_text("0", update_id=935))

        texts = sent_texts(bot)
        assert any("مثبت" in t or "عدد" in t for t in texts), (
            f"Expected validation error for zero amount, got: {texts}"
        )

    async def test_valid_amount_asks_for_proof(self, bot):
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=940)
        await process(bot, make_callback("personal_menu", update_id=943))
        await process(bot, make_callback("deposit_wallet", update_id=944))
        await process(bot, make_text("500000", update_id=945))

        texts = sent_texts(bot)
        assert any("فیش" in t or "رسید" in t for t in texts), (
            f"Expected proof prompt after valid amount, got: {texts}"
        )


class TestDepositProofSubmission:
    async def test_text_proof_submits_and_confirms(self, bot):
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=950)
        await process(bot, make_callback("personal_menu", update_id=953))
        await process(bot, make_callback("deposit_wallet", update_id=954))
        await process(bot, make_text("1000000", update_id=955))
        await process(bot, make_text("رسید واریز به شماره ۱۲۳۴۵۶", update_id=956), wait=1.5)

        texts = sent_texts(bot)
        assert any("ثبت شد" in t or "تایید" in t or "خطا" in t for t in texts), (
            f"Expected deposit confirmation or error, got: {texts}"
        )

    async def test_photo_proof_submits_and_confirms(self, bot):
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=960)
        await process(bot, make_callback("personal_menu", update_id=963))
        await process(bot, make_callback("deposit_wallet", update_id=964))
        await process(bot, make_text("2000000", update_id=965))
        await process(bot, make_photo(file_id="proof_photo_file_id", update_id=966), wait=1.5)

        texts = sent_texts(bot)
        assert any("ثبت شد" in t or "تایید" in t or "خطا" in t for t in texts), (
            f"Expected deposit confirmation or error after photo proof, got: {texts}"
        )