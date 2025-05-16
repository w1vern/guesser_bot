
import asyncio
import math
import random
from typing import Annotated, Awaitable, Protocol, Tuple, Type

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import (BufferedInputFile, KeyboardButton,
                           ReplyKeyboardMarkup, ReplyKeyboardRemove)
from fast_depends import Depends, inject
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.main import DatabaseSessionManager, get_db_url
from db.models.question import Question
from db.models.user import User
from db.repositories.battle_repository import BattleRepository
from db.repositories.question_repository import QuestionRepository
from db.repositories.user_repository import UserRepository
from db.s3 import get_s3_client

session_manager = DatabaseSessionManager(
    get_db_url(
        user=settings.db_user,
        password=settings.db_password,
        ip=settings.db_ip,
        port=settings.db_port,
        name=settings.db_name
    ), {"echo": False}
)

Session = Annotated[AsyncSession, Depends(session_manager.session)]


def change_rank(user_rank: float,
                question_rank: float,
                result: bool
                ) -> Tuple[float, float]:
    k = 5.0
    alpha = 0.1

    p_user = 1 / (1 + math.exp(k * (question_rank - user_rank)))

    tmp = int(result)

    user_diff = alpha * (tmp - p_user) * user_rank * (1 - user_rank)
    question_diff = alpha * (p_user - tmp) * \
        question_rank * (1 - question_rank)

    return user_diff, question_diff


def convert_rank(rank: float
                 ) -> int:
    return int(rank*1000)


async def get_user(message: types.Message,
                   session: Session
                   ) -> User:
    if not message.from_user:
        raise Exception("something 16")
    ur = UserRepository(session)
    user = await ur.get_by_tg_id(message.from_user.id)
    if user:
        return user
    raise Exception("something 3")
GetUser = Annotated[User, Depends(get_user)]


async def register_user(message: types.Message,
                        session: Session
                        ) -> User:
    if not message.from_user:
        raise Exception("something 16")
    ur = UserRepository(session)
    user = await ur.get_by_tg_id(message.from_user.id)
    if user:
        return user
    user = await ur.create(message.from_user.id)
    if not user:
        raise Exception("something 7")
    return user
CreateUser = Annotated[User, Depends(register_user)]


class StaticButton():
    def __init__(self,
                 text: str,
                 only_for_admin: bool = False,
                 only_for_creator: bool = False
                 ) -> None:
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
    creators = StaticButton("creators", only_for_admin=True)
    main_menu = StaticButton("back to main menu")
    todo_note = StaticButton("need more buttons there")


router = Router()


class MyState(State):
    def __init__(self,
                 state: str,
                 parent_state: "MyState | None" = None
                 ) -> None:
        self._state = state
        self._group_name = None
        self._group: Type[StatesGroup] | None = None
        self._parent = parent_state

    @property
    def state(self) -> str:
        if self._parent:
            return f"{self._parent.state}/{self._state}"
        return self._state


class AppState(StatesGroup):
    main_menu = MyState("main_menu")
    play = MyState("play", main_menu)
    settings_menu = MyState("settings_menu", main_menu)
    content_menu = MyState("content_menu", main_menu)
    creators_menu = MyState("creators_menu", main_menu)


class GetKeyboardSizeFunction(Protocol):
    def __call__(self,
                 values: list[str]
                 ) -> list[int]:
        ...


def get_keyboard_size(values: list[str]
                      ) -> list[int]:
    in_a_row = 4
    length = len(values)
    res: list[int] = []
    for _ in range(in_a_row, length + 1, in_a_row):
        res.append(4)
    if length % in_a_row:
        res.append(length % in_a_row)
    return res


def create_keyboard(values: list[str],
                    keyboard_size: GetKeyboardSizeFunction = get_keyboard_size
                    ) -> ReplyKeyboardMarkup:
    markup = keyboard_size(values)
    keyboard: list[list[KeyboardButton]] = []
    index = 0
    for i in range(len(markup)):
        keyboard.append([])
        for j in range(markup[i]):
            keyboard[i].append(KeyboardButton(text=values[index]))
            index += 1

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, input_field_placeholder="guess")


async def send_question(target: types.Message,
                        state: FSMContext,
                        session: Session
                        ) -> None:
    qr = QuestionRepository(session)
    current_question = await qr.get_random_question()
    if not current_question:
        raise Exception("something 5")
    questions = await qr.get_random_questions(current_question.answers_count - 1, [current_question])
    questions.append(current_question)

    keyboard = game_keyboard(questions)
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

    if not target:
        raise Exception("something 1")

    match media_type:
        case "image":
            await target.answer_photo(photo=input_file, caption=caption, reply_markup=keyboard)

        case "video":
            await target.answer_video(video=input_file, caption=caption, reply_markup=keyboard)

        case "audio":
            await target.answer_voice(voice=input_file, caption=caption, reply_markup=keyboard)
        case _:
            await target.answer("internal server error")

    await state.update_data(question_id=current_question.id)


def main_menu_keyboard(user: User
                       ) -> ReplyKeyboardMarkup:
    values: list[str] = []
    values.append(StaticButtons.start_game.text)
    values.append(StaticButtons.settings.text)
    if user.admin:
        values.append(StaticButtons.creators.text)
    if user.creator:
        values.append(StaticButtons.content.text)
    return create_keyboard(values)


def game_keyboard(questions: list[Question]
                  ) -> ReplyKeyboardMarkup:
    values: list[str] = []
    for q in questions:
        values.append(q.answer)
    random.shuffle(values)
    values.append(StaticButtons.end_game.text)
    return create_keyboard(values)


def settings_keyboard(user: User
                      ) -> ReplyKeyboardMarkup:
    return create_keyboard([StaticButtons.todo_note.text, StaticButtons.main_menu.text])


def content_keyboard(user: User
                     ) -> ReplyKeyboardMarkup:
    return create_keyboard([StaticButtons.todo_note.text, StaticButtons.main_menu.text])


def creators_keyboard(user: User
                      ) -> ReplyKeyboardMarkup:
    return create_keyboard([StaticButtons.todo_note.text, StaticButtons.main_menu.text])


async def start_game(message: types.Message,
                     state: FSMContext,
                     user: User,
                     session: AsyncSession
                     ) -> None:
    await state.set_state(AppState.play)
    await send_question(message, state, session)


async def end_game(message: types.Message,
                   state: FSMContext,
                   user: User,
                   session: AsyncSession
                   ) -> None:
    await to_main_menu(message, state, user, session)


async def to_main_menu(message: types.Message,
                       state: FSMContext,
                       user: User,
                       session: AsyncSession
                       ) -> None:
    await state.set_state(AppState.main_menu)
    await message.answer(text="use keyboard", reply_markup=main_menu_keyboard(user))


async def need_more_buttons_note(message: types.Message,
                                 state: FSMContext,
                                 user: User,
                                 session: AsyncSession
                                 ) -> None:
    await message.answer(text="chose another button")


async def edit_settings(message: types.Message,
                        state: FSMContext,
                        user: User,
                        session: AsyncSession
                        ) -> None:
    await state.set_state(AppState.settings_menu)
    await message.answer(text="use keyboard", reply_markup=settings_keyboard(user))


async def edit_content(message: types.Message,
                       state: FSMContext,
                       user: User, session:
                       AsyncSession
                       ) -> None:
    await state.set_state(AppState.content_menu)
    await message.answer(text="use keyboard", reply_markup=content_keyboard(user))


async def edit_creators(message: types.Message,
                        state: FSMContext,
                        user: User,
                        session: AsyncSession
                        ) -> None:
    await state.set_state(AppState.creators_menu)
    await message.answer(text="use keyboard", reply_markup=creators_keyboard(user))


async def incorrect_input(message: types.Message,
                          state: FSMContext,
                          user: User,
                          session: AsyncSession
                          ) -> None:
    await message.answer(text="error, use keyboard")


async def handle_answer(message: types.Message,
                        state: FSMContext,
                        user: User,
                        session: AsyncSession
                        ) -> None:
    if not message.text:
        raise Exception("something 2")
    data = await state.get_data()
    correct_id = data.get("question_id")
    if correct_id is None:
        await message.answer("something went wrong")
        return

    qr = QuestionRepository(session)
    correct_answer = await qr.get_by_id(correct_id)
    if correct_answer is None:
        raise Exception("Correct question not found")
    ur = UserRepository(session)
    br = BattleRepository(session)

    res = message.text == correct_answer.answer
    battle = await br.create(user, correct_answer, res, change_rank)
    if not battle:
        raise Exception("something 10")
    await ur.change_rank(user, battle.user_change)
    await qr.change_rank(correct_answer, battle.question_change)

    if res:
        await message.answer(f"✅ Right! Rank change: +{convert_rank(battle.user_rank + battle.user_change) - convert_rank(battle.user_rank)} (now {convert_rank(battle.user_change + battle.user_rank)})")
    else:
        await message.answer(f"❌ Wrong! The right answer is {correct_answer.file.answer}. Rank change: {convert_rank(battle.user_rank + battle.user_change) - convert_rank(battle.user_rank)} (now {convert_rank(battle.user_change + battle.user_rank)})")

    await send_question(message, state, session)


@router.message(Command("start"))
@inject
async def cmd_start(message: types.Message,
                    state: FSMContext,
                    user: CreateUser,
                    session: Session
                    ) -> None:
    await message.answer(f"hello, your rank: {user.rank}")
    await to_main_menu(message, state, user, session)


class Handler(Protocol):
    def __call__(self,
                 message: types.Message,
                 state: FSMContext,
                 user: GetUser,
                 session: AsyncSession
                 ) -> Awaitable[None]:
        ...


behavioral_dict: dict[str, Handler] = {
    f"{AppState.main_menu.state}/{StaticButtons.start_game.text}": start_game,
    f"{AppState.main_menu.state}/{StaticButtons.settings.text}": edit_settings,
    f"{AppState.main_menu.state}/{StaticButtons.creators.text}": edit_creators,
    f"{AppState.main_menu.state}/{StaticButtons.content.text}": edit_content,
    f"{AppState.play.state}/{StaticButtons.end_game.text}": end_game,
    f"{AppState.play.state}": handle_answer,
    f"{AppState.content_menu.state}": incorrect_input,
    f"{AppState.creators_menu.state}": incorrect_input,
    f"{AppState.settings_menu.state}": incorrect_input,
    f"{AppState.settings_menu.state}/{StaticButtons.todo_note.text}": need_more_buttons_note,
    f"{AppState.creators_menu.state}/{StaticButtons.todo_note.text}": need_more_buttons_note,
    f"{AppState.content_menu.state}/{StaticButtons.todo_note.text}": need_more_buttons_note,
    f"{AppState.settings_menu.state}/{StaticButtons.main_menu.text}": to_main_menu,
    f"{AppState.creators_menu.state}/{StaticButtons.main_menu.text}": to_main_menu,
    f"{AppState.content_menu.state}/{StaticButtons.main_menu.text}": to_main_menu
}


def get_func(current_state: str | None,
             message: str | None
             ) -> Handler:
    if not current_state:
        raise Exception("current state is None")
    if not message:
        raise Exception("message is None")
    func = behavioral_dict.get(f"{current_state}/{message}")
    if not func:
        func = behavioral_dict.get(current_state)
    if not func:
        func = incorrect_input
    return func


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


async def main() -> None:
    bot = Bot(token=settings.tg_bot_token)
    dp = Dispatcher()

    @dp.startup()
    @inject
    async def on_startup(session: Session
                         ) -> None:
        ur = UserRepository(session)
        users = await ur.all()
        for user in users:
            state = FSMContext(storage=dp.storage, key=StorageKey(
                bot.id, user.tg_id, user.tg_id))
            await state.set_state(AppState.main_menu)
            await bot.send_message(chat_id=user.tg_id, text="bot startup", reply_markup=main_menu_keyboard(user))

    @dp.shutdown()
    @inject
    async def on_shutdown(session: Session
                          ) -> None:
        ur = UserRepository(session)
        users = await ur.all()
        for user in users:
            await bot.send_message(user.tg_id, "bot shuting down", reply_markup=ReplyKeyboardRemove())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
