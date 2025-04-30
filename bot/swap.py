import asyncio
import math
import random
from uuid import UUID

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BufferedInputFile

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.main import DatabaseSessionManager, get_db_url
from db.models.user import User
from db.repositories.battle_repository import BattleRepository
from db.repositories.question_repository import QuestionRepository
from db.repositories.user_repository import UserRepository
from db.s3 import get_s3_client
from typing import Tuple, List


# —————————————————————————————————————————————————————————————————————————————
# FSM-состояния
# —————————————————————————————————————————————————————————————————————————————
class AppState(StatesGroup):
    main_menu = State()
    playing = State()
    settings = State()
    # можно добавить другие состояния (редактирование контента и т.п.)


# —————————————————————————————————————————————————————————————————————————————
# Помощники для работы с рейтингом (ваш существующий код)
# —————————————————————————————————————————————————————————————————————————————
def change_rank(user_rank: float, question_rank: float, result: bool) -> Tuple[float, float]:
    k = 5.0
    alpha = 0.1
    p_user = 1 / (1 + math.exp(k * (question_rank - user_rank)))
    tmp = int(result)
    user_diff = alpha * (tmp - p_user) * user_rank * (1 - user_rank)
    question_diff = alpha * (p_user - tmp) * question_rank * (1 - question_rank)
    return user_diff, question_diff

def convert_rank(rank: float) -> int:
    return int(rank * 1000)


# —————————————————————————————————————————————————————————————————————————————
# Менеджер сессий БД
# —————————————————————————————————————————————————————————————————————————————
session_manager = DatabaseSessionManager(
    get_db_url(
        user=settings.db_user,
        password=settings.db_password,
        ip=settings.db_ip,
        port=settings.db_port,
        name=settings.db_name
    ), {"echo": False}
)

router = Router()


# —————————————————————————————————————————————————————————————————————————————
# Генерация клавиатур под разные состояния
# —————————————————————————————————————————————————————————————————————————————
def main_menu_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Начать игру"), KeyboardButton(text="Настройки"), ]], resize_keyboard=True)
    return kb

def settings_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Вернуться в главное меню")]], resize_keyboard=True)
    return kb

async def playing_kb(answers: List[str]) -> ReplyKeyboardMarkup:
    buttons:list[list[KeyboardButton]] = [[]]
    for ans in answers:
        buttons[0].append(KeyboardButton(text=ans))
    buttons[0].append(KeyboardButton(text="Закончить игру"))
    kb = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    
    return kb


# —————————————————————————————————————————————————————————————————————————————
# Загрузка/регистрация пользователя
# —————————————————————————————————————————————————————————————————————————————
async def get_or_create_user(tg_id: int, session: AsyncSession) -> User:
    ur = UserRepository(session)
    user = await ur.get_by_tg_id(tg_id)
    if not user:
        user = await ur.create(tg_id)
    return user


# —————————————————————————————————————————————————————————————————————————————
# Заглушки для отсутствующей логики
# —————————————————————————————————————————————————————————————————————————————
async def stub_show_settings(message: types.Message, state: FSMContext):
    # TODO: реализовать отображение и сохранение настроек пользователя
    await message.answer("Здесь будут настройки (пока заглушка).", reply_markup=settings_kb())

async def stub_process_answer(message: types.Message, state: FSMContext, selected: str):
    # TODO: ваша логика проверки ответа
    await message.answer(f"Вы выбрали «{selected}» — пока заглушка обработки ответа.")
    # после обработки можно отправить следующий вопрос или закончить игру


# —————————————————————————————————————————————————————————————————————————————
# Отправка вопроса в состоянии игры
# —————————————————————————————————————————————————————————————————————————————
async def send_question(message: types.Message, state: FSMContext):
    async with session_manager.context_session() as session:
        qr = QuestionRepository(session)
        current = await qr.get_random_question()
        if not current:
            await message.answer("Вопросы закончились, игра окончена.", reply_markup=main_menu_kb())
            await state.set_state(AppState.main_menu)
            return

        # собираем варианты ответов
        others = await qr.get_random_questions(current.answers_count - 1, [current])
        options = [x.file.answer for x in others] + [current.file.answer]
        random.shuffle(options)

        # сохраняем correct_answer в FSM
        await state.update_data(correct=current.file.answer)

        # получаем файл из S3
        client = get_s3_client()
        obj = client.get_object(bucket_name=settings.minio_bucket, object_name=str(current.file.id))
        data = obj.read(); obj.close()
        input_file = BufferedInputFile(data, filename=str(current.file.id))

        media = current.file.file_type.split("/")[0]
        kb = await playing_kb(options)

        # отправляем в зависимости от типа
        if media == "image":
            await message.answer_photo(photo=input_file, caption="Угадайте фильм:", reply_markup=kb)
        elif media == "video":
            await message.answer_video(video=input_file, caption="Угадайте фильм:", reply_markup=kb)
        elif media == "audio":
            await message.answer_voice(voice=input_file, caption="Угадайте фильм:", reply_markup=kb)
        else:
            await message.answer("Неподдерживаемый тип файла.", reply_markup=kb)


# —————————————————————————————————————————————————————————————————————————————
# Стартовые команды /start
# —————————————————————————————————————————————————————————————————————————————
@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.set_state(AppState.main_menu)
    await message.answer("Добро пожаловать! Ваше меню:", reply_markup=main_menu_kb())


# —————————————————————————————————————————————————————————————————————————————
# Общий обработчик всех нажатий ReplyKeyboard
# —————————————————————————————————————————————————————————————————————————————
@router.message()
async def handle_button(message: types.Message, state: FSMContext):
    text = message.text
    current = await state.get_state()

    # главное меню
    if current == AppState.main_menu.state:
        match text:
            case "Начать игру":
                await state.set_state(AppState.playing)
                await send_question(message, state)
            case "Настройки":
                await state.set_state(AppState.settings)
                await stub_show_settings(message, state)
            case _:
                await message.answer("Пожалуйста, выберите пункт меню.", reply_markup=main_menu_kb())

    # настройки
    elif current == AppState.settings.state:
        match text:
            case "Вернуться в главное меню":
                await state.set_state(AppState.main_menu)
                await message.answer("Главное меню:", reply_markup=main_menu_kb())
            case _:
                await message.answer("В настройках доступна только кнопка «Вернуться в главное меню».", reply_markup=settings_kb())

    # во время игры
    elif current == AppState.playing.state:
        if text == "Закончить игру":
            await state.set_state(AppState.main_menu)
            await message.answer("Игра окончена. Главное меню:", reply_markup=main_menu_kb())
        else:
            # здесь можно вставить вашу логику из BattleRepository и change_rank
            await stub_process_answer(message, state, text)

    # прочие состояния
    else:
        await state.set_state(AppState.main_menu)
        await message.answer("Возврат в главное меню.", reply_markup=main_menu_kb())


# —————————————————————————————————————————————————————————————————————————————
# Запуск бота
# —————————————————————————————————————————————————————————————————————————————
async def main():
    bot = Bot(token=settings.tg_bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
