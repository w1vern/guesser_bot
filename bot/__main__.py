import asyncio
import random

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import settings



dp = Dispatcher()


# Состояния игры
class GameState(StatesGroup):
    playing = State()


# Генерация случайной клавиатуры
def generate_keyboard() -> ReplyKeyboardMarkup:
    buttons_count = random.randint(4, 8)
    numbers = random.sample(range(1, 101), buttons_count)
    buttons = [[KeyboardButton(text=str(num))] for num in numbers]

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )


# /start — просто приветствие
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Привет! Напиши /start_game чтобы начать игру.")


# /start_game — включаем состояние и начинаем цикл
@dp.message(Command("start_game"))
async def cmd_start_game(message: Message, state: FSMContext):
    await state.set_state(GameState.playing)
    await next_round(message)


# Обработка кнопок во время игры
@dp.message(GameState.playing, F.text)
async def handle_game_message(message: Message, state: FSMContext):
    await message.answer(f"Вы нажали на кнопку с числом {message.text}")
    await next_round(message)


# /end_game — выходим из состояния
@dp.message(Command("end_game"))
async def cmd_end_game(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Игра завершена!", reply_markup=ReplyKeyboardRemove())


# Функция запуска следующего раунда
async def next_round(message: Message):
    number = random.randint(1, 10)
    keyboard = generate_keyboard()
    await message.answer(
        f"🎲 Случайное число: <b>{number}</b>\nВыберите одно из чисел ниже:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


# Запуск
async def main():
    bot = Bot(token=settings.tg_bot_token)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
