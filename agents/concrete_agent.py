"""
Hybrid Concrete Agent:
- Локальный анализ (regex + парсеры)
- Опционально Claude для улучшений
- Сохраняет отчёт через save_merged_report
"""

import re
import logging
import os
import asyncio
from typing import List, Dict, Any

from parsers.doc_parser import DocParser
from parsers.smeta_parser import SmetaParser
from parsers.xml_smeta_parser import XMLSmetaParser
from utils.claude_client import get_claude_client
from outputs.save_report import save_merged_report  # ✅ сохраняем итоговый JSON

logger = logging.getLogger(__name__)


class HybridConcreteAnalysisAgent:
    def __init__(self, use_claude: bool = True, claude_mode: str = "enhancement"):
        """
        Args:
            use_claude: использовать ли Claude API
            claude_mode: "enhancement" | "primary" | "fallback"
        """
        self.use_claude = use_claude
        self.claude_mode = claude_mode
        self.claude_client = get_claude_client() if use_claude else None

        # Инициализация парсеров
        self.doc_parser = DocParser()
        self.smeta_parser = SmetaParser()
        self.xml_parser = XMLSmetaParser()

        # Паттерны поиска марок бетона
        self.concrete_patterns = [
            r'\b(C\d{1,2}/\d{1,2})\b',              
            r'\b(B\d{1,2})\b',                      
            r'(?:beton|betón)\s+([BCM]\d+(?:/\d+)?)',
            r'(?:třída|třída betonu)\s+([BCM]\d+(?:/\d+)?)'
        ]

        # Классы среды и удобоукладываемости
        self.env_classes_regex = r'\b(XO|XC[1-4]|XD[1-3]|XS[1-3]|XF[1-4]|XA[1-3])\b'
        self.workability_regex = r'\b(S[1-5])\b'

        # Контексты применения
        self.context_patterns = {
            "základy": r'základ|foundation',
            "věnce": r'věnec|ring beam',
            "stěny": r'stěna|wall',
            "sloupy": r'sloup|column',
            "deska": r'deska|slab|floor',
            "schodiště": r'schodiště|stair'
        }

    async def analyze_concrete(self, doc_paths: List[str], smeta_path: str) -> Dict[str, Any]:
        """Основной метод анализа"""
        logger.info(f"🚀 Запущен анализ {len(doc_paths)} документов + {smeta_path}")

        # 1. Локальный анализ
        local_analysis = await self._fast_local_analysis(doc_paths, smeta_path)

        # 2. При необходимости включаем Claude
        if self._should_use_claude(local_analysis):
            try:
                all_text = await self._extract_all_text(doc_paths)
                smeta_data = self._parse_smeta(smeta_path)

                enhanced = await self.claude_client.enhance_analysis(local_analysis, all_text, smeta_data)

                result = self._merge_analyses(local_analysis, enhanced, timing={})
                save_merged_report(result)  # ✅ сохраняем отчёт
                return result
            except Exception as e:
                logger.error(f"❌ Claude ошибка: {e}")

        # 3. Если Claude не используется → сохранить локальный анализ
        save_merged_report(local_analysis)
        return local_analysis

    async def _fast_local_analysis(self, doc_paths: List[str], smeta_path: str) -> Dict[str, Any]:
        """Быстрый локальный анализ"""
        all_text = ""
        for path in doc_paths:
            try:
                all_text += self.doc_parser.parse(path) + "\n"
            except Exception as e:
                logger.error(f"Ошибка парсинга {path}: {e}")

        smeta_data = self._parse_smeta(smeta_path)
        concrete_data = {}

        # Поиск упоминаний бетона
        for pattern in self.concrete_patterns:
            for match in re.finditer(pattern, all_text, re.IGNORECASE):
                grade = match.group(1) if match.groups() else match.group(0)
                grade = grade.upper().strip()
                if not grade:
                    continue

                if grade not in concrete_data:
                    concrete_data[grade] = {
                        "environment_classes": set(),
                        "workability_classes": set(),
                        "used_in": set(),
                        "smeta_mentions": []
                    }

                # Ищем классы среды и применения
                snippet = all_text[max(0, match.start()-100): match.end()+100]

                env_classes = set(re.findall(self.env_classes_regex, snippet, re.IGNORECASE))
                concrete_data[grade]["environment_classes"].update(env_classes)

                workability = set(re.findall(self.workability_regex, snippet, re.IGNORECASE))
                concrete_data[grade]["workability_classes"].update(workability)

                for context_name, context_pattern in self.context_patterns.items():
                    if re.search(context_pattern, snippet, re.IGNORECASE):
                        concrete_data[grade]["used_in"].add(context_name)

        # Поиск в смете
        for idx, row in enumerate(smeta_data):
            row_text = " ".join(str(v) for v in row.values()).lower()
            for grade in concrete_data.keys():
                if grade.lower() in row_text:
                    concrete_data[grade]["smeta_mentions"].append({
                        "row": idx+1,
                        "description": row_text[:200]
                    })

        result = [
            {
                "grade": grade,
                "used_in": sorted(data["used_in"]),
                "environment_classes": sorted(data["environment_classes"]),
                "workability_classes": sorted(data["workability_classes"]),
                "smeta_mentions": data["smeta_mentions"]
            }
            for grade, data in concrete_data.items()
        ]

        return {
            "concrete_summary": result,
            "analysis_stats": {
                "documents_processed": len(doc_paths),
                "smeta_rows_analyzed": len(smeta_data),
                "concrete_grades_found": len(result),
                "total_text_length": len(all_text)
            }
        }

    def _parse_smeta(self, smeta_path: str):
        try:
            if smeta_path.endswith(".xml"):
                return self.xml_parser.parse(smeta_path)
            elif smeta_path.endswith((".xls", ".xlsx")):
                return self.smeta_parser.parse(smeta_path)
            return []
        except Exception as e:
            logger.error(f"Ошибка сметы: {e}")
            return []

    async def _extract_all_text(self, doc_paths: List[str]) -> str:
        """Извлечение текста для Claude"""
        all_text = ""
        for path in doc_paths:
            try:
                all_text += self.doc_parser.parse(path)
            except Exception as e:
                logger.error(f"Ошибка извлечения текста {path}: {e}")
        return all_text[:8000]  # ограничение для Claude

    def _should_use_claude(self, local: Dict) -> bool:
        if not self.use_claude or not self.claude_client:
            return False
        stats = local.get("analysis_stats", {})
        return stats.get("concrete_grades_found", 0) < 2  # если мало нашли → зовём Claude

    def _merge_analyses(self, local: Dict, enhanced: Dict, timing: Dict) -> Dict:
        """Безопасное объединение локального и Claude анализа"""
        return {
            "concrete_summary": enhanced.get("claude_concrete_analysis", local.get("concrete_summary", [])),
            "local_analysis": local,
            "claude_analysis": enhanced.get("claude_concrete_analysis", {}),
            "materials_analysis": enhanced.get("claude_materials_analysis", {}),
            "analysis_method": "hybrid_local_claude",
            "timing": timing
        }


# === API функции ===
async def analyze_concrete(doc_paths: List[str], smeta_path: str, use_claude: bool = True, claude_mode: str = "enhancement") -> Dict[str, Any]:
    agent = HybridConcreteAnalysisAgent(use_claude=use_claude, claude_mode=claude_mode)
    return await agent.analyze_concrete(doc_paths, smeta_path)


def analyze_concrete_sync(doc_paths: List[str], smeta_path: str, use_claude: bool = True, claude_mode: str = "enhancement") -> Dict[str, Any]:
    return asyncio.run(analyze_concrete(doc_paths, smeta_path, use_claude, claude_mode))
