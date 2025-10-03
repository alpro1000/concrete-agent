# Stav Agent — модульная архитектура «бусы» (plug-and-play)

Цель: чтобы любой агент/блок знаний можно было добавить/удалить без поломки конвейера.

## 1. Конвейер (данные → знания → решения)

FORKFLOW
- Upload Stage: три зоны (project_documentation, budget_estimate, drawings), строгие имена полей; сохранение в /storage/{user}/uploads/{analysis_id}/
- Parsing Stage: DocParser, SmetaParser, DrawingParser + MinerU fallback → Raw JSON (с provenance)
- Extraction Stage: ConcreteAgent, MaterialAgent, DrawingVolumeAgent, TZDReader, DiffAgent → Entities JSON
- Orchestration & LLM: OrchestratorAgent, LLMService (Claude/GPT/Perplexity), PromptLoader
- TOV Planning: TOVAgent (захватки, ресурсы, технологии, график, стоимость, риски)
- Knowledge Integration: NORMS, CONCRETE_GRADES, MATERIAL_CODES, TECHNOLOGIES, NORMS, LAW, …
- Reporting: JSON/Markdown/API, выгрузки Excel/CSV, PDF/DOCX

Принципы:
- Tools-first, LLM — оркестратор и объяснитель.
- Provenance by design (путь/лист/страница/версия/хэш/дата/уверенность).
- HITL-триггеры для спорных мест.

## 2. Модульность и реестр

Каждый агент — папка в `app/agents/<name>` с манифестом.

Пример `app/agents/concrete_agent/manifest.toml`:
```toml
name = "ConcreteAgent"
version = "0.1.0"
enabled = true

[contracts]
inputs_schema = "schemas/concrete_agent.input.json"
outputs_schema = "schemas/concrete_agent.output.json"

[capabilities]
extracts = ["concrete_grades"]
depends_on = ["knowledge.CONCRETE_GRADES"]

[runtime]
entrypoint = "app/agents/concrete_agent/agent.py:run"
timeout_seconds = 60
```

Глобальный реестр `app/orchestration/registry.json`:
```json
{
  "pipeline": [
    "parsers.DocParser",
    "parsers.SmetaParser",
    "parsers.DrawingParser",
    "extractors.ConcreteAgent",
    "extractors.MaterialAgent",
    "extractors.DrawingVolumeAgent",
    "extractors.TZDReader",
    "extractors.DiffAgent",
    "planning.TOVAgent"
  ],
  "disabled": [],
  "fail_fast": false
}
```

Правило: если модуль выключен — оркестратор пропускает шаг, контракт следующего шага остаётся валидным (values may be null / empty), тесты покрывают деградацию.

## 3. Контракты и схемы

- Raw JSON после парсеров:
```json
{
  "source_type": "pdf|docx|txt|xlsx|xml|dwg|image",
  "source_id": "uuid",
  "extracted_at": "iso-datetime",
  "items": [],
  "errors": [],
  "provenance": {"path": "...", "sheet": "A", "page": 3, "hash": "...", "confidence": 0.92}
}
```

- Canonical JSON для экстракторов:
```json
{
  "document": {"type":"TZ|VV|BOQ|DRAWING", "lang":"cs|ru|en", "units":"SI"},
  "content": {...},
  "provenance": {...}
}
```

- Выходы экстракторов и TOV — строго типизированы (pydantic/JSON Schema), с единицами измерения и ссылками на источники.

## 4. База знаний (packages)

`knowledge/<package>/manifest.json`:
```json
{
  "id": "NORMS",
  "version": "2025.10.01",
  "provenance": [{"title":"ÚRS","url":"...","accessed_at":"2025-10-01"}],
  "schemas": ["norm.json","method_of_measure.json"],
  "update_policy": {"mode":"manual|scheduled","interval_days":30}
}
```

## 5. LLM-слой

- `LLMService` с провайдерами: OpenAI, Anthropic, Gemini, Azure OpenAI, Perplexity (search/verify).
- Конфиг через env: `config.model`, ключи провайдера.
- Ограничения: лимиты токенов, ретраи, timeouts, кэш ответов, контроль стоимости.

## 6. API и фронтенд

- Upload: POST /api/v1/upload; имена полей строго: project_documentation (required), budget_estimate, drawings.
- История/результаты/экспорт как в спецификации MVP.
- CORS: разрешить https://stav-agent.onrender.com; OPTIONS; cookies при необходимости.
- i18n: `frontend/src/i18n/{cs,ru,en}.json`; переключатель языка, сохранение в localStorage.
- Вкладка «Ведомость ресурсов и работ» — отдельный таб, готов под будущие данные.

## 7. Тесты и наблюдаемость

- Unit: парсеры/экстракторы/TOV.
- Contract: схемы I/O, деградация при отключённом модуле.
- Integration: загрузка → парсинг → экстракция → TOV → отчёты.
- E2E (smoke): фронт+бек на Render.
- Логи: ключевые шаги, provenance, маскирование секретов.

## 8. Безопасность

- Валидация MIME/размера (50MB).
- Санитизация имён/путей, UUID для analysis_id.
- Лимиты и timeouts на LLM.
- Политики доступа к storage по user_id.

## 9. Расширение и смена модулей

- Добавление нового агента = новая папка + manifest + схемы + тесты + запись в registry.
- Удаление/выключение = обновление registry, контракты downstream допускают null-входы.
- Знания — через новые пакеты, индексация и валидация отдельно.

---
