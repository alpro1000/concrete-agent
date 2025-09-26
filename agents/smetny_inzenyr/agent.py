"""
Специализированный агент-сметчик для парсинга смет и ведомостей
agents/smetny_inzenyr/agent.py

Отвечает только за:
1. Парсинг проектных документов (PDF, DOCX, Excel, XML)
2. Извлечение структурированных данных из смет
3. Нормализацию данных ведомостей объемов работ
4. Подготовку данных для других агентов
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from parsers.doc_parser import DocParser
from parsers.smeta_parser import SmetaParser
from parsers.xml_smeta_parser import parse_xml_smeta
from outputs.save_report import save_merged_report

logger = logging.getLogger(__name__)

@dataclass
class SmetaRow:
    """Структура строки сметы"""
    code: str
    description: str
    quantity: float
    unit: str
    unit_price: Optional[float]
    total_cost: Optional[float]
    source_document: str
    row_number: int
    category: Optional[str] = None  # бетон, арматура, материалы и т.д.

@dataclass
class DocumentParsingResult:
    """Результат парсинга документа"""
    document_path: str
    document_type: str  # pdf, docx, xlsx, xml
    success: bool
    rows_count: int
    error_message: Optional[str]
    parsed_data: Any
    metadata: Dict[str, Any]

class SmetnyInzenyr:
    """Специализированный агент для парсинга смет и ведомостей"""
    
    def __init__(self):
        self.doc_parser = DocParser()
        self.smeta_parser = SmetaParser()
        
        logger.info("📋 SmetnyInzenyr initialized")
        
        # Категории для классификации строк смет
        self.category_keywords = {
            "concrete": ["beton", "železobeton", "monolitick", "бетон", "железобетон"],
            "reinforcement": ["výztuž", "арматур", "ocel", "Fe500", "Fe400"],
            "formwork": ["bednění", "опалубк", "deska", "доска"],
            "earthworks": ["výkop", "zemní", "раскоп", "земляные"],
            "insulation": ["izolace", "изоляц", "tepelná", "теплов"],
            "roofing": ["střešní", "кровельн", "krytina", "покрыти"],
            "windows_doors": ["okna", "dveře", "окна", "двери"],
            "other": []
        }
    
    async def parse_documents(self, files: List[str]) -> Dict[str, DocumentParsingResult]:
        """Парсит документы и возвращает структурированные результаты"""
        logger.info(f"📋 Начинаем парсинг {len(files)} документов")
        
        results = {}
        
        for file_path in files:
            try:
                result = await self._parse_single_document(file_path)
                results[file_path] = result
                
                if result.success:
                    logger.info(f"✅ Успешно обработан {file_path}: {result.rows_count} строк")
                else:
                    logger.warning(f"⚠️ Ошибка обработки {file_path}: {result.error_message}")
                    
            except Exception as e:
                logger.error(f"❌ Критическая ошибка при обработке {file_path}: {e}")
                results[file_path] = DocumentParsingResult(
                    document_path=file_path,
                    document_type="unknown",
                    success=False,
                    rows_count=0,
                    error_message=str(e),
                    parsed_data=None,
                    metadata={}
                )
        
        # Сохраняем общий отчет
        await self._save_parsing_report(results)
        
        return results
    
    async def _parse_single_document(self, file_path: str) -> DocumentParsingResult:
        """Парсит один документ"""
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension in [".pdf", ".docx"]:
            return await self._parse_text_document(file_path, file_extension)
        elif file_extension in [".xls", ".xlsx"]:
            return await self._parse_excel_document(file_path, file_extension)
        elif file_extension == ".xml":
            return await self._parse_xml_document(file_path, file_extension)
        else:
            return DocumentParsingResult(
                document_path=file_path,
                document_type=file_extension,
                success=False,
                rows_count=0,
                error_message=f"Неподдерживаемый тип файла: {file_extension}",
                parsed_data=None,
                metadata={}
            )
    
    async def _parse_text_document(self, file_path: str, file_extension: str) -> DocumentParsingResult:
        """Парсит текстовые документы (PDF, DOCX)"""
        try:
            text = self.doc_parser.parse(file_path)
            if not text:
                return DocumentParsingResult(
                    document_path=file_path,
                    document_type=file_extension,
                    success=False,
                    rows_count=0,
                    error_message="Пустой документ или ошибка чтения",
                    parsed_data=None,
                    metadata={}
                )
            
            # Извлекаем структурированные данные из текста
            smeta_rows = self._extract_smeta_rows_from_text(text, file_path)
            
            return DocumentParsingResult(
                document_path=file_path,
                document_type=file_extension,
                success=True,
                rows_count=len(smeta_rows),
                error_message=None,
                parsed_data={
                    'text': text,
                    'smeta_rows': smeta_rows
                },
                metadata={
                    'text_length': len(text),
                    'lines_count': len(text.split('\n')),
                    'has_structured_data': len(smeta_rows) > 0
                }
            )
            
        except Exception as e:
            return DocumentParsingResult(
                document_path=file_path,
                document_type=file_extension,
                success=False,
                rows_count=0,
                error_message=str(e),
                parsed_data=None,
                metadata={}
            )
    
    async def _parse_excel_document(self, file_path: str, file_extension: str) -> DocumentParsingResult:
        """Парсит Excel документы"""
        try:
            smeta_data = self.smeta_parser.parse(file_path)
            if not smeta_data:
                return DocumentParsingResult(
                    document_path=file_path,
                    document_type=file_extension,
                    success=False,
                    rows_count=0,
                    error_message="Нет данных в Excel файле",
                    parsed_data=None,
                    metadata={}
                )
            
            # Конвертируем данные в структурированный формат
            smeta_rows = self._convert_excel_data_to_rows(smeta_data, file_path)
            
            return DocumentParsingResult(
                document_path=file_path,
                document_type=file_extension,
                success=True,
                rows_count=len(smeta_rows),
                error_message=None,
                parsed_data={
                    'raw_data': smeta_data,
                    'smeta_rows': smeta_rows
                },
                metadata={
                    'rows_count': len(smeta_data),
                    'has_prices': any(row.get('unit_price') for row in smeta_data if isinstance(row, dict)),
                    'has_quantities': any(row.get('quantity') for row in smeta_data if isinstance(row, dict))
                }
            )
            
        except Exception as e:
            return DocumentParsingResult(
                document_path=file_path,
                document_type=file_extension,
                success=False,
                rows_count=0,
                error_message=str(e),
                parsed_data=None,
                metadata={}
            )
    
    async def _parse_xml_document(self, file_path: str, file_extension: str) -> DocumentParsingResult:
        """Парсит XML документы"""
        try:
            xml_data = parse_xml_smeta(file_path)
            if not xml_data:
                return DocumentParsingResult(
                    document_path=file_path,
                    document_type=file_extension,
                    success=False,
                    rows_count=0,
                    error_message="Нет данных в XML файле",
                    parsed_data=None,
                    metadata={}
                )
            
            # Конвертируем XML данные в структурированный формат
            smeta_rows = self._convert_xml_data_to_rows(xml_data, file_path)
            
            return DocumentParsingResult(
                document_path=file_path,
                document_type=file_extension,
                success=True,
                rows_count=len(smeta_rows),
                error_message=None,
                parsed_data={
                    'raw_data': xml_data,
                    'smeta_rows': smeta_rows
                },
                metadata={
                    'xml_structure': type(xml_data).__name__,
                    'has_structured_format': True
                }
            )
            
        except Exception as e:
            return DocumentParsingResult(
                document_path=file_path,
                document_type=file_extension,
                success=False,
                rows_count=0,
                error_message=str(e),
                parsed_data=None,
                metadata={}
            )
    
    def _extract_smeta_rows_from_text(self, text: str, source_document: str) -> List[SmetaRow]:
        """Извлекает строки сметы из текста"""
        rows = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean or len(line_clean) < 10:
                continue
            
            # Попытка извлечь структурированные данные из строки
            row_data = self._parse_smeta_line(line_clean)
            if row_data:
                smeta_row = SmetaRow(
                    code=row_data.get('code', ''),
                    description=row_data.get('description', line_clean),
                    quantity=row_data.get('quantity', 0.0),
                    unit=row_data.get('unit', ''),
                    unit_price=row_data.get('unit_price'),
                    total_cost=row_data.get('total_cost'),
                    source_document=source_document,
                    row_number=line_num + 1,
                    category=self._classify_smeta_row(line_clean)
                )
                rows.append(smeta_row)
        
        return rows
    
    def _parse_smeta_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Парсит строку сметы"""
        import re
        
        # Паттерны для извлечения данных из строк смет
        patterns = [
            # Код | Описание | Количество | Единица | Цена | Сумма
            r'(\d+(?:\.\d+)*)\s*[|\s]+(.+?)\s+(\d+[,.]?\d*)\s+(\w+)\s+(\d+[,.]?\d*)\s+(\d+[,.]?\d*)',
            
            # Описание с количеством и единицей
            r'(.+?)\s+(\d+[,.]?\d*)\s+(m3|м3|m2|м2|ks|шт|kg|кг|t|тонн)',
            
            # Только описание с количеством
            r'(.+?)\s+(\d+[,.]?\d*)\s*$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                if len(groups) >= 6:  # Полный формат
                    return {
                        'code': groups[0],
                        'description': groups[1].strip(),
                        'quantity': float(groups[2].replace(',', '.')),
                        'unit': groups[3],
                        'unit_price': float(groups[4].replace(',', '.')),
                        'total_cost': float(groups[5].replace(',', '.'))
                    }
                elif len(groups) >= 3:  # Описание + количество + единица
                    quantity_str = groups[1].replace(',', '.')
                    try:
                        quantity = float(quantity_str)
                        return {
                            'description': groups[0].strip(),
                            'quantity': quantity,
                            'unit': groups[2]
                        }
                    except ValueError:
                        continue
                elif len(groups) >= 2:  # Описание + количество
                    quantity_str = groups[1].replace(',', '.')
                    try:
                        quantity = float(quantity_str)
                        return {
                            'description': groups[0].strip(),
                            'quantity': quantity
                        }
                    except ValueError:
                        continue
        
        return None
    
    def _convert_excel_data_to_rows(self, excel_data: List[Dict], source_document: str) -> List[SmetaRow]:
        """Конвертирует данные Excel в структурированные строки"""
        rows = []
        
        for row_num, row_data in enumerate(excel_data):
            if not isinstance(row_data, dict):
                continue
            
            smeta_row = SmetaRow(
                code=str(row_data.get('code', '')),
                description=str(row_data.get('description', '')),
                quantity=float(row_data.get('quantity', 0)) if row_data.get('quantity') else 0.0,
                unit=str(row_data.get('unit', '')),
                unit_price=float(row_data.get('unit_price')) if row_data.get('unit_price') else None,
                total_cost=float(row_data.get('total_cost')) if row_data.get('total_cost') else None,
                source_document=source_document,
                row_number=row_num + 1,
                category=self._classify_smeta_row(str(row_data.get('description', '')))
            )
            rows.append(smeta_row)
        
        return rows
    
    def _convert_xml_data_to_rows(self, xml_data: Any, source_document: str) -> List[SmetaRow]:
        """Конвертирует данные XML в структурированные строки"""
        rows = []
        
        # Предполагаем, что XML данные - это список словарей
        if isinstance(xml_data, list):
            for row_num, row_data in enumerate(xml_data):
                if isinstance(row_data, dict):
                    smeta_row = SmetaRow(
                        code=str(row_data.get('code', '')),
                        description=str(row_data.get('description', '')),
                        quantity=float(row_data.get('qty', 0)) if row_data.get('qty') else 0.0,
                        unit=str(row_data.get('unit', '')),
                        unit_price=None,  # XML может не содержать цены
                        total_cost=None,
                        source_document=source_document,
                        row_number=row_num + 1,
                        category=self._classify_smeta_row(str(row_data.get('description', '')))
                    )
                    rows.append(smeta_row)
        
        return rows
    
    def _classify_smeta_row(self, description: str) -> str:
        """Классифицирует строку сметы по категории"""
        description_lower = description.lower()
        
        for category, keywords in self.category_keywords.items():
            if any(keyword in description_lower for keyword in keywords):
                return category
        
        return "other"
    
    async def _save_parsing_report(self, results: Dict[str, DocumentParsingResult]):
        """Сохраняет отчет о парсинге"""
        report_data = {
            'summary': {
                'total_documents': len(results),
                'successful_documents': sum(1 for r in results.values() if r.success),
                'failed_documents': sum(1 for r in results.values() if not r.success),
                'total_rows': sum(r.rows_count for r in results.values()),
            },
            'documents': {}
        }
        
        for file_path, result in results.items():
            report_data['documents'][file_path] = {
                'success': result.success,
                'document_type': result.document_type,
                'rows_count': result.rows_count,
                'error_message': result.error_message,
                'metadata': result.metadata
            }
        
        save_merged_report(report_data, output_path="outputs/smetny_inzenyr_report.json")
        logger.info("📋 Отчет о парсинге сохранен")
    
    def extract_all_smeta_rows(self, parsing_results: Dict[str, DocumentParsingResult]) -> List[SmetaRow]:
        """Извлекает все строки смет из результатов парсинга"""
        all_rows = []
        
        for result in parsing_results.values():
            if result.success and result.parsed_data:
                smeta_rows = result.parsed_data.get('smeta_rows', [])
                all_rows.extend(smeta_rows)
        
        return all_rows
    
    def create_parsing_summary(self, parsing_results: Dict[str, DocumentParsingResult]) -> Dict[str, Any]:
        """Создает сводку по результатам парсинга"""
        successful_results = [r for r in parsing_results.values() if r.success]
        failed_results = [r for r in parsing_results.values() if not r.success]
        
        all_rows = self.extract_all_smeta_rows(parsing_results)
        
        # Группировка по категориям
        categories_summary = {}
        for row in all_rows:
            category = row.category
            if category not in categories_summary:
                categories_summary[category] = {
                    'count': 0,
                    'total_quantity': 0,
                    'documents': set()
                }
            
            categories_summary[category]['count'] += 1
            categories_summary[category]['total_quantity'] += row.quantity
            categories_summary[category]['documents'].add(row.source_document)
        
        # Конвертируем sets в списки
        for category_data in categories_summary.values():
            category_data['documents'] = list(category_data['documents'])
        
        return {
            'parsing_statistics': {
                'total_documents': len(parsing_results),
                'successful_documents': len(successful_results),
                'failed_documents': len(failed_results),
                'success_rate': len(successful_results) / len(parsing_results) if parsing_results else 0
            },
            'data_statistics': {
                'total_rows': len(all_rows),
                'categories_found': len(categories_summary),
                'has_prices': sum(1 for row in all_rows if row.unit_price is not None),
                'has_quantities': sum(1 for row in all_rows if row.quantity > 0)
            },
            'categories_summary': categories_summary,
            'failed_documents': [
                {
                    'path': r.document_path,
                    'error': r.error_message
                } for r in failed_results
            ]
        }


# Singleton instance  
_smetny_inzenyr = None

def get_smetny_inzenyr() -> SmetnyInzenyr:
    """Получение глобального экземпляра агента-сметчика"""
    global _smetny_inzenyr
    if _smetny_inzenyr is None:
        _smetny_inzenyr = SmetnyInzenyr()
        logger.info("📋 SmetnyInzenyr initialized")
    return _smetny_inzenyr

# Функция для быстрого использования без класса (обратная совместимость)
def parse_files(file_list: List[str]) -> Dict[str, DocumentParsingResult]:
    """Функция для быстрого использования без класса"""
    import asyncio
    agent = get_smetny_inzenyr()
    return asyncio.run(agent.parse_documents(file_list))


# ==============================
# 🧪 Функция для тестирования
# ==============================

async def test_smetny_inzenyr():
    """Тестирование агента-сметчика"""
    agent = get_smetny_inzenyr()
    
    print("🧪 TESTING SMETNY INZENYR")
    print("=" * 50)
    
    # Имитируем парсинг текста
    test_text = """
    001 Monolitická základová deska C25/30 10.5 m3 3500 36750
    002 Železobetonový věnec C25/30 5.2 m3 3800 19760
    003 Výztuž Fe500 1250 kg 25 31250
    """
    
    rows = agent._extract_smeta_rows_from_text(test_text, "test_smeta.txt")
    
    print(f"📋 Найдено строк: {len(rows)}")
    
    print("\n📊 Детали строк:")
    for row in rows:
        print(f"  • {row.description}")
        print(f"    Код: {row.code}")
        print(f"    Количество: {row.quantity} {row.unit}")
        print(f"    Категория: {row.category}")
        if row.unit_price:
            print(f"    Цена: {row.unit_price}, Сумма: {row.total_cost}")
        print()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_smetny_inzenyr())