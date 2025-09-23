FROM python:3.11.9-slim

# Установка системных зависимостей для обработки документов
RUN apt-get update && apt-get install -y \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-ces \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование requirements.txt первым (для кэширования слоев)
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копирование всего проекта
COPY . .

# Создание необходимых директорий
RUN mkdir -p uploads logs outputs

# Установка переменных окружения
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Проверка структуры приложения
RUN ls -la app/

# Команда запуска для Render
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
