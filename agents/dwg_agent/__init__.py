"""
DWG Agent Module - Specialized DWG/DXF analysis with ezdxf
"""

try:
    from .agent import (
        DwgAnalysisAgent, DwgTextEntity, DwgLayer, 
        ConcreteSpecification, DimensionInfo, get_dwg_analysis_agent
    )
    __all__ = [
        'DwgAnalysisAgent', 'DwgTextEntity', 'DwgLayer', 
        'ConcreteSpecification', 'DimensionInfo', 'get_dwg_analysis_agent'
    ]
except ImportError:
    # ezdxf не установлен
    __all__ = []