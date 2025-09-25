"""
parsers/smeta_parser.py
Улучшенный парсер смет для различных форматов
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class SmetaParser:
    """
    Универсальный парсер смет поддерживающий различные форматы
    """
    
    def __init__(self):
        self.supported_formats = ['.xml', '.xlsx', '.xls', '.pdf', '.docx', '.txt']
        logger.info("📋 SmetaParser инициализирован")

    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Главная функция парсинга сметы
        
        Args:
            file_path: Путь к файлу сметы
            
        Returns:
            Структура с позициями сметы
        """
        if not os.path.exists(file_path):
            logger.error(f"❌ Файл сметы не найден: {file_path}")
            return {"items": [], "summary": {}, "error": "Файл не найден"}
        
        file_ext = Path(file_path).suffix.lower()
        file_name = Path(file_path).name
        
        logger.info(f"📊 Начало парсинга сметы: {file_name}")
        
        try:
            if file_ext == '.xml':
                items = self._parse_xml_smeta(file_path)
            elif file_ext in ['.xlsx', '.xls']:
                items = self._parse_excel_smeta(file_path)
            elif file_ext == '.pdf':
                items = self._parse_pdf_smeta(file_path)
            elif file_ext in ['.docx', '.txt']:
                items = self._parse_document_smeta(file_path)
            else:
                logger.warning(f"⚠️ Неподдерживаемый формат сметы: {file_ext}")
                return {"items": [], "summary": {}, "error": f"Формат {file_ext} не поддерживается"}
            
            # Создаем сводку
            summary = self._create_summary(items)
            
            logger.info(f"✅ Смета обработана: {len(items)} позиций")
            
            return {
                "items": items,
                "summary": summary,
                "source_file": file_name,
                "format": file_ext,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга сметы {file_name}: {e}")
            return {"items": [], "summary": {}, "error": str(e)}

    def _parse_xml_smeta(self, file_path: str) -> List[Dict[str, Any]]:
        """Парсинг XML сметы"""
        try:
            # Импортируем существующий XML парсер
            from parsers.xml_smeta_parser import parse_xml_smeta
            
            xml_rows = parse_xml_smeta(file_path)
            
            # Конвертируем в стандартный формат
            items = []
            for row in xml_rows:
                items.append({
                    "row": row.get("row", 0),
                    "code": row.get("code", ""),
                    "name": row.get("name", ""),
                    "quantity": row.get("qty", 0),
                    "unit": row.get("unit", ""),
                    "price": 0,  # Цена не указана в XML парсере
                    "total": 0,
                    "source": "XML"
                })
            
            return items
            
        except ImportError:
            logger.error("❌ xml_smeta_parser не найден")
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга XML сметы: {e}")
            return []

    def _parse_excel_smeta(self, file_path: str) -> List[Dict[str, Any]]:
        """Парсинг Excel сметы"""
        try:
            import pandas as pd
            
            # Читаем Excel файл
            df = pd.read_excel(file_path, sheet_name=0, header=0)
            
            items = []
            
            # Пытаемся найти стандартные колонки
            column_mapping = self._detect_excel_columns(df.columns)
            
            for idx, row in df.iterrows():
                try:
                    # Извлекаем данные по найденным колонкам
                    item = {
                        "row": idx + 1,
                        "code": self._safe_get_value(row, column_mapping.get("code", "")),
                        "name": self._safe_get_value(row, column_mapping.get("name", "")),
                        "quantity": self._safe_get_numeric(row, column_mapping.get("quantity", "")),
                        "unit": self._safe_get_value(row, column_mapping.get("unit", "")),
                        "price": self._safe_get_numeric(row, column_mapping.get("price", "")),
                        "total": self._safe_get_numeric(row, column_mapping.get("total", "")),
                        "source": "Excel"
                    }
                    
                    # Добавляем только строки с содержимым
                    if item["name"] or item["code"]:
                        items.append(item)
                        
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка обработки строки {idx}: {e}")
                    continue
            
            return items
            
        except ImportError:
            logger.error("❌ pandas не установлен. Установите: pip install pandas openpyxl")
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга Excel сметы: {e}")
            return []

    def _parse_pdf_smeta(self, file_path: str) -> List[Dict[str, Any]]:
        """Парсинг PDF сметы"""
        try:
            # Используем существующий DocParser
            from parsers.doc_parser import DocParser
            
            doc_parser = DocParser()
            text = doc_parser.parse(file_path)
            
            if not text:
                return []
            
            # Анализируем текст на предмет сметных позиций
            return self._parse_text_smeta(text, "PDF")
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга PDF сметы: {e}")
            return []

    def _parse_document_smeta(self, file_path: str) -> List[Dict[str, Any]]:
        """Парсинг DOCX/TXT сметы"""
        try:
            from parsers.doc_parser import DocParser
            
            doc_parser = DocParser()
            text = doc_parser.parse(file_path)
            
            if not text:
                return []
            
            format_name = "DOCX" if file_path.endswith('.docx') else "TXT"
            return self._parse_text_smeta(text, format_name)
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга документа сметы: {e}")
            return []

    def _parse_text_smeta(self, text: str, source: str) -> List[Dict[str, Any]]:
        """Парсинг сметы из текста"""
        items = []
        lines = text.split('\n')
        
        # Паттерны для поиска сметных позиций
        smeta_patterns = [
            # Стандартные коды + описание + количество + единица
            r'(\d{3}\.\d{3}\.\d{3})\s+(.+?)\s+(\d+(?:[,.]\d+)?)\s+(m[23]|ks|kg|t|шт|м[23])',
            # Простой формат: номер + описание + количество
            r'^(\d+)\s+(.+?)\s+(\d+(?:[,.]\d+)?)\s*(m[23]|ks|kg|t|шт|м[23]|)',
            # Описание с количеством и единицами в конце
            r'(.+?)\s+(\d+(?:[,.]\d+)?)\s+(m[23]|ks|kg|t|шт|м[23])$',
        ]
        
        row_number = 1
        for line in lines:
            line = line.strip()
            if len(line) < 10:  # Пропускаем короткие строки
                continue
            
            for pattern in smeta_patterns:
                import re
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    try:
                        groups = match.groups()
                        
                        if len(groups) >= 3:
                            if len(groups) == 4:  # С кодом
                                code, name, qty_str, unit = groups
                            else:  # Без кода
                                code = ""
                                name, qty_str, unit = groups
                            
                            # Конвертируем количество
                            quantity = float(qty_str.replace(',', '.'))
                            
                            item = {
                                "row": row_number,
                                "code": code.strip(),
                                "name": name.strip(),
                                "quantity": quantity,
                                "unit": unit.strip(),
                                "price": 0,
                                "total": 0,
                                "source": source
                            }
                            
                            items.append(item)
                            row_number += 1
                            break
                            
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Ошибка обработки строки: {line[:50]}... - {e}")
                        continue
        
        return items

    def _detect_excel_columns(self, columns) -> Dict[str, str]:
        """Определяет названия колонок в Excel файле"""
        column_mapping = {}
        
        # Словарь возможных названий колонок
        column_patterns = {
            "code": ["код", "code", "шифр", "позиция", "№"],
            "name": ["наименование", "название", "name", "описание", "работы"],
            "quantity": ["количество", "qty", "кол-во", "объем", "кол."],
            "unit": ["ед.изм", "единица", "unit", "ед.", "изм"],
            "price": ["цена", "price", "стоимость", "тариф"],
            "total": ["всего", "total", "сумма", "итого"]
        }
        
        for field, patterns in column_patterns.items():
            for col in columns:
                col_lower = str(col).lower()
                for pattern in patterns:
                    if pattern in col_lower:
                        column_mapping[field] = col
                        break
                if field in column_mapping:
                    break
        
        return column_mapping

    def _safe_get_value(self, row, column: str) -> str:
        """Безопасное извлечение значения из строки"""
        if not column or column not in row.index:
            return ""
        
        value = row[column]
        if pd.isna(value):
            return ""
        
        return str(value).strip()

    def _safe_get_numeric(self, row, column: str) -> float:
        """Безопасное извлечение числового значения"""
        if not column or column not in row.index:
            return 0.0
        
        try:
            import pandas as pd
            value = row[column]
            if pd.isna(value):
                return 0.0
            
            # Конвертируем строку в число
            if isinstance(value, str):
                value = value.replace(',', '.').strip()
                # Удаляем все кроме цифр, точек и минусов
                import re
                value = re.sub(r'[^\d.,-]', '', value)
                if not value:
                    return 0.0
            
            return float(value)
            
        except (ValueError, TypeError):
            return 0.0

    def _create_summary(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Создает сводку по позициям сметы"""
        if not items:
            return {}
        
        total_items = len(items)
        total_quantity = sum(item.get("quantity", 0) for item in items)
        total_cost = sum(item.get("total", 0) for item in items)
        
        # Группировка по единицам измерения
        units_summary = {}
        for item in items:
            unit = item.get("unit", "")
            if unit:
                if unit not in units_summary:
                    units_summary[unit] = {"count": 0, "quantity": 0}
                units_summary[unit]["count"] += 1
                units_summary[unit]["quantity"] += item.get("quantity", 0)
        
        return {
            "total_items": total_items,
            "total_quantity": total_quantity,
            "total_cost": total_cost,
            "units_summary": units_summary,
            "has_prices": any(item.get("price", 0) > 0 for item in items),
            "has_codes": any(item.get("code", "") for item in items)
        }


# Функция для тестирования
def test_smeta_parser():
    """Тестирование парсера смет"""
    parser = SmetaParser()
    
    # Создаем тестовый текст
    test_text = """
    801.001.001 Beton prostý C12/15-X0 125,50 m3
    801.002.001 Železobeton C25/30-XC2 85,25 m3
    802.001.001 Výztuž betonářská 2500,00 kg
    """
    
    # Тестируем текстовый парсинг
    items = parser._parse_text_smeta(test_text, "TEST")
    
    print("🧪 TESTING SMETA PARSER")
    print("=" * 40)
    
    for item in items:
        print(f"Code: {item['code']}")
        print(f"Name: {item['name']}")
        print(f"Quantity: {item['quantity']} {item['unit']}")
        print("-" * 30)
    
    summary = parser._create_summary(items)
    print(f"Total items: {summary['total_items']}")
    print(f"Units: {list(summary['units_summary'].keys())}")
    
    return items


if __name__ == "__main__":
    test_smeta_parser()
