"""
Concrete Agent Module - Specialized concrete grade extraction
"""

from .agent import ConcreteGradeExtractor, ConcreteGrade, get_concrete_grade_extractor

# Re-export main functions from the parent concrete_agent.py for compatibility
try:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from concrete_agent import analyze_concrete, analyze_concrete_with_volumes, get_hybrid_agent
    
    __all__ = [
        'ConcreteGradeExtractor', 'ConcreteGrade', 'get_concrete_grade_extractor',
        'analyze_concrete', 'analyze_concrete_with_volumes', 'get_hybrid_agent'
    ]
except ImportError:
    __all__ = ['ConcreteGradeExtractor', 'ConcreteGrade', 'get_concrete_grade_extractor']