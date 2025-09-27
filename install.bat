@echo off
REM 🧱 Concrete Agent Installation Script for Windows
REM Скрипт для автоматической установки и настройки системы в Windows

echo 🧱 Concrete Agent - Установка и настройка (Windows)
echo =====================================================

REM Проверка Python
echo 🔍 Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден. Пожалуйста, установите Python 3.9 или выше.
    echo    Скачать можно с: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo ✅ Найден Python %PYTHON_VERSION%

REM Проверка pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip не найден. Устанавливаем pip...
    python -m ensurepip --upgrade
)

REM Создание виртуального окружения
set /p CREATE_VENV="🤔 Создать виртуальное окружение? (y/n): "
if /i "%CREATE_VENV%"=="y" (
    echo 📦 Создание виртуального окружения...
    python -m venv venv
    
    REM Активация виртуального окружения
    call venv\Scripts\activate.bat
    echo ✅ Виртуальное окружение активировано
)

REM Установка зависимостей
echo 📚 Установка зависимостей...
pip install -r requirements.txt

REM Создание .env файла
echo ⚙️ Настройка конфигурации...
if not exist .env (
    copy .env.template .env >nul
    echo 📝 Создан файл .env из шаблона
    
    echo.
    echo 🔑 Для полной функциональности необходим API ключ Claude AI
    echo    Получить ключ можно на: https://console.anthropic.com
    set /p CLAUDE_KEY="   Введите API ключ Claude (или нажмите Enter для пропуска): "
    
    if not "%CLAUDE_KEY%"=="" (
        REM Замена в .env файле (упрощенная версия)
        powershell -Command "(Get-Content .env) -replace 'ANTHROPIC_API_KEY=your_anthropic_api_key_here', 'ANTHROPIC_API_KEY=%CLAUDE_KEY%' | Set-Content .env"
        echo ✅ API ключ Claude настроен
    ) else (
        echo ⚠️ API ключ Claude не указан. Система будет работать в ограниченном режиме.
        echo    Вы можете добавить ключ позже в файл .env
    )
) else (
    echo ✅ Файл .env уже существует
)

REM Создание необходимых директорий
echo 📁 Создание рабочих директорий...
if not exist uploads mkdir uploads
if not exist logs mkdir logs
if not exist outputs mkdir outputs
if not exist examples mkdir examples
if not exist examples\sample_inputs mkdir examples\sample_inputs

REM Проверка установки
echo 🧪 Проверка установки...
python -c "from app.main import app; print('✅ Приложение импортируется успешно')" 2>nul
if errorlevel 1 (
    echo ❌ Ошибка импорта основных модулей
    pause
    exit /b 1
)
echo ✅ Основные модули работают корректно

REM Запуск системной диагностики
if exist test_system.py (
    echo 🔧 Запуск системной диагностики...
    python test_system.py
)

echo.
echo 🎉 Установка завершена успешно!
echo.
echo 🚀 Для запуска API сервера:
echo    uvicorn app.main:app --reload --port 8000
echo.
echo 💻 Для анализа через командную строку:
echo    python analyze_concrete_complete.py --docs your_document.pdf
echo.
echo 📚 Документация:
echo    - Полное руководство: USER_MANUAL.md
echo    - Краткое руководство: README_RU.md  
echo    - Примеры использования: python examples/usage_examples.py
echo.
echo 🌐 После запуска API:
echo    - Документация API: http://localhost:8000/docs
echo    - Проверка здоровья: http://localhost:8000/health

REM Предложение запуска
set /p START_SERVER="🤔 Запустить API сервер сейчас? (y/n): "
if /i "%START_SERVER%"=="y" (
    echo 🚀 Запуск API сервера...
    echo    Для остановки нажмите Ctrl+C
    echo    API будет доступен на: http://localhost:8000
    echo.
    uvicorn app.main:app --reload --port 8000
)

pause