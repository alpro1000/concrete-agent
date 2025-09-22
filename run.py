# run.py
import uvicorn
import os
import logging

# Создание папки logs
os.makedirs("logs", exist_ok=True)

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("logs/concrete_analysis.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

if __name__ == "__main__":
    is_development = os.getenv("ENVIRONMENT", "production") == "development"

    uvicorn.run(
        "app.main:app",  # <--- Путь к объекту FastAPI
        host="0.0.0.0",
        port=5000,
        reload=is_development
    )
