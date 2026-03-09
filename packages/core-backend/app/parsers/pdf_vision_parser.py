"""
PDF Vision Parser — Claude Vision для сканов и чертежей.
Не требует torch/GPU. Работает на Render Free (512MB).

Стратегия:
1. PyMuPDF конвертирует каждую страницу PDF → PNG (в памяти, без диска)
2. Claude Vision извлекает позиции / текст / размеры
3. Возвращает структуру совместимую с PDFParser
"""
import base64
import json
import re
from pathlib import Path
from typing import Any

import anthropic
import fitz  # PyMuPDF — уже установлен, лёгкий (~30MB)
from loguru import logger


PROMPT_SMETA_VISION = """
Это страница строительной сметы (скан или PDF-изображение).
Язык документа: чешский или русский.

Извлеки ВСЕ строки-позиции и верни ТОЛЬКО валидный JSON без пояснений:
{
  "positions": [
    {
      "position_number": "1.1",
      "description": "Название работы или материала",
      "unit": "m2",
      "quantity": 45.5,
      "unit_price": 320.0,
      "total_price": 14560.0
    }
  ],
  "raw_text": "весь текст страницы одной строкой"
}

Правила:
- Если поле отсутствует — ставь null
- Числа без пробелов и валюты (только число)
- Десятичный разделитель: точка
- Пропускай строки-заголовки и итоговые строки
"""

PROMPT_DRAWING_VISION = """
Это страница строительного чертежа.
Извлеки ВСЕ размеры, обозначения и текстовые элементы.
Верни ТОЛЬКО валидный JSON без пояснений:
{
  "dimensions": [
    {"label": "ширина", "value": 5.4, "unit": "m", "location": "стена А"}
  ],
  "annotations": ["текстовые обозначения на чертеже"],
  "title_block": {
    "object_name": "",
    "drawing_number": "",
    "scale": "",
    "date": ""
  },
  "raw_text": "весь текст одной строкой"
}
"""

PROMPT_TZ_VISION = """
Это страница технического задания на строительные работы.
Извлеки ключевую информацию и верни ТОЛЬКО валидный JSON:
{
  "requirements": ["список требований"],
  "materials": ["материалы"],
  "works": ["виды работ"],
  "parameters": {"ключ": "значение"},
  "raw_text": "весь текст страницы"
}
"""

_DOC_TYPE_PROMPTS = {
    "smeta": PROMPT_SMETA_VISION,
    "drawing": PROMPT_DRAWING_VISION,
    "tz": PROMPT_TZ_VISION,
}


class PdfVisionParser:
    """
    Парсер сканов PDF через Claude Vision (Anthropic).
    Без torch. Без GPU. Работает на 512MB RAM.

    Использовать когда:
    - PDFParser (pdfplumber) вернул 0 позиций
    - doc_type == 'drawing' (всегда)
    - Файл явно является сканом (нет текстового слоя)
    """

    DPI_SCALE = 2.0          # 2x масштаб = хорошее качество OCR
    MAX_PAGES = 50           # Ограничение для экономии API
    MAX_IMAGE_SIZE_MB = 4.5  # Claude Vision лимит ~5MB/изображение

    def __init__(self, anthropic_client: anthropic.Anthropic | None = None):
        self._client = anthropic_client or anthropic.Anthropic()

    def parse(
        self,
        file_path: Path,
        doc_type: str = "smeta",
        model: str = "claude-3-5-sonnet-20241022",
    ) -> dict[str, Any]:
        """
        Парсит PDF через Vision API.

        Args:
            file_path: Путь к PDF файлу
            doc_type:  'smeta' | 'drawing' | 'tz'
            model:     Claude модель

        Returns:
            Структура совместимая с PDFParser:
            {
                'document_info': {...},
                'positions': [...],       # для смет
                'pages_data': [...],      # сырые данные по страницам
                'diagnostics': {...}
            }
        """
        logger.info(f"PdfVisionParser: {file_path.name}, doc_type={doc_type}")

        prompt = _DOC_TYPE_PROMPTS.get(doc_type, PROMPT_SMETA_VISION)
        all_positions: list = []
        pages_data: list = []
        pages_processed = 0
        pages_failed = 0

        try:
            doc = fitz.open(str(file_path))
            total_pages = len(doc)
            pages_to_process = min(total_pages, self.MAX_PAGES)

            logger.info(f"Total pages: {total_pages}, processing: {pages_to_process}")

            for page_num in range(pages_to_process):
                page = doc[page_num]
                page_result = self._process_page(
                    page=page,
                    page_num=page_num + 1,
                    prompt=prompt,
                    doc_type=doc_type,
                    model=model,
                )

                if page_result is None:
                    pages_failed += 1
                    continue

                pages_data.append(page_result)
                pages_processed += 1

                if doc_type == "smeta":
                    page_positions = page_result.get("positions", [])
                    all_positions.extend(page_positions)
                    logger.debug(
                        f"Page {page_num + 1}: +{len(page_positions)} positions"
                    )

            doc.close()

        except Exception as e:
            logger.error(f"PdfVisionParser failed: {file_path.name}: {e}", exc_info=True)
            return self._error_result(file_path, str(e))

        logger.info(
            f"PdfVisionParser done: {file_path.name}, "
            f"positions={len(all_positions)}, "
            f"pages_ok={pages_processed}, pages_failed={pages_failed}"
        )

        return {
            "document_info": {
                "filename": file_path.name,
                "format": "pdf_vision",
                "doc_type": doc_type,
                "total_pages": total_pages,
                "pages_processed": pages_processed,
                "model_used": model,
            },
            "positions": all_positions,
            "pages_data": pages_data,
            "diagnostics": {
                "raw_total": len(all_positions),
                "normalized_total": len(all_positions),
                "skipped_total": 0,
                "pages_processed": pages_processed,
                "pages_failed": pages_failed,
                "source": "claude_vision",
            },
        }

    def _process_page(
        self,
        page: fitz.Page,
        page_num: int,
        prompt: str,
        doc_type: str,
        model: str,
    ) -> dict | None:
        """Конвертирует одну страницу в PNG и отправляет в Claude Vision."""
        try:
            # Рендерим страницу в растр (в памяти)
            matrix = fitz.Matrix(self.DPI_SCALE, self.DPI_SCALE)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img_bytes = pix.tobytes("png")

            # Проверяем размер
            img_size_mb = len(img_bytes) / (1024 * 1024)
            if img_size_mb > self.MAX_IMAGE_SIZE_MB:
                # Уменьшаем масштаб если изображение слишком большое
                matrix = fitz.Matrix(1.5, 1.5)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                img_bytes = pix.tobytes("png")
                logger.warning(
                    f"Page {page_num}: image too large ({img_size_mb:.1f}MB), "
                    f"reduced to 1.5x scale"
                )

            img_b64 = base64.standard_b64encode(img_bytes).decode("utf-8")

            response = self._client.messages.create(
                model=model,
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": img_b64,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )

            raw_response = response.content[0].text
            parsed = self._parse_json_response(raw_response)
            parsed["_page_num"] = page_num
            return parsed

        except anthropic.APIError as e:
            logger.error(f"Claude API error on page {page_num}: {e}")
            return None
        except Exception as e:
            logger.error(f"Page {page_num} processing failed: {e}", exc_info=True)
            return None

    @staticmethod
    def _parse_json_response(raw: str) -> dict:
        """Извлекает JSON из ответа Claude, даже если есть лишний текст."""
        # Ищем JSON блок в ```json ... ``` или просто {...}
        json_match = re.search(r"```json\s*([\s\S]+?)\s*```", raw)
        if json_match:
            raw = json_match.group(1)
        else:
            # Берём от первой { до последней }
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1:
                raw = raw[start : end + 1]

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Failed to parse Claude JSON response, returning raw text")
            return {"raw_text": raw, "positions": []}

    @staticmethod
    def _error_result(file_path: Path, error: str) -> dict:
        return {
            "document_info": {
                "filename": file_path.name,
                "format": "pdf_vision",
                "error": error,
            },
            "positions": [],
            "pages_data": [],
            "diagnostics": {
                "raw_total": 0,
                "normalized_total": 0,
                "skipped_total": 0,
                "pages_processed": 0,
                "pages_failed": 0,
                "source": "claude_vision",
            },
        }

    @staticmethod
    def is_scanned_pdf(file_path: Path, sample_pages: int = 3) -> bool:
        """
        Определяет является ли PDF сканом (нет текстового слоя).
        Используется SmartPdfParser для выбора стратегии.
        """
        try:
            doc = fitz.open(str(file_path))
            pages_to_check = min(sample_pages, len(doc))
            total_chars = 0

            for i in range(pages_to_check):
                text = doc[i].get_text()
                total_chars += len(text.strip())

            doc.close()
            avg_chars_per_page = total_chars / max(pages_to_check, 1)

            # Меньше 100 символов на страницу → считаем сканом
            is_scan = avg_chars_per_page < 100
            logger.debug(
                f"{file_path.name}: avg_chars/page={avg_chars_per_page:.0f}, "
                f"is_scan={is_scan}"
            )
            return is_scan

        except Exception as e:
            logger.warning(f"Could not detect scan status for {file_path.name}: {e}")
            return False
