import asyncio
import logging
from aiogram import Bot, Dispatcher, types

from config import TELEGRAM_TOKEN
from core.main import main

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

@dp.message()
async def handle_message(message: types.Message):
    user_name = message.from_user.first_name
    reply_text = main(message.text, user_name)
    await message.answer(reply_text)
    logger.info(f"{reply_text}")

async def start_bot():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(start_bot())