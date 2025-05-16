
import random
from typing import Protocol

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from db.models import Question, User


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
