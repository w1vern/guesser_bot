

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from fast_depends import inject

from bot.dependencies import CreateUser, GetUser, Session
from bot.services import get_func, to_main_menu

router = Router()


@router.message(Command("start"))
@inject
async def cmd_start(message: types.Message,
                    state: FSMContext,
                    user: CreateUser,
                    session: Session
                    ) -> None:
    await message.answer(f"hello, your rank: {user.rank}")
    await to_main_menu(message, state, user, session)


@router.message()
@inject
async def handle_button(message: types.Message,
                        state: FSMContext,
                        user: GetUser,
                        session: Session
                        ) -> None:
    await get_func(
        await state.get_state(),
        message.text)(message,
                      state,
                      user,
                      session)
