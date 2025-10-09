"""
Knowledge Base Loader
Автоматически загружает ВСЕ файлы из папок B1-B8
БЕЗ необходимости менять код при добавлении новых файлов
"""

import json
import csv
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class KnowledgeBaseLoader:
    """
    Умный загрузчик базы знаний
    
    Автоматически:
    - Сканирует все папки B1-B8
    - Определяет формат файлов (JSON, CSV, XLSX, PDF)
    - Загружает данные в память
    - Индексирует для быстрого поиска
    """
    
    # Категории базы знаний (фиксированные)
    CATEGORIES = [
        "B1_kros_urs_codes",
        "B2_csn_standards",
        "B3_current_prices",
        "B4_production_benchmarks",
        "B5_tech_cards",
        "B6_research_papers",
        "B7_regulations",
        "B8_company_specific"
    ]
    
    def __init__(self, kb_dir: Path):
        """
        Args:
            kb_dir: Путь к app/knowledge_base/
        """
        self.kb_dir = kb_dir
        self.data = {}
        self.metadata = {}
        self.loaded_at = None
        
    def load_all(self) -> Dict[str, Any]:
        """
        Главный метод: загружает ВСЮ базу знаний
        
        Returns:
            {
                "B1_kros_urs_codes": {...},
                "B2_csn_standards": {...},
                ...
            }
        """
        logger.info("🔄 Loading Knowledge Base...")
        start_time = datetime.now()
        
        for category in self.CATEGORIES:
            category_path = self.kb_dir / category
            
            if not category_path.exists():
                logger.warning(f"⚠️  Category not found: {category}")
                continue
            
            # Загружаем категорию
            self.data[category] = self._load_category(category_path)
            
            # Загружаем metadata
            metadata_path = category_path / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    self.metadata[category] = json.load(f)
            
            logger.info(f"✅ Loaded: {category}")
        
        self.loaded_at = datetime.now()
        elapsed = (self.loaded_at - start_time).total_seconds()
        
        logger.info(f"✨ Knowledge Base loaded in {elapsed:.2f}s")
        self._print_summary()
        
        return self.data
    
    def _load_category(self, path: Path) -> Dict[str, Any]:
        """
        Загружает все файлы из одной категории
        
        Поддерживает:
        - JSON
        - CSV
        - XLSX
        - PDF (текст извлекается)
        """
        data = {}
        
        # Рекурсивно ищем все файлы
        for file_path in path.rglob("*"):
            if not file_path.is_file():
                continue
            
            # Пропускаем metadata.json (загружается отдельно)
            if file_path.name == "metadata.json":
                continue
            
            try:
                # Определяем формат и загружаем
                file_data = self._load_file(file_path)
                
                # Сохраняем с относительным путем как ключом
                relative_path = str(file_path.relative_to(path))
                data[relative_path] = file_data
                
            except Exception as e:
                logger.error(f"❌ Failed to load {file_path}: {e}")
        
        return data
    
    def _load_file(self, file_path: Path) -> Any:
        """
        Умная загрузка файла - определяет формат автоматически
        """
        suffix = file_path.suffix.lower()
        
        if suffix == ".json":
            return self._load_json(file_path)
        
        elif suffix == ".csv":
            return self._load_csv(file_path)
        
        elif suffix in [".xlsx", ".xls"]:
            return self._load_excel(file_path)
        
        elif suffix == ".pdf":
            return self._load_pdf(file_path)
        
        elif suffix in [".txt", ".md"]:
            return self._load_text(file_path)
        
        else:
            logger.warning(f"⚠️  Unsupported format: {file_path}")
            return None
    
    def _load_json(self, path: Path) -> Dict:
        """Загрузка JSON"""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_csv(self, path: Path) -> List[Dict]:
        """
        Загрузка CSV как список словарей
        
        Пример KROS экспорта:
        code,name,unit,base_price
        121-01-001,"Beton C20/25",m³,2450
        
        Возвращает:
        [
            {"code": "121-01-001", "name": "Beton C20/25", ...},
            ...
        ]
        """
        data = []
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Убираем лишние пробелы из ключей
                cleaned_row = {k.strip(): v for k, v in row.items()}
                data.append(cleaned_row)
        return data
    
    def _load_excel(self, path: Path) -> Dict[str, Any]:
        """
        Загрузка Excel (может содержать несколько листов)
        
        Возвращает:
        {
            "Sheet1": [...],
            "Sheet2": [...],
            ...
        }
        """
        excel_file = pd.ExcelFile(path)
        data = {}
        
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet_name)
            # Конвертируем в список словарей
            data[sheet_name] = df.to_dict('records')
        
        return data
    
    def _load_pdf(self, path: Path) -> Dict[str, Any]:
        """
        Загрузка PDF - извлекает текст
        
        Для ČSN стандартов, технологических карт и т.д.
        """
        try:
            # Используем PyPDF2 или pdfplumber
            import pdfplumber
            
            text = ""
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            
            return {
                "filename": path.name,
                "pages": len(pdf.pages) if 'pdf' in locals() else 0,
                "text": text,
                "path": str(path)
            }
        
        except ImportError:
            logger.warning("⚠️  pdfplumber not installed, skipping PDF")
            return {
                "filename": path.name,
                "text": None,
                "path": str(path),
                "note": "Install pdfplumber to extract text"
            }
    
    def _load_text(self, path: Path) -> str:
        """Загрузка текстовых файлов"""
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _print_summary(self):
        """Выводит статистику загруженной KB"""
        logger.info("\n" + "="*60)
        logger.info("📊 Knowledge Base Summary")
        logger.info("="*60)
        
        for category in self.CATEGORIES:
            if category in self.data:
                files_count = len(self.data[category])
                
                # Информация из metadata
                meta = self.metadata.get(category, {})
                last_updated = meta.get("last_updated", "Unknown")
                version = meta.get("version", "N/A")
                
                logger.info(
                    f"{category:30} | {files_count:3} files | "
                    f"v{version} | Updated: {last_updated}"
                )
        
        logger.info("="*60 + "\n")
    
    # === МЕТОДЫ ПОИСКА (для использования в промптах) ===
    
    def get_kros_codes(self) -> List[Dict]:
        """
        Быстрый доступ к кодам KROS
        
        Returns:
            [
                {"code": "121-01-001", "name": "Beton C20/25", ...},
                ...
            ]
        """
        b1_data = self.data.get("B1_kros_urs_codes", {})
        
        # Ищем файл с KROS кодами (может быть CSV или JSON)
        for filename, data in b1_data.items():
            if "kros" in filename.lower() and isinstance(data, list):
                return data
        
        return []
    
    def get_current_prices(self, material_type: str = None) -> Dict:
        """
        Быстрый доступ к актуальным ценам
        
        Args:
            material_type: Опционально фильтр (beton, armatura, ...)
        
        Returns:
            {"beton": {...}, "armatura": {...}, ...}
        """
        b3_data = self.data.get("B3_current_prices", {})
        
        # Ищем файл с ценами (обычно market_prices_*.json)
        for filename, data in b3_data.items():
            if "market_prices" in filename.lower():
                materials = data.get("materials", {})
                
                if material_type:
                    return materials.get(material_type, {})
                
                return materials
        
        return {}
    
    def get_productivity_rates(self, work_type: str = None) -> Dict:
        """
        Быстрый доступ к нормативам производительности
        
        Args:
            work_type: concrete_work, masonry_work, etc.
        
        Returns:
            {"concrete_work": {...}, ...}
        """
        b4_data = self.data.get("B4_production_benchmarks", {})
        
        for filename, data in b4_data.items():
            if "productivity_rates" in filename.lower():
                if work_type:
                    return data.get(work_type, {})
                return data
        
        return {}
    
    def search_standards(self, query: str) -> List[Dict]:
        """
        Поиск по ČSN стандартам
        
        Args:
            query: "beton", "zdivo", "geometry", etc.
        
        Returns:
            [
                {"filename": "CSN_EN_1992.pdf", "text": "...", ...},
                ...
            ]
        """
        b2_data = self.data.get("B2_csn_standards", {})
        results = []
        
        query_lower = query.lower()
        
        for filename, data in b2_data.items():
            if isinstance(data, dict) and "text" in data:
                # Поиск в тексте PDF
                if query_lower in data.get("text", "").lower():
                    results.append({
                        "filename": filename,
                        "excerpt": self._extract_excerpt(
                            data["text"], 
                            query_lower
                        ),
                        "path": data.get("path")
                    })
        
        return results
    
    def _extract_excerpt(self, text: str, query: str, context: int = 200) -> str:
        """Извлекает фрагмент текста вокруг найденного запроса"""
        index = text.lower().find(query.lower())
        if index == -1:
            return ""
        
        start = max(0, index - context)
        end = min(len(text), index + len(query) + context)
        
        excerpt = text[start:end]
        return f"...{excerpt}..."


# === ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР ===

_kb_instance = None

def get_knowledge_base() -> KnowledgeBaseLoader:
    """
    Singleton: возвращает единственный экземпляр KB
    
    Загружается один раз при старте приложения
    """
    global _kb_instance
    
    if _kb_instance is None:
        from app.core.config import settings
        _kb_instance = KnowledgeBaseLoader(settings.KB_DIR)
        _kb_instance.load_all()
    
    return _kb_instance


# === ИСПОЛЬЗОВАНИЕ В КОДЕ ===

def example_usage():
    """Примеры как использовать в других сервисах"""
    
    # 1. Получить KB
    kb = get_knowledge_base()
    
    # 2. Получить коды KROS
    kros_codes = kb.get_kros_codes()
    print(f"Loaded {len(kros_codes)} KROS codes")
    
    # 3. Получить цены на бетон
    concrete_prices = kb.get_current_prices("beton")
    print(f"Beton C20/25: {concrete_prices.get('C20/25', {}).get('price_per_m3')} Kč")
    
    # 4. Получить производительность
    concrete_rates = kb.get_productivity_rates("concrete_work")
    print(f"Formwork rate: {concrete_rates.get('formwork', {}).get('simple', {})}")
    
    # 5. Поиск в стандартах
    standards = kb.search_standards("beton")
    print(f"Found {len(standards)} standards mentioning 'beton'")


if __name__ == "__main__":
    example_usage()

