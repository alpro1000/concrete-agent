from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import upload, analyze

app = FastAPI(
    title="Concrete MVP Service",
    description="Сервис для анализа строительной документации",
    version="0.1.0"
)

# Разрешаем CORS (например, для фронтенда)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(upload.router, prefix="/upload", tags=["Загрузка"])
app.include_router(analyze.router, prefix="/analyze", tags=["Анализ"])

@app.get("/")
def index():
    return {"message": "Concrete Analyzer API", "endpoints": ["/upload/files", "/analyze/concrete"]}
