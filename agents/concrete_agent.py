"""
Улучшенный ConcreteAgentHybrid — агент для комплексного анализа бетонов.
Возможности:
- OCR для чертежей с распознаванием марок и мест применения
- Расширенные regex для всех форматов обозначений
- Интеграция с knowledge base
- Парсинг XML смет с кодами
- Улучшение результатов через Claude
"""

import re
import os
import json
import logging
import pdfplumber
import pytesseract
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from xml.etree import ElementTree as ET
from PIL import Image, ImageEnhance
from dataclasses import dataclass

from parsers.doc_parser import DocParser
from parsers.smeta_parser import SmetaParser
from utils.claude_client import get_claude_client
from config.settings import settings
from outputs.save_report import save_merged_report

logger = logging.getLogger(__name__)

@dataclass
class ConcreteMatch:
    """Структура для найденной марки бетона"""
    grade: str
    context: str
    location: str
    confidence: float
    method: str
    coordinates: Optional[Tuple[int, int, int, int]] = None

@dataclass 
class StructuralElement:
    """Структура для конструктивного элемента"""
    name: str
    concrete_grade: Optional[str]
    location: str
    context: str

class analyze_concrete:
    def __init__(self, knowledge_base_path="complete-concrete-knowledge-base.json"):
        # Загружаем базу знаний
        try:
            with open(knowledge_base_path, "r", encoding="utf-8") as f:
                self.knowledge_base = json.load(f)
            logger.info("📚 Knowledge-base загружен успешно")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось загрузить knowledge-base: {e}")
            self.knowledge_base = self._create_default_kb()

        self.doc_parser = DocParser()
        self.smeta_parser = SmetaParser()
        self.claude_client = get_claude_client() if settings.is_claude_enabled() else None

        # Расширенные паттерны для поиска марок бетона
        self.concrete_patterns = [
            # Полные обозначения с классами воздействия
            r'\bC\d{1,2}/\d{1,2}(?:\s*[-–]\s*[XO][CDFASM]?\d*(?:\s*,\s*[XO][CDFASM]?\d*)*)*\b',
            # Стандартные обозначения
            r'\b[BC]\s*\d{1,2}(?:/\d{1,2})?\b',
            # Легкий бетон
            r'\bLC\s*\d{1,2}/\d{1,2}\b',
            # Только цифры (в контексте)
            r'(?i)(?:beton[uá]?\s+)?(?:tříd[ayě]\s+)?(\d{2}/\d{2}|\d{2,3})\b',
            # В чешском тексте
            r'(?i)(?:betony?|betonovéj?)\s+(?:tříd[yě]\s+)?([BC]?\d{1,2}(?:/\d{1,2})?)',
            # С префиксами качества
            r'\b(?:vysokopevnostn[íý]|lehk[ýá]|těžk[ýá])\s+beton\s+([BC]?\d{1,2}(?:/\d{1,2})?)\b',
        ]

        # Конструктивные элементы (чешские термины)
        self.structural_elements = {
            # Основные конструкции
            'OPĚRA': {'en': 'abutment', 'applications': ['XC4', 'XD1', 'XF2']},
            'PILÍŘ': {'en': 'pier', 'applications': ['XC4', 'XD3', 'XF4']},
            'ŘÍMSA': {'en': 'cornice', 'applications': ['XC4', 'XD3', 'XF4']},
            'MOSTOVKA': {'en': 'deck', 'applications': ['XC4', 'XD3', 'XF4']},
            'ZÁKLAD': {'en': 'foundation', 'applications': ['XC1', 'XC2', 'XA1']},
            'VOZOVKA': {'en': 'roadway', 'applications': ['XF2', 'XF4', 'XD1']},
            'GARÁŽ': {'en': 'garage', 'applications': ['XD1']},
            
            # Дополнительные элементы
            'STĚNA': {'en': 'wall', 'applications': ['XC1', 'XC3', 'XC4']},
            'SLOUP': {'en': 'column', 'applications': ['XC1', 'XC3']},
            'SCHODIŠTĚ': {'en': 'stairs', 'applications': ['XC1', 'XC3']},
            'PODKLADNÍ': {'en': 'subgrade', 'applications': ['X0', 'XC1']},
            'NOSNÁ': {'en': 'load-bearing', 'applications': ['XC1', 'XC3']},
            'VĚNEC': {'en': 'tie-beam', 'applications': ['XC2', 'XF1']},
            'DESKA': {'en': 'slab', 'applications': ['XC1', 'XC2']},
            'PREFABRIKÁT': {'en': 'precast', 'applications': ['XC1', 'XC3']},
            'MONOLITICKÝ': {'en': 'monolithic', 'applications': ['XC1', 'XC2']},
        }

        # Коды смет и их соответствия
        self.smeta_codes = {
            '801': 'Prostý beton',
            '802': 'Železobeton monolitický',
            '803': 'Železobeton prefabrikovaný',
            '811': 'Betony speciální',
            '271': 'Konstrukce betonové a železobetonové',
            'HSV': 'Hlavní stavební výroba',
            'PSV': 'Přidružená stavební výroba',
        }

    def _create_default_kb(self) -> Dict:
        """Создает минимальную базу знаний по умолчанию"""
        return {
            "environment_classes": {
                "XC1": {"description": "suché nebo stále mokré", "applications": ["interiér", "základy"]},
                "XC2": {"description": "mokré, občas suché", "applications": ["základy", "spodní stavba"]},
                "XC3": {"description": "středně mokré", "applications": ["kryté prostory"]},
                "XC4": {"description": "střídavě mokré a suché", "applications": ["vnější povrchy"]},
                "XD1": {"description": "chloridy - mírné", "applications": ["garáže", "parkoviště"]},
                "XD3": {"description": "chloridy - silné", "applications": ["mosty", "vozovky"]},
                "XF1": {"description": "mráz - mírný", "applications": ["vnější svislé plochy"]},
                "XF2": {"description": "mráz + soli", "applications": ["silniční konstrukce"]},
                "XF4": {"description": "mráz + soli - extrémní", "applications": ["mostovky", "vozovky"]},
                "XA1": {"description": "chemicky agresivní - slabě", "applications": ["základy", "septiky"]},
            }
        }

    # ==============================
# 🔧 Глобальные функции
# ==============================

# Глобальный экземпляр агента
_hybrid_agent = None

def get_hybrid_agent() -> analyze_concrete:
    """Получение глобального экземпляра гибридного агента"""
    global _hybrid_agent
    if _hybrid_agent is None:
        _hybrid_agent = analyze_concrete()
        logger.info("🤖 analyze_concrete инициализирован")
    return _hybrid_agent

# ==============================
# 🚀 API-совместимые функции
# ==============================

async def analyze_concrete(doc_paths: List[str], smeta_path: Optional[str] = None,
                           use_claude: bool = True, claude_mode: str = "enhancement") -> Dict[str, Any]:
    """
    Главная функция для анализа бетона - совместима с существующим API
    
    Args:
        doc_paths: Список путей к документам для анализа
        smeta_path: Путь к смете (опционально)
        use_claude: Использовать ли Claude для улучшения результатов
        claude_mode: Режим Claude ("enhancement", "primary", "fallback")
        
    Returns:
        Dict с результатами анализа
    """
    agent = get_hybrid_agent()
    
    try:
        result = await agent.analyze(doc_paths, smeta_path, use_claude, claude_mode)
        
        # Сохраняем результат
        try:
            save_merged_report(result, "outputs/concrete_analysis_report.json")
            logger.info("💾 Отчет сохранен в outputs/concrete_analysis_report.json")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось сохранить отчёт: {e}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в analyze_concrete: {e}")
        return {
            "error": str(e),
            "success": False,
            "analysis_method": "error",
            "concrete_summary": []
        }

def analyze_drawings_ocr(image_paths: List[str]) -> Dict[str, Any]:
    """
    Специализированная функция для анализа чертежей с OCR
    
    Args:
        image_paths: Пути к изображениям чертежей
        
    Returns:
        Dict с результатами OCR анализа
    """
    agent = get_hybrid_agent()
    results = []
    
    for image_path in image_paths:
        try:
            # Загружаем изображение
            image = Image.open(image_path)
            
            # OCR анализ
            text, word_positions = agent._extract_text_with_ocr(image)
            
            # Поиск марок бетона
            concrete_matches = agent._find_concrete_in_drawing(text, word_positions)
            
            results.append({
                'image': Path(image_path).name,
                'extracted_text': text[:500],  # Первые 500 символов
                'concrete_matches': [
                    {
                        'grade': match.grade,
                        'location': match.location,
                        'confidence': match.confidence,
                        'coordinates': match.coordinates
                    } for match in concrete_matches
                ],
                'word_positions_count': len(word_positions)
            })
            
        except Exception as e:
            logger.error(f"❌ Ошибка OCR анализа {image_path}: {e}")
            results.append({
                'image': Path(image_path).name,
                'error': str(e)
            })
    
    return {
        'ocr_results': results,
        'total_images': len(image_paths),
        'successful_analyses': len([r for r in results if 'error' not in r]),
        'analysis_method': 'ocr_specialized'
    }

def analyze_xml_smeta(xml_path: str) -> Dict[str, Any]:
    """
    Специализированная функция для анализа XML смет
    
    Args:
        xml_path: Путь к XML файлу сметы
        
    Returns:
        Dict с результатами анализа сметы
    """
    agent = get_hybrid_agent()
    
    try:
        smeta_items = agent._parse_xml_smeta_advanced(xml_path)
        
        # Группируем по типам бетона
        concrete_summary = {}
        total_volume = 0
        total_cost = 0
        
        for item in smeta_items:
            if 'concrete_grades' in item:
                for grade in item['concrete_grades']:
                    if grade not in concrete_summary:
                        concrete_summary[grade] = {
                            'grade': grade,
                            'total_quantity': 0,
                            'items': [],
                            'unit': item.get('unit', 'm³')
                        }
                    
                    concrete_summary[grade]['items'].append({
                        'description': item.get('description', ''),
                        'quantity': item.get('quantity', 0),
                        'code': item.get('code', ''),
                        'price': item.get('price', 0)
                    })
                    
                    # Суммируем количество
                    if isinstance(item.get('quantity'), (int, float)):
                        concrete_summary[grade]['total_quantity'] += item['quantity']
                        total_volume += item['quantity']
                    
                    # Суммируем стоимость
                    if isinstance(item.get('price'), (int, float)):
                        total_cost += item['price']
        
        return {
            'xml_smeta_analysis': {
                'file': Path(xml_path).name,
                'concrete_summary': list(concrete_summary.values()),
                'total_items': len(smeta_items),
                'concrete_items': len([i for i in smeta_items if 'concrete_grades' in i]),
                'total_concrete_volume': total_volume,
                'estimated_total_cost': total_cost,
                'analysis_method': 'xml_smeta_specialized',
                'success': True
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка анализа XML сметы: {e}")
        return {
            'error': str(e),
            'success': False,
            'analysis_method': 'xml_smeta_error'
        }

def get_knowledge_base_info() -> Dict[str, Any]:
    """
    Возвращает информацию о загруженной базе знаний
    """
    agent = get_hybrid_agent()
    kb = agent.knowledge_base
    
    return {
        'knowledge_base_status': 'loaded' if kb else 'not_loaded',
        'environment_classes_count': len(kb.get('concrete_knowledge_base', {}).get('environment_classes', {})),
        'structural_elements_count': len(agent.structural_elements),
        'concrete_patterns_count': len(agent.concrete_patterns),
        'smeta_codes_count': len(agent.smeta_codes),
        'supported_features': [
            'OCR for drawings',
            'Advanced PDF parsing', 
            'XML smeta parsing',
            'Knowledge base lookup',
            'Structural element detection',
            'Claude AI enhancement',
            'Multi-format concrete grade detection'
        ],
        'supported_formats': [
            'PDF (text + OCR)',
            'DOCX', 
            'TXT',
            'XML (smetы)',
            'Images (PNG, JPG, TIFF)'
        ]
    }

# ==============================
# 🧪 Утилиты для тестирования
# ==============================

def test_concrete_patterns(test_string: str) -> Dict[str, Any]:
    """
    Тестирует все паттерны поиска бетона на примере строки
    """
    agent = get_hybrid_agent()
    results = {}
    
    for i, pattern in enumerate(agent.concrete_patterns):
        matches = re.findall(pattern, test_string, re.IGNORECASE)
        results[f'pattern_{i+1}'] = {
            'pattern': pattern,
            'matches': [agent._normalize_concrete_grade(m) for m in matches],
            'count': len(matches)
        }
    
    return {
        'test_string': test_string,
        'pattern_results': results,
        'total_unique_matches': len(set([
            agent._normalize_concrete_grade(m) 
            for pattern_result in results.values() 
            for m in pattern_result['matches']
        ]))
    }

def test_structural_elements(test_string: str) -> Dict[str, Any]:
    """
    Тестирует определение конструктивных элементов
    """
    agent = get_hybrid_agent()
    detected_elements = []
    
    test_upper = test_string.upper()
    for element, info in agent.structural_elements.items():
        if element in test_upper:
            detected_elements.append({
                'element': element,
                'english': info['en'],
                'applications': info['applications']
            })
    
    return {
        'test_string': test_string,
        'detected_elements': detected_elements,
        'location_identification': agent._identify_structural_element(test_string)
    }

if __name__ == "__main__":
    # Примеры использования
    import asyncio
    
    async def run_examples():
        # Пример 1: Анализ документов
        print("🏗️ Тест анализа документов...")
        result = await analyze_concrete(
            doc_paths=["example.pdf"], 
            use_claude=False,
            claude_mode="enhancement"
        )
        print(f"Найдено марок бетона: {len(result.get('concrete_summary', []))}")
        
        # Пример 2: Тест паттернов
        print("\n🔍 Тест паттернов...")
        test_result = test_concrete_patterns("Použitý beton C30/37-XF2, XD1 pro ŘÍMSA a PILÍŘ")
        print(f"Уникальных совпадений: {test_result['total_unique_matches']}")
        
        # Пример 3: Тест конструктивных элементов
        print("\n🏢 Тест конструктивных элементов...")
        struct_result = test_structural_elements("BETONOVÁ OPĚRA C25/30-XF1")
        print(f"Найдено элементов: {len(struct_result['detected_elements'])}")
        
        # Пример 4: Информация о базе знаний
        print("\n📚 Информация о базе знаний...")
        kb_info = get_knowledge_base_info()
        print(f"Статус: {kb_info['knowledge_base_status']}")
        print(f"Поддерживаемые форматы: {', '.join(kb_info['supported_formats'])}")
    
    # Запуск примеров
    # asyncio.run(run_examples())
    # 🖼️ OCR и обработка изображений
    # ==============================
    def _preprocess_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """Предобработка изображения для улучшения OCR"""
        # Конвертация в numpy array
        img_array = np.array(image)
        
        # Конвертация в градации серого
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Увеличение контрастности
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # Бинаризация с адаптивным порогом
        binary = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Морфологическая обработка для очистки шума
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        return Image.fromarray(cleaned)

    def _extract_text_with_ocr(self, image: Image.Image, preprocess: bool = True) -> Tuple[str, Dict]:
        """Извлекает текст из изображения с помощью OCR"""
        if preprocess:
            image = self._preprocess_image_for_ocr(image)
        
        # Конфигурация Tesseract для технических чертежей
        config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZČĎĚŇŘŠŤŮŽ0123456789/-.,()[]'
        
        try:
            # Основной OCR с детальными данными
            data = pytesseract.image_to_data(
                image, lang='ces+eng', config=config, output_type=pytesseract.Output.DICT
            )
            
            # Извлекаем текст
            text = pytesseract.image_to_string(image, lang='ces+eng', config=config)
            
            # Создаем словарь координат слов
            word_positions = {}
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 30:  # Минимальная уверенность
                    word = data['text'][i].strip()
                    if word:
                        word_positions[word] = {
                            'x': data['left'][i],
                            'y': data['top'][i], 
                            'w': data['width'][i],
                            'h': data['height'][i],
                            'conf': data['conf'][i]
                        }
            
            return text, word_positions
            
        except Exception as e:
            logger.error(f"Ошибка OCR: {e}")
            return "", {}

    def _find_concrete_in_drawing(self, text: str, word_positions: Dict) -> List[ConcreteMatch]:
        """Поиск марок бетона на чертеже с учетом контекста"""
        matches = []
        
        # Разбиваем текст на строки для анализа контекста
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            # Ищем марки бетона в каждой строке
            for pattern in self.concrete_patterns:
                concrete_matches = re.finditer(pattern, line, re.IGNORECASE)
                
                for match in concrete_matches:
                    grade = match.group().strip()
                    if not grade:
                        continue
                    
                    # Определяем контекст (соседние строки)
                    context_lines = []
                    for j in range(max(0, i-2), min(len(lines), i+3)):
                        context_lines.append(lines[j].strip())
                    context = ' '.join(context_lines)
                    
                    # Ищем конструктивные элементы в контексте
                    location = self._identify_structural_element(context)
                    
                    # Определяем координаты (если доступны)
                    coordinates = self._find_word_coordinates(grade, word_positions)
                    
                    matches.append(ConcreteMatch(
                        grade=self._normalize_concrete_grade(grade),
                        context=context[:200],  # Ограничиваем длину контекста
                        location=location,
                        confidence=0.8 if coordinates else 0.6,
                        method='ocr',
                        coordinates=coordinates
                    ))
        
        return matches

    def _find_word_coordinates(self, word: str, word_positions: Dict) -> Optional[Tuple[int, int, int, int]]:
        """Находит координаты слова на изображении"""
        for pos_word, coords in word_positions.items():
            if word.lower() in pos_word.lower() or pos_word.lower() in word.lower():
                return (coords['x'], coords['y'], coords['w'], coords['h'])
        return None

    def _identify_structural_element(self, context: str) -> str:
        """Определяет тип конструктивного элемента из контекста"""
        context_upper = context.upper()
        
        # Прямое совпадение с ключевыми словами
        for element, info in self.structural_elements.items():
            if element in context_upper:
                return f"{element} ({info['en']})"
        
        # Поиск частичных совпадений
        for element, info in self.structural_elements.items():
            if any(part in context_upper for part in element.split()):
                return f"{element} ({info['en']}) - частичное совпадение"
        
        return "неопределено"

    def _normalize_concrete_grade(self, grade: str) -> str:
        """Нормализует обозначение марки бетона"""
        # Убираем лишние пробелы и приводим к стандартному формату
        normalized = re.sub(r'\s+', '', grade.upper())
        
        # Преобразования для стандартизации
        normalized = re.sub(r'^B(\d+)$', r'C\1/\1', normalized)  # B20 -> C20/25
        normalized = re.sub(r'^(\d+)$', r'C\1', normalized)       # 30 -> C30
        
        return normalized

    # ==============================
    # 📄 Улучшенная обработка PDF
    # ==============================
    def _parse_pdf_advanced(self, file_path: str) -> Tuple[str, List[ConcreteMatch]]:
        """Продвинутый анализ PDF с текстом и OCR"""
        text_content = ""
        ocr_matches = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Извлекаем обычный текст
                    page_text = page.extract_text() or ""
                    text_content += f"\n--- Страница {page_num + 1} ---\n{page_text}"
                    
                    # Если текста мало, используем OCR
                    if len(page_text.strip()) < 100:
                        try:
                            # Конвертируем страницу в изображение
                            img = page.to_image(resolution=300).original
                            
                            # OCR анализ
                            ocr_text, word_positions = self._extract_text_with_ocr(img)
                            
                            if ocr_text.strip():
                                text_content += f"\n--- OCR Страница {page_num + 1} ---\n{ocr_text}"
                                
                                # Ищем марки бетона на чертеже
                                drawing_matches = self._find_concrete_in_drawing(ocr_text, word_positions)
                                ocr_matches.extend(drawing_matches)
                        
                        except Exception as e:
                            logger.warning(f"OCR ошибка для страницы {page_num + 1}: {e}")
            
            logger.info(f"📄 PDF обработан: {len(text_content)} символов, {len(ocr_matches)} OCR совпадений")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки PDF {file_path}: {e}")
        
        return text_content, ocr_matches

    # ==============================
    # 📊 Расширенный парсинг XML смет
    # ==============================
    def _parse_xml_smeta_advanced(self, smeta_path: str) -> List[Dict]:
        """Продвинутый парсинг XML смет с кодами и маппингом"""
        items = []
        try:
            tree = ET.parse(smeta_path)
            root = tree.getroot()
            
            # Рекурсивный поиск элементов смет
            for elem in root.iter():
                item_data = {}
                
                # Извлекаем различные поля
                if elem.tag.lower() in ['item', 'row', 'position', 'pozice']:
                    # Код позиции
                    code = elem.findtext('.//code') or elem.findtext('.//kod') or elem.get('code', '')
                    if code:
                        item_data['code'] = code.strip()
                        item_data['code_description'] = self.smeta_codes.get(code[:3], 'Neznámá kategorie')
                    
                    # Описание
                    desc = elem.findtext('.//description') or elem.findtext('.//popis') or elem.findtext('.//name')
                    if desc and any(word in desc.lower() for word in ['beton', 'concrete', 'železobeton']):
                        item_data['description'] = desc.strip()
                        
                        # Ищем марки бетона в описании
                        concrete_grades = []
                        for pattern in self.concrete_patterns:
                            matches = re.findall(pattern, desc, re.IGNORECASE)
                            concrete_grades.extend([self._normalize_concrete_grade(m) for m in matches])
                        
                        if concrete_grades:
                            item_data['concrete_grades'] = list(set(concrete_grades))
                    
                    # Количество и единица
                    qty = elem.findtext('.//quantity') or elem.findtext('.//mnozstvi')
                    if qty:
                        item_data['quantity'] = float(qty.replace(',', '.')) if qty.replace(',', '.').replace('.', '').isdigit() else qty
                    
                    unit = elem.findtext('.//unit') or elem.findtext('.//jednotka')
                    if unit:
                        item_data['unit'] = unit.strip()
                    
                    # Цена
                    price = elem.findtext('.//price') or elem.findtext('.//cena')
                    if price:
                        try:
                            item_data['price'] = float(price.replace(',', '.').replace(' ', ''))
                        except:
                            item_data['price'] = price
                    
                    if item_data:
                        items.append(item_data)
                
                # Также проверяем прямой текст элементов
                elif elem.text and any(word in elem.text.lower() for word in ['beton', 'concrete']):
                    simple_item = {'description': elem.text.strip()}
                    
                    # Ищем марки бетона
                    concrete_grades = []
                    for pattern in self.concrete_patterns:
                        matches = re.findall(pattern, elem.text, re.IGNORECASE)
                        concrete_grades.extend([self._normalize_concrete_grade(m) for m in matches])
                    
                    if concrete_grades:
                        simple_item['concrete_grades'] = list(set(concrete_grades))
                    
                    items.append(simple_item)
            
            logger.info(f"📊 XML смета: найдено {len(items)} позиций")
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга XML сметы: {e}")
        
        return items

    # ==============================
    # 🧠 Интегрированный локальный анализ
    # ==============================
    def _local_concrete_analysis(self, text: str, ocr_matches: List[ConcreteMatch] = None) -> Dict[str, Any]:
        """Комплексный локальный анализ с использованием всех методов"""
        all_matches = []
        
        # 1. Обычный regex поиск в тексте
        for pattern in self.concrete_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                grade = self._normalize_concrete_grade(match.group().strip())
                context = text[max(0, match.start()-100):match.end()+100]
                location = self._identify_structural_element(context)
                
                all_matches.append(ConcreteMatch(
                    grade=grade,
                    context=context.strip(),
                    location=location,
                    confidence=0.9,
                    method='regex'
                ))
        
        # 2. Добавляем результаты OCR
        if ocr_matches:
            all_matches.extend(ocr_matches)
        
        # 3. Дедупликация и группировка
        unique_matches = {}
        for match in all_matches:
            key = match.grade
            if key not in unique_matches or match.confidence > unique_matches[key].confidence:
                unique_matches[key] = match
        
        # 4. Обогащение данными из knowledge base
        enriched_results = []
        for match in unique_matches.values():
            kb_info = self._lookup_in_kb(match.grade, match.context)
            
            result = {
                'grade': match.grade,
                'location': match.location,
                'context': match.context[:200],
                'confidence': match.confidence,
                'method': match.method,
                'kb_info': kb_info,
                'coordinates': match.coordinates
            }
            enriched_results.append(result)
        
        return {
            'concrete_summary': enriched_results,
            'analysis_method': 'enhanced_local',
            'total_matches': len(enriched_results),
            'success': True
        }

    def _lookup_in_kb(self, grade: str, context: str) -> Dict[str, Any]:
        """Расширенный поиск в базе знаний"""
        kb_classes = self.knowledge_base.get('concrete_knowledge_base', {}).get('environment_classes', {})
        
        # Извлекаем классы воздействия из марки
        exposure_classes = re.findall(r'X[CDFASM]\d*', grade, re.IGNORECASE)
        
        # Информация о найденных классах
        class_info = {}
        applications = []
        
        for exp_class in exposure_classes:
            exp_class_upper = exp_class.upper()
            if exp_class_upper in kb_classes:
                class_info[exp_class_upper] = kb_classes[exp_class_upper]
                applications.extend(kb_classes[exp_class_upper].get('applications', []))
        
        # Определяем рекомендуемые применения на основе контекста
        context_applications = []
        context_upper = context.upper()
        
        for element, info in self.structural_elements.items():
            if element in context_upper:
                context_applications.extend(info['applications'])
        
        return {
            'exposure_classes': exposure_classes,
            'class_details': class_info,
            'recommended_applications': list(set(applications)),
            'context_applications': list(set(context_applications)),
            'compliance': len(set(applications).intersection(set(context_applications))) > 0
        }

    # ==============================
    # 🤖 Claude интеграция
    # ==============================
    async def _claude_concrete_analysis(self, text: str, smeta_data: List[Dict]) -> Dict[str, Any]:
        """Анализ через Claude с расширенным контекстом"""
        if not self.claude_client:
            return {"success": False, "error": "Claude client not available"}
        
        try:
            # Подготавливаем контекст с найденными элементами
            context_prompt = f"""
Дополнительный контекст для анализа:

Конструктивные элементы в документе:
{', '.join(self.structural_elements.keys())}

Коды смет, найденные в документе:
{[item.get('code', 'N/A') for item in smeta_data if 'code' in item]}

Требуется найти и проанализировать:
1. Все марки бетона (включая C30/37-XF2,XD1,XC4)
2. Классы воздействия среды (XC, XD, XF, XA, XM)
3. Соответствие марок местам применения
4. Проверка соответствия чешским нормам ČSN EN 206
            """
            
            result = await self.claude_client.analyze_concrete_with_claude(
                text + "\n\n" + context_prompt, 
                smeta_data
            )
            
            return {
                'concrete_summary': result.get('claude_analysis', {}).get('concrete_grades', []),
                'analysis_method': 'claude_enhanced',
                'success': True,
                'tokens_used': result.get('tokens_used', 0),
                'raw_response': result.get('raw_response', '')
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка Claude анализа: {e}")
            return {"success": False, "error": str(e)}

    # ==============================
    # 🎯 Главная функция анализа
    # ==============================
    async def analyze(self, doc_paths: List[str], smeta_path: Optional[str] = None,
                      use_claude: bool = True, claude_mode: str = "enhancement") -> Dict[str, Any]:
        """
        Комплексный анализ документов с использованием всех возможностей
        """
        logger.info(f"🏗️ Запуск комплексного анализа (режим: {claude_mode})")
        
        all_text = ""
        all_ocr_matches = []
        processed_docs = []
        
        # Обрабатываем каждый документ
        for doc_path in doc_paths:
            try:
                if doc_path.lower().endswith('.pdf'):
                    text, ocr_matches = self._parse_pdf_advanced(doc_path)
                    all_text += text
                    all_ocr_matches.extend(ocr_matches)
                else:
                    text = self.doc_parser.parse(doc_path)
                    all_text += text
                
                processed_docs.append({
                    'file': Path(doc_path).name,
                    'type': 'PDF' if doc_path.lower().endswith('.pdf') else 'Document',
                    'text_length': len(text),
                    'ocr_matches': len(ocr_matches) if doc_path.lower().endswith('.pdf') else 0
                })
                
            except Exception as e:
                logger.error(f"❌ Ошибка обработки {doc_path}: {e}")
                processed_docs.append({'file': Path(doc_path).name, 'error': str(e)})
        
        # Обрабатываем смету
        smeta_data = []
        if smeta_path:
            try:
                if smeta_path.lower().endswith('.xml'):
                    smeta_data = self._parse_xml_smeta_advanced(smeta_path)
                else:
                    smeta_result = self.smeta_parser.parse(smeta_path)
                    smeta_data = smeta_result.get('items', [])
                
                logger.info(f"📊 Смета обработана: {len(smeta_data)} позиций")
            except Exception as e:
                logger.error(f"❌ Ошибка обработки сметы: {e}")
        
        # Локальный анализ с OCR
        local_result = self._local_concrete_analysis(all_text, all_ocr_matches)
        
        # Интеграция с Claude
        final_result = local_result.copy()
        
        if use_claude and self.claude_client:
            claude_result = await self._claude_concrete_analysis(all_text, smeta_data)
            
            if claude_mode == "primary" and claude_result.get("success"):
                # Используем только Claude результат
                final_result = claude_result
            elif claude_mode == "enhancement" and claude_result.get("success"):
                # Объединяем локальный и Claude результаты
                final_result.update({
                    'claude_analysis': claude_result,
                    'analysis_method': 'hybrid_enhanced',
                    'total_tokens_used': claude_result.get('tokens_used', 0)
                })
        
        # Добавляем метаданные
        final_result.update({
            'processed_documents': processed_docs,
            'smeta_items': len(smeta_data),
            'processing_time': 'completed',
            'knowledge_base_version': '3.0',
            'ocr_enabled': True,
            'features_used': [
                'regex_patterns',
                'ocr_analysis', 
                'knowledge_base_lookup',
                'structural_element_detection',
                'xml_smeta_parsing'
            ] + (['claude_enhancement'] if use_claude else [])
        })
        
        return final_result


# ==============================
