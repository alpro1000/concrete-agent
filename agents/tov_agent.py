# agents/tov_agent.py
"""
TOVAgent - Труд-Оборудование-Материалы Planning Agent
Builds resource schedules with work zones and Gantt charts

Moved from tov_planner.py to follow the agents naming convention.
"""
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from io import StringIO

logger = logging.getLogger(__name__)

@dataclass
class WorkZone:
    """Рабочая захватка"""
    zone_id: str
    name: str
    activities: List[str]
    start_date: datetime
    end_date: datetime
    resources: List[Dict[str, Any]]
    dependencies: List[str]
    floor_level: str = "Общий"
    estimated_duration_days: int = 0
    status: str = "planned"

@dataclass
class ResourceRequirement:
    """Требование к ресурсам"""
    resource_type: str  # 'labor', 'equipment', 'material'
    resource_name: str
    quantity: float
    unit: str
    cost_per_unit: float
    total_cost: float
    required_dates: List[datetime]
    priority: str = "normal"  # low, normal, high, critical

@dataclass
class WorkPackage:
    """Пакет работ"""
    package_id: str
    name: str
    description: str
    work_zones: List[WorkZone]
    total_duration_days: int
    total_cost: float
    critical_path: List[str]
    resource_requirements: List[ResourceRequirement]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: str = "draft"

class TOVAgent:
    """
    TOV Agent - Планировщик ресурсов TOV (Труд-Оборудование-Материалы)
    
    Основные функции:
    - Анализ смет и выделение ресурсов
    - Разбивка на захватки по технологическим паузам
    - Планирование последовательности работ
    - Оптимизация использования ресурсов
    - Генерация диаграммы Ганта
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def create_tov_plan(
        self, 
        estimate_data: Dict[str, Any],
        project_constraints: Optional[Dict[str, Any]] = None
    ) -> WorkPackage:
        """Создает план ресурсов TOV на основе сметных данных"""
        try:
            self.logger.info("🔄 Создание TOV плана...")
            
            # Извлекаем ресурсы из сметы
            resources = self._extract_resources_from_estimate(estimate_data)
            self.logger.info(f"📊 Извлечено ресурсов: {len(resources)}")
            
            # Создаем захватки
            work_zones = self._create_work_zones(resources, project_constraints)
            self.logger.info(f"🏗️ Создано захваток: {len(work_zones)}")
            
            # Планируем последовательность
            scheduled_zones = self._schedule_zones(work_zones, project_constraints)
            
            # Определяем критический путь
            critical_path = self._identify_critical_path(scheduled_zones)
            
            # Рассчитываем общие показатели
            total_duration = max([zone.estimated_duration_days for zone in scheduled_zones], default=0)
            total_cost = sum([sum([r.total_cost for r in zone.resources]) for zone in scheduled_zones])
            
            # Создаем итоговый пакет работ
            work_package = WorkPackage(
                package_id=f"TOV_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                name="TOV Plan - Resource Schedule",
                description="Пакет работ с планом ресурсов",
                work_zones=scheduled_zones,
                total_duration_days=total_duration,
                total_cost=total_cost,
                critical_path=critical_path,
                resource_requirements=resources
            )
            
            self.logger.info(f"✅ TOV план создан: {len(scheduled_zones)} захваток, {total_duration} дней")
            return work_package
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания TOV плана: {e}")
            raise

    def _extract_resources_from_estimate(self, estimate_data: Dict[str, Any]) -> List[ResourceRequirement]:
        """Извлекает ресурсы из сметных данных"""
        resources = []
        
        try:
            work_items = estimate_data.get("work_items", [])
            materials = estimate_data.get("materials", [])
            
            # Обрабатываем работы
            for item in work_items:
                work_name = item.get("name", "Неизвестная работа")
                quantity = float(item.get("quantity", 0))
                unit = item.get("unit", "шт")
                cost = float(item.get("cost", 0))
                
                # Трудовые ресурсы
                labor_hours = item.get("labor_hours", quantity * 0.5)  # Примерная оценка
                if labor_hours > 0:
                    resources.append(ResourceRequirement(
                        resource_type="labor",
                        resource_name=f"Работы: {work_name}",
                        quantity=labor_hours,
                        unit="час",
                        cost_per_unit=800,  # Примерная стоимость час/работы
                        total_cost=labor_hours * 800,
                        required_dates=[datetime.now()],
                        priority=self._classify_work_priority(work_name)
                    ))
                
                # Оборудование
                equipment = item.get("equipment", [])
                for eq in equipment:
                    resources.append(ResourceRequirement(
                        resource_type="equipment",
                        resource_name=eq.get("name", "Оборудование"),
                        quantity=eq.get("quantity", 1),
                        unit=eq.get("unit", "шт"),
                        cost_per_unit=eq.get("cost_per_unit", 1000),
                        total_cost=eq.get("total_cost", 1000),
                        required_dates=[datetime.now()],
                        priority="normal"
                    ))
            
            # Обрабатываем материалы
            for material in materials:
                resources.append(ResourceRequirement(
                    resource_type="material",
                    resource_name=material.get("name", "Материал"),
                    quantity=float(material.get("quantity", 0)),
                    unit=material.get("unit", "м3"),
                    cost_per_unit=float(material.get("price", 0)),
                    total_cost=float(material.get("total_cost", 0)),
                    required_dates=[datetime.now()],
                    priority=self._classify_material_priority(material.get("name", ""))
                ))
            
            return resources
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения ресурсов: {e}")
            return []

    def _create_work_zones(self, resources: List[ResourceRequirement], constraints: Optional[Dict[str, Any]]) -> List[WorkZone]:
        """Создает рабочие захватки на основе ресурсов"""
        zones = []
        
        try:
            # Группируем ресурсы по типам работ
            work_groups = {}
            
            for resource in resources:
                work_type = self._classify_work_type(resource.resource_name)
                if work_type not in work_groups:
                    work_groups[work_type] = []
                work_groups[work_type].append(resource)
            
            # Создаем захватки для каждого типа работ
            zone_counter = 1
            for work_type, group_resources in work_groups.items():
                
                # Определяем этаж/уровень для захватки
                floor_level = self._determine_floor_level(group_resources)
                
                # Рассчитываем продолжительность
                total_labor_hours = sum([r.quantity for r in group_resources if r.resource_type == "labor"])
                duration_days = max(1, int(total_labor_hours / 8))  # 8 часов в день
                
                zone = WorkZone(
                    zone_id=f"ZONE_{zone_counter:03d}",
                    name=f"Захватка {zone_counter}: {work_type}",
                    activities=[r.resource_name for r in group_resources if r.resource_type == "labor"],
                    start_date=datetime.now(),
                    end_date=datetime.now() + timedelta(days=duration_days),
                    resources=[{
                        "type": r.resource_type,
                        "name": r.resource_name,
                        "quantity": r.quantity,
                        "unit": r.unit,
                        "cost": r.total_cost
                    } for r in group_resources],
                    dependencies=[],
                    floor_level=floor_level,
                    estimated_duration_days=duration_days,
                    status="planned"
                )
                
                zones.append(zone)
                zone_counter += 1
            
            return zones
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания захваток: {e}")
            return []

    def _classify_work_type(self, work_name: str) -> str:
        """Классифицирует тип работы"""
        work_name_lower = work_name.lower()
        
        if any(keyword in work_name_lower for keyword in ["бетон", "concrete", "заливка", "армир"]):
            return "concrete_works"
        elif any(keyword in work_name_lower for keyword in ["кирпич", "кладка", "стена", "masonry", "brick"]):
            return "masonry_works"
        elif any(keyword in work_name_lower for keyword in ["отделка", "штукатурка", "покраска", "finish"]):
            return "finishing_works"
        elif any(keyword in work_name_lower for keyword in ["кровля", "крыша", "roof", "roofing"]):
            return "roofing_works"
        elif any(keyword in work_name_lower for keyword in ["фундамент", "foundation", "основание"]):
            return "foundation_works"
        elif any(keyword in work_name_lower for keyword in ["отопление", "вентиляция", "электр", "hvac", "electric"]):
            return "systems"
        else:
            return "other"

    def _classify_work_priority(self, work_name: str) -> str:
        """Определяет приоритет работы"""
        work_name_lower = work_name.lower()
        
        if any(keyword in work_name_lower for keyword in ["фундамент", "foundation", "несущ", "структур"]):
            return "critical"
        elif any(keyword in work_name_lower for keyword in ["бетон", "concrete", "армир", "reinf"]):
            return "high"
        elif any(keyword in work_name_lower for keyword in ["отделка", "finish", "покраска", "painting"]):
            return "low"
        else:
            return "normal"

    def _classify_material_priority(self, material_name: str) -> str:
        """Определяет приоритет материала"""
        material_name_lower = material_name.lower()
        
        if any(keyword in material_name_lower for keyword in ["бетон", "cement", "арматур", "rebar"]):
            return "critical"
        elif any(keyword in material_name_lower for keyword in ["кирпич", "brick", "блок", "block"]):
            return "high"
        else:
            return "normal"

    def _determine_floor_level(self, resources: List[ResourceRequirement]) -> str:
        """Определяет уровень/этаж для группы ресурсов"""
        # Анализируем названия ресурсов для определения этажа
        for resource in resources:
            floor_info = self._extract_floor_info(resource.resource_name)
            if floor_info != "Общий":
                return floor_info
        
        return "Общий"

    def _extract_floor_info(self, description: str) -> str:
        """Извлекает информацию об этаже из описания"""
        description_lower = description.lower()
        
        if "подвал" in description_lower or "basement" in description_lower:
            return "Подвал"
        elif "1 этаж" in description_lower or "1st floor" in description_lower:
            return "1 этаж"
        elif "2 этаж" in description_lower or "2nd floor" in description_lower:
            return "2 этаж"
        elif "3 этаж" in description_lower or "3rd floor" in description_lower:
            return "3 этаж"
        elif "крыша" in description_lower or "roof" in description_lower:
            return "Крыша"
        
        return "Общий"

    def _schedule_zones(self, zones: List[WorkZone], constraints: Optional[Dict[str, Any]]) -> List[WorkZone]:
        """Планирует последовательность захваток с учетом зависимостей"""
        try:
            # Устанавливаем зависимости между захватками
            scheduled_zones = []
            current_date = datetime.now()
            
            # Сортируем по приоритету работ
            priority_order = ["foundation_works", "concrete_works", "masonry_works", "systems", "finishing_works", "roofing_works", "other"]
            
            def get_work_priority(zone):
                work_type = None
                for activity in zone.activities:
                    work_type = self._classify_work_type(activity)
                    break
                return priority_order.index(work_type) if work_type in priority_order else len(priority_order)
            
            zones.sort(key=get_work_priority)
            
            # Планируем каждую захватку
            for i, zone in enumerate(zones):
                if i == 0:
                    # Первая захватка начинается сразу
                    zone.start_date = current_date
                else:
                    # Последующие захватки начинаются после предыдущих
                    prev_zone = scheduled_zones[i-1]
                    zone.start_date = prev_zone.end_date + timedelta(days=1)
                    zone.dependencies = [prev_zone.zone_id]
                
                zone.end_date = zone.start_date + timedelta(days=zone.estimated_duration_days)
                scheduled_zones.append(zone)
            
            return scheduled_zones
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка планирования захваток: {e}")
            return zones

    def _identify_critical_path(self, zones: List[WorkZone]) -> List[str]:
        """Определяет критический путь проекта"""
        try:
            # Упрощенный алгоритм: все захватки на критическом пути
            # В реальной реализации использовался бы метод критического пути (CPM)
            critical_path = []
            
            for zone in zones:
                # Захватки с большой продолжительностью или высокой стоимостью
                total_cost = sum([r.get("cost", 0) for r in zone.resources])
                if zone.estimated_duration_days > 5 or total_cost > 100000:
                    critical_path.append(zone.zone_id)
            
            return critical_path
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка определения критического пути: {e}")
            return []

    def export_to_csv(self, work_package: WorkPackage) -> str:
        """Экспортирует план в CSV формат"""
        try:
            output = StringIO()
            
            # Заголовки
            output.write("Zone_ID,Zone_Name,Start_Date,End_Date,Duration_Days,Total_Cost,Activities,Floor_Level,Status\n")
            
            # Данные по захваткам
            for zone in work_package.work_zones:
                total_cost = sum([r.get("cost", 0) for r in zone.resources])
                activities = "; ".join(zone.activities[:3])  # Первые 3 активности
                
                output.write(f"{zone.zone_id},{zone.name},{zone.start_date.strftime('%Y-%m-%d')},{zone.end_date.strftime('%Y-%m-%d')},{zone.estimated_duration_days},{total_cost},{activities},{zone.floor_level},{zone.status}\n")
            
            return output.getvalue()
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка экспорта в CSV: {e}")
            return ""

    def export_to_json(self, work_package: WorkPackage) -> str:
        """Экспортирует план в JSON формат"""
        try:
            # Конвертируем в сериализуемый формат
            export_data = {
                "package_id": work_package.package_id,
                "name": work_package.name,
                "description": work_package.description,
                "total_duration_days": work_package.total_duration_days,
                "total_cost": work_package.total_cost,
                "critical_path": work_package.critical_path,
                "status": work_package.status,
                "work_zones": []
            }
            
            for zone in work_package.work_zones:
                zone_data = {
                    "zone_id": zone.zone_id,
                    "name": zone.name,
                    "activities": zone.activities,
                    "start_date": zone.start_date.isoformat(),
                    "end_date": zone.end_date.isoformat(),
                    "estimated_duration_days": zone.estimated_duration_days,
                    "floor_level": zone.floor_level,
                    "status": zone.status,
                    "dependencies": zone.dependencies,
                    "resources": zone.resources
                }
                export_data["work_zones"].append(zone_data)
            
            return json.dumps(export_data, indent=2, ensure_ascii=False)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка экспорта в JSON: {e}")
            return "{}"

# Singleton instance
_tov_agent = None

def get_tov_agent() -> TOVAgent:
    """Получить экземпляр TOV агента"""
    global _tov_agent
    if _tov_agent is None:
        _tov_agent = TOVAgent()
    return _tov_agent