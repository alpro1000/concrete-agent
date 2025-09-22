import os
import logging

# Заглушка: имитирует парсинг DWG и возвращает фиктивный текст
def extract_text_from_dwg(file_path: str) -> str:
    logging.info(f"📐 Имитация извлечения текста из DWG: {os.path.basename(file_path)}")

    # Здесь можно подключить реальный API, например:
    # - AutoDWG
    # - cloudconvert
    # - AnyConv
    # - LibreDWG через subprocess
    #
    # Пока что — заглушка для тестов:
    dummy_text = """
        ZÁKLADY C30/37 XA2 XC2 50/60
        PILOTY C30/37 XA2 XC2 60/70
        PODKLADNÍ BETON C12/15 X0
        OKNA PVC 1200x1500
        ARMATURA Fe500
    """
    return dummy_text
