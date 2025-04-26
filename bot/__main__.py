import asyncio

from uuid import UUID

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BufferedInputFile

from config import settings
from db.main import DatabaseSessionManager, get_db_url
from db.repositories.battle_repository import BattleRepository
from db.repositories.question_repository import QuestionRepository
from db.repositories.user_repository import UserRepository
from db.s3 import get_s3_client
from db.repositories.battle_repository import RankChangeFunction


def change_rank(user_rank: float, question_rank: float, res: bool) -> tuple[float, float]:
    return ((0.01, -0.01) if res else (-0.01, 0.01))


session_manager = DatabaseSessionManager(
    get_db_url(
        settings.db_user,
        settings.db_password,
        settings.db_ip,
        settings.db_port,
        settings.db_name
    ), {"echo": False}
)


class GameState(StatesGroup):
    playing = State()


async def send_question(target: types.Message | types.CallbackQuery, state: FSMContext):
    async with session_manager.context_session() as session:
        qr = QuestionRepository(session)
        questions = await qr.get_random_questions(4)
        question = questions[0]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=item.file.answer,
                                  callback_data=f"answer:{item.id}")]
            for item in questions
        ]
    )
    caption = "Что за фильм?"

    minio_client = get_s3_client()
    obj = minio_client.get_object(
        bucket_name=settings.minio_bucket,
        object_name=str(question.file.id)
    )
    data = obj.read()
    obj.close()
    input_file = BufferedInputFile(data, filename=f"{question.file.id}")

    media_type = question.file.file_type.split("/")[0]
    if isinstance(target, types.CallbackQuery):
        send_target = target.message
    else:
        send_target = target

    if media_type == "image":
        await send_target.answer_photo(photo=input_file, caption=caption, reply_markup=keyboard)
    elif media_type == "video":
        await send_target.answer_video(video=input_file, caption=caption, reply_markup=keyboard)
    elif media_type == "audio":
        await send_target.answer_audio(audio=input_file, caption=caption, reply_markup=keyboard)
    else:
        await send_target.answer(caption)

    await state.update_data(question_id=question.id)

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Напиши /start_game, чтобы начать игру.")


@router.message(Command("start_game"))
async def cmd_start_game(message: types.Message, state: FSMContext):
    await state.set_state(GameState.playing)
    await send_question(message, state)


@router.callback_query(lambda c: c.data and c.data.startswith("answer:"))
async def handle_answer(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    correct_id = data.get("question_id")
    if correct_id is None:
        await callback.message.answer("Что-то пошло не так — текущий вопрос не найден.")
        return

    selected_id = UUID(callback.data.split(":", 1)[1])

    async with session_manager.context_session() as session:
        qr = QuestionRepository(session)
        correct_question = await qr.get_by_id(correct_id)
        if correct_question is None:
            raise Exception("Correct question not found")
        ur = UserRepository(session)
        br = BattleRepository(session)
        user = await ur.get_by_tg_id(str(callback.from_user.id))
        if user is None:
            raise Exception("User not found")

        if selected_id == correct_id:
            await br.create(user=user, question=correct_question, result=True, rank_change_function=change_rank)
            await callback.message.answer("✅ Правильно!")
        else:
            await callback.message.answer(f"❌ Неверно! Правильный ответ: {correct_question.file.answer}")

    await send_question(callback, state)


async def main():
    bot = Bot(token=settings.tg_bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
