from aiogram import Bot, Dispatcher
import sys
from core.settings import BOT_TOKEN
from aiogram.client.bot import DefaultBotProperties
import asyncio
import logging

from .handler.private import router

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
ds = Dispatcher()

ds.include_router(router)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.DEBUG)

logger.addHandler(stream_handler)


async def main():
    await ds.start_polling(bot)