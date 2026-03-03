import config
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage

bot = AsyncTeleBot(config.test_bot_token)

state_storage = StateMemoryStorage()