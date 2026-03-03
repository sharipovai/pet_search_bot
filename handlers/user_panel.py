from telebot import types
from telebot.types import Message

from loader import bot
from states import BotStates
from .start_menu import main_menu

from database_tools.db_main import PetStatus
from database_tools.db_queries import add_pet, find_similar_pets
from models.tools import get_embedding_from_image


@bot.message_handler(state="*", func=lambda msg: msg.text == 'Отмена')
async def cancel_any_action(message: Message):
    """
    Отменяет любое действие и возвращает в главное меню.
    """
    await bot.reset_data(message.from_user.id, message.chat.id)
    await bot.delete_state(message.from_user.id, message.chat.id)
    await bot.send_message(message.chat.id, "❌ Отменено")
    await main_menu(message)


# # # ДОБАВЛЕНИЕ ПИТОМЦА # # #

async def _add_pet_init(message: Message, data: dict):
    """
    Начало процесса добавления нового питомца. Запрашивает название города.
    """
    data['step'] = "city"
    await bot.send_message(message.chat.id, "Введите название города:",
                           reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add('Отмена'))

async def _add_pet_city(message: Message, data:dict):
    """
    Обрабатывает введенный город и запрашивает его изображения.
    """
    data['city'] = message.text
    data['step'] = "image"
    await bot.send_message(message.chat.id, "Пришлите фото питомца, желательно сделать несколько фотографий с разных ракурсов.")

async def _catch_pet_images(message: Message, data:dict):
    # Получаем данные из FSM
    if 'photos' not in data:
        data['photos'] = []
    
    # Берем фото в лучшем качестве
    file_id = message.photo[-1].file_id
    data['photos'].append(file_id)
    
    # Чтобы не спамить сообщениями на каждую фотку из альбома, 
    # проверяем media_group_id
    if not message.media_group_id or message.media_group_id != data.get('last_media_group'):
        data['last_media_group'] = message.media_group_id
        
        # Предлагаем завершить загрузку
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True).add("Завершить загрузку")
        
        await bot.send_message(
            message.chat.id, 
            "Фото получено! 📸\nПришлите еще фото с других ракурсов или нажмите кнопку ниже, если закончили.",
            reply_markup=markup
        )


async def _save_and_search_photo(message: Message, data:dict):
    photos = data.get('photos', [])
    if not photos:
        return await bot.send_message(message.chat.id, "Вы не прислали ни одной фотографии.")

    success_count = 0
    
    # Проходимся по каждой загруженной фотографии
    for photo_id in photos:
        try:
            # 1. Скачиваем фото
            file_info = await bot.get_file(photo_id)
            file_content = await bot.download_file(file_info.file_path)
            
            # 2. ПРОГОНЯЕМ ЧЕРЕЗ НЕЙРОСЕТИ (Твоя функция)
            # ВАЖНО: Эмбеддинг должен генерироваться здесь для каждого фото отдельно!
            
            embedding, pet_type = await get_embedding_from_image(file_content, save_debug=True) 
            
            # Если на фото нет животного (YOLO его не нашел), пропускаем
            if not embedding or not pet_type:
                continue

            # 3. Сохраняем в БД как отдельную запись
            await add_pet(
                pet_type=pet_type, 
                status=data['status'], # или статус из data
                city=data['city'], 
                photo_id=photo_id, # ID конкретной фотки
                tg_id=message.from_user.id, 
                embedding=embedding # Эмбеддинг ИМЕННО ЭТОЙ фотки
            )
            success_count += 1
            
        except Exception as e:
            print(f"Ошибка при сохранении фото {photo_id}: {e}")

        similar_pets = await find_similar_pets(
            target_embedding=embedding,
            city=data['city'],
            pet_type=pet_type,
            target_status=PetStatus.LOST if data['status'] == PetStatus.FOUND else PetStatus.FOUND, # Ищем противоположный статус
            threshold=0.4 # Порог косинусного расстояния
        )

        if similar_pets:
            print("🎉 Найдены совпадения!")
            for pet, distance in similar_pets:
                print(f"ID: {pet.id}, Совпадение: {(1 - distance)*100:.1f}%, Фото: {pet.photo_id}, Нашел пользователь ID: {pet.tg_id}")
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=pet.photo_id,
                    caption = f"🎉 Найден похожий питомец!\nТип: {pet.type}\nНашел пользователь ID: <a href='tg://user?id={pet.tg_id}'>Написать в Telegram</a>",
                    parse_mode='HTML'
                )
        else:
            print("😔 Совпадений не найдено для этого фото.")
            await bot.send_message(message.chat.id, "😔 Совпадений не найдено для этого фото.")

    # Подводим итоги
    if success_count > 0:
        await bot.send_message(message.chat.id, f"✅ Успешно сохранено {success_count} фото питомца!")
    else:
        await bot.send_message(message.chat.id, "❌ Не удалось распознать животное на фотографиях. Попробуйте другие кадры.")

    # Только теперь, когда всё обработано, очищаем state
    data.clear() 
    await bot.delete_state(message.from_user.id, message.chat.id)
    await main_menu(message) # Возврат в главное меню


@bot.message_handler(state=BotStates.add_new_pet, content_types=['text', 'photo'])
async def add_new_pet(message: Message, pet_status: str = None):
    """Диспетчер для добавления нового питомца"""
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        step = data.get('step')
        if step is None:
            data['status'] = pet_status
            if not await _add_pet_init(message, data):
                return
        elif step == 'city':
            await _add_pet_city(message, data)
        elif step == 'image':
            if message.content_type == 'text' and message.text.lower() == "завершить загрузку":
                 data['step'] = "save_and_search"
                 await _save_and_search_photo(message, data)
            else:
                await _catch_pet_images(message, data) 
        else:
            await bot.send_message(message.chat.id, "Произошла ошибка. Попробуйте снова.")
            data.clear() 
            await bot.delete_state(message.from_user.id, message.chat.id)
            await main_menu(message)