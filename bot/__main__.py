

import asyncio

from enum import Enum
import math
from uuid import UUID

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BufferedInputFile, ReplyKeyboardMarkup, KeyboardButton

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.main import DatabaseSessionManager, get_db_url
from db.models.user import User
from db.repositories.battle_repository import BattleRepository
from db.repositories.question_repository import QuestionRepository
from db.repositories.user_repository import UserRepository
from db.s3 import get_s3_client
import math
from typing import Protocol, Tuple


def change_rank(user_rank: float, question_rank: float, result: bool) -> Tuple[float, float]:
    k = 5.0
    alpha = 0.1

    p_user = 1 / (1 + math.exp(k * (question_rank - user_rank)))

    tmp = int(result)

    user_diff = alpha * (tmp - p_user) * user_rank * (1 - user_rank)
    question_diff = alpha * (p_user - tmp) * \
        question_rank * (1 - question_rank)

    return user_diff, question_diff


async def get_user(tg_id: int, session: AsyncSession) -> User:
    ur = UserRepository(session)
    user = await ur.get_by_tg_id(tg_id)
    if user:
        return user
    raise Exception("something 3")


def convert_rank(rank: float) -> int:
    return int(rank*1000)


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

class StaticButton():
    def __init__(self, text: str, only_for_admin: bool = False, only_for_creator: bool = False) -> None:
        self.text = text
        self.only_for_admin = only_for_admin
        self.only_for_creator = only_for_creator

    text: str
    only_for_admin: bool
    only_for_creator: bool

class StaticButtons:
    start_game = StaticButton("start game")
    end_game = StaticButton("end game")
    settings = StaticButton("settings")
    content = StaticButton("content", only_for_creator=True)
    creators = StaticButton("content", only_for_admin=True)
    main_menu = StaticButton("back to main menu")



""" class Dirs(str, Enum):
    main_menu = "main_menu"
    settings = "settings"
    play = "play"
    creators = "creators"
    content = "content"

static_buttons = {
    Dirs.main_menu.value: ["start game", "settings"],
} """

router = Router()


class AppState(StatesGroup):
    main_menu = State()
    play = State()
    settings = State()
    content = State()
    creators = State()


class GetKeyboardSizeFunction(Protocol):
    def __call__(self,
                 values: list[str]
                 ) -> list[int]:
        ...


def get_keyboard_size(values: list[str]) -> list[int]:
    length = len(values)
    res = []
    for i in range(4, length, 4):
        res.append(4)
    res.append(length % 4)
    return res


def create_keyboard(values: list[str], keyboard_size: GetKeyboardSizeFunction = get_keyboard_size) -> ReplyKeyboardMarkup:
    markup = keyboard_size(values)
    keyboard = []
    index = 0
    for i in range(len(values)):
        for j in range(markup[i]):
            keyboard.append(KeyboardButton(text=values[index]))
            index += 1

    return ReplyKeyboardMarkup(keyboard=keyboard)


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
            await send_target.answer_voice(voice=input_file, caption=caption, reply_markup=keyboard)
        case _:
            send_target.answer("internal server error")

    await state.update_data(question_id=current_question.id)


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    async with session_manager.context_session() as session:
        if not message.from_user:
            raise Exception("something 4")
        user = await get_user(message.from_user.id, session)
        await message.answer(f"hello, your rank: {user.rank}")


@router.message()
async def handle_button(message: types.Message, state: FSMContext):
    text = message.text
    current = await state.get_state()

    match current:
        case AppState.main_menu.state:
            match text:
                case StaticButtons.start_game.text:
                    pass
                case StaticButtons.settings.text:
                    pass
                case StaticButtons.content.text:
                    pass
                case StaticButtons.creators.text:
                    pass
                case _:
                    pass
        case AppState.play.state:
            match text:
                case StaticButtons.end_game.text:
                    pass

                case _:
                    pass
        case AppState.settings.state:
            pass
        case AppState.content.state:
            pass
        case AppState.creators.state:
            pass
        case _:
            pass


async def main():
    bot = Bot(token=settings.tg_bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
