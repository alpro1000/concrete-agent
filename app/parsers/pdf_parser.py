"""
Enhanced PDF Parser with Smart Text Detection
БЕЗ CLAUDE FALLBACK - только pdfplumber

✅ НОВОЕ: Smart Text Detection - автоопределение типа страницы
✅ Пропуск пустых страниц - экономия времени
✅ Детекция сканов - логирование для будущего OCR
✅ Page-by-page processing - memory efficient
"""
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import re

logger = logging.getLogger(__name__)


class PDFParser:
    """
    Enhanced PDF parser для строительных смет
    
    ✅ БЕЗ Claude fallback - только pdfplumber
    ✅ Smart Text Detection - автоопределение типа страницы
    ✅ Page-by-page processing (memory efficient)
    ✅ Чешская поддержка (MJ, J.cena, количества)
    """
    
    def __init__(self):
        """БЕЗ claude_client и mineru_client!"""
        pass
    
    def parse(self, pdf_path: Path, max_pages: int = 100) -> Dict[str, Any]:
        """
        Parse PDF estimate with Smart Detection
        
        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum pages to process
            
        Returns:
            Dict with parsed data
        """
        logger.info(f"📄 Parsing PDF with Smart Detection: {pdf_path}")
        
        return self._parse_with_smart_detection(pdf_path, max_pages)
    
    def _parse_with_smart_detection(self, pdf_path: Path, max_pages: int = 100) -> Dict[str, Any]:
        """
        Parse PDF using pdfplumber with Smart Page Detection
        
        ✅ НОВОЕ: Автоопределение типа страницы (text/image/empty)
        """
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("pdfplumber not installed. Install with: pip install pdfplumber")
        
        logger.info("Using pdfplumber with Smart Detection...")
        
        positions = []
        page_info = []
        all_text = []
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            pages_to_process = min(total_pages, max_pages)
            
            logger.info(f"Processing {pages_to_process} of {total_pages} pages")
            
            for page_num in range(pages_to_process):
                page = pdf.pages[page_num]
                
                # ✅ НОВОЕ: Smart Detection - определить тип страницы
                page_type, confidence = self._detect_page_type(page)
                
                page_info.append({
                    'page_number': page_num + 1,
                    'type': page_type,
                    'confidence': confidence
                })
                
                logger.info(f"  Page {page_num+1}/{pages_to_process}: {page_type} (confidence: {confidence:.0%})")
                
                # Обработка в зависимости от типа
                if page_type == 'text':
                    # ✅ Текстовая страница - обычная обработка
                    
                    # Извлечь текст для контекста
                    text = page.extract_text()
                    if text:
                        all_text.append(f"=== Page {page_num + 1} ===\n{text}")
                    
                    # Извлечь таблицы
                    tables = page.extract_tables()
                    for table_num, table in enumerate(tables, 1):
                        logger.info(f"    Found table {table_num} on page {page_num + 1}")
                        
                        # Parse table as positions
                        parsed_positions = self._parse_table(table, page_num + 1, table_num)
                        positions.extend(parsed_positions)
                
                elif page_type == 'empty':
                    # ⏭️ Пустая страница - пропустить
                    logger.info(f"    ⏭️  Skipping empty page")
                
                elif page_type == 'image':
                    # 🖼️ Скан/картинка - пока пропускаем (или OCR если реализован)
                    logger.warning(f"    🖼️  Page is a scan/image (OCR not implemented)")
                    logger.warning(f"    ⚠️  To process scans, consider adding EasyOCR integration")
                
                # ✅ Explicitly release page memory
                del page
        
        full_text = "\n\n".join(all_text)
        
        # Подсчитать статистику по типам страниц
        page_type_summary = self._summarize_page_types(page_info)
        
        result = {
            "positions": positions,
            "total_positions": len(positions),
            "document_info": {
                "document_type": "PDF Estimate",
                "format": "PDF_SMART_DETECTION",
                "pages": total_pages,
                "pages_processed": pages_to_process,
                "page_types": page_type_summary
            },
            "page_info": page_info,  # ✅ Детальная информация по каждой странице
            "sections": [],
            "raw_text": full_text[:5000]  # First 5000 chars for reference
        }
        
        logger.info(f"✅ Extracted {len(positions)} positions from PDF")
        logger.info(f"   Page types: {page_type_summary}")
        
        return result
    
    def _detect_page_type(self, page) -> tuple[str, float]:
        """
        ✅ НОВОЕ: Smart Detection - определить тип страницы
        
        Определяет:
        - 'text' - живой текст (можно извлекать)
        - 'image' - скан/картинка (нужен OCR)
        - 'empty' - пустая страница
        
        Args:
            page: pdfplumber page object
            
        Returns:
            (type, confidence) - тип страницы и уверенность (0.0-1.0)
        """
        # Попытаться извлечь текст
        text = page.extract_text()
        
        # === ПРОВЕРКА 1: Совсем нет текста ===
        if not text or len(text.strip()) < 5:
            # Проверить есть ли изображения
            if self._has_images(page):
                return ('image', 0.9)
            return ('empty', 0.95)
        
        # === ПРОВЕРКА 2: Мало текста ===
        text_clean = text.strip()
        words = text_clean.split()
        
        if len(words) < 3:
            # Очень мало слов - скорее всего пустая или картинка с артефактами
            if self._has_images(page):
                return ('image', 0.85)
            return ('empty', 0.8)
        
        # === ПРОВЕРКА 3: Процент букв (vs мусор) ===
        alpha_chars = sum(c.isalpha() for c in text)
        digit_chars = sum(c.isdigit() for c in text)
        total_chars = len(text.replace(' ', '').replace('\n', '').replace('\t', ''))
        
        if total_chars == 0:
            return ('empty', 0.9)
        
        alpha_ratio = alpha_chars / total_chars
        meaningful_ratio = (alpha_chars + digit_chars) / total_chars
        
        # Если меньше 5% букв - скорее всего мусор или плохой OCR
        if alpha_ratio < 0.05:
            if self._has_images(page):
                return ('image', 0.8)
            return ('empty', 0.7)
        
        # === ПРОВЕРКА 4: Есть ли таблицы? ===
        tables = page.extract_tables()
        if tables and len(tables) > 0:
            # Точно живой текст если есть таблицы!
            return ('text', 0.95)
        
        # === ПРОВЕРКА 5: Ключевые слова для смет ===
        text_lower = text.lower()
        
        # Чешские ключевые слова
        czech_keywords = [
            'kód', 'kod', 'popis', 'název', 'nazev',
            'množství', 'mnozstvi', 'cena', 'celkem',
            'stavba', 'objekt', 'práce', 'prace',
            'materiál', 'material', 'jednotka', 'mj'
        ]
        
        # Английские ключевые слова
        english_keywords = [
            'code', 'description', 'quantity', 'unit',
            'price', 'total', 'amount', 'work', 'item'
        ]
        
        keywords_found = sum(1 for kw in (czech_keywords + english_keywords) if kw in text_lower)
        
        if keywords_found >= 3:
            # Много ключевых слов - точно живой текст!
            return ('text', 0.9)
        
        if keywords_found >= 1:
            # Есть хотя бы одно ключевое слово
            return ('text', 0.7)
        
        # === ПРОВЕРКА 6: Длина текста ===
        if len(words) > 50 and meaningful_ratio > 0.3:
            # Много осмысленного текста
            return ('text', 0.8)
        
        if len(words) > 20 and meaningful_ratio > 0.2:
            # Средне текста
            return ('text', 0.6)
        
        # === ПРОВЕРКА 7: Есть ли большие картинки? ===
        if self._has_large_images(page):
            return ('image', 0.75)
        
        # === ПО УМОЛЧАНИЮ ===
        # Если не уверены но есть текст - считаем что текст
        if len(words) > 5:
            return ('text', 0.5)
        
        # Совсем не уверены - empty
        return ('empty', 0.5)
    
    def _has_images(self, page) -> bool:
        """Проверить есть ли картинки на странице"""
        try:
            images = page.images
            return len(images) > 0
        except Exception as e:
            logger.debug(f"Failed to check images: {e}")
            return False
    
    def _has_large_images(self, page) -> bool:
        """Проверить есть ли большие картинки (>50% страницы)"""
        try:
            images = page.images
            if not images:
                return False
            
            # Размер страницы
            page_width = page.width
            page_height = page.height
            page_area = page_width * page_height
            
            # Суммарная площадь картинок
            images_area = 0
            for img in images:
                img_width = img.get('width', 0)
                img_height = img.get('height', 0)
                images_area += img_width * img_height
            
            # Если картинки занимают >50% страницы
            return images_area > (page_area * 0.5)
        
        except Exception as e:
            logger.debug(f"Failed to check large images: {e}")
            return False
    
    def _summarize_page_types(self, page_info: List[Dict]) -> Dict[str, int]:
        """
        Подсчитать статистику по типам страниц
        
        Args:
            page_info: List of page info dicts
            
        Returns:
            Summary dict with counts
        """
        summary = {
            'text': 0,
            'image': 0,
            'empty': 0,
            'total': len(page_info)
        }
        
        for page in page_info:
            page_type = page.get('type', 'text')
            summary[page_type] = summary.get(page_type, 0) + 1
        
        # Добавить проценты
        if summary['total'] > 0:
            summary['text_pct'] = round(summary['text'] / summary['total'] * 100, 1)
            summary['image_pct'] = round(summary['image'] / summary['total'] * 100, 1)
            summary['empty_pct'] = round(summary['empty'] / summary['total'] * 100, 1)
        
        return summary
    
    def _parse_table(self, table: List[List[str]], page_num: int, table_num: int) -> List[Dict[str, Any]]:
        """
        Parse a table extracted from PDF
        
        Args:
            table: 2D list of table cells
            page_num: Page number
            table_num: Table number on page
            
        Returns:
            List of parsed positions
        """
        if not table or len(table) < 2:
            return []
        
        positions = []
        
        # Try to identify header row
        header = table[0]
        header_lower = [str(cell).lower().strip() if cell else '' for cell in header]
        
        # Find column indices - ✅ РАСШИРЕННЫЙ ПОИСК (чешские варианты)
        code_idx = self._find_column(header_lower, [
            'code', 'kód', 'kod', 'číslo', 'cislo', 'položka', 'polozka'
        ])
        desc_idx = self._find_column(header_lower, [
            'description', 'popis', 'název', 'nazev', 'name', 'text'
        ])
        unit_idx = self._find_column(header_lower, [
            'unit', 'mj', 'm.j.', 'jednotka', 'j.'
        ])
        qty_idx = self._find_column(header_lower, [
            'quantity', 'množství', 'mnozstvi', 'počet', 'pocet', 'qty'
        ])
        price_idx = self._find_column(header_lower, [
            'price', 'cena', 'j.cena', 'j. cena', 'jednotková', 'jednotkova', 'unit price'
        ])
        total_idx = self._find_column(header_lower, [
            'celkem', 'total', 'cena celkem', 'total price', 'amount'
        ])
        
        logger.debug(f"    Column mapping: desc={desc_idx}, qty={qty_idx}, unit={unit_idx}, price={price_idx}")
        
        # Parse data rows
        for row_idx, row in enumerate(table[1:], 1):
            if not row or len(row) == 0:
                continue
            
            # Skip rows that look like headers or totals
            if self._is_header_or_total_row(row):
                continue
            
            # Get description (required)
            description = self._get_cell(row, desc_idx, '')
            if not description or len(description.strip()) < 3:
                continue
            
            position = {
                "code": self._get_cell(row, code_idx, ''),
                "description": description,
                "unit": self._get_cell(row, unit_idx, ''),
                "quantity": self._parse_float(self._get_cell(row, qty_idx, '0')),
                "unit_price": self._parse_float(self._get_cell(row, price_idx, '0')),
                "total_price": self._parse_float(self._get_cell(row, total_idx, '0')),
                "page": page_num,
                "table": table_num,
                "row": row_idx
            }
            
            # Calculate total if missing
            if position["quantity"] and position["unit_price"] and not position["total_price"]:
                position["total_price"] = position["quantity"] * position["unit_price"]
            
            # Only add if we have meaningful data
            if position["description"]:
                positions.append(position)
        
        return positions
    
    def _find_column(self, header: List[str], keywords: List[str]) -> Optional[int]:
        """
        Find column index by keywords
        ✅ CASE-INSENSITIVE поиск
        """
        for idx, cell in enumerate(header):
            cell_clean = cell.lower().strip()
            for keyword in keywords:
                if keyword in cell_clean:
                    return idx
        return None
    
    def _get_cell(self, row: List, idx: Optional[int], default: str = '') -> str:
        """Safely get cell value"""
        if idx is None or idx >= len(row):
            return default
        return str(row[idx]).strip() if row[idx] else default
    
    def _is_header_or_total_row(self, row: List) -> bool:
        """Check if row is a header or total row"""
        row_text = ' '.join([str(cell).lower() for cell in row if cell]).strip()
        
        skip_keywords = [
            'total', 'celkem', 'suma', 'subtotal', 'mezisoučet',
            'code', 'kód', 'popis', 'description', 'quantity', 'množství'
        ]
        
        # If row text is short and matches keyword
        if len(row_text) < 30:
            return any(keyword in row_text for keyword in skip_keywords)
        
        return False
    
    def _parse_float(self, text: str) -> float:
        """
        Parse float from text
        ✅ Чешские числа (1 220,168)
        """
        try:
            text = str(text).strip()
            
            # Remove spaces (thousands separators)
            text = text.replace(' ', '').replace('\xa0', '')
            
            # Remove currency symbols
            text = text.replace('Kč', '').replace('CZK', '').replace('EUR', '').replace('€', '')
            text = text.strip()
            
            # Handle decimal separator
            # If both . and , → European format (1.220,50)
            if '.' in text and ',' in text:
                # European: dot = thousands, comma = decimal
                text = text.replace('.', '')
                text = text.replace(',', '.')
            elif ',' in text:
                # Only comma - check if decimal or thousands
                parts = text.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    # Decimal: 15,50
                    text = text.replace(',', '.')
                else:
                    # Thousands: 1,220
                    text = text.replace(',', '')
            
            # Clean any remaining non-numeric
            text = re.sub(r'[^\d.-]', '', text)
            
            if not text or text == '-':
                return 0.0
            
            return float(text)
        except (ValueError, AttributeError):
            return 0.0
