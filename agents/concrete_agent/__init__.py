"""
Concrete Agent Module - Specialized concrete grade extraction
"""

from .agent import ConcreteGradeExtractor, ConcreteGrade, get_concrete_grade_extractor

# Re-export main functions from the parent concrete_agent.py for compatibility
try:
    import importlib.util
    import os
    
    # Load the sibling concrete_agent.py module explicitly
    concrete_agent_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'concrete_agent.py')
    spec = importlib.util.spec_from_file_location("concrete_agent_module", concrete_agent_path)
    concrete_agent_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(concrete_agent_module)
    
    # Re-export the main functions
    analyze_concrete = concrete_agent_module.analyze_concrete
    analyze_concrete_with_volumes = concrete_agent_module.analyze_concrete_with_volumes
    get_hybrid_agent = concrete_agent_module.get_hybrid_agent
    
    __all__ = [
        'ConcreteGradeExtractor', 'ConcreteGrade', 'get_concrete_grade_extractor',
        'analyze_concrete', 'analyze_concrete_with_volumes', 'get_hybrid_agent'
    ]
except ImportError:
    __all__ = ['ConcreteGradeExtractor', 'ConcreteGrade', 'get_concrete_grade_extractor']