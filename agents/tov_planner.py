# agents/tov_planner.py
"""
TOVPlanner Agent - Труд-Оборудование-Материалы Planning
Builds resource schedules with work zones and Gantt charts
"""
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

@dataclass
class WorkZone:
    """Рабочая захватка"""
    zone_id: str
    name: str
    description: str
    activities: List[str]
    estimated_duration_days: int
    dependencies: List[str]
    resources_required: Dict[str, Any]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

@dataclass
class ResourceRequirement:
    """Требование к ресурсам"""
    resource_type: str  # "labor", "equipment", "material"
    resource_name: str
    quantity: float
    unit: str
    cost_per_unit: float
    availability_constraint: Optional[str] = None

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

class TOVPlanner:
    """
    Планировщик ресурсов TOV (Труд-Оборудование-Материалы)
    
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
        """
        Создает план ресурсов на основе сметных данных
        
        Args:
            estimate_data: Данные сметы с работами и ресурсами
            project_constraints: Ограничения проекта (сроки, бригады, техника)
            
        Returns:
            WorkPackage: Сформированный пакет работ
        """
        try:
            self.logger.info("🔧 Начинаем создание TOV плана")
            
            # Извлекаем ресурсы из сметы
            resources = self._extract_resources_from_estimate(estimate_data)
            
            # Создаем рабочие захватки
            work_zones = self._create_work_zones(
                estimate_data.get("work_items", []), 
                project_constraints
            )
            
            # Планируем последовательность работ
            scheduled_zones = self._schedule_work_zones(work_zones, resources)
            
            # Определяем критический путь
            critical_path = self._identify_critical_path(scheduled_zones)
            
            # Рассчитываем общую стоимость и продолжительность
            total_cost = sum(zone.resources_required.get("total_cost", 0) for zone in scheduled_zones)
            total_duration = self._calculate_total_duration(scheduled_zones)
            
            work_package = WorkPackage(
                package_id=f"wp_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                name="TOV Work Package",
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
            
            # Извлекаем труд
            for item in work_items:
                if "labor_hours" in item:
                    resources.append(ResourceRequirement(
                        resource_type="labor",
                        resource_name=item.get("specialty", "General worker"),
                        quantity=item["labor_hours"],
                        unit="hours",
                        cost_per_unit=item.get("labor_rate", 500.0)  # CZK per hour
                    ))
                
                # Извлекаем оборудование
                if "equipment" in item:
                    for equipment in item["equipment"]:
                        resources.append(ResourceRequirement(
                            resource_type="equipment",
                            resource_name=equipment.get("name", "Unknown equipment"),
                            quantity=equipment.get("hours", 1.0),
                            unit="hours",
                            cost_per_unit=equipment.get("rate", 1000.0)  # CZK per hour
                        ))
            
            # Извлекаем материалы
            for material in materials:
                resources.append(ResourceRequirement(
                    resource_type="material",
                    resource_name=material.get("name", "Unknown material"),
                    quantity=material.get("quantity", 1.0),
                    unit=material.get("unit", "pc"),
                    cost_per_unit=material.get("unit_price", 0.0)
                ))
            
            self.logger.info(f"📦 Извлечено ресурсов: {len(resources)}")
            return resources
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения ресурсов: {e}")
            return []
    
    def _create_work_zones(
        self, 
        work_items: List[Dict[str, Any]], 
        constraints: Optional[Dict[str, Any]]
    ) -> List[WorkZone]:
        """Создает рабочие захватки"""
        zones = []
        
        try:
            # Группируем работы по типам
            work_groups = self._group_works_by_type(work_items)
            
            zone_counter = 1
            for group_name, group_items in work_groups.items():
                # Определяем стратегию разбивки на захватки
                zone_strategy = self._determine_zone_strategy(group_name, group_items, constraints)
                
                if zone_strategy == "by_floors":
                    zones.extend(self._create_zones_by_floors(group_name, group_items, zone_counter))
                elif zone_strategy == "by_building_sections":
                    zones.extend(self._create_zones_by_sections(group_name, group_items, zone_counter))
                elif zone_strategy == "by_technology_breaks":
                    zones.extend(self._create_zones_by_tech_breaks(group_name, group_items, zone_counter))
                else:
                    # По умолчанию - простое разбиение
                    zones.extend(self._create_simple_zones(group_name, group_items, zone_counter))
                
                zone_counter += len(zones)
            
            self.logger.info(f"🏗️ Создано захваток: {len(zones)}")
            return zones
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания захваток: {e}")
            return []
    
    def _group_works_by_type(self, work_items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Группирует работы по типам"""
        groups = {
            "earthworks": [],
            "foundation": [],
            "structural": [],
            "finishing": [],
            "systems": [],
            "other": []
        }
        
        for item in work_items:
            work_type = self._classify_work_type(item.get("name", "").lower())
            groups[work_type].append(item)
        
        # Удаляем пустые группы
        return {k: v for k, v in groups.items() if v}
    
    def _classify_work_type(self, work_name: str) -> str:
        """Классифицирует тип работы"""
        if any(keyword in work_name for keyword in ["земля", "выемка", "засыпка", "earth", "excavation"]):
            return "earthworks"
        elif any(keyword in work_name for keyword in ["фундамент", "foundation", "бетон", "concrete"]):
            return "foundation"
        elif any(keyword in work_name for keyword in ["каркас", "колонна", "балка", "structural", "frame"]):
            return "structural"
        elif any(keyword in work_name for keyword in ["отделка", "покраска", "плитка", "finishing", "tile"]):
            return "finishing"
        elif any(keyword in work_name for keyword in ["отопление", "вентиляция", "электр", "hvac", "electric"]):
            return "systems"
        else:
            return "other"
    
    def _determine_zone_strategy(
        self, 
        group_name: str, 
        group_items: List[Dict[str, Any]], 
        constraints: Optional[Dict[str, Any]]
    ) -> str:
        """Определяет стратегию разбивки на захватки"""
        
        # Учитываем количество работ
        if len(group_items) > 20:
            return "by_floors"
        
        # Учитываем тип работ
        if group_name in ["structural", "foundation"]:
            return "by_building_sections"
        elif group_name == "finishing":
            return "by_floors"
        elif group_name in ["earthworks", "systems"]:
            return "by_technology_breaks"
        
        return "simple"
    
    def _create_zones_by_floors(
        self, 
        group_name: str, 
        group_items: List[Dict[str, Any]], 
        start_counter: int
    ) -> List[WorkZone]:
        """Создает захватки по этажам"""
        zones = []
        floor_groups = {}
        
        # Группируем по этажам (если указано в описании работ)
        for item in group_items:
            floor = self._extract_floor_info(item.get("description", ""))
            if floor not in floor_groups:
                floor_groups[floor] = []
            floor_groups[floor].append(item["name"])
        
        # Создаем зоны для каждого этажа
        counter = start_counter
        for floor, activities in floor_groups.items():
            zone = WorkZone(
                zone_id=f"zone_{counter}",
                name=f"{group_name.title()} - {floor}",
                description=f"Работы {group_name} на {floor}",
                activities=activities,
                estimated_duration_days=len(activities) * 2,  # Примерная оценка
                dependencies=[f"zone_{counter-1}"] if counter > start_counter else [],
                resources_required={"labor_hours": len(activities) * 8}
            )
            zones.append(zone)
            counter += 1
        
        return zones
    
    def _create_zones_by_sections(
        self, 
        group_name: str, 
        group_items: List[Dict[str, Any]], 
        start_counter: int
    ) -> List[WorkZone]:
        """Создает захватки по секциям здания"""
        zones = []
        section_size = max(1, len(group_items) // 4)  # Разбиваем на 4 секции
        
        for i in range(0, len(group_items), section_size):
            section_items = group_items[i:i + section_size]
            activities = [item["name"] for item in section_items]
            
            zone = WorkZone(
                zone_id=f"zone_{start_counter + i // section_size}",
                name=f"{group_name.title()} - Секция {i // section_size + 1}",
                description=f"Работы {group_name} в секции {i // section_size + 1}",
                activities=activities,
                estimated_duration_days=len(activities) * 3,
                dependencies=[],
                resources_required={"labor_hours": len(activities) * 10}
            )
            zones.append(zone)
        
        return zones
    
    def _create_zones_by_tech_breaks(
        self, 
        group_name: str, 
        group_items: List[Dict[str, Any]], 
        start_counter: int
    ) -> List[WorkZone]:
        """Создает захватки с технологическими паузами"""
        zones = []
        
        # Учитываем технологические паузы (сушка, испытания)
        tech_break_items = []
        normal_items = []
        
        for item in group_items:
            if any(keyword in item.get("name", "").lower() for keyword in ["сушка", "испытание", "cure", "test"]):
                tech_break_items.append(item)
            else:
                normal_items.append(item)
        
        # Создаем обычные зоны
        if normal_items:
            zone = WorkZone(
                zone_id=f"zone_{start_counter}",
                name=f"{group_name.title()} - Основные работы",
                description=f"Основные работы {group_name}",
                activities=[item["name"] for item in normal_items],
                estimated_duration_days=len(normal_items) * 2,
                dependencies=[],
                resources_required={"labor_hours": len(normal_items) * 8}
            )
            zones.append(zone)
        
        # Создаем зоны с технологическими паузами
        if tech_break_items:
            zone = WorkZone(
                zone_id=f"zone_{start_counter + 1}",
                name=f"{group_name.title()} - Технологические паузы",
                description=f"Работы с технологическими паузами {group_name}",
                activities=[item["name"] for item in tech_break_items],
                estimated_duration_days=len(tech_break_items) * 5,  # Дольше из-за пауз
                dependencies=[f"zone_{start_counter}"] if normal_items else [],
                resources_required={"labor_hours": len(tech_break_items) * 4}
            )
            zones.append(zone)
        
        return zones
    
    def _create_simple_zones(
        self, 
        group_name: str, 
        group_items: List[Dict[str, Any]], 
        start_counter: int
    ) -> List[WorkZone]:
        """Создает простые захватки"""
        activities = [item["name"] for item in group_items]
        
        zone = WorkZone(
            zone_id=f"zone_{start_counter}",
            name=f"{group_name.title()}",
            description=f"Работы типа {group_name}",
            activities=activities,
            estimated_duration_days=len(activities) * 2,
            dependencies=[],
            resources_required={"labor_hours": len(activities) * 8}
        )
        
        return [zone]
    
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
    
    def _schedule_work_zones(
        self, 
        zones: List[WorkZone], 
        resources: List[ResourceRequirement]
    ) -> List[WorkZone]:
        """Планирует расписание захваток"""
        
        try:
            # Сортируем зоны по зависимостям
            scheduled_zones = self._topological_sort_zones(zones)
            
            # Назначаем даты начала и окончания
            current_date = datetime.now()
            
            for zone in scheduled_zones:
                # Находим самую позднюю дату окончания зависимостей
                dep_end_date = current_date
                for dep_id in zone.dependencies:
                    dep_zone = next((z for z in scheduled_zones if z.zone_id == dep_id), None)
                    if dep_zone and dep_zone.end_date:
                        dep_end_date = max(dep_end_date, dep_zone.end_date)
                
                zone.start_date = dep_end_date
                zone.end_date = dep_end_date + timedelta(days=zone.estimated_duration_days)
                
                # Обновляем текущую дату
                current_date = zone.end_date
            
            return scheduled_zones
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка планирования захваток: {e}")
            return zones
    
    def _topological_sort_zones(self, zones: List[WorkZone]) -> List[WorkZone]:
        """Топологическая сортировка захваток по зависимостям"""
        # Простая реализация топологической сортировки
        sorted_zones = []
        remaining_zones = zones.copy()
        
        while remaining_zones:
            # Находим зоны без неудовлетворенных зависимостей
            ready_zones = []
            for zone in remaining_zones:
                deps_satisfied = all(
                    any(sz.zone_id == dep_id for sz in sorted_zones)
                    for dep_id in zone.dependencies
                )
                if deps_satisfied:
                    ready_zones.append(zone)
            
            if not ready_zones:
                # Если есть циклические зависимости, добавляем первую доступную
                ready_zones = [remaining_zones[0]]
            
            # Добавляем готовые зоны в результат
            for zone in ready_zones:
                sorted_zones.append(zone)
                remaining_zones.remove(zone)
        
        return sorted_zones
    
    def _identify_critical_path(self, zones: List[WorkZone]) -> List[str]:
        """Определяет критический путь"""
        # Находим самую длинную цепочку зависимостей
        critical_path = []
        
        # Простой алгоритм: находим зону с самой поздней датой окончания
        if zones:
            latest_zone = max(zones, key=lambda z: z.end_date if z.end_date else datetime.min)
            
            # Строим путь назад по зависимостям
            current_zone = latest_zone
            while current_zone:
                critical_path.append(current_zone.zone_id)
                
                # Находим зависимость с самой поздней датой окончания
                dep_zones = [z for z in zones if z.zone_id in current_zone.dependencies]
                if dep_zones:
                    current_zone = max(dep_zones, key=lambda z: z.end_date if z.end_date else datetime.min)
                else:
                    current_zone = None
        
        return list(reversed(critical_path))
    
    def _calculate_total_duration(self, zones: List[WorkZone]) -> int:
        """Рассчитывает общую продолжительность проекта"""
        if not zones:
            return 0
        
        # Находим самую позднюю дату окончания
        latest_end = max(z.end_date for z in zones if z.end_date)
        earliest_start = min(z.start_date for z in zones if z.start_date)
        
        if latest_end and earliest_start:
            return (latest_end - earliest_start).days
        
        return sum(z.estimated_duration_days for z in zones)
    
    async def generate_gantt_chart_data(self, work_package: WorkPackage) -> Dict[str, Any]:
        """Генерирует данные для диаграммы Ганта"""
        try:
            gantt_data = {
                "project_name": work_package.name,
                "total_duration": work_package.total_duration_days,
                "start_date": min(z.start_date for z in work_package.work_zones if z.start_date).isoformat(),
                "end_date": max(z.end_date for z in work_package.work_zones if z.end_date).isoformat(),
                "tasks": []
            }
            
            for zone in work_package.work_zones:
                task = {
                    "id": zone.zone_id,
                    "name": zone.name,
                    "start": zone.start_date.isoformat() if zone.start_date else None,
                    "end": zone.end_date.isoformat() if zone.end_date else None,
                    "duration": zone.estimated_duration_days,
                    "dependencies": zone.dependencies,
                    "progress": 0,  # Процент выполнения
                    "critical": zone.zone_id in work_package.critical_path
                }
                gantt_data["tasks"].append(task)
            
            return gantt_data
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка генерации данных Ганта: {e}")
            return {"error": str(e)}
    
    def export_to_csv(self, work_package: WorkPackage) -> str:
        """Экспортирует план в CSV формат"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Заголовки
        writer.writerow([
            "Zone ID", "Zone Name", "Activities", "Start Date", "End Date", 
            "Duration (days)", "Dependencies", "Labor Hours", "Cost"
        ])
        
        # Данные захваток
        for zone in work_package.work_zones:
            writer.writerow([
                zone.zone_id,
                zone.name,
                "; ".join(zone.activities),
                zone.start_date.strftime("%Y-%m-%d") if zone.start_date else "",
                zone.end_date.strftime("%Y-%m-%d") if zone.end_date else "",
                zone.estimated_duration_days,
                "; ".join(zone.dependencies),
                zone.resources_required.get("labor_hours", 0),
                zone.resources_required.get("total_cost", 0)
            ])
        
        return output.getvalue()


# Singleton instance
_tov_planner = None

def get_tov_planner() -> TOVPlanner:
    """Получить экземпляр планировщика TOV"""
    global _tov_planner
    if _tov_planner is None:
        _tov_planner = TOVPlanner()
    return _tov_planner