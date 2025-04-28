import asyncio

from uuid import UUID

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BufferedInputFile

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.main import DatabaseSessionManager, get_db_url
from db.models.user import User
from db.repositories.battle_repository import BattleRepository
from db.repositories.question_repository import QuestionRepository
from db.repositories.user_repository import UserRepository
from db.s3 import get_s3_client


def change_rank(user_rank: float, question_rank: float, result: bool) -> tuple[float, float]:
    return ((0.01, -0.01) if result else (-0.01, 0.01))


async def get_user(tg_id: int, session: AsyncSession) -> User:
    ur = UserRepository(session)
    user = await ur.get_by_tg_id(tg_id)
    if user:
        return user
    raise Exception("something 3")


async def register_user(tg_id: int, session: AsyncSession) -> User:
    ur = UserRepository(session)
    if await ur.get_by_tg_id(tg_id):
        raise Exception("something 6")
    user = await ur.create(tg_id)
    if not user:
        raise Exception("something 7")
    return user


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


class AppState(StatesGroup):
    main_menu = State()
    playing = State()
    editing_content = State()
    editing_creators = State()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    async with session_manager.context_session() as session:
        if not message.from_user:
            raise Exception("something 4")
        user = await get_user(message.from_user.id, session)
        await message.answer(f"hello, your rank: {user.rank}")


@router.message(Command("start_game"))
async def cmd_start_game(message: types.Message, state: FSMContext):
    await state.set_state(AppState.playing)
    await send_question(message, state)


@router.message(Command("end_game"))
async def cmd_end_game(message: types.Message, state: FSMContext):
    await state.set_state(AppState.main_menu)


async def send_question(target: types.Message | types.CallbackQuery, state: FSMContext):
    async with session_manager.context_session() as session:
        qr = QuestionRepository(session)
        current_question = await qr.get_random_question()
        if not current_question:
            raise Exception("something 5")
        questions = await qr.get_random_questions(current_question.answers_count - 1, [current_question])
        questions.append(current_question)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=item.file.answer,
                                  callback_data=f"answer:{item.id}")]
            for item in questions
        ]
    )
    caption = "Guess the film?"

    minio_client = get_s3_client()
    obj = minio_client.get_object(
        bucket_name=settings.minio_bucket,
        object_name=str(current_question.file.id)
    )
    data = obj.read()
    obj.close()
    input_file = BufferedInputFile(
        data, filename=f"{current_question.file.id}")

    media_type = current_question.file.file_type.split("/")[0]
    if isinstance(target, types.CallbackQuery):
        send_target = target.message
    else:
        send_target = target

    if not send_target:
        raise Exception("something 1")

    match media_type:
        case "image":
            await send_target.answer_photo(photo=input_file, caption=caption, reply_markup=keyboard)

        case "video":
            await send_target.answer_video(video=input_file, caption=caption, reply_markup=keyboard)

        case "audio":
            await send_target.answer_audio(audio=input_file, caption=caption, reply_markup=keyboard)
        case _:
            send_target.answer("internal server error")

    await state.update_data(question_id=current_question.id)


@router.callback_query(lambda c: c.data and c.data.startswith("answer:"))
async def handle_answer(callback: CallbackQuery, state: FSMContext):
    if not callback.message or not callback.data:
        raise Exception("something 2")
    await callback.answer()

    data = await state.get_data()
    correct_id = data.get("question_id")
    if correct_id is None:
        await callback.message.answer("something went wrong")
        return

    selected_id = UUID(callback.data.split(":", 1)[1])

    async with session_manager.context_session() as session:
        user = await get_user(callback.from_user.id, session)
        qr = QuestionRepository(session)
        correct_answer = await qr.get_by_id(correct_id)
        if correct_answer is None:
            raise Exception("Correct question not found")
        ur = UserRepository(session)
        br = BattleRepository(session)
        if user is None:
            raise Exception("User not found")

        res = selected_id == correct_id
        battle = await br.create(user, correct_answer, res, change_rank)
        if not battle:
            raise Exception("something 10")
        await ur.change_rank(user, battle.user_change)
        await qr.change_rank(correct_answer, battle.question_change)
        if not battle:
            raise Exception("something 8")

        if res:
            await callback.message.answer(f"✅ Right! Rank change: +{battle.user_change} (now {battle.user_change + battle.user_rank})")
        else:
            await callback.message.answer(f"❌ Wrong! The right answer is {correct_answer.file.answer}. Rank change: {battle.user_change} (now {battle.user_change + battle.user_rank})")

    await send_question(callback, state)


async def main():
    bot = Bot(token=settings.tg_bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
