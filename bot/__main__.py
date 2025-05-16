
import asyncio

from aiogram import Bot, Dispatcher

from bot.handlers import router
from bot.lifecycle import register_lifecycle
from config import settings


async def main() -> None:
    bot = Bot(token=settings.tg_bot_token)
    dp = Dispatcher()

    dp.include_router(router)
    register_lifecycle(dp, bot)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
