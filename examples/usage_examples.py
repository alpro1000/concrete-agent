#!/usr/bin/env python3
"""
Примеры использования Concrete Agent API
usage_examples.py

Этот файл содержит практические примеры работы с системой Concrete Agent.
"""

import asyncio
import requests
import json
from pathlib import Path
import time

# Базовый URL API (измените при необходимости)
BASE_URL = "http://localhost:8000"

def check_api_health():
    """Проверка работоспособности API"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API работает корректно")
            return True
        else:
            print(f"❌ API вернул статус {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка подключения к API: {e}")
        print("💡 Убедитесь, что сервер запущен: uvicorn app.main:app --reload")
        return False

def example_concrete_analysis():
    """Пример анализа бетона через API"""
    print("\n🔍 Пример анализа бетона")
    
    # Создаем тестовый файл, если его нет
    test_file = Path("examples/test_document.txt")
    if not test_file.exists():
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("""
        ТЕХНИЧЕСКОЕ ЗАДАНИЕ
        
        Проект: Жилой дом
        
        Марки бетона:
        - Фундамент: C25/30 XC2 - 150 м³
        - Стены подвала: C30/37 XF1 - 200 м³
        - Колонны: C35/45 XC3 - 75 м³
        
        Требования к бетону:
        - Класс прочности не менее C25/30
        - Морозостойкость F150
        - Водонепроницаемость W8
        """, encoding='utf-8')
        print(f"📝 Создан тестовый файл: {test_file}")
    
    try:
        with open(test_file, 'rb') as f:
            files = {
                'docs': ('test_document.txt', f, 'text/plain')
            }
            
            print("📤 Отправка запроса на анализ...")
            response = requests.post(
                f"{BASE_URL}/analyze/concrete",
                files=files,
                timeout=30
            )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Анализ завершен успешно!")
            print(f"📊 Найдено марок бетона: {len(result.get('concrete_summary', []))}")
            
            # Красивый вывод результатов
            if result.get('concrete_summary'):
                print("\n📋 Результаты анализа:")
                for i, item in enumerate(result['concrete_summary'], 1):
                    print(f"  {i}. Марка: {item.get('grade', 'Не определена')}")
                    print(f"     Применение: {', '.join(item.get('locations', ['Не указано']))}")
                    if 'volume_m3' in item:
                        print(f"     Объем: {item['volume_m3']} м³")
        else:
            print(f"❌ Ошибка анализа: {response.status_code}")
            print(f"Ответ: {response.text}")
            
    except FileNotFoundError:
        print("❌ Тестовый файл не найден")
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка запроса: {e}")

def example_file_upload():
    """Пример загрузки файлов"""
    print("\n📤 Пример загрузки файлов")
    
    # Создаем тестовый файл с бетоном
    test_files = []
    
    # Тестовый PDF контент (в реальности используйте настоящие PDF)
    spec_file = Path("examples/specifications.txt")
    if not spec_file.exists():
        spec_file.write_text("""
        СПЕЦИФИКАЦИЯ МАТЕРИАЛОВ
        
        1. Бетон фундаментный
           Марка: B25 (C30/37)
           Объем: 180 м³
           Класс по морозостойкости: F150
        
        2. Бетон для колонн
           Марка: B30 (C35/45)  
           Объем: 85 м³
           Класс по морозостойкости: F200
        """, encoding='utf-8')
        test_files.append(spec_file)
    
    try:
        files_to_upload = []
        for file_path in test_files:
            files_to_upload.append(
                ('files', (file_path.name, open(file_path, 'rb'), 'text/plain'))
            )
        
        response = requests.post(
            f"{BASE_URL}/upload/files",
            files=files_to_upload
        )
        
        # Закрываем файлы
        for _, (_, file_obj, _) in files_to_upload:
            file_obj.close()
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Файлы загружены успешно!")
            print(f"📁 Загружено файлов: {len(result.get('uploaded', []))}")
        else:
            print(f"❌ Ошибка загрузки: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def example_status_check():
    """Пример проверки статуса системы"""
    print("\n📊 Проверка статуса системы")
    
    try:
        response = requests.get(f"{BASE_URL}/status")
        if response.status_code == 200:
            status = response.json()
            print("✅ Статус получен:")
            print(f"  API статус: {status.get('api_status', 'unknown')}")
            print(f"  Claude доступен: {'✅' if status.get('claude_available') else '❌'}")
            
            deps = status.get('dependencies', {})
            print("  Зависимости:")
            for dep, available in deps.items():
                icon = "✅" if available else "❌"
                print(f"    {icon} {dep}")
        else:
            print(f"❌ Ошибка получения статуса: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка запроса: {e}")

def example_command_line_usage():
    """Пример использования через командную строку"""
    print("\n💻 Примеры использования через командную строку:")
    
    examples = [
        {
            "title": "Базовый анализ документа",
            "command": "python analyze_concrete_complete.py --docs project.pdf"
        },
        {
            "title": "Анализ с русским языком",
            "command": "python analyze_concrete_complete.py --docs project.pdf --language ru"
        },
        {
            "title": "Анализ со сметой",
            "command": "python analyze_concrete_complete.py --docs project.pdf --smeta budget.xlsx"
        },
        {
            "title": "Анализ без Claude AI",
            "command": "python analyze_concrete_complete.py --docs project.pdf --no-claude"
        },
        {
            "title": "Подробный вывод",
            "command": "python analyze_concrete_complete.py --docs project.pdf --verbose"
        }
    ]
    
    for example in examples:
        print(f"\n  📝 {example['title']}:")
        print(f"     {example['command']}")

def main():
    """Главная функция с демонстрацией возможностей"""
    print("🧱 Concrete Agent - Примеры использования")
    print("=" * 50)
    
    # Проверяем доступность API
    if not check_api_health():
        print("\n💡 Для работы с API запустите сервер:")
        print("   uvicorn app.main:app --reload --port 8000")
        print("\n📖 Или используйте командную строку:")
        example_command_line_usage()
        return
    
    # Демонстрируем различные возможности
    example_status_check()
    example_file_upload()
    example_concrete_analysis()
    example_command_line_usage()
    
    print("\n" + "=" * 50)
    print("✅ Демонстрация завершена!")
    print("📚 Полное руководство: USER_MANUAL.md")
    print("🌐 API документация: http://localhost:8000/docs")

if __name__ == "__main__":
    main()