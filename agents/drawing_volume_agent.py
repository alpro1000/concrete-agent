"""
DrawingVolumeAgent - Анализ объемов из чертежей и геометрических данных
agents/drawing_volume_agent.py

Будущая реализация с использованием:
- MinerU для извлечения данных из PDF-чертежей
- DocStrange для анализа технических чертежей
- Безопасные API-обертки для внешних сервисов

Пока содержит заглушки с fallback логикой.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class GeometricElement:
    """Геометрический элемент с чертежа"""
    element_type: str  # "rectangle", "circle", "line", etc.
    dimensions: Dict[str, float]  # {"width": 100, "height": 50, "diameter": 25}
    coordinates: Dict[str, float]  # {"x": 0, "y": 0, "z": 0}
    material_ref: Optional[str] = None
    volume_m3: Optional[float] = None
    area_m2: Optional[float] = None
    confidence: float = 0.0

@dataclass
class DrawingAnalysisResult:
    """Результат анализа чертежа"""
    drawing_file: str
    elements_found: int
    total_volume_m3: float
    total_area_m2: float
    elements: List[GeometricElement]
    analysis_method: str
    success: bool
    error_message: Optional[str] = None

class DrawingVolumeAgent:
    """Агент для анализа объемов из чертежей и геометрических данных"""
    
    def __init__(self):
        self.supported_formats = ['.pdf', '.dwg', '.dxf']
        self.external_services = {
            'mineru': self._check_mineru_availability(),
            'docstrange': self._check_docstrange_availability()
        }
        
        logger.info("📐 DrawingVolumeAgent initialized")
        logger.info(f"🔧 External services: {self.external_services}")
    
    def _check_mineru_availability(self) -> bool:
        """Проверка доступности MinerU"""
        try:
            # Заглушка - в реальной реализации здесь будет проверка API
            # import mineru_client
            # return mineru_client.is_available()
            return False  # Пока недоступно
        except Exception as e:
            logger.debug(f"MinerU недоступен: {e}")
            return False
    
    def _check_docstrange_availability(self) -> bool:
        """Проверка доступности DocStrange"""
        try:
            # Заглушка - в реальной реализации здесь будет проверка API
            # import docstrange_client
            # return docstrange_client.is_available()
            return False  # Пока недоступно
        except Exception as e:
            logger.debug(f"DocStrange недоступен: {e}")
            return False
    
    async def analyze_drawing_volumes(self, drawing_paths: List[str]) -> List[DrawingAnalysisResult]:
        """
        Анализирует объемы и геометрию из чертежей
        
        Args:
            drawing_paths: Пути к файлам чертежей
            
        Returns:
            Список результатов анализа для каждого чертежа
        """
        logger.info(f"📐 Начинаем анализ {len(drawing_paths)} чертежей")
        
        results = []
        
        for drawing_path in drawing_paths:
            result = await self._analyze_single_drawing(drawing_path)
            results.append(result)
        
        logger.info(f"✅ Анализ чертежей завершен: {len(results)} результатов")
        return results
    
    async def _analyze_single_drawing(self, drawing_path: str) -> DrawingAnalysisResult:
        """Анализ одного чертежа"""
        file_path = Path(drawing_path)
        
        if not file_path.exists():
            return DrawingAnalysisResult(
                drawing_file=drawing_path,
                elements_found=0,
                total_volume_m3=0.0,
                total_area_m2=0.0,
                elements=[],
                analysis_method="error",
                success=False,
                error_message=f"Файл не найден: {drawing_path}"
            )
        
        file_ext = file_path.suffix.lower()
        
        if file_ext not in self.supported_formats:
            return DrawingAnalysisResult(
                drawing_file=drawing_path,
                elements_found=0,
                total_volume_m3=0.0,
                total_area_m2=0.0,
                elements=[],
                analysis_method="unsupported_format",
                success=False,
                error_message=f"Неподдерживаемый формат: {file_ext}"
            )
        
        # Выбираем метод анализа в зависимости от доступности сервисов
        if file_ext == '.pdf':
            if self.external_services['mineru']:
                return await self._analyze_with_mineru(drawing_path)
            else:
                return await self._analyze_pdf_fallback(drawing_path)
        
        elif file_ext in ['.dwg', '.dxf']:
            if self.external_services['docstrange']:
                return await self._analyze_with_docstrange(drawing_path)
            else:
                return await self._analyze_cad_fallback(drawing_path)
        
        else:
            return DrawingAnalysisResult(
                drawing_file=drawing_path,
                elements_found=0,
                total_volume_m3=0.0,
                total_area_m2=0.0,
                elements=[],
                analysis_method="fallback",
                success=False,
                error_message="Анализ недоступен - внешние сервисы не подключены"
            )
    
    async def _analyze_with_mineru(self, drawing_path: str) -> DrawingAnalysisResult:
        """Анализ PDF с помощью MinerU (будущая реализация)"""
        logger.info(f"📊 Анализ {drawing_path} с помощью MinerU")
        
        try:
            # Здесь будет реальный вызов MinerU API
            # mineru_result = await mineru_client.analyze_pdf(drawing_path)
            # elements = self._parse_mineru_result(mineru_result)
            
            # Заглушка
            elements = [
                GeometricElement(
                    element_type="rectangle",
                    dimensions={"width": 500, "height": 300, "thickness": 200},
                    coordinates={"x": 0, "y": 0, "z": 0},
                    volume_m3=30.0,
                    area_m2=150.0,
                    confidence=0.8
                )
            ]
            
            return DrawingAnalysisResult(
                drawing_file=drawing_path,
                elements_found=len(elements),
                total_volume_m3=sum(e.volume_m3 or 0 for e in elements),
                total_area_m2=sum(e.area_m2 or 0 for e in elements),
                elements=elements,
                analysis_method="mineru",
                success=True
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа с MinerU: {e}")
            return await self._analyze_pdf_fallback(drawing_path)
    
    async def _analyze_with_docstrange(self, drawing_path: str) -> DrawingAnalysisResult:
        """Анализ CAD с помощью DocStrange (будущая реализация)"""
        logger.info(f"📊 Анализ {drawing_path} с помощью DocStrange")
        
        try:
            # Здесь будет реальный вызов DocStrange API
            # docstrange_result = await docstrange_client.analyze_cad(drawing_path)
            # elements = self._parse_docstrange_result(docstrange_result)
            
            # Заглушка
            elements = [
                GeometricElement(
                    element_type="beam",
                    dimensions={"length": 6000, "width": 300, "height": 500},
                    coordinates={"x": 0, "y": 0, "z": 0},
                    volume_m3=0.9,
                    confidence=0.9
                )
            ]
            
            return DrawingAnalysisResult(
                drawing_file=drawing_path,
                elements_found=len(elements),
                total_volume_m3=sum(e.volume_m3 or 0 for e in elements),
                total_area_m2=sum(e.area_m2 or 0 for e in elements),
                elements=elements,
                analysis_method="docstrange",
                success=True
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа с DocStrange: {e}")
            return await self._analyze_cad_fallback(drawing_path)
    
    async def _analyze_pdf_fallback(self, drawing_path: str) -> DrawingAnalysisResult:
        """Fallback анализ PDF (без внешних сервисов)"""
        logger.info(f"📄 Fallback анализ PDF: {drawing_path}")
        
        # Простая эвристика - ищем PDF с геометрическими данными в тексте
        try:
            import pdfplumber
            
            elements = []
            with pdfplumber.open(drawing_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    
                    # Ищем размеры в тексте
                    import re
                    dimension_patterns = [
                        r'(\d+(?:[.,]\d+)?)\s*[xх×]\s*(\d+(?:[.,]\d+)?)\s*[xх×]?\s*(\d+(?:[.,]\d+)?)?',  # 100x200x300
                        r'(?:délka|length)[:\s]*(\d+(?:[.,]\d+)?)',  # délka: 500
                        r'(?:šířka|width)[:\s]*(\d+(?:[.,]\d+)?)',   # šířka: 300
                        r'(?:výška|height)[:\s]*(\d+(?:[.,]\d+)?)',  # výška: 200
                    ]
                    
                    for pattern in dimension_patterns:
                        matches = re.finditer(pattern, text, re.IGNORECASE)
                        for match in matches:
                            # Создаем элемент на основе найденных размеров
                            dims = [float(g.replace(',', '.')) for g in match.groups() if g]
                            if len(dims) >= 2:
                                element = GeometricElement(
                                    element_type="detected_element",
                                    dimensions={"width": dims[0], "height": dims[1], 
                                              "depth": dims[2] if len(dims) > 2 else 100},
                                    coordinates={"x": 0, "y": 0, "z": 0},
                                    volume_m3=(dims[0] * dims[1] * (dims[2] if len(dims) > 2 else 100)) / 1000000,  # мм в м³
                                    confidence=0.6
                                )
                                elements.append(element)
            
            return DrawingAnalysisResult(
                drawing_file=drawing_path,
                elements_found=len(elements),
                total_volume_m3=sum(e.volume_m3 or 0 for e in elements),
                total_area_m2=sum(e.area_m2 or 0 for e in elements),
                elements=elements,
                analysis_method="pdf_fallback",
                success=True
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка fallback анализа PDF: {e}")
            return DrawingAnalysisResult(
                drawing_file=drawing_path,
                elements_found=0,
                total_volume_m3=0.0,
                total_area_m2=0.0,
                elements=[],
                analysis_method="pdf_fallback",
                success=False,
                error_message=str(e)
            )
    
    async def _analyze_cad_fallback(self, drawing_path: str) -> DrawingAnalysisResult:
        """Fallback анализ CAD (без внешних сервисов)"""
        logger.info(f"📐 CAD файлы требуют специализированных сервисов: {drawing_path}")
        
        return DrawingAnalysisResult(
            drawing_file=drawing_path,
            elements_found=0,
            total_volume_m3=0.0,
            total_area_m2=0.0,
            elements=[],
            analysis_method="cad_fallback",
            success=False,
            error_message="CAD анализ требует подключения DocStrange API"
        )
    
    def create_drawing_summary(self, results: List[DrawingAnalysisResult]) -> Dict[str, Any]:
        """Создает сводку по результатам анализа чертежей"""
        total_elements = sum(r.elements_found for r in results)
        total_volume = sum(r.total_volume_m3 for r in results)
        total_area = sum(r.total_area_m2 for r in results)
        successful_analyses = sum(1 for r in results if r.success)
        
        return {
            "total_drawings": len(results),
            "successful_analyses": successful_analyses,
            "total_elements_found": total_elements,
            "total_volume_m3": total_volume,
            "total_area_m2": total_area,
            "analysis_methods": list(set(r.analysis_method for r in results)),
            "external_services_status": self.external_services,
            "drawings": [
                {
                    "file": r.drawing_file,
                    "success": r.success,
                    "elements": r.elements_found,
                    "volume_m3": r.total_volume_m3,
                    "method": r.analysis_method,
                    "error": r.error_message
                }
                for r in results
            ]
        }

# Singleton instance
_drawing_volume_agent = None

def get_drawing_volume_agent() -> DrawingVolumeAgent:
    """Получение глобального экземпляра агента анализа чертежей"""
    global _drawing_volume_agent
    if _drawing_volume_agent is None:
        _drawing_volume_agent = DrawingVolumeAgent()
        logger.info("📐 DrawingVolumeAgent initialized")
    return _drawing_volume_agent

# Тестовая функция
async def test_drawing_analysis():
    """Тестирование анализа чертежей"""
    agent = get_drawing_volume_agent()
    
    # Создаем тестовый PDF
    import tempfile
    temp_dir = tempfile.mkdtemp()
    test_pdf = f"{temp_dir}/test_drawing.pdf"
    
    # Простой PDF с размерами
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Technical Drawing", ln=1, align="C")
    pdf.cell(200, 10, txt="Beam: 6000 x 300 x 500 mm", ln=1)
    pdf.cell(200, 10, txt="Column: 400 x 400 x 3000 mm", ln=1)
    pdf.output(test_pdf)
    
    # Анализируем
    results = await agent.analyze_drawing_volumes([test_pdf])
    summary = agent.create_drawing_summary(results)
    
    print("📐 DRAWING ANALYSIS TEST")
    print("=" * 40)
    print(f"Total drawings: {summary['total_drawings']}")
    print(f"Successful analyses: {summary['successful_analyses']}")
    print(f"Total volume: {summary['total_volume_m3']} m³")
    print(f"Methods used: {summary['analysis_methods']}")
    
    # Очистка
    import shutil
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_drawing_analysis())