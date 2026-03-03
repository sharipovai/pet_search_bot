import asyncio
from loader import bot
from telebot import asyncio_filters
import handlers
from models.tools import init_models
from database_tools.db_main import init_db

async def main():
    await init_db()
    init_models()
    bot.add_custom_filter(asyncio_filters.StateFilter(bot))
    print("Бот запущен")
    await bot.infinity_polling()

if __name__ == "__main__":
    asyncio.run(main())
