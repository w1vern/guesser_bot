import asyncio
import random
from typing import Annotated
from webbrowser import get

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession


from bot.di_implementation import Container
from config import settings
from db.main import DatabaseSessionManager, get_db_url
from db.models import Question



from config import settings
from db.models.user import User
from db.repositories.user_repository import UserRepository



""" 
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
    await message.answer("Игра завершена!", reply_markup=ReplyKeyboardRemove()) """


async def main():
    container = Container()

    bot = Bot(token=settings.tg_bot_token)
    dp = Dispatcher()

    container.wire(modules=[__name__, "handlers"])

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
