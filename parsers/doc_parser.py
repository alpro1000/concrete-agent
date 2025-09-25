"""
Улучшенный парсер документов с поддержкой чешских кодировок
parsers/doc_parser.py - ПОЛНЫЙ КОМПЛЕКТНЫЙ КОД ДЛЯ ЗАМЕНЫ
"""

import os
import logging
import pdfplumber
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class DocParser:
    """Улучшенный парсер документов с поддержкой чешского языка"""
    
    def __init__(self):
        """Инициализация парсера"""
        # Список кодировок для чешского языка (в порядке приоритета)
        self.czech_encodings = [
            'utf-8',       # Современный стандарт
            'cp1250',      # Windows Eastern European
            'iso-8859-2',  # Latin-2 (Central European)
            'utf-16',      # Unicode 16-bit
            'cp1252',      # Windows Western European (fallback)
        ]
        
        logger.info("📚 DocParser инициализирован с поддержкой чешских кодировок")

    def parse(self, file_path: str) -> str:
        """
        Главная функция парсинга документов
        
        Args:
            file_path: Путь к файлу для обработки
            
        Returns:
            Извлеченный текст из документа
            
        Raises:
            FileNotFoundError: Если файл не найден
            ValueError: Если формат файла не поддерживается
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        file_ext = Path(file_path).suffix.lower()
        file_name = Path(file_path).name
        
        logger.info(f"🔍 Начало обработки файла: {file_name}")
        
        try:
            if file_ext == '.pdf':
                text = self._extract_text_from_pdf_enhanced(file_path)
            elif file_ext in ['.docx', '.doc']:
                text = self._extract_text_from_docx_enhanced(file_path)
            elif file_ext == '.txt':
                text = self._read_text_file_with_encoding(file_path)
            else:
                raise ValueError(f"Неподдерживаемый формат файла: {file_ext}")
            
            if not text.strip():
                logger.warning(f"⚠️ Извлеченный текст пуст: {file_name}")
                return ""
            
            logger.info(f"✅ Файл успешно обработан: {len(text)} символов из {file_name}")
            return text
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки файла {file_name}: {e}")
            raise

    def _extract_text_from_pdf_enhanced(self, file_path: str) -> str:
        """
        Улучшенная обработка PDF с чешским текстом
        
        Args:
            file_path: Путь к PDF файлу
            
        Returns:
            Извлеченный текст
        """
        text_parts = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                logger.info(f"📄 Обработка PDF: {total_pages} страниц")
                
                for page_num, page in enumerate(pdf.pages):
                    try:
                        # Основной метод извлечения
                        page_text = page.extract_text()
                        
                        if not page_text or len(page_text.strip()) < 10:
                            # Пробуем с другими параметрами для сложных PDF
                            page_text = page.extract_text(
                                x_tolerance=2,
                                y_tolerance=2,
                                layout=True,
                                x_density=7.25,
                                y_density=7.25
                            )
                        
                        if not page_text or len(page_text.strip()) < 10:
                            # Альтернативный метод для очень сложных PDF
                            try:
                                page_text = page.extract_text(
                                    x_tolerance=1,
                                    y_tolerance=1
                                )
                            except:
                                page_text = ""
                        
                        if page_text and page_text.strip():
                            text_parts.append(f"\n=== Страница {page_num + 1} ===\n")
                            text_parts.append(page_text.strip())
                            text_parts.append("\n")
                            logger.debug(f"📖 Страница {page_num + 1}: {len(page_text)} символов")
                        else:
                            logger.warning(f"⚠️ Пустая страница {page_num + 1}")
                            
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка обработки страницы {page_num + 1}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"❌ Критическая ошибка чтения PDF {file_path}: {e}")
            return ""
        
        combined_text = "".join(text_parts)
        
        if combined_text:
            logger.info(f"📄 PDF успешно обработан: {len(text_parts)//3} страниц, {len(combined_text)} символов")
        else:
            logger.error(f"❌ Не удалось извлечь текст из PDF: {file_path}")
        
        return combined_text

    def _extract_text_from_docx_enhanced(self, file_path: str) -> str:
        """
        Улучшенная обработка DOCX файлов
        
        Args:
            file_path: Путь к DOCX файлу
            
        Returns:
            Извлеченный текст
        """
        try:
            from docx import Document
        except ImportError:
            logger.error("❌ Библиотека python-docx не установлена: pip install python-docx")
            return ""
        
        try:
            doc = Document(file_path)
            text_parts = []
            paragraph_count = 0
            table_count = 0
            
            # Извлекаем основной текст из параграфов
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text.strip())
                    paragraph_count += 1
            
            # Пробуем извлечь текст из таблиц
            for table in doc.tables:
                table_count += 1
                table_text = []
                
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    
                    if row_text:
                        table_text.append(" | ".join(row_text))
                
                if table_text:
                    text_parts.append(f"\n=== Таблица {table_count} ===")
                    text_parts.extend(table_text)
                    text_parts.append("")
            
            combined_text = "\n".join(text_parts)
            
            logger.info(f"📝 DOCX обработан: {paragraph_count} параграфов, {table_count} таблиц, {len(combined_text)} символов")
            
            return combined_text
            
        except Exception as e:
            logger.error(f"❌ Ошибка чтения DOCX {file_path}: {e}")
            return ""

    def _read_text_file_with_encoding(self, file_path: str) -> str:
        """
        Чтение текстовых файлов с автоматическим определением кодировки
        
        Args:
            file_path: Путь к текстовому файлу
            
        Returns:
            Содержимое файла
        """
        file_name = Path(file_path).name
        
        # Пробуем разные кодировки
        for encoding in self.czech_encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    text = f.read()
                    
                if text.strip():  # Проверяем, что текст не пуст
                    logger.info(f"📖 Текстовый файл {file_name} прочитан с кодировкой: {encoding}")
                    return text
                    
            except (UnicodeDecodeError, UnicodeError):
                logger.debug(f"🔄 Кодировка {encoding} не подходит для {file_name}")
                continue
            except Exception as e:
                logger.warning(f"⚠️ Ошибка чтения {file_name} с кодировкой {encoding}: {e}")
                continue
        
        # Если все кодировки не сработали, пробуем с заменой ошибок
        logger.warning(f"⚠️ Все кодировки не сработали для {file_name}, используем UTF-8 с заменой ошибок")
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()
                logger.warning(f"⚠️ Файл {file_name} прочитан с заменой поврежденных символов")
                return text
                
        except Exception as e:
            logger.error(f"❌ Критическая ошибка чтения файла {file_name}: {e}")
            return ""

    def parse_multiple(self, file_paths: List[str]) -> Dict[str, str]:
        """
        Обработка нескольких файлов одновременно
        
        Args:
            file_paths: Список путей к файлам
            
        Returns:
            Словарь {имя_файла: извлеченный_текст}
        """
        results = {}
        
        logger.info(f"🔄 Начало пакетной обработки: {len(file_paths)} файлов")
        
        for file_path in file_paths:
            file_name = Path(file_path).name
            
            try:
                text = self.parse(file_path)
                results[file_name] = text
                
                if text:
                    logger.info(f"✅ {file_name}: {len(text)} символов")
                else:
                    logger.warning(f"⚠️ {file_name}: пустой результат")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка обработки {file_name}: {e}")
                results[file_name] = ""
        
        successful = len([r for r in results.values() if r.strip()])
        logger.info(f"📊 Пакетная обработка завершена: {successful}/{len(file_paths)} файлов успешно")
        
        return results

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Получение информации о файле
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Словарь с информацией о файле
        """
        if not os.path.exists(file_path):
            return {'error': 'Файл не найден'}
        
        file_stat = os.stat(file_path)
        file_path_obj = Path(file_path)
        
        info = {
            'name': file_path_obj.name,
            'extension': file_path_obj.suffix.lower(),
            'size_bytes': file_stat.st_size,
            'size_mb': round(file_stat.st_size / (1024 * 1024), 2),
            'path': str(file_path_obj.absolute()),
            'supported': file_path_obj.suffix.lower() in ['.pdf', '.docx', '.doc', '.txt']
        }
        
        return info


# Функция для тестирования
def test_doc_parser():
    """Функция для тестирования парсера"""
    parser = DocParser()
    
    # Создаем тестовый файл
    test_content = """
    Testovací dokument s českou diakritikou.
    Třída betonu C30/37 – XC4, XF3.
    Dřík opěrné zdi, základová část.
    """
    
    test_file = "test_czech.txt"
    
    try:
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # Тестируем парсер
        result = parser.parse(test_file)
        
        print("🧪 TESTING DOC PARSER")
        print("=" * 30)
        print(f"Input:  {test_content.strip()}")
        print(f"Output: {result.strip()}")
        print(f"Length: {len(result)} characters")
        
        # Удаляем тестовый файл
        os.remove(test_file)
        
        return result
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return ""


if __name__ == "__main__":
    test_doc_parser()
