"""
Агент-сметчик (MVP)
Задача: парсинг проектных документов (PDF, DOCX, Excel, XML)
и подготовка данных для анализа ресурсов.
"""
import logging
from parsers.doc_parser import DocParser
from parsers.smeta_parser import SmetaParser
from parsers.xml_smeta_parser import parse_xml_smeta
from services.doc_parser import parse_document  # New unified parser
from outputs.save_report import save_merged_report  # ✅ добавлено

logger = logging.getLogger(__name__)

class SmetnyInzenyr:
    def __init__(self):
        self.doc_parser = DocParser()
        self.smeta_parser = SmetaParser()
        # Note: xml_smeta_parser is a function, not a class

    def parse_documents(self, files: list[str]) -> dict:
        """Использует унифицированный парсер с поддержкой MinerU"""
        results = {}
        for file_path in files:
            try:
                # Use unified parser with MinerU integration
                result = parse_document(file_path)
                
                if result["success"]:
                    # Process the results from unified parser
                    combined_content = {}
                    parsers_used = []
                    
                    for parse_result in result["results"]:
                        parsers_used.append(parse_result.parser_used)
                        content = parse_result.content
                        
                        if isinstance(content, str):
                            combined_content["text"] = combined_content.get("text", "") + content + "\n"
                        elif isinstance(content, dict):
                            combined_content.update(content)
                        elif isinstance(content, list):
                            combined_content["items"] = combined_content.get("items", []) + content
                        else:
                            combined_content["raw"] = str(content)
                    
                    combined_content["metadata"] = {
                        "parsers_used": parsers_used,
                        "files_processed": len(result["results"]),
                        "source_type": result.get("source_type", "single_file")
                    }
                    
                    results[file_path] = combined_content
                    
                else:
                    logger.error(f"Ошибка парсинга {file_path}: {result.get('error', 'Unknown error')}")
                    results[file_path] = {"error": result.get("error", "Unknown error")}
                    
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
