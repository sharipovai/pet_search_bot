# Используем официальный легкий образ Python 3.11
FROM python:3.11-slim

# Настраиваем переменные окружения для Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Папка, куда HuggingFace (DINOv2) будет сохранять кэш модели
    HUGGINGFACE_HUB_CACHE=/app/.cache 

# Создаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости (gcc нужен для сборки asyncpg и других пакетов)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл с зависимостями
COPY requirements.txt .

# ПРО-СОВЕТ: Сначала ставим PyTorch для CPU (экономит ~3-4 ГБ места в образе!)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Затем устанавливаем остальные зависимости из файла
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь исходный код проекта внутрь контейнера
COPY . .

# Команда для запуска бота
CMD["python", "main.py"]
