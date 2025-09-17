# 🧱 Concrete Intelligence Agent

LLM-агент для извлечения **марок бетона и мест их применения** из проектной документации и смет. Подходит для зданий, дорог, заводов, ИЖС. Используется в автоматической проверке соответствия документации и расчётов.

---

## 🚀 Возможности

- 📄 Читает и анализирует документацию: `.PDF`, `.DOCX`, `.TXT`
- 📊 Парсит сметы в `.XLS`, `.CSV`, `.XML`
- 🔎 Извлекает марки бетона (B20, C25/30, C30/37 XF4…)
- 🏗 Определяет, где эти бетоны применяются в конструкциях
- 📋 Проверяет, учтены ли они в смете
- 📤 Отдаёт структурированный JSON-отчёт
- 🧠 Использует внутренний reasoning loop (`SSRL`) для повторной проверки

---

## 📁 Структура проекта

concrete-agent/
├── prompt/
│ └── concrete_extractor_prompt.json # JSON-промт для LLM
├── api/
│ └── app.py # FastAPI endpoint (можно развернуть как microservice)
├── agents/
│ └── concrete_agent.py # Вызов LLM + логика извлечения
├── parsers/
│ ├── smeta_parser.py # Сметы (.xls/.xml)
│ └── doc_parser.py # Тексты и документы (.pdf/.docx)
├── examples/
│ └── sample_inputs/ # Примеры смет и ТЗ
├── outputs/
│ └── sample_report.json # Пример вывода
├── requirements.txt
└── README.md
