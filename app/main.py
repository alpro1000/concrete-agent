from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import upload, analyze

app = FastAPI(
    title="Concrete MVP Service",
    description="Сервис для анализа строительной документации",
    version="1.0.0"
)

# Разрешаем CORS
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
    return {
        "message": "Concrete Analyzer API",
        "endpoints": {
            "upload": "/upload/files",
            "analyze": "/analyze/concrete"
        }
    }

@app.get("/health")
def health():
    return {"status": "healthy"}
