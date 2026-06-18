import asyncio
import datetime
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from telegram import CallbackQuery, Chat, Contact, Message, MessageEntity, Update, User

from core.main import BaleBot

# ── Test identity ─────────────────────────────────────────────────────────────
# Must match a real user in the running FastAPI/DB.
TEST_TELEGRAM_USER_ID = int(os.getenv("TEST_TELEGRAM_USER_ID", "101010101"))
TEST_CHAT_ID = TEST_TELEGRAM_USER_ID
TEST_USERNAME = os.getenv("TEST_USERNAME", "dan_bosbos")
TEST_PHONE = os.getenv("TEST_PHONE", "09308222060")


# ── Bot fixture ───────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def bot():
    """
    Full integration fixture — requires RabbitMQ + FastAPI running.
    Mocks all outbound Bale/Telegram HTTP API calls at the class level so
    tests never make real HTTP requests.
    """
    bale_bot = BaleBot()

    # Set bot user info directly — avoids the get_me() HTTP call entirely.
    # PTB v22's CommandHandler.check_update reads bot.username, which requires
    # _bot_user to be set. Setting _initialized=True makes bot.initialize() a no-op.
    bale_bot.app.bot._bot_user = MagicMock(
        id=999999999, is_bot=True, first_name="TestBot", username="testbot",
    )
    bale_bot.app.bot._initialized = True

    # PTB v22 freezes bot objects — unfreeze to allow patching direct API calls
    bale_bot.app.bot._frozen = False
    bale_bot.app.bot.send_message = AsyncMock(
        return_value=MagicMock(message_id=1, chat=MagicMock(id=TEST_CHAT_ID))
    )
    bale_bot.app.bot.answer_callback_query = AsyncMock(return_value=True)
    bale_bot.app.bot.edit_message_text = AsyncMock(return_value=MagicMock(message_id=1))
    # Photo proofs are downloaded (get_file -> download_as_bytearray) before upload (KAA-70).
    _proof_file = MagicMock()
    _proof_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"fake-image-bytes"))
    bale_bot.app.bot.get_file = AsyncMock(return_value=_proof_file)
    bale_bot.app.bot._frozen = True

    # Patch Message.reply_text and CallbackQuery.answer at class level so
    # tests don't need bot injection on manually constructed objects.
    with patch.object(Message, "reply_text", new_callable=AsyncMock) as mock_reply, \
         patch.object(Message, "reply_photo", new_callable=AsyncMock) as mock_photo, \
         patch.object(CallbackQuery, "edit_message_text", new_callable=AsyncMock) as mock_edit, \
         patch.object(CallbackQuery, "answer", new_callable=AsyncMock):
        bale_bot.mock_reply = mock_reply
        # Proof photos in the admin transactions list (KAA-64) go through reply_photo.
        bale_bot.mock_photo = mock_photo
        # Menu navigation now edits the message in place instead of sending a new
        # one (KAA-55), so tests must look at edit_message_text calls too.
        bale_bot.mock_edit = mock_edit

        async with bale_bot.app:
            yield bale_bot


# ── Process helper ────────────────────────────────────────────────────────────

def _inject_bot(update: Update, bot: object) -> None:
    """
    Set _bot on the objects inside an Update that PTB v22 requires.
    CommandHandler.check_update calls message.get_bot() before dispatching,
    which raises RuntimeError if _bot is not set.
    PTB v22 uses __slots__ so we target only the specific objects that need it.
    """
    if update.message:
        update.message._bot = bot
        if update.message.from_user:
            update.message.from_user._bot = bot
    if update.callback_query:
        update.callback_query._bot = bot
        if update.callback_query.message:
            update.callback_query.message._bot = bot
            if update.callback_query.message.from_user:
                update.callback_query.message.from_user._bot = bot


async def process(bale_bot: BaleBot, update: Update, wait: float = 0.5) -> None:
    """
    Inject bot into the update, process it, and wait for any
    asyncio.create_task callbacks to complete.
    `wait` must be ≥ total blocking RPC time (DEFAULT_TIMEOUT = 0.2s each).
    Sign-in steps do two RPC calls — use wait=1.5 for those.
    """
    _inject_bot(update, bale_bot.app.bot)
    await bale_bot.app.process_update(update)
    await asyncio.sleep(wait)


# ── Update factories ──────────────────────────────────────────────────────────

def _user(user_id: int = TEST_TELEGRAM_USER_ID, username: str = TEST_USERNAME) -> User:
    return User(id=user_id, first_name="Test", is_bot=False, username=username)


def _chat(chat_id: int = TEST_CHAT_ID) -> Chat:
    return Chat(id=chat_id, type=Chat.PRIVATE)


def _now() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc)


def make_command(command: str, update_id: int = 1) -> Update:
    """
    Simulate a bot command (e.g. /start).
    Includes BOT_COMMAND MessageEntity so PTB's CommandHandler filter matches.
    """
    text = f"/{command}"
    msg = Message(
        message_id=update_id,
        date=_now(),
        chat=_chat(),
        from_user=_user(),
        text=text,
        entities=(MessageEntity(type=MessageEntity.BOT_COMMAND, offset=0, length=len(text)),),
    )
    return Update(update_id=update_id, message=msg)


def make_callback(data: str, update_id: int = 2) -> Update:
    """Simulate an inline keyboard button press."""
    msg = Message(message_id=1, date=_now(), chat=_chat(), from_user=_user())
    cq = CallbackQuery(
        id=str(update_id),
        from_user=_user(),
        chat_instance=str(TEST_CHAT_ID),
        data=data,
        message=msg,
    )
    return Update(update_id=update_id, callback_query=cq)


def make_text(text: str, update_id: int = 3) -> Update:
    """Simulate a plain text message."""
    msg = Message(
        message_id=update_id,
        date=_now(),
        chat=_chat(),
        from_user=_user(),
        text=text,
    )
    return Update(update_id=update_id, message=msg)


def make_contact(phone_number: str = TEST_PHONE, update_id: int = 4) -> Update:
    """Simulate the user sharing their phone contact."""
    contact = Contact(phone_number=phone_number, first_name="Test", user_id=TEST_TELEGRAM_USER_ID)
    msg = Message(
        message_id=update_id,
        date=_now(),
        chat=_chat(),
        from_user=_user(),
        contact=contact,
    )
    return Update(update_id=update_id, message=msg)


def make_photo(file_id: str = "test_file_id_photo", update_id: int = 5) -> Update:
    """Simulate a photo message."""
    from telegram import PhotoSize
    photo = (PhotoSize(file_id=file_id, file_unique_id="unique_photo_1", width=100, height=100),)
    msg = Message(
        message_id=update_id,
        date=_now(),
        chat=_chat(),
        from_user=_user(),
        photo=photo,
    )
    return Update(update_id=update_id, message=msg)


def _message_calls(bale_bot: BaleBot) -> list:
    """All reply_text + edit_message_text calls recorded so far.

    Navigation handlers edit the existing message (KAA-55), so both mocks must be
    inspected to see everything the bot rendered.
    """
    calls = list(bale_bot.mock_reply.call_args_list)
    if hasattr(bale_bot, "mock_edit"):
        calls += list(bale_bot.mock_edit.call_args_list)
    return calls


def sent_texts(bale_bot: BaleBot) -> list[str]:
    """Return all texts the bot rendered (new messages and in-place edits)."""
    return [
        c.args[0] if c.args else c.kwargs.get("text", "")
        for c in _message_calls(bale_bot)
    ]


def all_button_datas(bale_bot: BaleBot) -> set:
    """Collect every callback_data across all rendered messages (sent or edited)."""
    datas = set()
    for c in _message_calls(bale_bot):
        markup = c.kwargs.get("reply_markup")
        if markup and hasattr(markup, "inline_keyboard"):
            for row in markup.inline_keyboard:
                for btn in row:
                    datas.add(btn.callback_data)
    return datas