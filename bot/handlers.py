
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from dependency_injector.wiring import inject, Provide
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.user import User
from db.repositories.question_repository import QuestionRepository
from di.di_implementation import Container as C
from db.models import Question
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


router = Router()

class GameState(StatesGroup):
    playing = State()


@router.message(Command("start_game"))
@inject
async def cmd_start_game(
    message: Message,
    state: FSMContext,
    session: AsyncSession = Provide[C.db_session],
    user: User = Provide[C.get_user]
):
    await state.set_state(GameState.playing)
    qr = QuestionRepository(session)
    question = await qr.get_by_creator(user)
    await message.answer(f"Вопрос: {question.}")
