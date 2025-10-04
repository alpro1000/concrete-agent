# Stav Agent - Minimal Shell

Этот проект — минимальная оболочка Stav Agent.

Перед каждым деплоем Render автоматически очищает старые кэши,
предотвращая повторное использование старых файлов и агентов.

## Структура

```
/backend/app          # Backend приложение
/backend/tests        # Тесты
/frontend/src         # Frontend исходники
/knowledgebase        # База знаний
/prompts              # Промпты
/storage              # Хранилище данных
```

## Запуск

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 10000
```

## API

- `GET /` - Проверка статуса: `{"status": "OK", "message": "Empty shell ready"}`

