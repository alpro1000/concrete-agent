"""
Агент-сметчик (MVP)
Задача: парсинг проектных документов (PDF, DOCX, Excel, XML)
и подготовка данных для анализа ресурсов.
"""
import logging
from parsers.doc_parser import DocParser
from parsers.smeta_parser import SmetaParser
from parsers.xml_smeta_parser import XMLSmetaParser
from outputs.save_report import save_merged_report  # ✅ добавлено

logger = logging.getLogger(__name__)

class SmetnyInzenyr:
    def __init__(self):
        self.doc_parser = DocParser()
        self.smeta_parser = SmetaParser()
        self.xml_parser = XMLSmetaParser()

    def parse_documents(self, files: list[str]) -> dict:
        """Определяет парсер по расширению файла"""
        results = {}
        for file_path in files:
            try:
                if file_path.endswith((".pdf", ".docx")):
                    results[file_path] = self.doc_parser.parse(file_path)
                elif file_path.endswith((".xls", ".xlsx")):
                    results[file_path] = self.smeta_parser.parse(file_path)
                elif file_path.endswith(".xml"):
                    results[file_path] = self.xml_parser.parse(file_path)
                else:
                    results[file_path] = {"error": "Unsupported file type"}
            except Exception as e:
                logger.error(f"Ошибка парсинга {file_path}: {e}")
                results[file_path] = {"error": str(e)}

        # ✅ сохраняем в JSON
        save_merged_report(results, output_path="outputs/smetny_inzenyr_report.json")
        return results


def parse_files(file_list: list[str]) -> dict:
    """Функция для быстрого использования без класса"""
    agent = SmetnyInzenyr()
    return agent.parse_documents(file_list)
