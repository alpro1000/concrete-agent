"""
Hybrid Concrete Agent:
- Быстрый локальный анализ (regex + парсеры)
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
from outputs.save_report import save_merged_report  # ✅ добавлено

logger = logging.getLogger(__name__)


class HybridConcreteAnalysisAgent:
    def __init__(self, use_claude: bool = True, claude_mode: str = "enhancement"):
        self.use_claude = use_claude
        self.claude_mode = claude_mode
        self.claude_client = get_claude_client() if use_claude else None

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

        self.env_classes_regex = r'\b(XO|XC[1-4]|XD[1-3]|XS[1-3]|XF[1-4]|XA[1-3])\b'
        self.workability_regex = r'\b(S[1-5])\b'

        # Классы среды
        self.env_class_descriptions = {
            "XC1": "Suché prostředí",
            "XC2": "Vlhké prostředí",
            "XF4": "Mrazuvzdornost se solemi",
            "XA2": "Chemicky středně agresivní prostředí"
        }

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
        logger.info(f"🚀 Запущен гибридный анализ: {len(doc_paths)} документов")

        # Локальный анализ
        local_analysis = await self._fast_local_analysis(doc_paths, smeta_path)

        # При необходимости включаем Claude
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

        # Только локальный анализ
        save_merged_report(local_analysis)  # ✅ сохраняем отчёт
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
        results = []

        for pattern in self.concrete_patterns:
            for match in re.finditer(pattern, all_text, re.IGNORECASE):
                grade = match.group(1) if match.groups() else match.group(0)
                results.append({"grade": grade})

        return {"concrete_summary": results, "analysis_stats": {"docs": len(doc_paths)}}

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
        all_text = ""
        for path in doc_paths:
            try:
                all_text += self.doc_parser.parse(path)
            except Exception as e:
                logger.error(f"Ошибка извлечения текста: {e}")
        return all_text[:8000]

    def _should_use_claude(self, local: Dict) -> bool:
        if not self.use_claude or not self.claude_client:
            return False
        return local.get("analysis_stats", {}).get("docs", 0) > 0

    def _merge_analyses(self, local: Dict, enhanced: Dict, timing: Dict) -> Dict:
        return {
            "concrete_summary": enhanced.get("claude_concrete_analysis", local.get("concrete_summary", [])),
            "local": local,
            "claude": enhanced,
            "timing": timing
        }


# === API функции ===
async def analyze_concrete(doc_paths: List[str], smeta_path: str, use_claude: bool = True, claude_mode: str = "enhancement") -> Dict[str, Any]:
    agent = HybridConcreteAnalysisAgent(use_claude=use_claude, claude_mode=claude_mode)
    return await agent.analyze_concrete(doc_paths, smeta_path)


def analyze_concrete_sync(doc_paths: List[str], smeta_path: str, use_claude: bool = True, claude_mode: str = "enhancement") -> Dict[str, Any]:
    return asyncio.run(analyze_concrete(doc_paths, smeta_path, use_claude, claude_mode))
