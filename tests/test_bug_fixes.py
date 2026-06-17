"""
Regression tests for the bugs found during manual testing (KAA-56..KAA-62).

These pin the EXPECTED post-fix behaviour, so a test fails while its bug is open
and turns green once the matching fix lands.

Requires: RabbitMQ + FastAPI running, user TEST_USERNAME present in DB.
Update IDs: 1100–1146 (kept clear of the other suites).
"""
from tests.conftest import (
    bot, make_command, make_callback, make_text, process, sent_texts, all_button_datas,
)


async def _sign_in(bot, base_id: int = 0):
    await process(bot, make_command("start", update_id=base_id + 1))
    await process(bot, make_callback("sign_in", update_id=base_id + 2), wait=1.5)


def _reset(bot):
    bot.mock_reply.reset_mock()
    if hasattr(bot, "mock_edit"):
        bot.mock_edit.reset_mock()


class TestBankInfoBackButtons:
    async def test_bank_info_view_has_back_button(self, bot):
        """KAA-56: viewing bank info must offer a way back to the menu."""
        _reset(bot)
        await _sign_in(bot, base_id=1100)
        await process(bot, make_callback("personal_menu", update_id=1103))
        await process(bot, make_callback("bank_info", update_id=1104))
        await process(bot, make_callback("bank_info_view", update_id=1105), wait=1.5)

        datas = all_button_datas(bot)
        assert "bank_info" in datas or "personal_menu" in datas, (
            f"Expected a back button after viewing bank info, got buttons: {datas}"
        )

    async def test_back_button_after_saving_card(self, bot):
        """KAA-58: a save confirmation must include a back button."""
        _reset(bot)
        await _sign_in(bot, base_id=1110)
        await process(bot, make_callback("personal_menu", update_id=1113))
        await process(bot, make_callback("bank_info", update_id=1114))
        await process(bot, make_callback("bank_info_update", update_id=1115))
        await process(bot, make_callback("bank_info_update_card", update_id=1116))
        await process(bot, make_text("6037991234567890", update_id=1117), wait=1.5)

        texts = sent_texts(bot)
        assert any("ذخیره شد" in t for t in texts), f"Expected save confirmation, got: {texts}"
        datas = all_button_datas(bot)
        assert "bank_info" in datas or "personal_menu" in datas, (
            f"Expected a back button after saving the card number, got buttons: {datas}"
        )


class TestIbanWithoutPrefix:
    async def test_iban_accepts_24_digits_without_ir(self, bot):
        """KAA-57: a bare 24-digit Sheba (no IR) should be accepted and saved."""
        _reset(bot)
        await _sign_in(bot, base_id=1120)
        await process(bot, make_callback("personal_menu", update_id=1123))
        await process(bot, make_callback("bank_info", update_id=1124))
        await process(bot, make_callback("bank_info_update", update_id=1125))
        await process(bot, make_callback("bank_info_update_iban", update_id=1126))
        await process(bot, make_text("062170000000109202965164", update_id=1127), wait=1.5)

        texts = sent_texts(bot)
        assert any("ذخیره شد" in t for t in texts), (
            f"Expected a 24-digit IBAN without IR to save, got: {texts}"
        )

    async def test_iban_prompt_does_not_require_ir(self, bot):
        """KAA-57: the prompt should ask for digits only, not an IR-prefixed value."""
        _reset(bot)
        await _sign_in(bot, base_id=1150)
        await process(bot, make_callback("personal_menu", update_id=1153))
        await process(bot, make_callback("bank_info", update_id=1154))
        await process(bot, make_callback("bank_info_update", update_id=1155))
        await process(bot, make_callback("bank_info_update_iban", update_id=1156))

        texts = sent_texts(bot)
        assert any("۲۴" in t or "24" in t for t in texts), (
            f"Expected the prompt to ask for 24 digits, got: {texts}"
        )


class TestCancelCommand:
    async def test_cancel_aborts_pending_deposit_input(self, bot):
        """KAA-59: /cancel must clear a pending input flow."""
        _reset(bot)
        await _sign_in(bot, base_id=1130)
        await process(bot, make_callback("personal_menu", update_id=1133))
        await process(bot, make_callback("deposit_wallet", update_id=1134))  # now awaiting amount

        _reset(bot)
        await process(bot, make_command("cancel", update_id=1135))
        texts = sent_texts(bot)
        assert any("لغو" in t for t in texts), (
            f"Expected a cancellation confirmation from /cancel, got: {texts}"
        )

        # A number typed after /cancel must NOT be consumed as the deposit amount.
        _reset(bot)
        await process(bot, make_text("5000", update_id=1136))
        after = sent_texts(bot)
        assert not any("فیش" in t or "رسید" in t for t in after), (
            f"After /cancel the bot should not still wait for a deposit amount, got: {after}"
        )


class TestPayInstallmentEditsMessage:
    async def test_pay_installment_edits_previous_message(self, bot):
        """KAA-62: the pending-installments result should edit the tapped message."""
        await _sign_in(bot, base_id=1140)
        await process(bot, make_callback("personal_menu", update_id=1143))

        _reset(bot)
        await process(bot, make_callback("pay_installment", update_id=1144), wait=1.5)

        assert bot.mock_edit.call_count >= 1, (
            "Expected pay_installment to edit the previous message rather than send a new one"
        )
