import asyncio
import random
from typing import Annotated

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject

from config import settings
from db.main import DatabaseSessionManager, get_db_url
from db.models import Question

from enum import Enum

from redis.asyncio import Redis

from config import settings


class RedisType(str, Enum):
    pass


def get_redis_client() -> Redis:
    return Redis(host=settings.redis_ip,
                 port=settings.redis_port,
                 db=0,
                 decode_responses=True)

DB_URL = get_db_url(user=settings.db_user,
                    password=settings.db_password,
                    ip=settings.db_ip,
                    port=settings.db_port,
                    name=settings.db_name
                    )


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["handlers"])

    config = providers.Configuration()
    db_session_manager = providers.Singleton(
        DatabaseSessionManager,
        host=DB_URL,
        engine_kwargs={"echo": True}
    )

    db_session = providers.Resource(
        lambda db_manager: db_manager.session(),
        db_manager=db_session_manager,
    )


Session: Annotated[AsyncSession, Provide[Container.db_session]]


dp = Dispatcher()

async def get_user(message: types.Message, session: AsyncSession = types.Dependency(session_ma) ):


class GameState(StatesGroup):
    playing = State()
    creators_editing = State()
    creating_content = State()


def generate_keyboard(question: Question) -> ReplyKeyboardMarkup:

    buttons_count = question.answers_count + 1
    numbers = random.sample(range(1, 101), buttons_count)
    buttons = [[KeyboardButton(text=str(num))] for num in numbers]

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )



async def next_round(message: Message):
    number = random.randint(1, 10)
    keyboard = generate_keyboard()
    await message.answer(
        f"🎲 Случайное число: <b>{number}</b>\nВыберите одно из чисел ниже:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Привет! Напиши /start_game чтобы начать игру.")


@dp.message(Command("start_game"))
async def cmd_start_game(message: Message, state: FSMContext):
    await state.set_state(GameState.playing)
    await next_round(message)


@dp.message(GameState.playing, F.text)
async def handle_game_message(message: Message, state: FSMContext):
    await message.answer(f"Вы нажали на кнопку с числом {message.text}")
    await next_round(message)


@dp.message(Command("end_game"))
async def cmd_end_game(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Игра завершена!", reply_markup=ReplyKeyboardRemove())


async def main():
    bot = Bot(token=settings.tg_bot_token)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
