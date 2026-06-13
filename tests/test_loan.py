"""
Integration tests for the loan request flow.
Requires: RabbitMQ + FastAPI running.
TEST_USERNAME must have LOAN_CREATE permission assigned in DB.
"""
from tests.conftest import bot, make_command, make_callback, process, sent_texts


async def _sign_in(bot, base_id: int = 0):
    """Run /start → sign_in to put the user in signed-in state."""
    await process(bot, make_command("start", update_id=base_id + 1))
    await process(bot, make_callback("sign_in", update_id=base_id + 2), wait=1.5)


class TestPersonalMenu:
    async def test_personal_menu_shown_after_sign_in(self, bot):
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=100)
        await process(bot, make_callback("personal_menu", update_id=103))

        assert any("منوی شخصی" in t for t in sent_texts(bot))


class TestLoanFlow:
    async def test_apply_for_loan_shows_duration_buttons(self, bot):
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=200)
        await process(bot, make_callback("personal_menu", update_id=203))
        await process(bot, make_callback("apply_for_loan", update_id=204))

        texts = sent_texts(bot)
        assert any("مدت" in t or "ماه" in t for t in texts)

    async def test_duration_selection_shows_confirmation(self, bot):
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=300)
        await process(bot, make_callback("personal_menu", update_id=303))
        await process(bot, make_callback("apply_for_loan", update_id=304))
        await process(bot, make_callback("loan_duration_6", update_id=305))

        texts = sent_texts(bot)
        assert any("تایید" in t or "خلاصه" in t or "ماه" in t for t in texts)

    async def test_loan_confirm_sends_response(self, bot):
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=400)
        await process(bot, make_callback("personal_menu", update_id=403))
        await process(bot, make_callback("apply_for_loan", update_id=404))
        await process(bot, make_callback("loan_duration_12", update_id=405))
        await process(bot, make_callback("loan_confirm", update_id=406), wait=1.5)

        texts = sent_texts(bot)
        assert any("ثبت شد" in t or "درخواست" in t or "متاسفانه" in t for t in texts), (
            f"Expected loan response, got: {texts}"
        )

    async def test_loan_cancel_shows_cancel_message(self, bot):
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=500)
        await process(bot, make_callback("personal_menu", update_id=503))
        await process(bot, make_callback("apply_for_loan", update_id=504))
        await process(bot, make_callback("loan_duration_6", update_id=505))
        await process(bot, make_callback("loan_cancel", update_id=506))

        assert any("لغو" in t for t in sent_texts(bot))

    async def test_loan_duration_15_months_shown_in_summary(self, bot):
        bot.mock_reply.reset_mock()
        await _sign_in(bot, base_id=600)
        await process(bot, make_callback("personal_menu", update_id=603))
        await process(bot, make_callback("apply_for_loan", update_id=604))
        await process(bot, make_callback("loan_duration_15", update_id=605))

        texts = sent_texts(bot)
        assert any("15" in t or "۱۵" in t for t in texts)