import asyncio
import os
from database_tools.db_main import init_db
from database_tools.db_queries import add_pet, find_similar_pets
from models.tools import init_models, get_embedding_from_image
from database_tools.db_main import PetStatus

async def load_local_image(filepath: str) -> bytes:
    with open(filepath, "rb") as f:
        return f.read()

async def main():
    print("=== 1. Инициализация ===")
    await init_db()
    init_models()
    print("========================\n")

    # Пути к тестовым файлам
    img_lost = "./test_images/dog_lost.jpg"
    img_found = "./test_images/dog_found.jpg"
    img_other = "./test_images/cat_found.jpg"

    if not all(os.path.exists(p) for p in [img_lost, img_found, img_other]):
        print("❌ Ошибка: Положи картинки (dog_lost.jpg, dog_found.jpg, cat_found.jpg) в папку test_images!")
        return

    print("=== 2. Обработка 'Потерянной' собаки (Эмуляция заявки от хозяина) ===")
    img_lost_bytes = await load_local_image(img_lost)
    emb_lost, pet_type_lost = await get_embedding_from_image(img_lost_bytes, save_debug=True)
    
    if emb_lost is None:
        print("❌ На фото dog_lost.jpg животное не найдено!")
        return
        
    print("✅ Эмбеддинг потерянной собаки получен. Сохраняем в БД...")
    # Добавляем в БД как LOST
    await add_pet(
        pet_type=pet_type_lost, 
        status=PetStatus.LOST, 
        city="Москва", 
        photo_id="test_photo_1", 
        tg_id=111, 
        embedding=emb_lost
    )
    print("В БД добавлена запись о потерянной собаке.\n")


    print("=== 3. Обработка 'Найденного' кота (Шум для БД) ===")
    img_other_bytes = await load_local_image(img_other)
    emb_other, pet_type_other = await get_embedding_from_image(img_other_bytes, save_debug=True)
    if emb_other:
        await add_pet(pet_type_other, PetStatus.FOUND, "Москва", "test_photo_2", 222, emb_other)
        print("В БД добавлена запись о найденном коте.\n")


    print("=== 4. Обработка 'Найденной' собаки (Эмуляция того, кто нашел) ===")
    img_found_bytes = await load_local_image(img_found)
    emb_found, pet_type_found = await get_embedding_from_image(img_found_bytes, save_debug=True)
    
    print("✅ Эмбеддинг найденной собаки вычислен. Ищем совпадения в БД...")
    
    # Ищем среди ПОТЕРЯННЫХ в Москве
    similar_pets = await find_similar_pets(
        target_embedding=emb_found,
        city="Москва",
        target_status=PetStatus.LOST,
        threshold=0.4 # Порог 0.4 - обычно хороший старт для DINOv2
    )

    print("\n=== РЕЗУЛЬТАТЫ ПОИСКА ===")
    if similar_pets:
        print(f"🎉 Найдено {len(similar_pets)} похожих питомцев!")
        for pet, distance in similar_pets:
            # (1 - distance) переводит косинусное расстояние в процент сходства (от 0 до 100%)
            similarity = (1 - distance) * 100
            print(f"-> ID: {pet.id} | Тип: {pet.type} | Совпадение: {similarity:.1f}% (Distance: {distance:.4f})")
    else:
        print("❌ Совпадений не найдено. (Попробуй увеличить threshold)")

if __name__ == "__main__":
    # Для Windows, чтобы не было ошибок с asyncio
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())