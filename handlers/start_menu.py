from loader import bot
from states import BotStates

from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton


@bot.message_handler(state=BotStates.main_menu)
async def main_menu(message: Message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("Я нашел питомца"))
    markup.row(KeyboardButton("Я потерял питомца"))
    markup.row(KeyboardButton("Техподдержка"))
    await bot.set_state(message.from_user.id, BotStates.wait_user_menu, message.chat.id)
    text = "Выберите действие"
    await bot.send_message(message.chat.id, text, reply_markup=markup)