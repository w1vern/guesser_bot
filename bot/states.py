

from typing import Type

from aiogram.fsm.state import State, StatesGroup


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