"""
Гибридный агент для анализа бетона (локальный + Claude)
"""
import os
import re
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from parsers.doc_parser import DocParser
from parsers.smeta_parser import SmetaParser
from utils.claude_client import get_claude_client
from config.settings import settings
from outputs.save_report import save_merged_report

logger = logging.getLogger(__name__)


class ConcreteAgentHybrid:
    """Гибридный агент для анализа бетона"""

    def __init__(self, prompt_path: str = "prompts/concrete_extractor_prompt.json"):
        self.doc_parser = DocParser()
        self.smeta_parser = SmetaParser()
        self.claude_client = get_claude_client() if settings.is_claude_enabled() else None

        # Загружаем промт
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.prompt = json.load(f)
            logger.info(f"✅ Загружен промт: {prompt_path}")
        except FileNotFoundError:
            logger.warning(f"⚠️ Промт {prompt_path} не найден, используем дефолтные правила")
            self.prompt = {}

        # Локальные паттерны
        self.concrete_patterns = [
            r'\b[BC]\s*\d{1,2}(?:/\d{1,2})?\s*(?:XC|XF|XD|XS|XA|XO)\d?\b',
            r'\b[BC]\s*\d{1,2}(?:/\d{1,2})?\b',
            r'\bbeton\s+[BC]\s*\d{1,2}(?:/\d{1,2})?\b',
        ]

        self.usage_patterns = {
            'základy': r'\bzáklady?\b|\bzákladové?\b|\bfundament\b',
            'věnce': r'\bvěnce?\b|\bvěnec\b|\bkronšteiny?\b',
            'stropy': r'\bstropy?\b|\bstrop\b|\bdeck\b',
            'stěny': r'\bstěny?\b|\bstěna\b|\bwall\b',
            'sloupy': r'\bsloup\w*\b|\bpillar\b|\bcolumn\b',
            'schodiště': r'\bschodiště\b|\bstairs\b|\bsteps\b',
        }

    def _local_concrete_analysis(self, text: str) -> Dict[str, Any]:
        """Локальный regex-анализ бетона"""
        concrete_grades = []
        for pattern in self.concrete_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                grade = match.strip()
                usage = []
                for usage_type, usage_pattern in self.usage_patterns.items():
                    if re.search(usage_pattern, text, re.IGNORECASE):
                        usage.append(usage_type)

                concrete_grades.append({
                    "grade": grade,
                    "used_in": usage,
                    "method": "regex"
                })

        # Убираем дубликаты
        unique = {}
        for g in concrete_grades:
            if g["grade"] not in unique:
                unique[g["grade"]] = g
            else:
                unique[g["grade"]]["used_in"] = list(set(unique[g["grade"]]["used_in"]) | set(g["used_in"]))

        return {
            "concrete_summary": list(unique.values()),
            "analysis_method": "local_regex",
            "success": True
        }

    async def _claude_concrete_analysis(self, text: str, smeta_data: List[Dict]) -> Dict[str, Any]:
        """Анализ с использованием Claude и промта"""
        if not self.claude_client:
            return {"success": False, "error": "Claude client not available"}

        try:
            result = await self.claude_client.analyze_concrete_with_claude(text, smeta_data, self.prompt)
            claude_analysis = result.get("claude_analysis", {})
            return {
                "concrete_summary": claude_analysis.get("concrete_grades", []),
                "analysis_method": "claude",
                "tokens_used": result.get("tokens_used", 0),
                "success": True
            }
        except Exception as e:
            logger.error(f"Ошибка Claude анализа: {e}")
            return {"success": False, "error": str(e)}

    def _merge_analyses(self, local_result: Dict, claude_result: Dict) -> Dict[str, Any]:
        """Слияние локального и Claude анализа"""
        if not claude_result.get("success"):
            return local_result

        local = {g["grade"]: g for g in local_result.get("concrete_summary", [])}
        claude = {g["grade"]: g for g in claude_result.get("concrete_summary", [])}

        merged = {}
        for grade, info in claude.items():
            merged[grade] = {**info, "method": "claude", "local_confirmation": grade in local}
        for grade, info in local.items():
            if grade not in merged:
                merged[grade] = {**info, "method": "local_only", "claude_confirmation": False}

        return {
            "concrete_summary": list(merged.values()),
            "analysis_method": "hybrid_local_claude",
            "local_analysis": local_result,
            "claude_analysis": claude_result,
            "success": True,
            "tokens_used": claude_result.get("tokens_used", 0)
        }

    async def analyze(self, doc_paths: List[str], smeta_path: Optional[str] = None,
                      use_claude: bool = True, claude_mode: str = "enhancement") -> Dict[str, Any]:
        """Главная функция анализа бетона"""
        logger.info(f"🏗️ Анализ бетона (режим: {claude_mode})")

        # Документы
        all_text = ""
        for path in doc_paths:
            try:
                text = self.doc_parser.parse(path)
                all_text += f"\n{text}"
                logger.info(f"📄 {Path(path).name} обработан")
            except Exception as e:
                logger.error(f"❌ Ошибка {path}: {e}")

        if not all_text.strip():
            return {"success": False, "error": "Документы пустые"}

        # Смета
        smeta_data = []
        if smeta_path:
            try:
                smeta_data = self.smeta_parser.parse(smeta_path).get("items", [])
                logger.info(f"📊 Смета: {len(smeta_data)} позиций")
            except Exception as e:
                logger.error(f"❌ Ошибка сметы: {e}")

        # Стратегия
        if claude_mode == "primary" and use_claude:
            c = await self._claude_concrete_analysis(all_text, smeta_data)
            return c if c.get("success") else self._local_concrete_analysis(all_text)

        elif claude_mode == "enhancement" and use_claude:
            l = self._local_concrete_analysis(all_text)
            c = await self._claude_concrete_analysis(all_text, smeta_data)
            return self._merge_analyses(l, c)

        else:
            return self._local_concrete_analysis(all_text)


# === Глобальный агент и API-функция ===
_hybrid_agent: Optional[ConcreteAgentHybrid] = None

def get_hybrid_agent() -> ConcreteAgentHybrid:
    global _hybrid_agent
    if _hybrid_agent is None:
        _hybrid_agent = ConcreteAgentHybrid()
    return _hybrid_agent

async def analyze_concrete(doc_paths: List[str], smeta_path: Optional[str] = None,
                           use_claude: bool = True, claude_mode: str = "enhancement") -> Dict[str, Any]:
    agent = get_hybrid_agent()
    result = await agent.analyze(doc_paths, smeta_path, use_claude, claude_mode)
    try:
        save_merged_report(result, "outputs/concrete_analysis_report.json")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось сохранить отчет: {e}")
    return result
