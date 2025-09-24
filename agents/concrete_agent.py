diff --git a/agents/concrete_agent.py b/agents/concrete_agent.py
index 70db43f1aa8fff790eeb77c98f509427aa6e1141..f31b4f2a87fd2396a24b34667af7452ef02c3100 100644
--- a/agents/concrete_agent.py
+++ b/agents/concrete_agent.py
@@ -1,302 +1,810 @@
-"""
-Улучшенный ConcreteAgentHybrid — агент для комплексного анализа бетонов.
-"""
-import re
-import os
+"""ConcreteAgentHybrid — гибридный агент для комплексного анализа бетонов."""
+
+from __future__ import annotations
+
 import json
 import logging
+import os
+import re
+import time
+from dataclasses import asdict, dataclass
 from pathlib import Path
-from typing import Dict, List, Any, Optional, Tuple
-from dataclasses import dataclass
+from typing import Any, Dict, List, Optional, Set, Tuple
 
 from parsers.doc_parser import DocParser
 from parsers.smeta_parser import SmetaParser
 from utils.claude_client import get_claude_client
 from config.settings import settings
 from outputs.save_report import save_merged_report
 
 logger = logging.getLogger(__name__)
 
+
+# ============================================================================
+# 📦 Структуры данных
+# ============================================================================
+
+
 @dataclass
 class ConcreteMatch:
-    """Структура для найденной марки бетона"""
+    """Информация о найденной марке бетона."""
+
     grade: str
     context: str
     location: str
     confidence: float
     method: str
     coordinates: Optional[Tuple[int, int, int, int]] = None
+    structural_element: Optional[str] = None
+    exposure_class: Optional[str] = None
+    position: Optional[Dict[str, int]] = None
 
-@dataclass 
-class StructuralElement:
-    """Структура для конструктивного элемента"""
-    name: str
-    concrete_grade: Optional[str]
-    location: str
-    context: str
 
-class ConcreteAgentHybrid:
-    def __init__(self, knowledge_base_path="knowledge_base/complete-concrete-knowledge-base.json"):
-        # Загружаем базу знаний
-        try:
-            with open(knowledge_base_path, "r", encoding="utf-8") as f:
-                self.knowledge_base = json.load(f)
-            logger.info("📚 Knowledge-base загружен успешно")
-        except Exception as e:
-            logger.warning(f"⚠️ Не удалось загрузить knowledge-base: {e}")
-            self.knowledge_base = self._create_default_kb()
+@dataclass
+class AnalysisResult:
+    """Результат локального анализа."""
 
-        self.doc_parser = DocParser()
-        self.smeta_parser = SmetaParser()
-        self.claude_client = get_claude_client() if settings.is_claude_enabled() else None
+    success: bool
+    total_matches: int
+    analysis_method: str
+    processing_time: float
+    concrete_summary: List[Dict[str, Any]]
+    structural_elements: List[Dict[str, Any]]
+    compliance_issues: List[str]
+    recommendations: List[str]
+    confidence_score: float
 
-        # Расширенные паттерны для поиска марок бетона
-        self.concrete_patterns = [
-            r'\bC\d{1,2}/\d{1,2}(?:\s*[-–]\s*[XO][CDFASM]?\d*(?:\s*,\s*[XO][CDFASM]?\d*)*)*\b',
-            r'\b[BC]\s*\d{1,2}(?:/\d{1,2})?\b',
-            r'\bLC\s*\d{1,2}/\d{1,2}\b',
-            r'(?i)(?:beton[uá]?\s+)?(?:tříd[ayě]\s+)?(\d{2}/\d{2}|\d{2,3})\b',
-            r'(?i)(?:betony?|betonové[j]?)\s+(?:tříd[yě]\s+)?([BC]?\d{1,2}(?:/\d{1,2})?)',
-            r'\b(?:vysokopevnostn[íý]|lehk[ýá]|těžk[ýá])\s+beton\s+([BC]?\d{1,2}(?:/\d{1,2})?)\b',
-        ]
 
-        # Конструктивные элементы (чешские термины)
+# ============================================================================
+# 🧠 Чешский языковой процессор и валидаторы
+# ============================================================================
+
+
+class CzechLanguageProcessor:
+    """Обрабатывает чешские термины, связанные с бетоном."""
+
+    def __init__(self) -> None:
+        self.concrete_terms = {
+            "beton": [
+                "beton",
+                "betonu",
+                "betony",
+                "betonů",
+                "betonem",
+                "betonech",
+                "betonová",
+                "betonové",
+                "betonový",
+                "betonovou",
+                "betonových",
+                "betonovým",
+                "betonami",
+                "betonářský",
+                "betonářské",
+            ],
+            "třída": [
+                "třída",
+                "třídy",
+                "třídě",
+                "třídu",
+                "třídou",
+                "třídách",
+                "třídami",
+                "tříd",
+                "třídám",
+            ],
+            "stupeň": [
+                "stupeň",
+                "stupně",
+                "stupni",
+                "stupněm",
+                "stupních",
+                "stupňů",
+                "stupňům",
+            ],
+            "pevnost": [
+                "pevnost",
+                "pevnosti",
+                "pevností",
+                "pevnostem",
+                "pevnostech",
+                "pevnostní",
+                "pevnostním",
+                "pevnostních",
+            ],
+            "konstrukce": [
+                "konstrukce",
+                "konstrukcí",
+                "konstrukcím",
+                "konstrukcemi",
+                "konstrukcích",
+                "konstrukční",
+                "konstrukčním",
+            ],
+            "cement": [
+                "cement",
+                "cementu",
+                "cementy",
+                "cementů",
+                "cementem",
+                "cementech",
+                "cementový",
+                "cementové",
+            ],
+            "betonáž": [
+                "betonáž",
+                "betonáže",
+                "betonáži",
+                "betonáží",
+                "betonování",
+                "betonovat",
+            ],
+            "směs": [
+                "směs",
+                "směsi",
+                "směsí",
+                "směsem",
+                "směsích",
+                "směsový",
+                "směsové",
+            ],
+        }
+
         self.structural_elements = {
-            'OPĚRA': {'en': 'abutment', 'applications': ['XC4', 'XD1', 'XF2']},
-            'PILÍŘ': {'en': 'pier', 'applications': ['XC4', 'XD3', 'XF4']},
-            'ŘÍMSA': {'en': 'cornice', 'applications': ['XC4', 'XD3', 'XF4']},
-            'MOSTOVKA': {'en': 'deck', 'applications': ['XC4', 'XD3', 'XF4']},
-            'ZÁKLAD': {'en': 'foundation', 'applications': ['XC1', 'XC2', 'XA1']},
-            'VOZOVKA': {'en': 'roadway', 'applications': ['XF2', 'XF4', 'XD1']},
-            'GARÁŽ': {'en': 'garage', 'applications': ['XD1']},
-            'STĚNA': {'en': 'wall', 'applications': ['XC1', 'XC3', 'XC4']},
-            'SLOUP': {'en': 'column', 'applications': ['XC1', 'XC3']},
-            'SCHODIŠTĚ': {'en': 'stairs', 'applications': ['XC1', 'XC3']},
-            'PODKLADNÍ': {'en': 'subgrade', 'applications': ['X0', 'XC1']},
-            'NOSNÁ': {'en': 'load-bearing', 'applications': ['XC1', 'XC3']},
-            'VĚNEC': {'en': 'tie-beam', 'applications': ['XC2', 'XF1']},
-            'DESKA': {'en': 'slab', 'applications': ['XC1', 'XC2']},
-            'PREFABRIKÁT': {'en': 'precast', 'applications': ['XC1', 'XC3']},
-            'MONOLITICKÝ': {'en': 'monolithic', 'applications': ['XC1', 'XC2']},
+            "základ": ["základ", "základy", "základů", "základem", "základní", "základová"],
+            "pilíř": ["pilíř", "pilíře", "pilířů", "pilířem", "pilíři"],
+            "sloup": ["sloup", "sloupy", "sloupů", "sloupem", "sloupu"],
+            "stěna": ["stěna", "stěny", "stěn", "stěnou", "stěně"],
+            "deska": ["deska", "desky", "desek", "deskou", "desce"],
+            "nosník": ["nosník", "nosníky", "nosníků", "nosníkem", "nosníku"],
+            "věnec": ["věnec", "věnce", "věnců", "věncem", "věnci"],
+            "schodiště": ["schodiště", "schodišť", "schodištěm", "schodišti"],
+            "mostovka": ["mostovka", "mostovky", "mostovkou", "mostovce"],
+            "vozovka": ["vozovka", "vozovky", "vozovkou", "vozovce"],
+            "garáž": ["garáž", "garáže", "garáží", "garážou", "garážích"],
+            "říms": ["římsa", "římsu", "římsy", "římsou", "římsách"],
         }
 
-        # Коды смет и их соответствия
-        self.smeta_codes = {
-            '801': 'Prostý beton',
-            '802': 'Železobeton monolitický',
-            '803': 'Železobeton prefabrikovaný',
-            '811': 'Betony speciální',
-            '271': 'Konstrukce betonové a železobetonové',
-            'HSV': 'Hlavní stavební výroba',
-            'PSV': 'Přidružená stavební výroba',
+        self.exclusion_terms = {
+            "admin": ["stránka", "strana", "str.", "page", "kapitola", "oddíl", "část", "section"],
+            "codes": ["kód", "číslo", "number", "id", "identifikátor", "označení"],
+            "companies": ["firma", "společnost", "company", "spol.", "s.r.o.", "a.s."],
+            "dates": ["datum", "date", "rok", "year", "měsíc", "month", "den", "day"],
+            "money": ["cena", "price", "cost", "kč", "koruna", "euro", "eur"],
+            "contacts": ["telefon", "tel", "phone", "email", "adresa", "address"],
         }
 
-    def _create_default_kb(self) -> Dict:
-        """Создает минимальную базу знаний по умолчанию"""
+    def count_concrete_terms(self, text: str) -> int:
+        text_lower = text.lower()
+        return sum(any(term in text_lower for term in terms) for terms in self.concrete_terms.values())
+
+    def identify_structural_element(self, text: str) -> Optional[str]:
+        text_lower = text.lower()
+        for element, variants in self.structural_elements.items():
+            if any(variant in text_lower for variant in variants):
+                return element.upper()
+        return None
+
+    def count_exclusion_terms(self, text: str) -> int:
+        text_lower = text.lower()
+        return sum(sum(1 for term in terms if term in text_lower) for terms in self.exclusion_terms.values())
+
+    def is_valid_czech_context(self, text: str, threshold: int = 1) -> bool:
+        concrete_count = self.count_concrete_terms(text)
+        exclusion_count = self.count_exclusion_terms(text)
+        return concrete_count >= threshold and exclusion_count <= 2
+
+
+class ConcreteGradeValidator:
+    """Работает с базой знаний и валидирует марки бетона."""
+
+    def __init__(
+        self,
+        knowledge_base: Optional[Dict[str, Any]] = None,
+        knowledge_base_path: str = "knowledge_base/complete-concrete-knowledge-base.json",
+    ) -> None:
+        if knowledge_base is not None:
+            self.knowledge_base = knowledge_base
+        else:
+            self.knowledge_base = self._load_knowledge_base(knowledge_base_path)
+
+        self.valid_grades = self._extract_valid_grades()
+        self.grade_mappings = self._build_grade_mappings()
+
+    def _load_knowledge_base(self, path: str) -> Dict[str, Any]:
+        if os.path.exists(path):
+            try:
+                with open(path, "r", encoding="utf-8") as kb_file:
+                    return json.load(kb_file)
+            except Exception as exc:  # pragma: no cover - защитный код
+                logger.warning("Не удалось загрузить базу знаний: %s", exc)
+        return self._create_default_kb()
+
+    @staticmethod
+    def _create_default_kb() -> Dict[str, Any]:
         return {
-            "environment_classes": {
-                "XC1": {"description": "suché nebo stále mokré", "applications": ["interiér", "základy"]},
-                "XC2": {"description": "mokré, občas suché", "applications": ["základy", "spodní stavba"]},
-                "XC3": {"description": "středně mokré", "applications": ["kryté prostory"]},
-                "XC4": {"description": "střídavě mokré a suché", "applications": ["vnější povrchy"]},
-                "XD1": {"description": "chloridy - mírné", "applications": ["garáže", "parkoviště"]},
-                "XD3": {"description": "chloridy - silné", "applications": ["mosty", "vozovky"]},
-                "XF1": {"description": "mráz - mírný", "applications": ["vnější svislé plochy"]},
-                "XF2": {"description": "mráz + soli", "applications": ["silniční konstrukce"]},
-                "XF4": {"description": "mráz + soli - extrémní", "applications": ["mostovky", "vozovky"]},
-                "XA1": {"description": "chemicky agresivní - slabě", "applications": ["základy", "septiky"]},
+            "concrete_knowledge_base": {
+                "strength_classes": {
+                    "standard": {
+                        "C8/10": {"fck_cyl": 8, "fck_cube": 10},
+                        "C12/15": {"fck_cyl": 12, "fck_cube": 15},
+                        "C16/20": {"fck_cyl": 16, "fck_cube": 20},
+                        "C20/25": {"fck_cyl": 20, "fck_cube": 25},
+                        "C25/30": {"fck_cyl": 25, "fck_cube": 30},
+                        "C30/37": {"fck_cyl": 30, "fck_cube": 37},
+                        "C35/45": {"fck_cyl": 35, "fck_cube": 45},
+                        "C40/50": {"fck_cyl": 40, "fck_cube": 50},
+                        "C45/55": {"fck_cyl": 45, "fck_cube": 55},
+                        "C50/60": {"fck_cyl": 50, "fck_cube": 60},
+                    }
+                },
+                "concrete_types_by_density": {
+                    "lehký_beton": {
+                        "strength_classes": [
+                            "LC8/9",
+                            "LC12/13",
+                            "LC16/18",
+                            "LC20/22",
+                            "LC25/28",
+                            "LC30/33",
+                        ]
+                    }
+                },
             }
         }
 
-    def _local_concrete_analysis(self, text: str) -> Dict[str, Any]:
-        """Локальный анализ текста на наличие марок бетона"""
-        all_matches = []
-        
-        for pattern in self.concrete_patterns:
+    def _extract_valid_grades(self) -> Set[str]:
+        valid_grades: Set[str] = set()
+        knowledge_base = self.knowledge_base.get("concrete_knowledge_base", {})
+
+        strength_classes = knowledge_base.get("strength_classes", {})
+        standard_classes = strength_classes.get("standard", {})
+        if isinstance(standard_classes, dict):
+            valid_grades.update(standard_classes.keys())
+
+        uhpc_classes = strength_classes.get("uhpc", {})
+        if isinstance(uhpc_classes, dict):
+            valid_grades.update(uhpc_classes.keys())
+
+        density_types = knowledge_base.get("concrete_types_by_density", {})
+        for data in density_types.values():
+            strength_data = data.get("strength_classes")
+            if isinstance(strength_data, dict):
+                valid_grades.update(strength_data.keys())
+            elif isinstance(strength_data, list):
+                valid_grades.update(strength_data)
+
+        logger.info("Загружено %s валидных марок бетона", len(valid_grades))
+        return valid_grades
+
+    def _build_grade_mappings(self) -> Dict[str, str]:
+        mappings: Dict[str, str] = {}
+        standard_mappings = {
+            "C8": "C8/10",
+            "C12": "C12/15",
+            "C16": "C16/20",
+            "C20": "C20/25",
+            "C25": "C25/30",
+            "C30": "C30/37",
+            "C35": "C35/45",
+            "C40": "C40/50",
+            "C45": "C45/55",
+            "C50": "C50/60",
+            "C55": "C55/67",
+            "C60": "C60/75",
+            "C70": "C70/85",
+            "C80": "C80/95",
+            "C90": "C90/105",
+            "C100": "C100/115",
+        }
+        for simple, full in standard_mappings.items():
+            if full in self.valid_grades:
+                mappings[simple] = full
+        return mappings
+
+    def normalize_grade(self, grade: str) -> str:
+        normalized = re.sub(r"\s+", "", grade.upper())
+        return self.grade_mappings.get(normalized, normalized)
+
+    def is_valid_grade(self, grade: str) -> bool:
+        normalized = self.normalize_grade(grade)
+        return normalized in self.valid_grades
+
+    def get_grade_info(self, grade: str) -> Dict[str, Any]:
+        normalized = self.normalize_grade(grade)
+        if not self.is_valid_grade(normalized):
+            return {}
+
+        knowledge_base = self.knowledge_base.get("concrete_knowledge_base", {})
+        strength_classes = knowledge_base.get("strength_classes", {})
+        for section in ("standard", "uhpc"):
+            data = strength_classes.get(section, {})
+            if normalized in data:
+                return data[normalized]
+        return {}
+
+
+class ImprovedRegexEngine:
+    """Ищет потенциальные марки бетона в тексте."""
+
+    def __init__(self, validator: ConcreteGradeValidator) -> None:
+        self.validator = validator
+        self.patterns = self._build_patterns()
+        self.exclusion_patterns = self._build_exclusion_patterns()
+
+    def _build_patterns(self) -> List[str]:
+        patterns: List[str] = []
+
+        if self.validator.valid_grades:
+            escaped_grades = [re.escape(grade) for grade in self.validator.valid_grades]
+            exact_pattern = "|".join(sorted(escaped_grades))
+            patterns.append(rf"\b(?:{exact_pattern})\b")
+
+        patterns.append(r"\bC([8-9]|[1-9][0-9]|1[0-7][0-9])/([1-9][0-9]|1[0-1][0-9])\b")
+        patterns.append(r"\bLC([8-9]|[1-8][0-9])/([9]|[1-8][0-9])\b")
+        patterns.append(r"\bC([8-9]|[1-9][0-9]|1[0-7][0-9])(?!/\d)\b")
+        patterns.append(
+            r"\bC\d{1,2}/\d{1,2}(?:\s*[-–]?\s*X[CDFASM]\d*(?:\s*,\s*X[CDFASM]\d*)*)?(?:\s*[-–]?\s*X[CDFASM]\d*)*\b"
+        )
+        return patterns
+
+    def _build_exclusion_patterns(self) -> List[str]:
+        return [
+            r"C\d{4,}",
+            r"[Cc]z\d+",
+            r"C\d+[A-Z]{3,}",
+            r"\bC(?:ad|AD)\b",
+            r"\bC(?:o|O)\.?\s*\d+",
+            r"C[A-Z]\d+[A-Z]",
+            r"\bC\s?\d+\s?(?:kg|mm|cm|m|%)\b",
+            r"\bC\d+[-_]\d+[-_]\d+",
+        ]
+
+    def _is_excluded(self, grade: str, context: str) -> bool:
+        for pattern in self.exclusion_patterns:
+            if re.search(pattern, grade, re.IGNORECASE):
+                return True
+
+        exclusion_terms = [
+            "stránka",
+            "strana",
+            "page",
+            "kapitola",
+            "oddíl",
+            "kód",
+            "číslo",
+            "number",
+            "firma",
+            "společnost",
+            "datum",
+            "date",
+            "cena",
+            "price",
+            "telefon",
+            "email",
+        ]
+        lowered = context.lower()
+        exclusion_count = sum(1 for term in exclusion_terms if term in lowered)
+        return exclusion_count >= 3
+
+    def find_matches(self, text: str) -> List[Tuple[str, int, int]]:
+        matches: List[Tuple[str, int, int]] = []
+        seen: Set[str] = set()
+
+        for pattern in self.patterns:
             for match in re.finditer(pattern, text, re.IGNORECASE):
-                grade = self._normalize_concrete_grade(match.group().strip())
-                context = text[max(0, match.start()-100):match.end()+100]
-                location = self._identify_structural_element(context)
-                
-                all_matches.append(ConcreteMatch(
-                    grade=grade,
-                    context=context.strip(),
-                    location=location,
-                    confidence=0.9,
-                    method='regex',
-                    coordinates=None
-                ))
-        
-        # Дедупликация
-        unique_matches = {}
-        for match in all_matches:
-            key = match.grade
-            if key not in unique_matches or match.confidence > unique_matches[key].confidence:
-                unique_matches[key] = match
-        
+                grade = match.group().strip().upper()
+                start, end = match.span()
+
+                if grade in seen:
+                    continue
+
+                context_start = max(0, start - 300)
+                context_end = min(len(text), end + 300)
+                context = text[context_start:context_end]
+
+                if self._is_excluded(grade, context):
+                    continue
+
+                matches.append((grade, start, end))
+                seen.add(grade)
+
+        return matches
+
+
+# ============================================================================
+# 🤖 ConcreteAgentHybrid
+# ============================================================================
+
+
+class ConcreteAgentHybrid:
+    """Основной агент, объединяющий локальный анализ и интеграцию с Claude."""
+
+    def __init__(self, knowledge_base_path: str = "knowledge_base/complete-concrete-knowledge-base.json") -> None:
+        self.knowledge_base_path = knowledge_base_path
+        self.knowledge_base = self._load_knowledge_base()
+
+        self.validator = ConcreteGradeValidator(self.knowledge_base, knowledge_base_path)
+        self.czech_processor = CzechLanguageProcessor()
+        self.regex_engine = ImprovedRegexEngine(self.validator)
+
+        self.doc_parser = DocParser()
+        self.smeta_parser = SmetaParser()
+        self.claude_client = get_claude_client() if settings.is_claude_enabled() else None
+
+        self.min_confidence_threshold = 0.6
+        self.max_context_length = 500
+
+        logger.info("ConcreteAgentHybrid инициализирован")
+
+    # ------------------------------------------------------------------
+    # 📚 Работа с базой знаний
+    # ------------------------------------------------------------------
+
+    def _load_knowledge_base(self) -> Dict[str, Any]:
+        try:
+            with open(self.knowledge_base_path, "r", encoding="utf-8") as kb_file:
+                logger.info("📚 Knowledge-base загружен успешно")
+                return json.load(kb_file)
+        except Exception as exc:
+            logger.warning("⚠️ Не удалось загрузить knowledge-base: %s", exc)
+            return self._create_default_kb()
+
+    def _create_default_kb(self) -> Dict[str, Any]:
+        validator = ConcreteGradeValidator._create_default_kb()
+        validator["environment_classes"] = {
+            "XC1": {"description": "suché nebo stále mokré", "applications": ["interiér", "základy"]},
+            "XC2": {"description": "mokré, občas suché", "applications": ["základy", "spodní stavba"]},
+            "XC3": {"description": "středně mokré", "applications": ["kryté prostory"]},
+            "XC4": {"description": "střídavě mokré a suché", "applications": ["vnější povrchy"]},
+            "XD1": {"description": "chloridy - mírné", "applications": ["garáže", "parkoviště"]},
+            "XD3": {"description": "chloridy - silné", "applications": ["mosty", "vozovky"]},
+            "XF1": {"description": "mráz - mírný", "applications": ["vnější svislé plochy"]},
+            "XF2": {"description": "mráz + soli", "applications": ["silniční konstrukce"]},
+            "XF4": {"description": "mráz + soli - extrémní", "applications": ["mostovky", "vozovky"]},
+            "XA1": {"description": "chemicky agresivní - slabě", "applications": ["základy", "septiky"]},
+        }
+        return validator
+
+    def _get_kb_version(self) -> str:
+        knowledge_base = self.knowledge_base.get("concrete_knowledge_base", {})
+        return str(knowledge_base.get("version", "unknown"))
+
+    # ------------------------------------------------------------------
+    # 🔍 Локальный анализ
+    # ------------------------------------------------------------------
+
+    def _local_concrete_analysis(self, text: str) -> Dict[str, Any]:
+        analysis = self._analyze_text(text)
+        return self._analysis_result_to_dict(analysis)
+
+    def _analyze_text(self, text: str) -> AnalysisResult:
+        start_time = time.time()
+
+        try:
+            raw_matches = self.regex_engine.find_matches(text)
+            validated_matches: List[ConcreteMatch] = []
+            structural_elements: List[Dict[str, Any]] = []
+
+            for grade, start, end in raw_matches:
+                processed = self._process_match(text, grade, start, end)
+                if processed and processed.confidence >= self.min_confidence_threshold:
+                    validated_matches.append(processed)
+                    element = self._extract_structural_element(processed.context)
+                    if element:
+                        structural_elements.append(element)
+
+            compliance_issues = self._check_compliance(validated_matches)
+            recommendations = self._generate_recommendations(validated_matches, compliance_issues)
+            confidence = (
+                sum(match.confidence for match in validated_matches) / len(validated_matches)
+                if validated_matches
+                else 0.0
+            )
+
+            return AnalysisResult(
+                success=True,
+                total_matches=len(validated_matches),
+                analysis_method="improved_hybrid_regex_czech_validation",
+                processing_time=time.time() - start_time,
+                concrete_summary=[self._match_to_dict(match) for match in validated_matches],
+                structural_elements=structural_elements,
+                compliance_issues=compliance_issues,
+                recommendations=recommendations,
+                confidence_score=confidence,
+            )
+        except Exception as exc:  # pragma: no cover - защитный код
+            logger.error("Ошибка локального анализа: %s", exc)
+            return AnalysisResult(
+                success=False,
+                total_matches=0,
+                analysis_method="error",
+                processing_time=time.time() - start_time,
+                concrete_summary=[],
+                structural_elements=[],
+                compliance_issues=[f"Ошибка анализа: {exc}"],
+                recommendations=["Проверьте входные данные и повторите анализ"],
+                confidence_score=0.0,
+            )
+
+    def _process_match(self, text: str, grade: str, start: int, end: int) -> Optional[ConcreteMatch]:
+        context_start = max(0, start - 250)
+        context_end = min(len(text), end + 250)
+        context = text[context_start:context_end]
+
+        if not self.czech_processor.is_valid_czech_context(context):
+            return None
+
+        normalized_grade = self.validator.normalize_grade(grade)
+        if not self.validator.is_valid_grade(normalized_grade):
+            return None
+
+        structural_element = self.czech_processor.identify_structural_element(context)
+        location = structural_element or "nespecifikováno"
+        exposure_class = self._extract_exposure_class(context)
+        confidence = self._calculate_confidence(
+            normalized_grade,
+            context,
+            structural_element,
+            exposure_class,
+        )
+
+        return ConcreteMatch(
+            grade=normalized_grade,
+            context=context.strip()[: self.max_context_length],
+            location=location,
+            confidence=confidence,
+            method="hybrid_regex_czech",
+            coordinates=None,
+            structural_element=structural_element,
+            exposure_class=exposure_class,
+            position={"start": start, "end": end},
+        )
+
+    def _extract_exposure_class(self, context: str) -> Optional[str]:
+        matches = re.findall(r"X[CDFASM]\d*", context, flags=re.IGNORECASE)
+        return ", ".join(sorted({match.upper() for match in matches})) if matches else None
+
+    def _calculate_confidence(
+        self,
+        grade: str,
+        context: str,
+        structural_element: Optional[str],
+        exposure_class: Optional[str],
+    ) -> float:
+        confidence = 0.4
+
+        if self.validator.is_valid_grade(grade):
+            confidence += 0.3
+
+        concrete_terms_count = self.czech_processor.count_concrete_terms(context)
+        confidence += min(concrete_terms_count * 0.05, 0.25)
+
+        if structural_element:
+            confidence += 0.1
+
+        if exposure_class:
+            confidence += 0.1
+
+        tech_terms = ["mpa", "pevnost", "cement", "norma", "výroba", "kvalita"]
+        tech_bonus = sum(0.02 for term in tech_terms if term in context.lower())
+        confidence += min(tech_bonus, 0.15)
+
+        return min(confidence, 1.0)
+
+    def _extract_structural_element(self, context: str) -> Optional[Dict[str, Any]]:
+        element = self.czech_processor.identify_structural_element(context)
+        if not element:
+            return None
+
         return {
-            'concrete_summary': [
-                {
-                    'grade': match.grade,
-                    'location': match.location,
-                    'context': match.context[:200],
-                    'confidence': match.confidence,
-                    'method': match.method
-                }
-                for match in unique_matches.values()
-            ],
-            'analysis_method': 'local',
-            'total_matches': len(unique_matches),
-            'success': True
+            "type": element,
+            "context": context[:200],
+            "requirements": self._get_element_requirements(element),
         }
 
-    def _normalize_concrete_grade(self, grade: str) -> str:
-        """Нормализует обозначение марки бетона"""
-        normalized = re.sub(r'\s+', '', grade.upper())
-        normalized = re.sub(r'^B(\d+)$', r'C\1/\1', normalized)  # B20 -> C20/25
-        normalized = re.sub(r'^(\d+)$', r'C\1', normalized)       # 30 -> C30
-        return normalized
-
-    def _identify_structural_element(self, context: str) -> str:
-        """Определяет тип конструктивного элемента из контекста"""
-        context_upper = context.upper()
-        
-        for element, info in self.structural_elements.items():
-            if element in context_upper:
-                return f"{element} ({info['en']})"
-        
-        for element, info in self.structural_elements.items():
-            if any(part in context_upper for part in element.split()):
-                return f"{element} ({info['en']}) - частичное совпадение"
-        
-        return "неопределено"
-
-    async def _claude_concrete_analysis(self, text: str, smeta_data: List[Dict]) -> Dict[str, Any]:
-        """Анализ через Claude с расширенным контекстом"""
+    def _get_element_requirements(self, element_type: str) -> List[str]:
+        requirements = {
+            "ZÁKLAD": ["Minimální třída C16/20", "Ochrana proti XA", "Krytí min 35mm"],
+            "PILÍŘ": ["Minimální třída C20/25", "Vhodnost pro XC prostředí"],
+            "STĚNA": ["Minimální třída C16/20", "Ochrana proti XC"],
+            "DESKA": ["Minimální třída C20/25", "Ochrana proti XC"],
+        }
+        return requirements.get(element_type, ["Kontrola dle ČSN EN 206"])
+
+    def _check_compliance(self, matches: List[ConcreteMatch]) -> List[str]:
+        issues: List[str] = []
+
+        for match in matches:
+            if match.grade.startswith("C"):
+                try:
+                    strength_value = int(match.grade.split("/")[0][1:])
+                    if strength_value < 12:
+                        issues.append(f"Марка {match.grade} ниже минимальной C12/15")
+                except ValueError:  # pragma: no cover - защитный код
+                    continue
+
+            if match.structural_element == "ZÁKLAD" and match.grade in {"C8/10", "C12/15"}:
+                issues.append(
+                    f"Для фундаментов рекомендуется минимум C16/20, найдено {match.grade}"
+                )
+
+        return issues
+
+    def _generate_recommendations(
+        self, matches: List[ConcreteMatch], issues: List[str]
+    ) -> List[str]:
+        if not matches:
+            return ["Марки бетона не обнаружены. Проверьте документацию."]
+
+        recommendations: List[str] = []
+
+        if len(matches) > 5:
+            recommendations.append("Обнаружено много разных марок. Рассмотрите стандартизацию.")
+
+        if not any(match.exposure_class for match in matches):
+            recommendations.append("Укажите классы воздействующей среды (XC, XF, XA и т.д.)")
+
+        if not any(match.structural_element for match in matches):
+            recommendations.append("Уточните применение бетона в конструктивных элементах")
+
+        if issues:
+            recommendations.append("Проанализируйте выявленные несоответствия и скорректируйте спецификацию")
+
+        return recommendations
+
+    def _match_to_dict(self, match: ConcreteMatch) -> Dict[str, Any]:
+        result = asdict(match)
+        grade_info = self.validator.get_grade_info(match.grade)
+        if grade_info:
+            result["grade_properties"] = grade_info
+        return result
+
+    def _analysis_result_to_dict(self, result: AnalysisResult) -> Dict[str, Any]:
+        return {
+            "success": result.success,
+            "total_matches": result.total_matches,
+            "analysis_method": result.analysis_method,
+            "processing_time": result.processing_time,
+            "concrete_summary": result.concrete_summary,
+            "structural_elements": result.structural_elements,
+            "compliance_issues": result.compliance_issues,
+            "recommendations": result.recommendations,
+            "confidence_score": result.confidence_score,
+            "grade_frequency": self._calculate_grade_frequency(result.concrete_summary),
+        }
+
+    def _calculate_grade_frequency(self, matches: List[Dict[str, Any]]) -> Dict[str, int]:
+        frequency: Dict[str, int] = {}
+        for match in matches:
+            grade = match.get("grade", "unknown")
+            frequency[grade] = frequency.get(grade, 0) + 1
+        return frequency
+
+    # ------------------------------------------------------------------
+    # 🤝 Интеграция с Claude
+    # ------------------------------------------------------------------
+
+    async def _claude_concrete_analysis(
+        self, text: str, smeta_data: List[Dict[str, Any]]
+    ) -> Dict[str, Any]:
         if not self.claude_client:
             return {"success": False, "error": "Claude client not available"}
-        
+
         try:
             result = await self.claude_client.analyze_concrete_with_claude(text, smeta_data)
-            
             return {
-                'concrete_summary': result.get('claude_analysis', {}).get('concrete_grades', []),
-                'analysis_method': 'claude_enhanced',
-                'success': True,
-                'tokens_used': result.get('tokens_used', 0),
-                'raw_response': result.get('raw_response', '')
+                "concrete_summary": result.get("claude_analysis", {}).get("concrete_grades", []),
+                "analysis_method": "claude_enhanced",
+                "success": True,
+                "tokens_used": result.get("tokens_used", 0),
+                "raw_response": result.get("raw_response", ""),
             }
-            
-        except Exception as e:
-            logger.error(f"❌ Ошибка Claude анализа: {e}")
-            return {"success": False, "error": str(e)}
-
-    async def analyze(self, doc_paths: List[str], smeta_path: Optional[str] = None,
-                      use_claude: bool = True, claude_mode: str = "enhancement") -> Dict[str, Any]:
-        """
-        Комплексный анализ документов с использованием всех возможностей
-        """
-        logger.info(f"🏗️ Запуск комплексного анализа (режим: {claude_mode})")
-        
+        except Exception as exc:  # pragma: no cover - защитный код
+            logger.error("❌ Ошибка Claude анализа: %s", exc)
+            return {"success": False, "error": str(exc)}
+
+    # ------------------------------------------------------------------
+    # 🗂️ Основной метод анализа
+    # ------------------------------------------------------------------
+
+    async def analyze(
+        self,
+        doc_paths: List[str],
+        smeta_path: Optional[str] = None,
+        use_claude: bool = True,
+        claude_mode: str = "enhancement",
+    ) -> Dict[str, Any]:
+        logger.info("🏗️ Запуск комплексного анализа (режим: %s)", claude_mode)
+
         all_text = ""
-        processed_docs = []
-        
-        # Обрабатываем каждый документ
+        processed_docs: List[Dict[str, Any]] = []
+
         for doc_path in doc_paths:
             try:
                 text = self.doc_parser.parse(doc_path)
                 all_text += text + "\n"
-                
-                processed_docs.append({
-                    'file': Path(doc_path).name,
-                    'type': 'Document',
-                    'text_length': len(text)
-                })
-                
-            except Exception as e:
-                logger.error(f"❌ Ошибка обработки {doc_path}: {e}")
-                processed_docs.append({'file': Path(doc_path).name, 'error': str(e)})
-        
-        # Обрабатываем смету
-        smeta_data = []
+                processed_docs.append(
+                    {"file": Path(doc_path).name, "type": "Document", "text_length": len(text)}
+                )
+            except Exception as exc:
+                logger.error("❌ Ошибка обработки %s: %s", doc_path, exc)
+                processed_docs.append({"file": Path(doc_path).name, "error": str(exc)})
+
+        smeta_data: List[Dict[str, Any]] = []
         if smeta_path:
             try:
                 smeta_result = self.smeta_parser.parse(smeta_path)
-                smeta_data = smeta_result.get('items', [])
-                logger.info(f"📊 Смета обработана: {len(smeta_data)} позиций")
-            except Exception as e:
-                logger.error(f"❌ Ошибка обработки сметы: {e}")
-        
-        # Локальный анализ
+                smeta_data = smeta_result.get("items", [])
+                logger.info("📊 Смета обработана: %s позиций", len(smeta_data))
+            except Exception as exc:
+                logger.error("❌ Ошибка обработки сметы: %s", exc)
+
         local_result = self._local_concrete_analysis(all_text)
-        
-        # Интеграция с Claude
-        final_result = local_result.copy()
-        
-        if use_claude and self.claude_client:
+        final_result = dict(local_result)
+
+        if use_claude and self.claude_client and all_text.strip():
             claude_result = await self._claude_concrete_analysis(all_text, smeta_data)
-            
             if claude_mode == "primary" and claude_result.get("success"):
                 final_result = claude_result
             elif claude_mode == "enhancement" and claude_result.get("success"):
-                final_result.update({
-                    'claude_analysis': claude_result,
-                    'analysis_method': 'hybrid_enhanced',
-                    'total_tokens_used': claude_result.get('tokens_used', 0)
-                })
-        
-        # Добавляем метаданные
-        final_result.update({
-            'processed_documents': processed_docs,
-            'smeta_items': len(smeta_data),
-            'processing_time': 'completed',
-            'knowledge_base_version': '3.0'
-        })
-        
+                final_result.update(
+                    {
+                        "claude_analysis": claude_result,
+                        "analysis_method": "hybrid_enhanced",
+                        "total_tokens_used": claude_result.get("tokens_used", 0),
+                    }
+                )
+
+        final_result.update(
+            {
+                "processed_documents": processed_docs,
+                "smeta_items": len(smeta_data),
+                "processing_time": final_result.get("processing_time", "completed"),
+                "knowledge_base_version": self._get_kb_version(),
+            }
+        )
+
         return final_result
 
-# ==============================
-# 🔧 Глобальные функции
-# ==============================
 
-_hybrid_agent = None
+# ============================================================================
+# 🔧 Глобальные функции и совместимость с API
+# ============================================================================
+
+
+_hybrid_agent: Optional[ConcreteAgentHybrid] = None
+
 
 def get_hybrid_agent() -> ConcreteAgentHybrid:
-    """Получение глобального экземпляра гибридного агента"""
     global _hybrid_agent
     if _hybrid_agent is None:
         _hybrid_agent = ConcreteAgentHybrid()
         logger.info("🤖 ConcreteAgentHybrid инициализирован")
     return _hybrid_agent
 
-# ==============================
-# 🚀 API-совместимые функции
-# ==============================
 
-async def analyze_concrete(doc_paths: List[str], smeta_path: Optional[str] = None,
-                           use_claude: bool = True, claude_mode: str = "enhancement") -> Dict[str, Any]:
-    """
-    Главная функция для анализа бетона - совместима с существующим API
-    """
+async def analyze_concrete(
+    doc_paths: List[str],
+    smeta_path: Optional[str] = None,
+    use_claude: bool = True,
+    claude_mode: str = "enhancement",
+) -> Dict[str, Any]:
     agent = get_hybrid_agent()
-    
+
     try:
         result = await agent.analyze(doc_paths, smeta_path, use_claude, claude_mode)
-        
-        # Сохраняем результат
         try:
             save_merged_report(result, "outputs/concrete_analysis_report.json")
             logger.info("💾 Отчет сохранен в outputs/concrete_analysis_report.json")
-        except Exception as e:
-            logger.warning(f"⚠️ Не удалось сохранить отчёт: {e}")
-        
+        except Exception as exc:  # pragma: no cover - защитный код
+            logger.warning("⚠️ Не удалось сохранить отчёт: %s", exc)
         return result
-        
-    except Exception as e:
-        logger.error(f"❌ Критическая ошибка в analyze_concrete: {e}")
+    except Exception as exc:  # pragma: no cover - защитный код
+        logger.error("❌ Критическая ошибка в analyze_concrete: %s", exc)
         return {
-            "error": str(e),
+            "error": str(exc),
             "success": False,
             "analysis_method": "error",
-            "concrete_summary": []
+            "concrete_summary": [],
         }
