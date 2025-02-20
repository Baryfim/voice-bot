import asyncio
from pathlib import Path
from aiogram import Bot, Dispatcher

from handlers import audio_handlers
from config.settings import settings


async def main():
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    Path("temp").mkdir(exist_ok=True)

    dp.include_router(audio_handlers.audio_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())