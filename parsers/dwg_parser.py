"""
dwg_parser.py
Заглушка для работы с DWG-файлами.
"""
import logging

logger = logging.getLogger(__name__)

class DWGParser:
    def parse(self, path: str) -> str:
        """
        Пока возвращает заглушку.
        В будущем можно подключить библиотеку ezdxf.
        """
        logger.info(f"⚠️ DWG-файлы пока не поддерживаются: {path}")
        return ""
