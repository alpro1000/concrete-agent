# ===============================================
# Concrete Agent — Backend Dockerfile (Stable)
# Environment: Python 3.11 / FastAPI / Render
# ===============================================

FROM python:3.11-slim AS base

# Рабочая директория
WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements из текущего контекста (backend/)
COPY requirements.txt /app/requirements.txt

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r /app/requirements.txt

# Копируем приложение
COPY app /app/app

# Создаем нужные директории
RUN mkdir -p /app/logs /app/storage /app/uploads

# Настройка переменных окружения
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Открываем порт
EXPOSE 8000

# Проверка здоровья приложения
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Запускаем сервер
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
