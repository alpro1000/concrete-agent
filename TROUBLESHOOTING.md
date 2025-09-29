# 🛠️ Руководство по устранению неполадок Concrete Agent

## Быстрая диагностика

Если сервис не работает как ожидается, выполните следующие шаги:

### 1. Автоматическая диагностика
```bash
# Полная диагностика системы
python scripts/diagnose_service.py

# Сохранить отчет диагностики
python scripts/diagnose_service.py --save-report

# Проверить конкретный сервер
python scripts/diagnose_service.py --server-url http://localhost:8001
```

### 2. Проверка настройки
```bash
# Проверить установку модулей
python scripts/setup_modules.py

# Быстрая проверка возможности запуска
python scripts/start_service.py --check-only
```

### 3. Запуск сервиса
```bash
# Простой запуск
python scripts/start_service.py

# Запуск на другом порту
python scripts/start_service.py --port 8001

# Запуск без автоперезагрузки
python scripts/start_service.py --no-reload
```

## Частые проблемы и решения

### ❌ "Сервис не работает"

**Симптомы:**
- Сервер не отвечает
- Ошибки при обращении к API
- Браузер показывает "Connection refused"

**Диагностика:**
```bash
# Проверить запущен ли сервер
curl http://localhost:8000/health

# Проверить процессы
ps aux | grep uvicorn

# Проверить порты
netstat -tlnp | grep :8000
```

**Решения:**
1. **Запустить сервер:**
   ```bash
   python scripts/start_service.py
   # или
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Проверить логи запуска на ошибки**

3. **Проверить зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

### ❌ "ModuleNotFoundError" при запуске

**Симптомы:**
- `ModuleNotFoundError: No module named 'fastapi'`
- `ImportError: cannot import name 'X' from 'Y'`

**Решения:**
1. **Установить зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Проверить Python path:**
   ```bash
   python -c "import sys; print(sys.path)"
   ```

3. **Использовать виртуальное окружение:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # или
   venv\Scripts\activate     # Windows
   pip install -r requirements.txt
   ```

### ⚠️ "Claude/OpenAI недоступен"

**Симптомы:**
- Анализ документов не работает
- Ошибки "API key not configured"
- `claude_status: "disabled"`

**Решения:**
1. **Настроить API ключи:**
   ```bash
   # Для Claude (Anthropic)
   export ANTHROPIC_API_KEY="your_api_key_here"
   
   # Для OpenAI
   export OPENAI_API_KEY="your_api_key_here"
   ```

2. **Создать .env файл:**
   ```bash
   echo "ANTHROPIC_API_KEY=your_key_here" > .env
   echo "OPENAI_API_KEY=your_key_here" >> .env
   ```

3. **Получить API ключи:**
   - Anthropic: https://console.anthropic.com/
   - OpenAI: https://platform.openai.com/

### 🗄️ Проблемы с базой данных

**Симптомы:**
- `database_status: "error"`
- Ошибки при сохранении проектов
- `sqlalchemy.exc.OperationalError`

**Решения:**
1. **Проверить подключение:**
   ```bash
   python -c "
   from app.database import AsyncSessionLocal
   import asyncio
   async def test():
       async with AsyncSessionLocal() as session:
           await session.execute('SELECT 1')
       print('✅ База данных доступна')
   asyncio.run(test())
   "
   ```

2. **Настроить DATABASE_URL (если нужно):**
   ```bash
   export DATABASE_URL="postgresql+asyncpg://user:password@localhost/concrete_agent"
   ```

3. **Использовать SQLite (по умолчанию):**
   - Автоматически создается файл `concrete_agent.db`
   - Не требует дополнительной настройки

### 📁 Отсутствующие файлы

**Симптомы:**
- `FileNotFoundError`
- "Агент не найден"
- Ошибки импорта модулей

**Решения:**
1. **Восстановить структуру:**
   ```bash
   python scripts/setup_modules.py
   ```

2. **Проверить Git статус:**
   ```bash
   git status
   git pull origin main
   ```

3. **Убедиться в правильной структуре папок:**
   ```
   concrete-agent/
   ├── app/
   ├── agents/
   ├── routers/
   ├── utils/
   ├── scripts/
   └── requirements.txt
   ```

### 🌐 Проблемы с сетью/портами

**Симптомы:**
- "Port already in use"
- "Address already in use"
- Не удается подключиться к серверу

**Решения:**
1. **Использовать другой порт:**
   ```bash
   python scripts/start_service.py --port 8001
   ```

2. **Найти и остановить процесс:**
   ```bash
   # Linux/Mac
   lsof -ti:8000 | xargs kill -9
   
   # Windows
   netstat -ano | findstr :8000
   taskkill /PID <PID> /F
   ```

3. **Проверить firewall/прокси настройки**

## Расширенная диагностика

### Проверка компонентов системы

```bash
# Проверить все компоненты
python -c "
import sys
sys.path.append('.')

# Проверка основных модулей
try:
    from app.main import app
    print('✅ FastAPI app загружается')
except Exception as e:
    print(f'❌ Ошибка загрузки app: {e}')

# Проверка агентов
try:
    from agents.concrete_agent.agent import ConcreteGradeExtractor
    print('✅ ConcreteGradeExtractor доступен')
except Exception as e:
    print(f'❌ Ошибка загрузки агента: {e}')

# Проверка базы данных
try:
    from app.database import AsyncSessionLocal
    print('✅ База данных модуль доступен')
except Exception as e:
    print(f'❌ Ошибка модуля БД: {e}')
"
```

### Тестирование API endpoints

```bash
# Основные endpoints
curl -s http://localhost:8000/ | jq '.'
curl -s http://localhost:8000/health | jq '.'
curl -s http://localhost:8000/status | jq '.'

# Проверка загрузки файлов
curl -X POST -F "files=@test.txt" http://localhost:8000/legacy/upload/files

# Проверка анализа (если API ключи настроены)
curl -X POST -F "files=@document.pdf" http://localhost:8000/legacy/analyze/concrete
```

### Логи и отладка

1. **Включить детальные логи:**
   ```bash
   python scripts/start_service.py --log-level debug
   ```

2. **Проверить логи в файлах:**
   ```bash
   tail -f logs/*.log
   ```

3. **Python отладка:**
   ```bash
   export DEBUG=true
   python scripts/start_service.py
   ```

## Получение помощи

### Сбор информации для поддержки

```bash
# Создать полный отчет
python scripts/diagnose_service.py --save-report

# Информация о системе
python -c "
import sys, platform
print(f'Python: {sys.version}')
print(f'Platform: {platform.platform()}')
print(f'Architecture: {platform.architecture()}')
"

# Версии ключевых пакетов
pip show fastapi uvicorn anthropic openai
```

### Контакты

- **GitHub Issues:** [github.com/alpro1000/concrete-agent/issues](https://github.com/alpro1000/concrete-agent/issues)
- **Документация:** `USER_MANUAL.md`
- **API документация:** http://localhost:8000/docs (когда сервер запущен)

### Полезные команды для диагностики

```bash
# Полная проверка системы
python scripts/setup_modules.py && python scripts/diagnose_service.py

# Быстрый перезапуск
pkill -f uvicorn; python scripts/start_service.py

# Проверка установленных пакетов
pip list | grep -E "(fastapi|uvicorn|anthropic|openai)"

# Тест импорта основных модулей
python -c "import fastapi, uvicorn, anthropic; print('✅ All core modules available')"
```

---

**💡 Совет:** Всегда начинайте диагностику с команды `python scripts/diagnose_service.py` - она автоматически проверит большинство распространенных проблем и предложит решения.