"""
Централизованный сервис базы знаний
utils/knowledge_base_service.py

Предоставляет единую точку доступа к знаниям о:
- Марках бетона и их свойствах
- Конструктивных элементах 
- Стандартах и нормативах
- Контекстных словарях
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from functools import lru_cache

logger = logging.getLogger(__name__)

@dataclass
class ConcreteGrade:
    """Структура для марки бетона"""
    grade: str
    strength_class: str
    exposure_classes: List[str]
    typical_applications: List[str]
    density_kg_m3: Optional[float] = None
    max_w_c_ratio: Optional[float] = None
    min_cement_kg_m3: Optional[float] = None

@dataclass 
class ConstructionElement:
    """Структура для конструктивного элемента"""
    name: str
    czech_names: List[str]
    english_names: List[str]
    typical_grades: List[str]
    exposure_requirements: List[str]
    keywords: List[str]

@dataclass
class ExposureClass:
    """Класс воздействия среды"""
    code: str
    description: str
    typical_conditions: List[str]
    required_grades: List[str]

class KnowledgeBaseService:
    """
    Централизованный сервис базы знаний для системы анализа бетона
    """
    
    def __init__(self, knowledge_base_path: str = "knowledge_base/complete-concrete-knowledge-base.json"):
        self.knowledge_base_path = knowledge_base_path
        self._raw_data = {}
        self._concrete_grades = {}
        self._construction_elements = {}
        self._exposure_classes = {}
        self._context_keywords = set()
        
        self._load_knowledge_base()
        self._process_data()

    def _load_knowledge_base(self):
        """Загружает данные из файла базы знаний"""
        try:
            kb_path = Path(self.knowledge_base_path)
            if kb_path.exists():
                with open(kb_path, "r", encoding="utf-8") as f:
                    self._raw_data = json.load(f)
                logger.info(f"✅ База знаний загружена из {self.knowledge_base_path}")
            else:
                logger.warning(f"⚠️ Файл базы знаний не найден: {self.knowledge_base_path}")
                self._create_default_knowledge_base()
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки базы знаний: {e}")
            self._create_default_knowledge_base()

    def _create_default_knowledge_base(self):
        """Создает минимальную базу знаний по умолчанию"""
        self._raw_data = {
            "concrete_grades": {
                "C12/15": {
                    "strength_class": "C12/15",
                    "exposure_classes": ["X0", "XC1"],
                    "applications": ["Подкладочный бетон", "Фундаменты в сухой среде"],
                    "density": 2400,
                    "max_w_c": 0.65
                },
                "C16/20": {
                    "strength_class": "C16/20", 
                    "exposure_classes": ["X0", "XC1", "XC2"],
                    "applications": ["Стяжки", "Ненагруженные конструкции"],
                    "density": 2400,
                    "max_w_c": 0.60
                },
                "C20/25": {
                    "strength_class": "C20/25",
                    "exposure_classes": ["XC1", "XC2", "XC3"],
                    "applications": ["Стены", "Фундаменты", "Колонны"],
                    "density": 2400,
                    "max_w_c": 0.55
                },
                "C25/30": {
                    "strength_class": "C25/30",
                    "exposure_classes": ["XC1", "XC2", "XC3", "XC4", "XD1"],
                    "applications": ["Железобетонные конструкции", "Фундаменты"],
                    "density": 2400,
                    "max_w_c": 0.50
                },
                "C30/37": {
                    "strength_class": "C30/37",
                    "exposure_classes": ["XC3", "XC4", "XD1", "XD2", "XF1", "XF2"],
                    "applications": ["Мостовые конструкции", "Опоры", "Карнизы"],
                    "density": 2400,
                    "max_w_c": 0.45
                },
                "C35/45": {
                    "strength_class": "C35/45",
                    "exposure_classes": ["XD2", "XD3", "XF2", "XF3", "XF4"],
                    "applications": ["Критические конструкции", "Морские сооружения"],
                    "density": 2400,
                    "max_w_c": 0.40
                },
                "LC25/28": {
                    "strength_class": "LC25/28",
                    "exposure_classes": ["XC1", "XC2", "XC3"],
                    "applications": ["Легкий конструкционный бетон"],
                    "density": 2000,
                    "max_w_c": 0.50
                }
            },
            "construction_elements": {
                "foundation": {
                    "czech": ["základ", "základy", "základová", "fundament"],
                    "english": ["foundation", "footing", "base"],
                    "typical_grades": ["C20/25", "C25/30", "C30/37"],
                    "exposure": ["X0", "XC1", "XC2", "XA1"],
                    "keywords": ["založení", "základní", "spodní"]
                },
                "wall": {
                    "czech": ["stěna", "stěny", "stěn", "zeď"],
                    "english": ["wall", "partition"],
                    "typical_grades": ["C16/20", "C20/25", "C25/30"],
                    "exposure": ["XC1", "XC2", "XC3"],
                    "keywords": ["obvodová", "nosná", "dělící"]
                },
                "column": {
                    "czech": ["sloup", "sloupy", "pilíř", "pilíře"],
                    "english": ["column", "pillar", "pier"],
                    "typical_grades": ["C25/30", "C30/37", "C35/45"],
                    "exposure": ["XC2", "XC3", "XC4"],
                    "keywords": ["nosný", "svislá", "podpora"]
                },
                "beam": {
                    "czech": ["trám", "trámy", "nosník"],
                    "english": ["beam", "girder"],
                    "typical_grades": ["C25/30", "C30/37"],
                    "exposure": ["XC2", "XC3", "XC4"],
                    "keywords": ["vodorovný", "nosný", "překlady"]
                },
                "slab": {
                    "czech": ["deska", "desky", "desk"],
                    "english": ["slab", "deck", "plate"],
                    "typical_grades": ["C20/25", "C25/30", "C30/37"],
                    "exposure": ["XC1", "XC2", "XC3"],
                    "keywords": ["stropní", "podlahová", "plošná"]
                },
                "abutment": {
                    "czech": ["opěra", "opěry", "opěrná"],
                    "english": ["abutment", "retaining wall"],
                    "typical_grades": ["C30/37", "C35/45"],
                    "exposure": ["XC4", "XD1", "XD2", "XF2"],
                    "keywords": ["mostní", "podpěrná", "opěrný"]
                },
                "cornice": {
                    "czech": ["římsa", "říms", "římse"],
                    "english": ["cornice", "ledge"],
                    "typical_grades": ["C30/37", "C35/45"],
                    "exposure": ["XC4", "XD3", "XF4"],
                    "keywords": ["venkovní", "přesah", "ochranná"]
                }
            },
            "exposure_classes": {
                "XC1": {"description": "Сухая или постоянно влажная среда", "conditions": ["интерьер"]},
                "XC2": {"description": "Влажная, редко сухая", "conditions": ["подвал", "фундамент"]},
                "XC3": {"description": "Умеренная влажность", "conditions": ["экстерьер"]},
                "XC4": {"description": "Циклы влажность-сухость", "conditions": ["дождь", "снег"]},
                "XD1": {"description": "Умеренная влажность с хлоридами", "conditions": ["гараж"]},
                "XD2": {"description": "Влажная среда с хлоридами", "conditions": ["бассейн"]},
                "XD3": {"description": "Циклы с хлоридами", "conditions": ["мост", "дорога"]},
                "XF1": {"description": "Умеренная влажность с заморозками", "conditions": ["вертикальные поверхности"]},
                "XF2": {"description": "Умеренная влажность с противогололедными солями", "conditions": ["дороги"]},
                "XF3": {"description": "Высокая влажность с заморозками", "conditions": ["горизонтальные поверхности"]},
                "XF4": {"description": "Высокая влажность с солями и заморозками", "conditions": ["морские конструкции"]}
            }
        }
        logger.info("📚 Создана базовая база знаний")

    def _process_data(self):
        """Обрабатывает сырые данные в структурированные объекты"""
        
        # Поддерживаем оба формата - новый и старый
        concrete_grades_data = self._raw_data.get("concrete_grades", {})
        if not concrete_grades_data and "concrete_knowledge_base" in self._raw_data:
            # Новый формат JSON
            kb_data = self._raw_data["concrete_knowledge_base"]
            concrete_grades_data = kb_data.get("concrete_grades", {})
            construction_elements_data = kb_data.get("construction_elements", {})
            exposure_classes_data = kb_data.get("exposure_classes", {})
        else:
            # Старый формат
            construction_elements_data = self._raw_data.get("construction_elements", {})
            exposure_classes_data = self._raw_data.get("exposure_classes", {})
        
        # Обрабатываем марки бетона
        for grade_name, grade_data in concrete_grades_data.items():
            self._concrete_grades[grade_name] = ConcreteGrade(
                grade=grade_name,
                strength_class=grade_data.get("strength_class", grade_name),
                exposure_classes=grade_data.get("exposure_classes", []),
                typical_applications=grade_data.get("applications", []),
                density_kg_m3=grade_data.get("density"),
                max_w_c_ratio=grade_data.get("max_w_c"),
                min_cement_kg_m3=grade_data.get("min_cement")
            )
        
        # Обрабатываем конструктивные элементы
        for element_name, element_data in construction_elements_data.items():
            self._construction_elements[element_name] = ConstructionElement(
                name=element_name,
                czech_names=element_data.get("czech", []),
                english_names=element_data.get("english", []),
                typical_grades=element_data.get("typical_grades", []),
                exposure_requirements=element_data.get("exposure", []),
                keywords=element_data.get("keywords", [])
            )
            
            # Добавляем ключевые слова в общий набор
            self._context_keywords.update(element_data.get("czech", []))
            self._context_keywords.update(element_data.get("keywords", []))
        
        # Обрабатываем классы воздействия
        for class_code, class_data in exposure_classes_data.items():
            self._exposure_classes[class_code] = ExposureClass(
                code=class_code,
                description=class_data.get("description", ""),
                typical_conditions=class_data.get("conditions", []),
                required_grades=[]  # Будет заполнено позже
            )
        
        # Заполняем обратные связи для классов воздействия
        for grade_name, grade in self._concrete_grades.items():
            for exp_class in grade.exposure_classes:
                if exp_class in self._exposure_classes:
                    self._exposure_classes[exp_class].required_grades.append(grade_name)

        logger.info(f"📊 Обработано: {len(self._concrete_grades)} марок, "
                   f"{len(self._construction_elements)} элементов, "
                   f"{len(self._exposure_classes)} классов воздействия")

    @lru_cache(maxsize=100)
    def get_concrete_grade(self, grade: str) -> Optional[ConcreteGrade]:
        """Получает информацию о марке бетона"""
        return self._concrete_grades.get(grade.upper())

    @lru_cache(maxsize=100)  
    def is_valid_concrete_grade(self, grade: str) -> bool:
        """Проверяет, является ли строка валидной маркой бетона"""
        grade_upper = grade.upper()
        
        # Проверяем точное совпадение
        if grade_upper in self._concrete_grades:
            return True
            
        # Проверяем формат
        import re
        pattern = r'^(?:LC)?C\d{1,3}/\d{1,3}$'
        return bool(re.match(pattern, grade_upper))

    def get_all_concrete_grades(self) -> List[str]:
        """Возвращает список всех известных марок бетона"""
        return list(self._concrete_grades.keys())

    def get_construction_element(self, element_name: str) -> Optional[ConstructionElement]:
        """Получает информацию о конструктивном элементе"""
        return self._construction_elements.get(element_name.lower())

    def identify_construction_element(self, text: str) -> Optional[str]:
        """Определяет тип конструктивного элемента по тексту"""
        text_lower = text.lower()
        
        # Ищем точные совпадения
        for element_name, element in self._construction_elements.items():
            # Проверяем чешские названия
            for czech_name in element.czech_names:
                if czech_name.lower() in text_lower:
                    return element_name
                    
            # Проверяем ключевые слова
            for keyword in element.keywords:
                if keyword.lower() in text_lower:
                    return element_name
        
        return None

    def get_compatible_grades_for_element(self, element_name: str) -> List[str]:
        """Возвращает подходящие марки бетона для элемента"""
        element = self.get_construction_element(element_name)
        if element:
            return element.typical_grades
        return []

    def get_compatible_grades_for_exposure(self, exposure_class: str) -> List[str]:
        """Возвращает марки бетона, подходящие для класса воздействия"""
        exposure = self._exposure_classes.get(exposure_class.upper())
        if exposure:
            return exposure.required_grades
        return []

    def validate_grade_element_compatibility(self, grade: str, element_name: str) -> bool:
        """Проверяет совместимость марки бетона и конструктивного элемента"""
        element = self.get_construction_element(element_name)
        if not element:
            return True  # Если элемент неизвестен, считаем совместимым
            
        return grade.upper() in element.typical_grades

    def get_context_keywords(self) -> Set[str]:
        """Возвращает набор ключевых слов для контекстного поиска"""
        return self._context_keywords.copy()

    def search_grades_by_application(self, application: str) -> List[str]:
        """Ищет марки бетона по области применения"""
        application_lower = application.lower()
        matching_grades = []
        
        for grade_name, grade in self._concrete_grades.items():
            for app in grade.typical_applications:
                if application_lower in app.lower():
                    matching_grades.append(grade_name)
                    break
        
        return matching_grades

    def get_grade_recommendations(self, element_name: str, 
                                exposure_class: Optional[str] = None) -> List[str]:
        """Получает рекомендации по марке бетона"""
        recommendations = []
        
        # Рекомендации по элементу
        element_grades = self.get_compatible_grades_for_element(element_name)
        recommendations.extend(element_grades)
        
        # Рекомендации по классу воздействия
        if exposure_class:
            exposure_grades = self.get_compatible_grades_for_exposure(exposure_class)
            # Пересечение рекомендаций
            if recommendations:
                recommendations = [g for g in recommendations if g in exposure_grades]
            else:
                recommendations = exposure_grades
        
        return list(set(recommendations))  # Убираем дубликаты

    def export_knowledge_summary(self) -> Dict[str, Any]:
        """Экспортирует сводку базы знаний"""
        return {
            "concrete_grades": {
                "total": len(self._concrete_grades),
                "grades": list(self._concrete_grades.keys())
            },
            "construction_elements": {
                "total": len(self._construction_elements),
                "elements": list(self._construction_elements.keys())
            },
            "exposure_classes": {
                "total": len(self._exposure_classes),
                "classes": list(self._exposure_classes.keys())
            },
            "context_keywords_count": len(self._context_keywords)
        }

    def validate_analysis_result(self, concrete_grade: str, element: str, 
                               exposure_class: Optional[str] = None) -> Dict[str, Any]:
        """Валидирует результат анализа против базы знаний"""
        validation_result = {
            "valid": True,
            "warnings": [],
            "recommendations": []
        }
        
        # Проверяем марку бетона
        if not self.is_valid_concrete_grade(concrete_grade):
            validation_result["valid"] = False
            validation_result["warnings"].append(f"Неизвестная марка бетона: {concrete_grade}")
        
        # Проверяем совместимость
        if not self.validate_grade_element_compatibility(concrete_grade, element):
            validation_result["warnings"].append(
                f"Марка {concrete_grade} не типична для элемента {element}"
            )
            
            # Даем рекомендации
            recommended = self.get_compatible_grades_for_element(element)
            if recommended:
                validation_result["recommendations"].append(
                    f"Рекомендуемые марки для {element}: {', '.join(recommended)}"
                )
        
        # Проверяем класс воздействия
        if exposure_class:
            compatible_grades = self.get_compatible_grades_for_exposure(exposure_class)
            if concrete_grade not in compatible_grades:
                validation_result["warnings"].append(
                    f"Марка {concrete_grade} может не подходить для условий {exposure_class}"
                )
                
                validation_result["recommendations"].append(
                    f"Рекомендуемые марки для {exposure_class}: {', '.join(compatible_grades)}"
                )
        
        return validation_result

    def save_knowledge_base(self, path: Optional[str] = None):
        """Сохраняет базу знаний в файл"""
        save_path = path or self.knowledge_base_path
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(self._raw_data, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 База знаний сохранена в {save_path}")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения базы знаний: {e}")


# Singleton instance
_knowledge_service = None

def get_knowledge_service() -> KnowledgeBaseService:
    """Получение глобального экземпляра сервиса базы знаний"""
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeBaseService()
        logger.info("📚 KnowledgeBaseService initialized")
    return _knowledge_service


# ==============================
# 🧪 Функция для тестирования
# ==============================

def test_knowledge_service():
    """Тестирование сервиса базы знаний"""
    kb = get_knowledge_service()
    
    print("🧪 TESTING KNOWLEDGE BASE SERVICE")
    print("=" * 50)
    
    # Тест 1: Проверка марок бетона
    test_grades = ["C25/30", "C30/37", "LC25/28", "INVALID"]
    for grade in test_grades:
        valid = kb.is_valid_concrete_grade(grade)
        grade_info = kb.get_concrete_grade(grade)
        print(f"Grade {grade}: Valid={valid}, Info={'Found' if grade_info else 'Not found'}")
    
    # Тест 2: Определение элементов
    test_texts = [
        "mostní opěra ze železobetonu",
        "základy pod sloupem", 
        "betonová deska stropní",
        "římsa venkovní ochranná"
    ]
    
    print(f"\n🏗️ Element identification:")
    for text in test_texts:
        element = kb.identify_construction_element(text)
        print(f"'{text}' -> {element}")
    
    # Тест 3: Рекомендации
    print(f"\n💡 Recommendations:")
    recommendations = kb.get_grade_recommendations("abutment", "XD2")
    print(f"For abutment in XD2: {recommendations}")
    
    # Тест 4: Валидация
    print(f"\n✅ Validation:")
    validation = kb.validate_analysis_result("C16/20", "abutment", "XD3")
    print(f"C16/20 for abutment in XD3: Valid={validation['valid']}")
    if validation['warnings']:
        print(f"Warnings: {validation['warnings']}")
    if validation['recommendations']:
        print(f"Recommendations: {validation['recommendations']}")
    
    # Тест 5: Сводка
    summary = kb.export_knowledge_summary()
    print(f"\n📊 Knowledge base summary:")
    print(f"Concrete grades: {summary['concrete_grades']['total']}")
    print(f"Construction elements: {summary['construction_elements']['total']}")
    print(f"Exposure classes: {summary['exposure_classes']['total']}")

if __name__ == "__main__":
    test_knowledge_service()