import asyncio
import logging

from maxapi import Bot, Dispatcher, F
from maxapi.types import MessageCreated

from core.main import main
from config import MAX_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(MAX_TOKEN)
dp = Dispatcher()

@dp.message_created(F.message.body.text)
async def echo(event: MessageCreated):
    text = event.message.body.text
    try:
        user_name = event.message.sender.first_name
    except:
        user_name = "пользователь"

    reply_text = main(text, user_name)

    await event.message.answer(reply_text)

    #logger.info(f"{reply_text}")


async def start_bot():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(start_bot())