from sqlalchemy import select
from database_tools.db_main import async_session, Pet, PetStatus

# --- 1. Добавление питомца в БД ---
async def add_pet(pet_type: str, status: PetStatus, city: str, photo_id: str, tg_id: int, embedding: list[float]):
    async with async_session() as session:
        new_pet = Pet(
            type=pet_type,
            status=status,
            city=city,
            photo_id=photo_id,
            tg_id=tg_id,
            embedding=embedding # Просто передаем list[float]
        )
        session.add(new_pet)
        await session.commit()
        return new_pet

# --- 2. Векторный поиск (Магия!) ---
async def find_similar_pets(target_embedding: list[float], city: str, pet_type: str, target_status: PetStatus, threshold: float):
    """
    Ищет похожих питомцев.
    Если собака потеряна, target_status должен быть FOUND, и наоборот.
    threshold - порог расстояния (чем меньше, тем больше сходство).
    """
    async with async_session() as session:
        # Считаем косинусное расстояние между сохраненными векторами и нашим
        distance = Pet.embedding.cosine_distance(target_embedding).label("distance")
        
        # Строим запрос
        query = (
            select(Pet, distance)
            .where(Pet.city == city) # Фильтр по городу
            .where(Pet.type == pet_type) # Фильтр по типу животного
            .where(Pet.status == target_status) # Фильтр по противоположному статусу
            .where(distance < threshold) # Отсекаем непохожих
            .order_by(distance) # Сортируем: самые похожие будут первыми
            .limit(3) # Берем Топ-3
        )
        
        result = await session.execute(query)
        # Возвращаем список кортежей (Pet, distance)
        return result.all()