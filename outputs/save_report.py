import json
import os
import logging


def save_merged_report(data: dict, output_path: str = "outputs/merged_report.json") -> str:
    """
    Сохраняет итоговый JSON-отчёт в файл.

    :param data: Словарь с объединёнными результатами анализа
    :param output_path: Путь до выходного файла
    :return: Путь до сохранённого файла
    """
    # Создаём директорию, если её нет
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logging.info(f"✅ Итоговый отчёт сохранён: {output_path}")
        return output_path
    except Exception as e:
        logging.error(f"❌ Ошибка при сохранении JSON-отчёта: {e}")
        raise


def load_merged_report(input_path: str = "outputs/merged_report.json") -> dict:
    """
    Загружает итоговый отчёт из JSON (если он существует).
    
    :param input_path: Путь к файлу
    :return: Словарь с данными или пустой dict
    """
    if not os.path.exists(input_path):
        logging.warning(f"⚠️ Файл отчёта {input_path} не найден.")
        return {}

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"❌ Ошибка при загрузке JSON-отчёта: {e}")
        return {}
