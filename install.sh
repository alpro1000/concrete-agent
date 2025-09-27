#!/bin/bash

# 🧱 Concrete Agent Installation Script
# Скрипт для автоматической установки и настройки системы

set -e  # Выход при ошибке

echo "🧱 Concrete Agent - Установка и настройка"
echo "========================================"

# Проверка версии Python
echo "🔍 Проверка Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Пожалуйста, установите Python 3.9 или выше."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Найден Python $PYTHON_VERSION"

# Проверка pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 не найден. Устанавливаем pip..."
    python3 -m ensurepip --upgrade
fi

# Создание виртуального окружения (опционально)
read -p "🤔 Создать виртуальное окружение? (y/n): " CREATE_VENV
if [[ $CREATE_VENV == "y" || $CREATE_VENV == "Y" ]]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
    
    # Активация виртуального окружения
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        # Windows
        source venv/Scripts/activate
        echo "✅ Виртуальное окружение активировано (Windows)"
    else
        # Linux/macOS
        source venv/bin/activate
        echo "✅ Виртуальное окружение активировано (Linux/macOS)"
    fi
fi

# Установка зависимостей
echo "📚 Установка зависимостей..."
pip3 install -r requirements.txt

# Создание .env файла
echo "⚙️ Настройка конфигурации..."
if [ ! -f .env ]; then
    cp .env.template .env
    echo "📝 Создан файл .env из шаблона"
    
    # Запрос API ключа Claude
    echo ""
    echo "🔑 Для полной функциональности необходим API ключ Claude AI"
    echo "   Получить ключ можно на: https://console.anthropic.com"
    read -p "   Введите API ключ Claude (или нажмите Enter для пропуска): " CLAUDE_KEY
    
    if [ ! -z "$CLAUDE_KEY" ]; then
        # Замена в .env файле
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/ANTHROPIC_API_KEY=your_anthropic_api_key_here/ANTHROPIC_API_KEY=$CLAUDE_KEY/" .env
        else
            # Linux
            sed -i "s/ANTHROPIC_API_KEY=your_anthropic_api_key_here/ANTHROPIC_API_KEY=$CLAUDE_KEY/" .env
        fi
        echo "✅ API ключ Claude настроен"
    else
        echo "⚠️ API ключ Claude не указан. Система будет работать в ограниченном режиме."
        echo "   Вы можете добавить ключ позже в файл .env"
    fi
else
    echo "✅ Файл .env уже существует"
fi

# Создание необходимых директорий
echo "📁 Создание рабочих директорий..."
mkdir -p uploads logs outputs examples/sample_inputs

# Проверка установки
echo "🧪 Проверка установки..."
if python3 -c "from app.main import app; print('✅ Приложение импортируется успешно')" 2>/dev/null; then
    echo "✅ Основные модули работают корректно"
else
    echo "❌ Ошибка импорта основных модулей"
    exit 1
fi

# Запуск системной диагностики
if [ -f "test_system.py" ]; then
    echo "🔧 Запуск системной диагностики..."
    python3 test_system.py
fi

echo ""
echo "🎉 Установка завершена успешно!"
echo ""
echo "🚀 Для запуска API сервера:"
echo "   uvicorn app.main:app --reload --port 8000"
echo ""
echo "💻 Для анализа через командную строку:"
echo "   python analyze_concrete_complete.py --docs your_document.pdf"
echo ""
echo "📚 Документация:"
echo "   - Полное руководство: USER_MANUAL.md"
echo "   - Краткое руководство: README_RU.md"
echo "   - Примеры использования: python examples/usage_examples.py"
echo ""
echo "🌐 После запуска API:"
echo "   - Документация API: http://localhost:8000/docs"
echo "   - Проверка здоровья: http://localhost:8000/health"

# Предложение запуска
read -p "🤔 Запустить API сервер сейчас? (y/n): " START_SERVER
if [[ $START_SERVER == "y" || $START_SERVER == "Y" ]]; then
    echo "🚀 Запуск API сервера..."
    echo "   Для остановки нажмите Ctrl+C"
    echo "   API будет доступен на: http://localhost:8000"
    echo ""
    uvicorn app.main:app --reload --port 8000
fi