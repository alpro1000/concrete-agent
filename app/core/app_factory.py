# app/core/app_factory.py
"""
Фабрика приложения с автоматической регистрацией компонентов
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
import logging

from .router_registry import router_registry

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    
    # Startup
    logger.info("🚀 Запуск Concrete Intelligence System")
    
    # Создаем директории
    directories = ['uploads', 'temp', 'logs', 'exports']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    # Автоматически обнаруживаем и регистрируем роутеры
    routers = router_registry.discover_routers()
    logger.info(f"📊 Обнаружено роутеров: {len(routers)}")
    
    # Регистрируем найденные роутеры
    for router_info in routers:
        try:
            app.include_router(
                router_info['router'],
                prefix=router_info.get('prefix', ''),
                tags=router_info.get('tags', [router_info['name']])
            )
            logger.info(f"✅ {router_info['name']}: {router_info['routes_count']} endpoints")
        except Exception as e:
            logger.error(f"❌ Ошибка регистрации {router_info['name']}: {e}")
    
    # Сохраняем реестр в состоянии приложения
    app.state.router_registry = router_registry
    
    registry_status = router_registry.get_registry_status()
    logger.info(f"✅ Система запущена: {registry_status['successful']}/{registry_status['total_discovered']} роутеров активно")
    
    yield
    
    # Shutdown
    logger.info("🔄 Завершение работы системы")
    

def create_app() -> FastAPI:
    """Создает и настраивает FastAPI приложение"""
    
    app = FastAPI(
        title="Concrete Intelligence System",
        description="""
        🧠 Интеллектуальная система анализа строительной документации
        
        **Автоматическая регистрация компонентов:**
        - Роутеры подключаются автоматически из app/routers/
        - Агенты регистрируются динамически
        - Добавление новых модулей не требует изменения main.py
        
        **Поддерживаемые стандарты:**
        - Бетон: ČSN EN 206+A2
        - Сталь: ČSN EN 10025
        - Теплотехника: ČSN 73 0540
        """,
        version="2.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Статические файлы
    static_dir = Path("static")
    if static_dir.exists():
        from fastapi.staticfiles import StaticFiles
        app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # Основные endpoints
    setup_core_endpoints(app)
    
    return app


def setup_core_endpoints(app: FastAPI):
    """Настройка основных endpoints"""
    
    from fastapi.responses import HTMLResponse, JSONResponse
    from datetime import datetime
    
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Главная страница с автоматически сгенерированной информацией"""
        
        # Получаем информацию о роутерах
        registry = getattr(app.state, 'router_registry', None)
        routers_info = ""
        
        if registry:
            status = registry.get_registry_status()
            
            routers_info = f"""
            <div class="registry-status">
                <h2>📊 Статус роутеров</h2>
                <div class="stats">
                    <span class="stat success">✅ Активных: {status['successful']}</span>
                    <span class="stat error">❌ Ошибок: {status['failed']}</span>
                    <span class="stat total">📦 Всего: {status['total_discovered']}</span>
                </div>
                
                <div class="routers-grid">
            """
            
            for router_name, router_data in status['detailed_status'].items():
                routers_info += f"""
                <div class="router-card">
                    <h3>{router_name}</h3>
                    <p class="prefix">{router_data.get('prefix', 'No prefix')}</p>
                    <p class="routes">Endpoints: {router_data.get('routes_count', 0)}</p>
                    <div class="tags">
                        {' '.join([f'<span class="tag">{tag}</span>' for tag in router_data.get('tags', [])])}
                    </div>
                </div>
                """
            
            routers_info += """
                </div>
            </div>
            """
        
        return f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Concrete Intelligence System</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }}
                .container {{ 
                    max-width: 1200px; 
                    margin: 0 auto; 
                    background: white;
                    border-radius: 15px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .header {{ 
                    text-align: center; 
                    padding: 40px;
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    color: white;
                }}
                .header h1 {{ font-size: 2.5rem; margin-bottom: 10px; }}
                .header p {{ font-size: 1.1rem; opacity: 0.9; }}
                
                .registry-status {{ padding: 30px; }}
                .registry-status h2 {{ color: #333; margin-bottom: 20px; }}
                .stats {{ 
                    display: flex; 
                    gap: 20px; 
                    margin-bottom: 30px;
                    justify-content: center;
                }}
                .stat {{ 
                    padding: 10px 20px; 
                    border-radius: 25px; 
                    font-weight: 600;
                }}
                .stat.success {{ background: #d4edda; color: #155724; }}
                .stat.error {{ background: #f8d7da; color: #721c24; }}
                .stat.total {{ background: #e2e3e5; color: #383d41; }}
                
                .routers-grid {{ 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
                    gap: 20px;
                }}
                .router-card {{ 
                    background: #f8f9fa; 
                    padding: 20px; 
                    border-radius: 10px;
                    border-left: 4px solid #007bff;
                    transition: transform 0.2s;
                }}
                .router-card:hover {{ transform: translateY(-2px); }}
                .router-card h3 {{ color: #007bff; margin-bottom: 8px; }}
                .router-card .prefix {{ 
                    color: #6c757d; 
                    font-family: monospace; 
                    background: #e9ecef;
                    padding: 4px 8px;
                    border-radius: 4px;
                    display: inline-block;
                    margin-bottom: 8px;
                }}
                .router-card .routes {{ color: #495057; margin-bottom: 10px; }}
                .tags {{ display: flex; flex-wrap: wrap; gap: 5px; }}
                .tag {{ 
                    background: #007bff; 
                    color: white; 
                    padding: 2px 8px; 
                    border-radius: 12px; 
                    font-size: 0.8rem;
                }}
                
                .actions {{ 
                    padding: 30px; 
                    text-align: center; 
                    background: #f8f9fa;
                }}
                .actions a {{ 
                    display: inline-block; 
                    margin: 0 10px; 
                    padding: 12px 30px; 
                    background: #007bff; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 25px;
                    transition: all 0.3s;
                }}
                .actions a:hover {{ 
                    background: #0056b3; 
                    transform: translateY(-2px);
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🧠 Concrete Intelligence System</h1>
                    <p>Автоматическая регистрация компонентов v2.1</p>
                </div>
                
                {routers_info}
                
                <div class="actions">
                    <a href="/docs">📚 API Документация</a>
                    <a href="/system/routers">🔍 Реестр роутеров</a>
                    <a href="/health">❤️ Статус системы</a>
                </div>
            </div>
        </body>
        </html>
        """
    
    @app.get("/system/routers")
    async def get_routers_registry():
        """Подробная информация о зарегистрированных роутерах"""
        registry = getattr(app.state, 'router_registry', None)
        if not registry:
            return {"error": "Router registry не инициализирован"}
        
        return registry.get_registry_status()
    
    @app.get("/health")
    async def health_check():
        """Проверка состояния системы"""
        registry = getattr(app.state, 'router_registry', None)
        registry_status = registry.get_registry_status() if registry else {}
        
        return {
            "service": "Concrete Intelligence System",
            "version": "2.1.0", 
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "auto_discovery": True,
            "routers": registry_status
        }