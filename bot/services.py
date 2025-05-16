

from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from bot.dependencies import Handler, Session
from bot.keyboards import (StaticButtons, content_keyboard, creators_keyboard,
                           game_keyboard, main_menu_keyboard,
                           settings_keyboard)
from bot.states import AppState
from bot.utils import change_rank, convert_rank
from config import settings
from db.models import User
from db.repositories import (BattleRepository, QuestionRepository,
                             UserRepository)
from db.s3 import get_s3_client


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
