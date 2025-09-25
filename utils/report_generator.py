"""
Генератор человекочитаемых отчетов с объемами бетона
utils/report_generator.py
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class ConcreteReportGenerator:
    """Генератор отчетов по анализу бетона с объемами"""
    
    def __init__(self, language: str = 'cz'):
        self.language = language.lower()
        
        # Словари переводов
        self.translations = {
            'cz': {
                'title': 'ANALÝZA BETONU A OBJEMŮ',
                'project_overview': 'PŘEHLED PROJEKTU',
                'concrete_grades': 'NALEZENÉ TŘÍDY BETONU',
                'volume_summary': 'SOUHRN OBJEMŮ',
                'detailed_analysis': 'DETAILNÍ ANALÝZA',
                'technical_specs': 'TECHNICKÉ PARAMETRY',
                'total_volume': 'Celkový objem',
                'applications': 'Použití',
                'exposure_classes': 'Třídy prostředí',
                'construction_element': 'Konstrukční prvek',
                'confidence': 'Spolehlivost',
                'source_documents': 'Zdrojové dokumenty',
                'processing_stats': 'Statistiky zpracování',
                'recommendations': 'DOPORUČENÍ',
                'cubic_meters': 'm³',
                'square_meters': 'm²',
                'thickness': 'Tloušťka',
                'no_volume_data': 'Objem nezjištěn',
                'total': 'Celkem',
                'element': 'Prvek',
                'volume': 'Objem',
                'method': 'Metoda',
            },
            'en': {
                'title': 'CONCRETE AND VOLUME ANALYSIS',
                'project_overview': 'PROJECT OVERVIEW',
                'concrete_grades': 'IDENTIFIED CONCRETE GRADES',
                'volume_summary': 'VOLUME SUMMARY',
                'detailed_analysis': 'DETAILED ANALYSIS',
                'technical_specs': 'TECHNICAL SPECIFICATIONS',
                'total_volume': 'Total Volume',
                'applications': 'Applications',
                'exposure_classes': 'Exposure Classes',
                'construction_element': 'Construction Element',
                'confidence': 'Confidence',
                'source_documents': 'Source Documents',
                'processing_stats': 'Processing Statistics',
                'recommendations': 'RECOMMENDATIONS',
                'cubic_meters': 'm³',
                'square_meters': 'm²',
                'thickness': 'Thickness',
                'no_volume_data': 'Volume not determined',
                'total': 'Total',
                'element': 'Element',
                'volume': 'Volume',
                'method': 'Method',
            },
            'ru': {
                'title': 'АНАЛИЗ БЕТОНА И ОБЪЕМОВ',
                'project_overview': 'ОБЗОР ПРОЕКТА',
                'concrete_grades': 'НАЙДЕННЫЕ МАРКИ БЕТОНА',
                'volume_summary': 'СВОДКА ОБЪЕМОВ',
                'detailed_analysis': 'ДЕТАЛЬНЫЙ АНАЛИЗ',
                'technical_specs': 'ТЕХНИЧЕСКИЕ ХАРАКТЕРИСТИКИ',
                'total_volume': 'Общий объем',
                'applications': 'Применение',
                'exposure_classes': 'Классы воздействия',
                'construction_element': 'Конструктивный элемент',
                'confidence': 'Достоверность',
                'source_documents': 'Исходные документы',
                'processing_stats': 'Статистика обработки',
                'recommendations': 'РЕКОМЕНДАЦИИ',
                'cubic_meters': 'м³',
                'square_meters': 'м²',
                'thickness': 'Толщина',
                'no_volume_data': 'Объем не определен',
                'total': 'Итого',
                'element': 'Элемент',
                'volume': 'Объем',
                'method': 'Метод',
            }
        }

    def t(self, key: str) -> str:
        """Получает перевод по ключу"""
        return self.translations.get(self.language, self.translations['cz']).get(key, key)

    def generate_markdown_report(self, analysis_result: Dict[str, Any]) -> str:
        """Генерирует полный отчет в формате Markdown"""
        
        report_lines = []
        
        # Заголовок
        report_lines.extend([
            f"# {self.t('title')}",
            "",
            f"*Создан: {datetime.now().strftime('%d.%m.%Y %H:%M')}*",
            "",
            "---",
            ""
        ])
        
        # Обзор проекта
        report_lines.extend(self._generate_project_overview(analysis_result))
        
        # Сводка объемов
        if self._has_volume_data(analysis_result):
            report_lines.extend(self._generate_volume_summary(analysis_result))
        
        # Детальный анализ по маркам
        report_lines.extend(self._generate_detailed_analysis(analysis_result))
        
        # Статистика обработки
        report_lines.extend(self._generate_processing_stats(analysis_result))
        
        # Рекомендации
        report_lines.extend(self._generate_recommendations(analysis_result))
        
        return "\n".join(report_lines)

    def _generate_project_overview(self, data: Dict[str, Any]) -> List[str]:
        """Генерирует обзор проекта"""
        lines = [
            f"## {self.t('project_overview')}",
            ""
        ]
        
        # Документы
        docs = data.get('processed_documents', [])
        if docs:
            lines.extend([
                f"**{self.t('source_documents')}:**",
            ])
            
            total_chars = 0
            for doc in docs:
                if isinstance(doc, dict) and 'file' in doc:
                    chars = doc.get('text_length', 0)
                    total_chars += chars
                    status = "" if chars > 0 else " ⚠️"
                    lines.append(f"- `{doc['file']}` ({chars:,} символов){status}")
            
            lines.extend([
                "",
                f"**Общий объем текста:** {total_chars:,} символов",
                ""
            ])
        
        # Основные результаты
        concrete_count = len(data.get('concrete_summary', []))
        volume_info = data.get('volume_analysis', {})
        
        lines.extend([
            f"**Основные результаты:**",
            f"- Найдено марок бетона: {concrete_count}",
            f"- Метод анализа: {data.get('analysis_method', 'неизвестно')}",
        ])
        
        if volume_info:
            lines.append(f"- Позиций с объемами: {volume_info.get('total_entries', 0)}")
            lines.append(f"- Марок с объемами: {volume_info.get('grades_with_volumes', 0)}")
        
        # Чешская предобработка
        czech_stats = data.get('czech_preprocessing', {})
        if czech_stats and czech_stats.get('diacritic_fixes', 0) > 0:
            lines.extend([
                "",
                f"**Предобработка чешского текста:**",
                f"- Исправлено символов: {czech_stats['diacritic_fixes']:,}",
            ])
        
        lines.extend(["", "---", ""])
        return lines

    def _generate_volume_summary(self, data: Dict[str, Any]) -> List[str]:
        """Генерирует сводку по объемам"""
        lines = [
            f"## {self.t('volume_summary')}",
            ""
        ]
        
        # Таблица общих объемов
        concrete_summary = data.get('concrete_summary', [])
        
        if concrete_summary:
            lines.extend([
                "| Марка бетона | Общий объем | Применения | Статус |",
                "|-------------|-------------|------------|--------|"
            ])
            
            total_volume = 0
            for item in concrete_summary:
                grade = item.get('grade', 'N/A')
                volume = item.get('total_volume_m3', 0)
                apps = item.get('volume_applications', [])
                has_volume = item.get('has_volume_data', False)
                
                volume_str = f"{volume:.2f} {self.t('cubic_meters')}" if volume > 0 else self.t('no_volume_data')
                apps_str = f"{len(apps)} элементов" if apps else "—"
                status = "✅" if has_volume else "⚠️"
                
                lines.append(f"| **{grade}** | {volume_str} | {apps_str} | {status} |")
                
                if volume > 0:
                    total_volume += volume
            
            lines.extend([
                "",
                f"**{self.t('total')}:** {total_volume:.2f} {self.t('cubic_meters')}",
                "",
                "---",
                ""
            ])
        
        return lines

    def _generate_detailed_analysis(self, data: Dict[str, Any]) -> List[str]:
        """Генерирует детальный анализ по каждой марке"""
        lines = [
            f"## {self.t('detailed_analysis')}",
            ""
        ]
        
        concrete_summary = data.get('concrete_summary', [])
        
        for i, item in enumerate(concrete_summary, 1):
            grade = item.get('grade', 'N/A')
            location = item.get('location', 'неопределено')
            confidence = item.get('confidence', 0)
            context = item.get('context', '')
            
            lines.extend([
                f"### {i}. {grade}",
                ""
            ])
            
            # Основная информация
            lines.extend([
                f"**{self.t('construction_element')}:** {location}",
                f"**{self.t('confidence')}:** {confidence:.0%}",
                f"**{self.t('method')}:** {item.get('method', 'неизвестно')}",
                ""
            ])
            
            # Объемные данные
            volume_apps = item.get('volume_applications', [])
            total_vol = item.get('total_volume_m3', 0)
            
            if volume_apps:
                lines.extend([
                    f"**{self.t('volume_summary')}:**",
                    f"- {self.t('total_volume')}: {total_vol:.2f} {self.t('cubic_meters')}",
                    ""
                ])
                
                for app in volume_apps:
                    element = app.get('element', 'неизвестно')
                    vol = app.get('volume_m3', 0)
                    count = app.get('entries_count', 0)
                    lines.append(f"  - {element}: {vol:.2f} {self.t('cubic_meters')} ({count} позиций)")
                
                lines.append("")
            else:
                lines.extend([
                    f"**{self.t('volume')}:** {self.t('no_volume_data')}",
                    ""
                ])
            
            # Контекст
            if context:
                lines.extend([
                    "**Контекст:**",
                    f"> {context[:200]}{'...' if len(context) > 200 else ''}",
                    ""
                ])
            
            lines.extend(["---", ""])
        
        return lines

    def _generate_processing_stats(self, data: Dict[str, Any]) -> List[str]:
        """Генерирует статистику обработки"""
        lines = [
            f"## {self.t('processing_stats')}",
            ""
        ]
        
        # Claude анализ
        claude_stats = data.get('claude_analysis', {})
        if claude_stats:
            lines.extend([
                "**Claude AI анализ:**",
                f"- Использовано токенов: {claude_stats.get('tokens_used', 0):,}",
                f"- Статус: {'✅' if claude_stats.get('success') else '❌'}",
                ""
            ])
        
        # Общая статистика
        lines.extend([
            "**Общая статистика:**",
            f"- Допустимых марок в базе: {data.get('allowed_grades_count', 0)}",
            f"- Версия базы знаний: {data.get('knowledge_base_version', 'неизвестно')}",
            f"- Время обработки: {data.get('processing_time', 'неизвестно')}",
            ""
        ])
        
        # Объемная статистика
        volume_stats = data.get('volume_analysis', {})
        if volume_stats:
            lines.extend([
                "**Анализ объемов:**",
                f"- Всего позиций с объемами: {volume_stats.get('total_entries', 0)}",
                f"- Марок с объемами: {volume_stats.get('grades_with_volumes', 0)}",
                ""
            ])
        
        lines.extend(["---", ""])
        return lines

    def _generate_recommendations(self, data: Dict[str, Any]) -> List[str]:
        """Генерирует рекомендации"""
        lines = [
            f"## {self.t('recommendations')}",
            ""
        ]
        
        recommendations = []
        
        # Проверка документов
        docs = data.get('processed_documents', [])
        empty_docs = [d for d in docs if isinstance(d, dict) and d.get('text_length', 0) == 0]
        if empty_docs:
            recommendations.append(
                f"**Проблемы с документами:** {len(empty_docs)} файлов не обработались. "
                f"Проверьте доступность и целостность PDF файлов."
            )
        
        # Проверка объемов
        concrete_summary = data.get('concrete_summary', [])
        no_volume = [c for c in concrete_summary if not c.get('has_volume_data', False)]
        if no_volume:
            recommendations.append(
                f"**Отсутствуют объемы:** для {len(no_volume)} марок не найдены объемы. "
                f"Проверьте смету или výkaz výměr."
            )
        
        # Проверка диакритики
        czech_stats = data.get('czech_preprocessing', {})
        if czech_stats and czech_stats.get('diacritic_fixes', 0) > 1000:
            recommendations.append(
                f"**Качество PDF:** обнаружено {czech_stats['diacritic_fixes']} поврежденных символов. "
                f"Рассмотрите использование более качественных PDF файлов."
            )
        
        # Проверка соответствия стандартам
        recommendations.append(
            "**Проверка соответствия:** убедитесь, что найденные марки соответствуют "
            "требованиям ČSN EN 206+A2 и условиям эксплуатации."
        )
        
        # Добавляем рекомендации
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"{i}. {rec}")
                lines.append("")
        else:
            lines.extend([
                "Анализ не выявил критических проблем. Система работает корректно.",
                ""
            ])
        
        return lines

    def _has_volume_data(self, data: Dict[str, Any]) -> bool:
        """Проверяет наличие объемных данных"""
        return bool(data.get('volume_analysis', {}).get('total_entries', 0) > 0)

    def generate_excel_data(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Генерирует данные для Excel таблицы"""
        
        excel_data = {
            'summary': [],
            'details': [],
            'volumes': [],
            'documents': []
        }
        
        # Сводная таблица
        concrete_summary = analysis_result.get('concrete_summary', [])
        for item in concrete_summary:
            excel_data['summary'].append({
                'Марка бетона': item.get('grade', ''),
                'Класс воздействия': self._extract_exposure_classes(item.get('context', '')),
                'Конструктивный элемент': item.get('location', ''),
                'Общий объем (м³)': item.get('total_volume_m3', 0),
                'Количество применений': len(item.get('volume_applications', [])),
                'Достоверность': f"{item.get('confidence', 0):.0%}",
                'Есть объемы': 'Да' if item.get('has_volume_data', False) else 'Нет'
            })
        
        # Детальная таблица
        for item in concrete_summary:
            volume_apps = item.get('volume_applications', [])
            if volume_apps:
                for app in volume_apps:
                    excel_data['details'].append({
                        'Марка бетона': item.get('grade', ''),
                        'Элемент': app.get('element', ''),
                        'Объем (м³)': app.get('volume_m3', 0),
                        'Количество позиций': app.get('entries_count', 0),
                        'Источник': item.get('method', ''),
                        'Контекст': item.get('context', '')[:100] + '...' if len(item.get('context', '')) > 100 else item.get('context', '')
                    })
            else:
                excel_data['details'].append({
                    'Марка бетона': item.get('grade', ''),
                    'Элемент': item.get('location', ''),
                    'Объем (м³)': 0,
                    'Количество позиций': 0,
                    'Источник': item.get('method', ''),
                    'Контекст': item.get('context', '')[:100] + '...' if len(item.get('context', '')) > 100 else item.get('context', '')
                })
        
        # Документы
        docs = analysis_result.get('processed_documents', [])
        for doc in docs:
            if isinstance(doc, dict):
                excel_data['documents'].append({
                    'Файл': doc.get('file', ''),
                    'Тип': doc.get('type', ''),
                    'Размер (символов)': doc.get('text_length', 0),
                    'Статус': 'Обработан' if doc.get('text_length', 0) > 0 else 'Ошибка'
                })
        
        return excel_data

    def _extract_exposure_classes(self, context: str) -> str:
        """Извлекает классы воздействия из контекста"""
        classes = []
        for match in re.finditer(r'\b[XO][CDFASM]?\d*\b', context):
            classes.append(match.group())
        return ', '.join(classes) if classes else ''

    def save_markdown_report(self, analysis_result: Dict[str, Any], output_path: str) -> bool:
        """Сохраняет отчет в Markdown файл"""
        try:
            report_content = self.generate_markdown_report(analysis_result)
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            logger.info(f"📄 Markdown отчет сохранен: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения отчета: {e}")
            return False

    def save_json_data(self, analysis_result: Dict[str, Any], output_path: str) -> bool:
        """Сохраняет данные в JSON для дальнейшей обработки"""
        try:
            excel_data = self.generate_excel_data(analysis_result)
            
            output_data = {
                'analysis_result': analysis_result,
                'excel_data': excel_data,
                'generated_at': datetime.now().isoformat(),
                'language': self.language
            }
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📊 JSON данные сохранены: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения JSON: {e}")
            return False


# Singleton instance
_report_generator = None

def get_report_generator(language: str = 'cz') -> ConcreteReportGenerator:
    """Получение глобального экземпляра генератора отчетов"""
    global _report_generator
    if _report_generator is None or _report_generator.language != language.lower():
        _report_generator = ConcreteReportGenerator(language)
        logger.info(f"📋 Report generator initialized (language: {language})")
    return _report_generator


def test_report_generator():
    """Тестирование генератора отчетов"""
    generator = get_report_generator('cz')
    
    # Тестовые данные
    test_data = {
        'concrete_summary': [
            {
                'grade': 'C25/30',
                'location': 'vrtané piloty (drilled piles)',
                'context': 'Založení zdi bude provedeno z velkoprůměrových vrtaných pilot betonu třídy C25/30 – XA1, XC2.',
                'confidence': 0.95,
                'method': 'regex_enhanced_czech',
                'total_volume_m3': 85.25,
                'volume_applications': [
                    {'element': 'piloty', 'volume_m3': 85.25, 'entries_count': 3}
                ],
                'has_volume_data': True
            }
        ],
        'analysis_method': 'hybrid_enhanced_czech',
        'czech_preprocessing': {'diacritic_fixes': 2137},
        'processed_documents': [
            {'file': 'test.pdf', 'type': 'Document', 'text_length': 75000}
        ],
        'volume_analysis': {
            'total_entries': 5,
            'grades_with_volumes': 2
        }
    }
    
    # Генерируем отчет
    report = generator.generate_markdown_report(test_data)
    
    print("🧪 TESTING REPORT GENERATOR")
    print("=" * 50)
    print(report[:500] + "...")
    
    return report


if __name__ == "__main__":
    test_report_generator()
