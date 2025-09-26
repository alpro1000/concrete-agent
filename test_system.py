import os
import sys
from pathlib import Path

def diagnose_system():
    print("=== ДИАГНОСТИКА СИСТЕМЫ ===")
    
    # Проверка основного скрипта
    if Path("analyze_concrete_complete.py").exists():
        print("✅ analyze_concrete_complete.py найден")
    else:
        print("❌ analyze_concrete_complete.py НЕ НАЙДЕН")
    
    # Проверка модулей
    modules = [
        "utils/volume_analyzer.py",
        "utils/report_generator.py", 
        "utils/czech_preprocessor.py"
    ]
    
    for module in modules:
        if Path(module).exists():
            print(f"✅ {module}")
        else:
            print(f"❌ {module} ОТСУТСТВУЕТ")
    
    # Проверка прав
    try:
        Path("outputs").mkdir(exist_ok=True)
        test_file = Path("outputs/test.txt")
        test_file.write_text("test")
        test_file.unlink()
        print("✅ Права на запись в outputs/")
    except Exception as e:
        print(f"❌ Нет прав на запись: {e}")
    
    # Проверка импортов
    try:
        # Импортируем напрямую из файла concrete_agent.py в папке agents
        import importlib.util
        import os
        
        spec = importlib.util.spec_from_file_location(
            "concrete_agent_main", 
            os.path.join("agents", "concrete_agent.py")
        )
        concrete_agent_main = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(concrete_agent_main)
        
        if hasattr(concrete_agent_main, 'analyze_concrete_with_volumes'):
            print("✅ Функция analyze_concrete_with_volumes доступна")
        else:
            print("❌ Функция analyze_concrete_with_volumes не найдена в модуле")
            
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        
    # Дополнительная проверка агентов
    try:
        from agents.concrete_agent.agent import get_concrete_grade_extractor
        from agents.volume_agent.agent import get_volume_analysis_agent
        from agents.smetny_inzenyr.agent import get_smetny_inzenyr
        print("✅ Специализированные агенты доступны")
    except ImportError as e:
        print(f"⚠️ Предупреждение - некоторые агенты недоступны: {e}")

if __name__ == "__main__":
    diagnose_system()
