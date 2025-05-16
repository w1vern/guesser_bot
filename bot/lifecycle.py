

from aiogram import Bot, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import ReplyKeyboardRemove
from fast_depends import inject

from bot.dependencies import Session
from bot.keyboards import main_menu_keyboard
from bot.states import AppState
from db.repositories import UserRepository


def register_lifecycle(dp: Dispatcher, bot: Bot) -> None:
    @dp.startup()
    @inject
    async def on_startup(session: Session) -> None:
        ur = UserRepository(session)
        users = await ur.all()
        for user in users:
            state = FSMContext(storage=dp.storage, key=StorageKey(
                bot.id, user.tg_id, user.tg_id))
            await state.set_state(AppState.main_menu)
            await bot.send_message(chat_id=user.tg_id, text="bot startup", reply_markup=main_menu_keyboard(user))

    @dp.shutdown()
    @inject
    async def on_shutdown(session: Session) -> None:
        ur = UserRepository(session)
        users = await ur.all()
        for user in users:
            await bot.send_message(user.tg_id, "bot shuting down", reply_markup=ReplyKeyboardRemove())
