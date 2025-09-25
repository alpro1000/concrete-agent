"""
Модуль для предобработки чешского текста с восстановлением диакритики
utils/czech_preprocessor.py
"""

import re
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class CzechTextPreprocessor:
    """Препроцессор для восстановления поврежденной чешской диакритики из PDF"""
    
    def __init__(self):
        # Карта восстановления поврежденных символов (на основе анализа реальных PDF)
        self.diacritic_map = {
            # Основные поврежденные символы
            'ē': 'č', 'Ē': 'Č',  # часть -> část
            'Ǝ': 'ř', 'ě': 'ě',  # dřík -> dřík  
            'Ģ': 'ž', 'ŵ': 'ů',  # výžtuž -> výztuž, průměr -> průměr
            'ƽ': 'ů', 'Ţ': 'í',  # průměr -> průměr, třídy -> třídy
            'ş': 'í', 'ţ': 'í',   # třídy -> třídy
            
            # Комбинации символов
            'ƎŲ': 'řů',   # průměr
            'ŵĢ': 'ůž',   # výztuž  
            'ƎĢ': 'rž',   # různé
            'ŞĢ': 'íž',   # různé
            'ƎŢ': 'ří',   # třídy
            'pƎ': 'př',   # např. příčný
            'smĢ': 'smě',  # směr
            'ētĢ': 'čtž',  # конструкцe
            'ƎşĢ': 'říž', # napříč
            'ƎŢ': 'ří',   # třídy
            'ƎŲ': 'řů',   # průměr
            'ŢĻ': 'íl',   # profil
            'ĻĢ': 'lž',   # dlažba
            
            # Специфические строительные термины
            'opĢrn': 'opěrn',        # opěrná
            'betonáƎsk': 'betonářsk',  # betonářská
            'vodotĢsn': 'vodotěsn',    # vodotěsná
            'štĢrkodrt': 'štěrkodrt',  # štěrkodrt
            'drenážn': 'drenážn',      # drenážní
            'základov': 'základov',     # základová
            'železobeton': 'železobeton', # železobeton
            'vyplnĢn': 'vyplněn',      # vyplněna
            'proveden': 'proveden',     # provedena
            'uložen': 'uložen',        # uložena
            'upraven': 'upraven',      # upravena
        }
        
        # Расширенные чешские строительные термины для лучшего распознавания
        self.construction_terms = {
            'dřík': 'shaft/stem of structure',
            'základová část': 'foundation part', 
            'podkladní beton': 'substrate concrete',
            'říms': 'cornice/ledge',
            'opěrná zeď': 'retaining wall',
            'vrtané piloty': 'drilled piles',
            'betonářská ocel': 'reinforcing steel',
            'dilatační spára': 'expansion joint',
            'drenážní zásyp': 'drainage backfill',
            'štěrkodrt': 'crushed stone',
            'vodotěsná izolace': 'waterproof insulation',
            'lícová strana': 'face side',
            'železobetonová': 'reinforced concrete',
            'nosná konstrukce': 'load-bearing structure',
            'výztuž': 'reinforcement',
            'dlažba': 'paving/tiles',
            'pilíř': 'pier/column',
            'mostovka': 'bridge deck',
            'vozovka': 'roadway',
            'základ': 'foundation',
            'stěna': 'wall',
            'sloup': 'column',
            'deska': 'slab',
            'věnec': 'tie beam',
            'schodiště': 'stairs',
            'prefabrikát': 'precast element',
            'monolitický': 'monolithic',
        }

        # Паттерны для распознавания конструктивных элементов
        self.element_patterns = {
            r'vrtané\s+piloty': 'vrtané piloty (drilled piles)',
            r'opěrná\s+zeď': 'opěrná zeď (retaining wall)', 
            r'základová\s+část': 'základová část (foundation part)',
            r'dřík\s+konstrukce': 'dřík konstrukce (shaft of structure)',
            r'dřík\s+opěrné\s+zdi': 'dřík opěrné zdi (shaft of retaining wall)',
            r'železobetonová\s+římsa': 'železobetonová římsa (RC cornice)',
            r'spodní\s+část': 'spodní část (lower part)',
            r'horní\s+část': 'horní část (upper part)',
            r'nosná\s+konstrukce': 'nosná konstrukce (load-bearing structure)',
            r'podkladní\s+beton': 'podkladní beton (substrate concrete)',
            r'betonová\s+vrstva': 'betonová vrstva (concrete layer)',
        }

    def fix_czech_diacritics(self, text: str) -> str:
        """
        Основная функция восстановления диакритики
        """
        if not text:
            return text
            
        fixed_text = text
        fixes_applied = 0
        
        # Применяем исправления от более длинных к коротким
        sorted_fixes = sorted(self.diacritic_map.items(), key=lambda x: len(x[0]), reverse=True)
        
        for broken_char, correct_char in sorted_fixes:
            if broken_char in fixed_text:
                old_count = fixed_text.count(broken_char)
                fixed_text = fixed_text.replace(broken_char, correct_char)
                fixes_applied += old_count
                
        if fixes_applied > 0:
            logger.debug(f"🇨🇿 Applied {fixes_applied} diacritic fixes")
                
        return fixed_text

    def enhance_context_window(self, text: str, match_start: int, match_end: int, 
                             window_size: int = 150) -> str:
        """
        Расширенное извлечение контекста с исправленной диакритикой
        """
        context_start = max(0, match_start - window_size)
        context_end = min(len(text), match_end + window_size)
        
        context = text[context_start:context_end]
        
        # Исправляем диакритику в контексте
        fixed_context = self.fix_czech_diacritics(context)
        
        return fixed_context

    def identify_construction_element_enhanced(self, context: str) -> str:
        """
        Улучшенное определение конструктивных элементов
        """
        # Исправляем диакритику в контексте
        fixed_context = self.fix_czech_diacritics(context.lower())
        
        # Проверяем паттерны (от сложных к простым)
        for pattern, description in self.element_patterns.items():
            if re.search(pattern, fixed_context, re.IGNORECASE):
                return description
        
        # Проверяем точные совпадения терминов
        for term, translation in self.construction_terms.items():
            if term.lower() in fixed_context:
                return f"{term} ({translation})"
        
        # Проверяем части терминов (fallback)
        if 'dřík' in fixed_context:
            return "dřík konstrukce (shaft of structure)"
        elif 'základov' in fixed_context:
            return "základová část (foundation part)"
        elif 'říms' in fixed_context:
            return "římsa (cornice)"
        elif 'pilot' in fixed_context:
            return "vrtané piloty (drilled piles)"
        elif 'podkladn' in fixed_context:
            return "podkladní beton (substrate concrete)"
        elif 'opěrn' in fixed_context:
            return "opěrná zeď (retaining wall)"
        elif 'železobeton' in fixed_context:
            return "železobetonová konstrukce (RC structure)"
        elif 'výztuž' in fixed_context:
            return "výztuž (reinforcement)"
        elif 'izolace' in fixed_context:
            return "izolace (insulation)"
        elif 'vrstva' in fixed_context:
            return "betonová vrstva (concrete layer)"
        
        return "neurčený prvek (undefined element)"

    def preprocess_document_text(self, text: str) -> Dict[str, any]:
        """
        Предобработка всего документа
        """
        if not text:
            return {
                'original_text': text,
                'fixed_text': text,
                'changes_count': 0,
                'original_length': 0,
                'fixed_length': 0
            }
            
        original_length = len(text)
        fixed_text = self.fix_czech_diacritics(text)
        
        # Подсчитываем количество исправлений
        changes_made = 0
        for broken_char in self.diacritic_map.keys():
            changes_made += text.count(broken_char)
        
        if changes_made > 0:
            logger.info(f"🔧 Czech preprocessor: {changes_made} diacritic fixes applied")
        
        return {
            'original_text': text,
            'fixed_text': fixed_text,
            'changes_count': changes_made,
            'original_length': original_length,
            'fixed_length': len(fixed_text)
        }

    def extract_concrete_info_enhanced(self, text: str) -> Dict[str, any]:
        """
        Расширенное извлечение информации о бетоне с учетом чешского контекста
        """
        
        # Исправляем диакритику
        fixed_text = self.fix_czech_diacritics(text)
        
        concrete_info = {
            'concrete_grades': [],
            'construction_elements': [],
            'technical_specifications': [],
            'preprocessing_stats': {
                'original_length': len(text),
                'fixed_length': len(fixed_text),
                'diacritic_fixes': len([c for c in self.diacritic_map.keys() if c in text])
            }
        }
        
        # Паттерн для поиска марок бетона с контекстом
        concrete_pattern = r'(?i)beton(?:u|em|y|ová|ové)?\s+třídy?\s+((?:LC)?C\d{1,3}/\d{1,3})\s*(?:[-–]\s*([XO][CDFASM]?\d*(?:\s*,\s*[XO][CDFASM]?\d*)*))?'
        
        for match in re.finditer(concrete_pattern, fixed_text):
            grade = match.group(1).upper()
            exposure_classes = match.group(2) if match.group(2) else ""
            
            # Извлекаем расширенный контекст
            start = max(0, match.start() - 200)
            end = min(len(fixed_text), match.end() + 200)
            context = fixed_text[start:end]
            
            # Определяем конструктивный элемент
            element = self.identify_construction_element_enhanced(context)
            
            concrete_info['concrete_grades'].append({
                'grade': grade,
                'exposure_classes': exposure_classes,
                'construction_element': element,
                'context': context.strip()[:300]  # Ограничиваем длину контекста
            })
        
        return concrete_info


# Singleton instance
_czech_preprocessor = None

def get_czech_preprocessor() -> CzechTextPreprocessor:
    """Получение глобального экземпляра препроцессора"""
    global _czech_preprocessor
    if _czech_preprocessor is None:
        _czech_preprocessor = CzechTextPreprocessor()
        logger.info("🇨🇿 Czech text preprocessor initialized")
    return _czech_preprocessor


# Функция для тестирования
def test_czech_preprocessing():
    """Функция для тестирования предобработки"""
    processor = get_czech_preprocessor()
    
    test_text = """
    Ǝík opĢrné zdi bude proveden z betonu tƎídy C30/37 – XF3, XC4, základová ēást z betonu C30/37.
    Spodní ēást výkopu za zdí bude vyplnĢna betonem tƎídy C12/15 – X0.
    """
    
    result = processor.preprocess_document_text(test_text)
    
    print("🧪 TESTING CZECH PREPROCESSOR")
    print("=" * 40)
    print(f"Original: {test_text}")
    print(f"Fixed:    {result['fixed_text']}")
    print(f"Changes:  {result['changes_count']}")
    
    return result


if __name__ == "__main__":
    test_czech_preprocessing()
