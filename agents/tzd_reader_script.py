#!/usr/bin/env python3
"""
Technical Assignment Reader (TZD_READER)
Агент для анализа технических заданий с помощью AI моделей.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

# Импорты для обработки файлов
import pdfplumber
from docx import Document

# AI клиенты
import openai
from anthropic import Anthropic

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FileProcessor:
    """Обработчик файлов различных форматов"""
    
    @staticmethod
    def read_pdf(file_path: str) -> str:
        """Извлекает текст из PDF файла"""
        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            logger.error(f"Ошибка чтения PDF {file_path}: {e}")
        return text

    @staticmethod
    def read_docx(file_path: str) -> str:
        """Извлекает текст из DOCX файла"""
        text = ""
        try:
            doc = Document(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            logger.error(f"Ошибка чтения DOCX {file_path}: {e}")
        return text

    @staticmethod
    def read_txt(file_path: str) -> str:
        """Читает текстовый файл"""
        text = ""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='cp1251') as f:
                    text = f.read()
            except Exception as e:
                logger.error(f"Ошибка чтения TXT {file_path}: {e}")
        except Exception as e:
            logger.error(f"Ошибка чтения TXT {file_path}: {e}")
        return text

    def process_files(self, file_paths: List[str]) -> str:
        """Обрабатывает список файлов и объединяет текст"""
        combined_text = ""
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                logger.warning(f"Файл не найден: {file_path}")
                continue
                
            file_ext = Path(file_path).suffix.lower()
            logger.info(f"Обработка файла: {file_path}")
            
            if file_ext == '.pdf':
                text = self.read_pdf(file_path)
            elif file_ext == '.docx':
                text = self.read_docx(file_path)
            elif file_ext == '.txt':
                text = self.read_txt(file_path)
            else:
                logger.warning(f"Неподдерживаемый формат файла: {file_path}")
                continue
            
            if text.strip():
                combined_text += f"\n--- Файл: {Path(file_path).name} ---\n"
                combined_text += text + "\n"
            else:
                logger.warning(f"Не удалось извлечь текст из файла: {file_path}")
        
        return combined_text


class AIAnalyzer:
    """Анализатор текста с помощью AI моделей"""
    
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        
        # Инициализация OpenAI
        if os.getenv('OPENAI_API_KEY'):
            openai.api_key = os.getenv('OPENAI_API_KEY')
            self.openai_client = openai
        
        # Инициализация Anthropic
        if os.getenv('ANTHROPIC_API_KEY'):
            self.anthropic_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    def get_analysis_prompt(self) -> str:
        """Возвращает промпт для анализа технического задания"""
        return """
Проанализируй техническое задание и верни результат ТОЛЬКО в формате JSON без дополнительных комментариев.

JSON должен содержать следующие поля:
- "project_name": название/идентификатор проекта (строка)
- "project_scope": краткое описание и объём работ (строка)
- "materials": список упомянутых материалов (массив строк)
- "concrete_requirements": марки бетона и условия применения (массив строк)
- "norms": упомянутые нормативные документы (массив строк)
- "functional_requirements": ключевые функциональные требования (массив строк)
- "risks_and_constraints": риски и ограничения (массив строк)

Если информация не найдена, используй пустую строку для строковых полей или пустой массив для массивов.

Текст технического задания:
"""

    def analyze_with_gpt(self, text: str) -> Dict[str, Any]:
        """Анализ текста с помощью OpenAI GPT"""
        if not self.openai_client:
            raise ValueError("OpenAI API key не настроен. Установите переменную OPENAI_API_KEY")
        
        try:
            prompt = self.get_analysis_prompt() + text
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Ты эксперт по анализу технических заданий в строительстве. Отвечай только в формате JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Попытка извлечь JSON из ответа
            if "```json" in result_text:
                start = result_text.find("```json") + 7
                end = result_text.find("```", start)
                result_text = result_text[start:end].strip()
            elif result_text.startswith("```") and result_text.endswith("```"):
                result_text = result_text[3:-3].strip()
            
            return json.loads(result_text)
            
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON от GPT: {e}")
            return self._get_empty_result()
        except Exception as e:
            logger.error(f"Ошибка анализа с GPT: {e}")
            return self._get_empty_result()

    def analyze_with_claude(self, text: str) -> Dict[str, Any]:
        """Анализ текста с помощью Anthropic Claude"""
        if not self.anthropic_client:
            raise ValueError("Anthropic API key не настроен. Установите переменную ANTHROPIC_API_KEY")
        
        try:
            prompt = self.get_analysis_prompt() + text
            
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            result_text = response.content[0].text.strip()
            
            # Попытка извлечь JSON из ответа
            if "```json" in result_text:
                start = result_text.find("```json") + 7
                end = result_text.find("```", start)
                result_text = result_text[start:end].strip()
            elif result_text.startswith("```") and result_text.endswith("```"):
                result_text = result_text[3:-3].strip()
            
            return json.loads(result_text)
            
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON от Claude: {e}")
            return self._get_empty_result()
        except Exception as e:
            logger.error(f"Ошибка анализа с Claude: {e}")
            return self._get_empty_result()

    def _get_empty_result(self) -> Dict[str, Any]:
        """Возвращает пустой результат при ошибках"""
        return {
            "project_name": "",
            "project_scope": "",
            "materials": [],
            "concrete_requirements": [],
            "norms": [],
            "functional_requirements": [],
            "risks_and_constraints": []
        }


def tzd_reader(files: List[str], engine: str = "gpt") -> Dict[str, Any]:
    """
    Основная функция для анализа технических заданий
    
    Args:
        files: Список путей к файлам
        engine: Используемый AI движок ("gpt" или "claude")
    
    Returns:
        Словарь с результатами анализа
    """
    # Обработка файлов
    processor = FileProcessor()
    combined_text = processor.process_files(files)
    
    if not combined_text.strip():
        logger.error("Не удалось извлечь текст из файлов")
        return AIAnalyzer()._get_empty_result()
    
    # Анализ с помощью AI
    analyzer = AIAnalyzer()
    
    if engine.lower() == "gpt":
        result = analyzer.analyze_with_gpt(combined_text)
    elif engine.lower() == "claude":
        result = analyzer.analyze_with_claude(combined_text)
    else:
        raise ValueError(f"Неподдерживаемый AI движок: {engine}")
    
    return result


def main():
    """Основная функция CLI"""
    parser = argparse.ArgumentParser(description="Technical Assignment Reader (TZD_READER)")
    parser.add_argument("--files", nargs="+", required=True, 
                       help="Список файлов для анализа")
    parser.add_argument("--engine", choices=["gpt", "claude"], default="gpt",
                       help="AI движок для анализа (по умолчанию: gpt)")
    
    args = parser.parse_args()
    
    try:
        result = tzd_reader(args.files, args.engine)
        
        # Вывод результата в консоль
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except Exception as e:
        logger.error(f"Ошибка выполнения: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
