#!/usr/bin/env python3
"""
Главный скрипт для полного анализа бетона с объемами и отчетами
analyze_concrete_complete.py
"""

import asyncio
import argparse
import sys
import logging
from pathlib import Path
from typing import List, Optional

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('concrete_analysis.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def setup_arguments():
    """Настройка аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description="Полный анализ бетона с извлечением объемов и генерацией отчетов",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  Базовый анализ:
    python analyze_concrete_complete.py --docs file1.pdf file2.pdf

  Анализ со сметой:
    python analyze_concrete_complete.py --docs *.pdf --smeta smeta.xlsx

  Анализ с настройками:
    python analyze_concrete_complete.py --docs *.pdf --language ru --no-claude

  Только объемы без Claude:
    python analyze_concrete_complete.py --docs *.pdf --smeta vykaz.pdf --language en --no-claude
        """
    )
    
    # Основные аргументы
    parser.add_argument(
        '--docs', '--documents',
        nargs='+',
        required=True,
        help='Список PDF документов для анализа'
    )
    
    parser.add_argument(
        '--smeta', '--budget',
        type=str,
        help='Путь к файлу сметы или výkaz výměr (PDF, XLSX, DOCX)'
    )
    
    # Настройки анализа
    parser.add_argument(
        '--language', '-l',
        choices=['cz', 'en', 'ru'],
        default='cz',
        help='Язык отчетов (по умолчанию: cz)'
    )
    
    parser.add_argument(
        '--claude-mode',
        choices=['enhancement', 'primary'],
        default='enhancement',
        help='Режим Claude AI (по умолчанию: enhancement)'
    )
    
    parser.add_argument(
        '--no-claude',
        action='store_true',
        help='Отключить использование Claude AI'
    )
    
    # Настройки вывода
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='outputs',
        help='Папка для сохранения отчетов (по умолчанию: outputs)'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Минимальный вывод в консоль'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Подробный вывод в консоль'
    )
    
    return parser

def validate_files(doc_paths: List[str], smeta_path: Optional[str] = None) -> bool:
    """Проверяет существование файлов"""
    missing_files = []
    
    # Проверяем документы
    for doc_path in doc_paths:
        if not Path(doc_path).exists():
            missing_files.append(doc_path)
    
    # Проверяем смету
    if smeta_path and not Path(smeta_path).exists():
        missing_files.append(smeta_path)
    
    if missing_files:
        logger.error("Не найдены файлы:")
        for file in missing_files:
            logger.error(f"  - {file}")
        return False
    
    return True

def print_analysis_summary(result: dict, language: str = 'cz'):
    """Выводит краткую сводку анализа"""
    
    lang_labels = {
        'cz': {
            'found_grades': 'Nalezené třídy betonu',
            'total_volume': 'Celkový objem',
            'volume_entries': 'Pozice s objemy',
            'documents': 'Zpracované dokumenty',
            'method': 'Metoda analýzy',
            'reports_saved': 'Uložené reporty'
        },
        'en': {
            'found_grades': 'Found concrete grades',
            'total_volume': 'Total volume',
            'volume_entries': 'Volume entries',
            'documents': 'Processed documents',
            'method': 'Analysis method',
            'reports_saved': 'Saved reports'
        },
        'ru': {
            'found_grades': 'Найденные марки бетона',
            'total_volume': 'Общий объем',
            'volume_entries': 'Позиции с объемами',
            'documents': 'Обработанные документы',
            'method': 'Метод анализа',
            'reports_saved': 'Сохраненные отчеты'
        }
    }
    
    labels = lang_labels.get(language, lang_labels['cz'])
    
    print("\n" + "="*60)
    print(f"📊 {labels['found_grades'].upper()}")
    print("="*60)
    
    # Марки бетона
    concrete_summary = result.get('concrete_summary', [])
    total_volume = 0
    
    for item in concrete_summary:
        grade = item.get('grade', 'N/A')
        volume = item.get('total_volume_m3', 0)
        location = item.get('location', 'неопределено')
        
        volume_str = f"{volume:.2f} m³" if volume > 0 else "объем не найден"
        print(f"  {grade}: {volume_str} ({location})")
        
        if volume > 0:
            total_volume += volume
    
    print("-"*60)
    print(f"📏 {labels['total_volume']}: {total_volume:.2f} m³")
    print(f"📊 {labels['volume_entries']}: {result.get('volume_entries_found', 0)}")
    print(f"📄 {labels['documents']}: {len(result.get('processed_documents', []))}")
    print(f"🔧 {labels['method']}: {result.get('analysis_method', 'неизвестно')}")
    
    # Сохраненные отчеты
    saved_reports = result.get('saved_reports', {})
    if saved_reports:
        print(f"\n💾 {labels['reports_saved']}:")
        for report_type, file_path in saved_reports.items():
            print(f"  - {report_type}: {file_path}")
    
    print("="*60)

async def main():
    """Главная функция"""
    parser = setup_arguments()
    args = parser.parse_args()
    
    # Настройка уровня логирования
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    elif args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Проверка файлов
    if not validate_files(args.docs, args.smeta):
        sys.exit(1)
    
    logger.info(f"🚀 Запуск полного анализа бетона")
    logger.info(f"   Документы: {len(args.docs)} файлов")
    logger.info(f"   Смета: {'есть' if args.smeta else 'нет'}")
    logger.info(f"   Язык отчетов: {args.language}")
    logger.info(f"   Claude AI: {'выключен' if args.no_claude else 'включен'}")
    
    try:
        # Импортируем функцию анализа
        from agents.concrete_agent import analyze_concrete_with_volumes
        
        # Запускаем анализ
        result = await analyze_concrete_with_volumes(
            doc_paths=args.docs,
            smeta_path=args.smeta,
            use_claude=not args.no_claude,
            claude_mode=args.claude_mode,
            language=args.language
        )
        
        # Проверяем успешность
        if not result.get('success', True):
            logger.error(f"❌ Анализ завершился с ошибкой: {result.get('error', 'неизвестная ошибка')}")
            sys.exit(1)
        
        # Выводим сводку
        if not args.quiet:
            print_analysis_summary(result, args.language)
        
        logger.info("✅ Анализ успешно завершен")
        
        # Проверяем качество результатов
        concrete_count = len(result.get('concrete_summary', []))
        volume_count = result.get('volume_entries_found', 0)
        
        if concrete_count == 0:
            logger.warning("⚠️ Марки бетона не найдены - проверьте качество документов")
        
        if volume_count == 0:
            logger.warning("⚠️ Объемы не найдены - проверьте наличие смет или výkaz výměr")
        
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта модулей: {e}")
        logger.error("Убедитесь, что все модули системы установлены корректно")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
