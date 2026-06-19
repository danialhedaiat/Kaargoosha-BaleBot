"""
Integration tests for the admin transactions menu (KAA-64).
Requires: RabbitMQ + FastAPI running, admin user TEST_USERNAME present in DB.
Update IDs: 1200-1230 (kept clear of the other suites).
"""
from tests.conftest import (
    bot, make_command, make_callback, make_text, make_photo, process, sent_texts, all_button_datas,
)


async def _sign_in(bot, base_id=1200):
    await process(bot, make_command("start", update_id=base_id + 1))
    await process(bot, make_callback("sign_in", update_id=base_id + 2), wait=1.5)


def _reset(bot):
    bot.mock_reply.reset_mock()
    if hasattr(bot, "mock_edit"):
        bot.mock_edit.reset_mock()


class TestAdminTransactionsMenu:
    async def test_admin_menu_has_transactions_button(self, bot):
        await _sign_in(bot, base_id=1200)
        await process(bot, make_callback("admin_menu", update_id=1204), wait=1.5)
        assert "transactions_menu" in all_button_datas(bot)

    async def test_full_drilldown_to_results(self, bot):
        await _sign_in(bot, base_id=1210)
        await process(bot, make_callback("admin_menu", update_id=1214), wait=1.5)

        await process(bot, make_callback("transactions_menu", update_id=1215))
        datas = all_button_datas(bot)
        assert "tx_type_dep" in datas and "tx_type_inst" in datas, datas

        await process(bot, make_callback("tx_type_dep", update_id=1216))
        datas = all_button_datas(bot)
        assert {"tx_st_dep_approved", "tx_st_dep_pending", "tx_st_dep_rejected", "tx_st_dep_all"} <= datas, datas

        await process(bot, make_callback("tx_st_dep_all", update_id=1217))
        datas = all_button_datas(bot)
        assert {"tx_rng_dep_all_day", "tx_rng_dep_all_week", "tx_rng_dep_all_month"} <= datas, datas

        _reset(bot)
        await process(bot, make_callback("tx_rng_dep_all_month", update_id=1218), wait=1.5)
        texts = sent_texts(bot)
        assert any("پایان لیست" in t or "تراکنشی یافت نشد" in t for t in texts), texts

    async def test_pending_receipt_shows_approve_button(self, bot):
        """A submitted deposit appears as a pending receipt with an approve button."""
        await _sign_in(bot, base_id=1230)
        # client submits a wallet-charge receipt (text proof) -> creates a pending receipt
        await process(bot, make_callback("personal_menu", update_id=1233))
        await process(bot, make_callback("deposit_wallet", update_id=1234))
        await process(bot, make_text("700000", update_id=1235))
        await process(bot, make_text("rasid-test", update_id=1236), wait=1.5)

        # admin views pending wallet-charge receipts
        await process(bot, make_callback("admin_menu", update_id=1237), wait=1.5)
        _reset(bot)
        await process(bot, make_callback("tx_rng_dep_pending_month", update_id=1238), wait=1.5)

        datas = all_button_datas(bot)
        assert any(d.startswith("receipt_approve_") for d in datas), (
            f"Expected a receipt_approve button on a pending receipt, got: {datas}"
        )

    async def test_pending_photo_receipt_sends_image_to_admin(self, bot):
        """A photo-proof receipt is shown to the admin as an actual image, not a link."""
        await _sign_in(bot, base_id=1240)
        await process(bot, make_callback("personal_menu", update_id=1243))
        await process(bot, make_callback("deposit_wallet", update_id=1244))
        await process(bot, make_text("800000", update_id=1245))
        await process(bot, make_photo(update_id=1246), wait=1.5)  # photo proof -> receipt

        await process(bot, make_callback("admin_menu", update_id=1247), wait=1.5)
        bot.mock_photo.reset_mock()
        await process(bot, make_callback("tx_rng_dep_pending_month", update_id=1248), wait=1.5)

        assert bot.mock_photo.call_count >= 1, "Expected the receipt photo to be sent to the admin"
