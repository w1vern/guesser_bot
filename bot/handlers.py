from datetime import timedelta
from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dependency_injector.wiring import inject, Provide
from minio import Minio
from sqlalchemy.ext.asyncio import AsyncSession
import random

from bot.di_implementation import Container as C
from db.repositories.question_repository import QuestionRepository
from config import settings

router = Router()

class GameState(StatesGroup):
    playing = State()

@router.message(Command("start_game"))
@inject
async def cmd_start_game(
    message: types.Message,
    state: FSMContext,
    session: AsyncSession = Provide[C.db_session]
):
    """
    Обработчик команды /start_game: переводит в состояние игры и отправляет первый вопрос.
    """
    await state.set_state(GameState.playing)
    # Инициализируем список уже заданных вопросов
    await state.update_data(asked=[])
    # Отправляем первый вопрос
    await send_question(message, state)

@inject
async def send_question(
    message: types.Message,
    state: FSMContext,
    session: AsyncSession = Provide[C.db_session],
    minio_client: Minio = Provide[C.minio_client]
):
    """
    Функция для отправки одного вопроса с четырьмя вариантами ответа.
    """
    qr = QuestionRepository(session)

    # Получаем новый вопрос, исключая уже заданные
    questions = await qr.get_random_questions(5)
    question = questions[0]

    # Берем 4 неверных варианта
    wrong_opts = questions[1:]

    # Собираем и перемешиваем варианты (1 правильный + 4 неверных)
    random.shuffle(questions)

    # Формируем Inline-клавиатуру
    keyboard = InlineKeyboardMarkup(row_width=2)
    for opt in questions:
        btn = InlineKeyboardButton(
            text=opt.file.answer,
            callback_data=f"answer:{opt.id}"
        )
        keyboard.insert(btn)

    # Генерируем presigned URL для медиа-вопроса
    media_url = minio_client.presigned_get_object(
        bucket_name=settings.minio_bucket,
        object_name=str(question.file.id),
        expires=timedelta(minutes=5)  # ссылка валидна 5 минут
    )

    # Отправляем картинку и клавиатуру
    await message.answer_photo(
        photo=media_url,
        caption="ABOBA?",
        reply_markup=keyboard
    )

    # Сохраняем в состоянии текущий вопрос и обновляем список заданных
    await state.update_data(question_id=question.id)

@router.callback_query(lambda c: c.data and c.data.startswith("answer:"))
@inject
async def handle_answer(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession = Provide[C.db_session]
):
    """
    Обработчик ответа пользователя: проверяет правильность и отправляет следующий вопрос.
    """
    # Подтверждаем обработку callback, чтобы убрать «часики» у пользователя
    await callback.answer()

    data = await state.get_data()
    current_qid: int = data.get("question_id")
    selected_id = int(callback.data.split("\":\", 1)[1])

    qr = QuestionRepository(session)
    question = await qr.get_by_id(current_qid)

    # Проверяем правильность
    if selected_id == question.id:
        result_text = "✅ Правильно!"
    else:
        result_text = f"❌ Неверно! Правильный ответ: {question.answer_text}"

    # Отправляем результат и следующий вопрос
    await callback.message.answer(result_text)
    await send_question(callback.message, state)

