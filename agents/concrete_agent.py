"""
Гибридная версия агента: быстрый + точный анализ
Объединяет лучшее из обеих версий
"""
import re
import logging
import os
import asyncio
from typing import List, Dict, Any

# Импорты парсеров и клиента Claude
try:
    from parsers.doc_parser import DocParser
    from parsers.smeta_parser import SmetaParser
    from parsers.xml_smeta_parser import XMLSmetaParser
    from utils.claude_client import get_claude_client
    PARSERS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Import warning: {e}")
    PARSERS_AVAILABLE = False

logger = logging.getLogger(__name__)


class HybridConcreteAnalysisAgent:
    """
    Гибридный агент: сочетает скорость простого анализа с мощью Claude
    """

    def __init__(self, use_claude: bool = True, claude_mode: str = "enhancement"):
        """
        Args:
            use_claude: использовать ли Claude API
            claude_mode: "enhancement" | "primary" | "fallback"
        """
        self.use_claude = use_claude
        self.claude_mode = claude_mode
        self.claude_client = get_claude_client() if use_claude else None

        if not PARSERS_AVAILABLE:
            raise ImportError("Парсеры не доступны")

        self.doc_parser = DocParser()
        self.smeta_parser = SmetaParser()
        self.xml_parser = XMLSmetaParser()

        # Улучшенные паттерны
        self.concrete_patterns = [
            r'\b(C\d{1,2}/\d{1,2})\b',              # C25/30, C30/37
            r'\b(B\d{1,2})\b',                      # B20, B25, B30
            r'(?:beton|betón)\s+([BCM]\d+(?:/\d+)?)', # beton C25/30
            r'(?:třída|třída betonu)\s+([BCM]\d+(?:/\d+)?)'
        ]

        self.env_classes_regex = r'\b(XO|XC[1-4]|XD[1-3]|XS[1-3]|XF[1-4]|XA[1-3])\b'
        self.workability_regex = r'\b(S[1-5])\b'

        self.env_class_descriptions = {
            "XO": "Bez rizika koroze. Pro beton bez výztuže v suchém prostředí.",
            "XC1": "Koroze karbonatací – suché nebo trvale vlhké prostředí.",
            "XC2": "Koroze karbonatací – vlhké, občas suché prostředí.",
            "XC3": "Koroze karbonatací – středně vlhké prostředí.",
            "XC4": "Koroze karbonatací – střídavě vlhké a suché prostředí.",
            "XD1": "Koroze chloridy – středně vlhké prostředí.",
            "XD2": "Koroze chloridy – vlhké, občas suché prostředí.",
            "XD3": "Koroze chloridy – střídavě vlhké a suché prostředí.",
            "XS1": "Mořská sůl ve vzduchu – povrch vystavený solím.",
            "XS2": "Stálé ponoření do mořské vody.",
            "XS3": "Zóny přílivu, odlivu a rozstřiků mořské vody.",
            "XF1": "Zamrzání/rozmrazování – mírně nasákavé, bez posypových solí.",
            "XF2": "Zamrzání/rozmrazování – mírně nasákavé, s posypovými solemi.",
            "XF3": "Zamrzání/rozmrazování – silně nasákavé, bez posypových solí.",
            "XF4": "Zamrzání/rozmrazování – silně nasákavé, s posypovými solemi.",
            "XA1": "Slabě agresivní chemické prostředí.",
            "XA2": "Středně agresivní chemické prostředí.",
            "XA3": "Silně agresivní chemické prostředí."
        }

        self.context_patterns = {
            "základy": r'základ|foundation',
            "věnce": r'věnec|ring beam',
            "piloty": r'pilot[ay]?|pile',
            "stěny": r'příčka|zeď|stěna|wall',
            "sloupy": r'sloup|pilíř|column',
            "průvlaky": r'průvlak|beam',
            "deska": r'deska|slab|floor',
            "schodiště": r'schodiště|stair',
            "střecha": r'střecha|roof',
            "mostní konstrukce": r'most|bridge',
            "spodní stavba": r'spodní stavba|substructure',
            "horní stavba": r'horní stavba|superstructure'
        }

    async def analyze_concrete(self, doc_paths: List[str], smeta_path: str) -> Dict[str, Any]:
        """
        Основной метод анализа
        """
        logger.info(f"🚀 Начало гибридного анализа: {len(doc_paths)} документов")

        start_time = asyncio.get_event_loop().time()
        local_analysis = await self._fast_local_analysis(doc_paths, smeta_path)
        local_time = asyncio.get_event_loop().time() - start_time

        logger.info(f"⚡ Локальный анализ завершен за {local_time:.2f}с")

        if self._should_use_claude(local_analysis):
            try:
                logger.info("🤖 Запуск Claude enhancement")
                claude_start = asyncio.get_event_loop().time()

                all_text = await self._extract_all_text(doc_paths)
                smeta_data = self._parse_smeta(smeta_path)

                enhanced_analysis = await self.claude_client.enhance_analysis(
                    local_analysis, all_text, smeta_data
                )

                claude_time = asyncio.get_event_loop().time() - claude_start
                logger.info(f"🤖 Claude анализ завершен за {claude_time:.2f}с")

                return self._merge_analyses(local_analysis, enhanced_analysis, {
                    "local_time": local_time,
                    "claude_time": claude_time,
                    "total_time": local_time + claude_time
                })

            except Exception as e:
                logger.error(f"❌ Ошибка Claude: {e}")
                local_analysis["claude_error"] = str(e)
                local_analysis["analysis_method"] = "local_fallback"

        local_analysis["analysis_method"] = "local_only"
        local_analysis["timing"] = {"total_time": local_time}
        return local_analysis

    async def _fast_local_analysis(self, doc_paths: List[str], smeta_path: str) -> Dict[str, Any]:
        """Быстрый локальный анализ"""
        all_text = ""
        for doc_path in doc_paths:
            try:
                content = self.doc_parser.parse(doc_path)
                all_text += f"\n\n=== {os.path.basename(doc_path)} ===\n{content}"
            except Exception as e:
                logger.error(f"Ошибка парсинга {doc_path}: {e}")

        all_text_lower = all_text.lower()
        smeta_data = self._parse_smeta(smeta_path)
        concrete_data = {}

        for pattern in self.concrete_patterns:
            for match in re.finditer(pattern, all_text_lower, re.IGNORECASE):
                grade = match.group(1) if match.groups() else match.group(0)
                grade = grade.upper().strip()

                if not grade or len(grade) < 2:
                    continue

                if grade not in concrete_data:
                    concrete_data[grade] = {
                        "environment_classes": set(),
                        "workability_classes": set(),
                        "used_in": set(),
                        "context_snippets": [],
                        "smeta_mentions": []
                    }

                start = max(0, match.start() - 100)
                end = min(len(all_text_lower), match.end() + 100)
                snippet = all_text_lower[start:end]

                env_classes = set(re.findall(self.env_classes_regex, snippet, re.IGNORECASE))
                concrete_data[grade]["environment_classes"].update(env_classes)

                workability = set(re.findall(self.workability_regex, snippet, re.IGNORECASE))
                concrete_data[grade]["workability_classes"].update(workability)

                for context_name, context_pattern in self.context_patterns.items():
                    if re.search(context_pattern, snippet, re.IGNORECASE):
                        concrete_data[grade]["used_in"].add(context_name)
                        concrete_data[grade]["context_snippets"].append({
                            "element": context_name,
                            "snippet": snippet.strip()[:150],
                            "confidence": "high"
                        })

        self._find_concrete_in_smeta(concrete_data, smeta_data)

        result = []
        for grade, data in concrete_data.items():
            result.append({
                "grade": grade,
                "used_in": sorted(list(data["used_in"])),
                "environment_classes": [
                    {
                        "code": cls.upper(),
                        "description": self.env_class_descriptions.get(cls.upper(), "Popis není k dispozici.")
                    }
                    for cls in sorted(data["environment_classes"])
                ],
                "workability_classes": sorted(list(data["workability_classes"])),
                "context_snippets": data["context_snippets"][:5],
                "smeta_mentions": data["smeta_mentions"],
                "mentioned_in_docs": True
            })

        return {
            "concrete_summary": result,
            "analysis_stats": {
                "documents_processed": len(doc_paths),
                "concrete_grades_found": len(result),
                "smeta_rows_analyzed": len(smeta_data) if smeta_data else 0,
                "total_text_length": len(all_text)
            }
        }

    def _find_concrete_in_smeta(self, concrete_data: Dict, smeta_data: List[Dict]):
        """Поиск марок в смете"""
        if not smeta_data:
            return

        for row_idx, row in enumerate(smeta_data):
            row_text = " ".join([
                str(row.get('description', '')),
                str(row.get('material', '')),
                str(row.get('specification', '')),
                str(row.get('name', ''))
            ]).lower()

            for grade in concrete_data.keys():
                if grade.lower() in row_text:
                    concrete_data[grade]["smeta_mentions"].append({
                        "row": row_idx + 1,
                        "description": row_text.strip()[:200],
                        "code": row.get("code", ""),
                        "qty": row.get("qty", 0),
                        "unit": row.get("unit", "")
                    })

    def _should_use_claude(self, local_analysis: Dict) -> bool:
        if not self.claude_client or not self.use_claude:
            return False

        stats = local_analysis.get("analysis_stats", {})
        concrete_count = stats.get("concrete_grades_found", 0)

        if self.claude_mode == "primary":
            return True
        elif self.claude_mode == "enhancement":
            return concrete_count < 3 or stats.get("total_text_length", 0) > 10000
        else:
            return concrete_count == 0

    def _merge_analyses(self, local: Dict, enhanced: Dict, timing: Dict) -> Dict:
        """Объединение локального и Claude анализов (с защитой)"""
        return {
            "concrete_summary": enhanced.get("claude_concrete_analysis", {}).get(
                "claude_analysis",
                local.get("concrete_summary", [])
            ),
            "local_analysis": local,
            "claude_analysis": enhanced.get("claude_concrete_analysis", {}),
            "materials_analysis": enhanced.get("claude_materials_analysis", {}),
            "analysis_method": "hybrid_local_claude",
            "enhanced": True,
            "timing": timing
        }

    async def _extract_all_text(self, doc_paths: List[str]) -> str:
        """Извлечение текста для Claude"""
        all_text = ""
        for doc_path in doc_paths:
            try:
                content = self.doc_parser.parse(doc_path)
                all_text += f"\n\n=== {os.path.basename(doc_path)} ===\n{content}"
            except Exception as e:
                logger.error(f"Ошибка извлечения текста {doc_path}: {e}")
        return all_text[:8000]

    def _parse_smeta(self, smeta_path: str) -> List[Dict]:
        try:
            if smeta_path.endswith('.xml'):
                return self.xml_parser.parse(smeta_path)
            elif smeta_path.endswith(('.xls', '.xlsx')):
                return self.smeta_parser.parse(smeta_path)
            else:
                return []
        except Exception as e:
            logger.error(f"Ошибка парсинга сметы: {e}")
            return []


# === API функции ===
async def analyze_concrete(
    doc_paths: List[str],
    smeta_path: str,
    use_claude: bool = True,
    claude_mode: str = "enhancement"
) -> Dict[str, Any]:
    agent = HybridConcreteAnalysisAgent(use_claude=use_claude, claude_mode=claude_mode)
    return await agent.analyze_concrete(doc_paths, smeta_path)


def analyze_concrete_sync(
    doc_paths: List[str],
    smeta_path: str,
    use_claude: bool = True,
    claude_mode: str = "enhancement"
) -> Dict[str, Any]:
    return asyncio.run(analyze_concrete(doc_paths, smeta_path, use_claude, claude_mode))
