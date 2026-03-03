from telebot.types import Message
from .user_panel import *
import config
from .start_menu import main_menu
from database_tools.db_main import init_db, PetStatus

@bot.message_handler(commands=['start'])
async def start_command(message: Message):
    await bot.send_message(message.chat.id, f'Привет, {message.from_user.first_name}!')
    await bot.send_message(message.chat.id, f'{config.first_message}')
    await init_db()
    await main_menu(message)
    
@bot.message_handler(state=BotStates.wait_user_menu)
async def wait_user_menu(message: Message):
    if message.text.lower() == 'я нашел питомца':
        await bot.set_state(message.from_user.id, BotStates.add_new_pet, message.chat.id)
        await add_new_pet(message, PetStatus.FOUND)
    elif message.text.lower() == 'я потерял питомца':
        await bot.set_state(message.from_user.id, BotStates.add_new_pet, message.chat.id)
        await add_new_pet(message, PetStatus.LOST)
    elif message.text.lower() == 'техподдержка':
        text = "Если есть вопросы, свяжитесь с нами @bot_helping"
        await bot.send_message(message.chat.id, text)
        await main_menu(message)
    else:
        await main_menu(message)