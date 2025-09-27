# 🚀 Concrete-Agent - Руководство по установке и активации модулей

## Автоматическая установка

### Быстрый старт

```bash
# 1. Клонирование репозитория
git clone https://github.com/alpro1000/concrete-agent.git
cd concrete-agent

# 2. Автоматическая настройка системы
python setup_modules.py

# 3. Запуск сервера
uvicorn app.main:app --reload
```

### Ручная проверка и установка

#### 1. Проверка структуры и агентов ✅

Убедитесь, что присутствуют все рабочие модули:

```
agents/
├── concrete_agent/agent.py          ✅ ConcreteGradeExtractor
├── volume_agent/agent.py            ✅ VolumeAnalysisAgent  
├── material_agent/agent.py          ✅ MaterialAnalysisAgent
├── tzd_reader/agent.py              ✅ SecureAIAnalyzer + TZD Reader
├── smetny_inzenyr/agent.py          ✅ SmetnyInzenyr
└── dwg_agent/agent.py               ✅ DwgAnalysisAgent
```

#### 2. Проверка роутеров ✅

Все роутеры экспортируют объект `router` и совместимы с FastAPI:

```
routers/
├── analyze_concrete.py              ✅ /concrete
├── analyze_materials.py             ✅ /materials
├── analyze_volume.py                ✅ /volume
├── version_diff.py                  ✅ /docs, /smeta
├── upload.py                        ✅ /files
└── tzd_router.py                    ✅ /api/v1/tzd/*
```

#### 3. Проверка сервисов и утилит ✅

```
utils/
├── knowledge_base_service.py        ✅ Работает
├── report_generator.py              ✅ Работает
└── czech_preprocessor.py            ✅ Работает

parsers/
├── doc_parser.py                    ✅ Работает
└── smeta_parser.py                  ✅ Работает
```

#### 4. Система регистрации роутеров ✅

- **Автоматическая регистрация**: ✅ `app/core/router_registry.py`
- **Fallback система**: ✅ Резервное ручное подключение
- **После запуска все endpoints доступны в Swagger UI**

#### 5. Проверка зависимостей ✅

```bash
pip install -r requirements.txt
```

Критичные зависимости:
- ✅ `fastapi==0.104.1`
- ✅ `uvicorn[standard]==0.24.0`
- ✅ `pdfplumber==0.11.0`
- ✅ `python-docx==1.1.0`
- ✅ `anthropic==0.35.0`

## Доступные Endpoints

После успешной установки доступны следующие API endpoints:

### Основные анализы:
- `POST /concrete` - Анализ бетонных конструкций
- `POST /materials` - Анализ строительных материалов  
- `POST /volume` - Анализ объемов работ

### Сравнение документов:
- `POST /docs` - Сравнение документов
- `POST /smeta` - Сравнение смет

### Техническое задание (TZD):
- `POST /api/v1/tzd/analyze` - Анализ ТЗД (с поддержкой project_summary)
- `GET /api/v1/tzd/health` - Статус TZD Reader
- `GET /api/v1/tzd/capabilities` - Возможности TZD (включая MinerU статус)

### CLI интерфейсы:
- `python scripts/tzd_reader_cli.py` - TZD Reader CLI

### Утилиты:
- `POST /files` - Загрузка файлов
- `GET /health` - Проверка работоспособности
- `GET /status` - Детальный статус системы

### Документация:
- `GET /docs` - Swagger UI
- `GET /` - Информация о сервисе

## Проверка работоспособности

### Запуск сервера:
```bash
uvicorn app.main:app --reload --port 8000
```

### Ожидаемые логи при успешном запуске:
```
[INFO] 🚀 Construction Analysis API запускается...
[INFO] 📦 Статус зависимостей: {'anthropic': True, 'pdfplumber': True, ...}
[INFO] ✅ Роутер analyze_concrete загружен успешно
[INFO] ✅ Роутер analyze_materials загружен успешно
[INFO] ✅ Роутер analyze_volume загружен успешно
[INFO] ✅ Роутер version_diff загружен успешно
[INFO] ✅ Роутер upload загружен успешно
[INFO] ✅ Роутер tzd_router загружен успешно
[INFO] 📊 Успешно подключено 6/6 роутеров
[INFO] ✅ Сервер успешно запущен
```

### Тестовые запросы:

```bash
# Проверка статуса
curl http://localhost:8000/health

# Тестирование анализа материалов
curl -X POST "http://localhost:8000/materials" \
     -F "docs=@test_document.pdf"

# Тестирование анализа бетона
curl -X POST "http://localhost:8000/concrete" \
     -F "docs=@technical_spec.pdf" \
     -F "smeta=@budget.xlsx"
```

## Автоматизация через CI/CD

### GitHub Actions (пример):
```yaml
name: Deploy Concrete-Agent
on: [push]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Setup Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    - name: Install and setup
      run: |
        pip install -r requirements.txt
        python setup_modules.py
    - name: Run tests
      run: |
        python -m pytest tests/
    - name: Deploy to Render
      run: |
        # Деплой команды
```

### Docker (пример):
```dockerfile
FROM python:3.9-slim

COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt
RUN python setup_modules.py

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## CLI интерфейсы

### TZD Reader CLI

Новый интерфейс командной строки для анализа технических заданий:

```bash
# Базовое использование
python scripts/tzd_reader_cli.py --files document.pdf --engine gpt

# Анализ с Claude AI
python scripts/tzd_reader_cli.py --files task.pdf spec.docx --engine claude

# С ограничением безопасности базовой директории
python scripts/tzd_reader_cli.py --files *.pdf --engine gpt --base-dir ./projects

# Сохранение в файл с подробными логами
python scripts/tzd_reader_cli.py --files document.pdf --output result.json --verbose
```

### Примеры вывода CLI

```json
{
  "project_name": "Реконструкция жилого дома",
  "project_scope": "Капитальный ремонт фасада и кровли",
  "materials": ["Кирпич керамический", "Утеплитель минеральный"],
  "concrete_requirements": ["C25/30", "XC1"],
  "norms": ["ČSN EN 206+A2", "ČSN 73 0540"],
  "project_summary": {
    "overview": "Проект реконструкции включает работы по фасаду...",
    "scope": "Капитальный ремонт фасада и кровли",
    "concrete": ["C25/30", "XC1"],
    "materials": ["Кирпич керамический", "Утеплитель минеральный"],
    "norms": ["ČSN EN 206+A2"],
    "risks": ["Погодные условия", "Доступность материалов"]
  },
  "processing_metadata": {
    "processed_files": 1,
    "processing_time_seconds": 12.34,
    "ai_engine": "gpt",
    "mineru_used": false
  }
}
```

## Опционально: MinerU для улучшенной обработки PDF

MinerU (@opendatalab/MinerU) предоставляет улучшенное извлечение текста и структуры из PDF документов.

### Что дает MinerU:
- Более точное извлечение текста из сложных PDF
- Сохранение структуры документа
- Лучшая обработка таблиц и схем
- Поддержка сложных макетов

### Установка MinerU (опционально):

```bash
# Установка зависимостей MinerU (может потребовать дополнительные системные пакеты)
pip install mineru

# Включение MinerU через переменную окружения
export MINERU_ENABLED=true
```

### Использование MinerU:

```bash
# Через переменную окружения
MINERU_ENABLED=true python scripts/tzd_reader_cli.py --files complex_document.pdf

# MinerU будет автоматически использован для PDF файлов
# При недоступности - автоматический fallback на DocParser
```

### Статус MinerU в API:

```bash
# Проверка статуса MinerU через API
curl http://localhost:8000/api/v1/tzd/capabilities

# Ответ покажет: "mineru_available": true/false
```

**Примечание:** MinerU является опциональной зависимостью. Система полностью функциональна без неё, используя встроенный DocParser.

## Диагностика проблем

### Если роутеры не подключаются:
1. Проверьте наличие `router = APIRouter()` в каждом файле роутера
2. Убедитесь в правильности импортов агентов
3. Запустите `python setup_modules.py` для диагностики

### Если агенты не работают:
1. Проверьте файл `setup_report.json` после запуска скрипта
2. Убедитесь в наличии всех необходимых файлов
3. Проверьте импорты зависимостей

### Если анализ возвращает пустые результаты:
1. Убедитесь, что файлы содержат релевантный контент
2. Проверьте формат входных данных
3. Посмотрите логи сервера для деталей

## Результат успешной установки

✅ **Все агенты активны и работают в реальном режиме**  
✅ **6/6 роутеров подключены автоматически**  
✅ **Анализ бетона, объемов, материалов и ТЗД функционирует**  
✅ **Swagger UI доступен на `/docs`**  
✅ **Нет режима demo_mode или заглушек**  

🚀 **Система готова к production использованию!**