"""
Concrete Agent Module - Specialized concrete grade extraction
"""

from .agent import ConcreteGradeExtractor, ConcreteGrade, get_concrete_grade_extractor

# Re-export main functions from the parent concrete_agent.py for compatibility
try:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from agents.concrete_agent import analyze_concrete, analyze_concrete_with_volumes, get_hybrid_agent
    
    __all__ = [
        'ConcreteGradeExtractor', 'ConcreteGrade', 'get_concrete_grade_extractor',
        'analyze_concrete', 'analyze_concrete_with_volumes', 'get_hybrid_agent'
    ]
except ImportError as e:
    # Fallback: try direct import
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ Import fallback for concrete_agent: {e}")
    try:
        # Direct import from parent module
        import importlib.util
        spec = importlib.util.spec_from_file_location("concrete_agent_main", 
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "concrete_agent.py"))
        concrete_agent_main = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(concrete_agent_main)
        
        analyze_concrete = concrete_agent_main.analyze_concrete
        analyze_concrete_with_volumes = concrete_agent_main.analyze_concrete_with_volumes
        get_hybrid_agent = concrete_agent_main.get_hybrid_agent
        
        __all__ = [
            'ConcreteGradeExtractor', 'ConcreteGrade', 'get_concrete_grade_extractor',
            'analyze_concrete', 'analyze_concrete_with_volumes', 'get_hybrid_agent'
        ]
    except Exception as e2:
        logger.error(f"❌ Failed to import concrete_agent functions: {e2}")
        __all__ = ['ConcreteGradeExtractor', 'ConcreteGrade', 'get_concrete_grade_extractor']