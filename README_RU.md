# 🧱 Concrete Agent - Краткое руководство

Интеллектуальная система анализа строительной документации на базе ИИ.

## 🚀 Быстрый старт

### 1. Установка

```bash
git clone https://github.com/alpro1000/concrete-agent.git
cd concrete-agent
pip install -r requirements.txt
```

### 2. Настройка

```bash
cp .env.template .env
# Отредактируйте .env файл, добавьте ANTHROPIC_API_KEY
```

### 3. Запуск

```bash
# API сервер
uvicorn app.main:app --reload --port 8000

# Командная строка
python analyze_concrete_complete.py --docs project.pdf --smeta budget.xlsx
```

## 📊 Основные возможности

- **Анализ бетона**: извлечение марок (B20, C25/30, C30/37 XF4...)
- **Обработка документов**: PDF, DOCX, XLS, CSV, XML
- **Объемный анализ**: расчет количества материалов
- **Сравнение версий**: анализ изменений в документах
- **ИИ-обработка**: улучшение точности с помощью Claude AI

## 🔧 API Endpoints

- `GET /health` - проверка работоспособности
- `POST /analyze/concrete` - анализ бетона
- `POST /analyze/materials` - анализ материалов
- `POST /compare/docs` - сравнение документов
- `POST /upload/files` - загрузка файлов

## 📖 Полная документация

**📚 [ПОЛНОЕ РУКОВОДСТВО ПОЛЬЗОВАТЕЛЯ](USER_MANUAL.md)** - подробная инструкция со всеми настройками, примерами и решением проблем.

## 🧪 Тестирование

```bash
# Системная диагностика
python test_system.py

# Модульные тесты
python -m pytest tests/ -v

# Тест Claude интеграции
python tests/test_claude_integration.py
```

## 📁 Структура проекта

```
concrete-agent/
├── agents/           # ИИ-агенты для анализа
├── app/             # FastAPI приложение
├── routers/         # API маршруты
├── utils/           # Утилиты и помощники
├── tests/           # Тесты
├── examples/        # Примеры документов
└── outputs/         # Результаты анализа
```

## ⚡ Примеры использования

### API запрос

```bash
curl -X POST "http://localhost:8000/analyze/concrete" \
  -F "docs=@project.pdf" \
  -F "smeta=@budget.xlsx"
```

### Python скрипт

```python
import requests

response = requests.post(
    'http://localhost:8000/analyze/concrete',
    files={
        'docs': [('project.pdf', open('project.pdf', 'rb'))],
        'smeta': ('budget.xlsx', open('budget.xlsx', 'rb'))
    }
)

result = response.json()
print(result['concrete_summary'])
```

### Командная строка

```bash
# Базовый анализ
python analyze_concrete_complete.py --docs project.pdf

# С русским языком и сметой
python analyze_concrete_complete.py \
  --docs project.pdf specs.docx \
  --smeta budget.xlsx \
  --language ru
```

## 🔑 Переменные окружения

```bash
ANTHROPIC_API_KEY=your_claude_api_key    # Обязательно для ИИ
USE_CLAUDE=true                          # Включить Claude AI
CLAUDE_MODEL=claude-3-sonnet-20240229    # Модель Claude
MAX_FILE_SIZE=52428800                   # Максимум 50МБ
LOG_LEVEL=INFO                          # Уровень логирования
```

## 🎯 Результаты анализа

Система генерирует отчеты в форматах:
- **JSON**: структурированные данные
- **CSV**: таблицы для Excel
- **PDF**: детальные отчеты

Пример JSON результата:
```json
{
  "success": true,
  "concrete_summary": [
    {
      "grade": "C25/30",
      "locations": ["фундамент", "колонны"],
      "volume_m3": 150.5,
      "smeta_match": {
        "found_in_budget": true,
        "variance_percent": 2.1
      }
    }
  ]
}
```

## 🆘 Решение проблем

### Часто встречающиеся ошибки

**Ошибка импорта модулей**:
```bash
pip install -r requirements.txt
```

**Claude API не работает**:
- Проверьте `ANTHROPIC_API_KEY` в `.env`
- Используйте `--no-claude` для работы без ИИ

**Файл слишком большой**:
- Увеличьте `MAX_FILE_SIZE` в `.env`
- Или сжмите PDF файлы

### Диагностика

```bash
# Проверка системы
python test_system.py

# Проверка API
curl http://localhost:8000/health

# Просмотр логов
tail -f logs/concrete_analysis.log
```

## 📧 Поддержка

- **Документация**: [USER_MANUAL.md](USER_MANUAL.md)
- **API Docs**: http://localhost:8000/docs
- **Issues**: https://github.com/alpro1000/concrete-agent/issues

---

**🔗 Полная документация доступна в [USER_MANUAL.md](USER_MANUAL.md)**