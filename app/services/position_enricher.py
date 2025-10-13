"""
Position Enricher
Обогащает позиции из сметы техническими данными из чертежей
Использует Claude для сопоставления и извлечения параметров
"""
import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from app.core.claude_client import ClaudeClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class PositionEnricher:
    """
    Enrich positions from estimate with technical specifications from drawings
    
    Workflow:
    1. Match position with drawing specifications (fuzzy matching via Claude)
    2. Extract technical parameters
    3. Validate compliance with standards
    4. Return enriched position
    """
    
    def __init__(self):
        self.claude = ClaudeClient()
    
    async def enrich_positions(
        self,
        positions: List[Dict[str, Any]],
        drawing_specs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enrich all positions with drawing specifications
        
        Args:
            positions: List of positions from výkaz výměr
            drawing_specs: List of specifications from drawings
            
        Returns:
            List of enriched positions
        """
        logger.info(
            f"Enriching {len(positions)} positions with "
            f"{len(drawing_specs)} drawing specifications"
        )
        
        if not drawing_specs:
            logger.warning("No drawing specifications available for enrichment")
            return positions
        
        enriched_positions = []
        match_stats = {
            'matched': 0,
            'partial': 0,
            'unmatched': 0
        }
        
        for idx, position in enumerate(positions, start=1):
            logger.info(f"Enriching position {idx}/{len(positions)}: {position.get('description', 'N/A')[:50]}")
            
            enriched = await self.enrich_single_position(position, drawing_specs)
            
            # Track matching statistics
            if enriched.get('enrichment_status') == 'matched':
                match_stats['matched'] += 1
            elif enriched.get('enrichment_status') == 'partial':
                match_stats['partial'] += 1
            else:
                match_stats['unmatched'] += 1
            
            enriched_positions.append(enriched)
        
        logger.info(
            f"✅ Enrichment complete: "
            f"matched={match_stats['matched']}, "
            f"partial={match_stats['partial']}, "
            f"unmatched={match_stats['unmatched']}"
        )
        
        return enriched_positions
    
    async def enrich_single_position(
        self,
        position: Dict[str, Any],
        drawing_specs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Enrich a single position with drawing specifications
        
        Args:
            position: Single position from estimate
            drawing_specs: All available specifications from drawings
            
        Returns:
            Enriched position
        """
        try:
            # Prepare Claude prompt
            prompt = self._create_enrichment_prompt(position, drawing_specs)
            
            # Call Claude for matching and extraction using updated SDK method
            response = await asyncio.to_thread(self.claude.call, prompt)
            
            # Parse Claude's response
            enrichment_data = self._parse_enrichment_response(response)
            
            # Merge enrichment data with position
            enriched_position = self._merge_enrichment(position, enrichment_data)
            
            logger.debug(
                f"Position enriched: {position.get('description', 'N/A')[:30]} - "
                f"Status: {enriched_position.get('enrichment_status')}"
            )
            
            return enriched_position
            
        except Exception as e:
            logger.error(f"Error enriching position: {str(e)}", exc_info=True)
            
            # Return original position with error status
            position['enrichment_status'] = 'error'
            position['enrichment_error'] = str(e)
            return position
    
    def _create_enrichment_prompt(
        self,
        position: Dict[str, Any],
        drawing_specs: List[Dict[str, Any]]
    ) -> str:
        """
        Create prompt for Claude to match and extract data
        
        Returns:
            Formatted prompt string
        """
        # Simplify drawing specs for prompt (only relevant fields)
        simplified_specs = []
        for spec in drawing_specs:
            simplified = {
                'material': spec.get('material', ''),
                'material_type': spec.get('material_type', ''),
                'source': spec.get('_source', {})
            }
            
            # Add type-specific fields
            if spec.get('concrete_class'):
                simplified['concrete_class'] = spec['concrete_class']
            if spec.get('exposure_classes'):
                simplified['exposure_classes'] = spec['exposure_classes']
            if spec.get('concrete_cover_mm'):
                simplified['concrete_cover_mm'] = spec['concrete_cover_mm']
            if spec.get('surface'):
                simplified['surface'] = spec['surface']
            if spec.get('steel_class'):
                simplified['steel_class'] = spec['steel_class']
            if spec.get('thickness_mm'):
                simplified['thickness_mm'] = spec['thickness_mm']
            
            simplified_specs.append(simplified)
        
        prompt = f"""Máš pozici z výkazu výměr (stavební smety):

**Pozice:**
{json.dumps(position, ensure_ascii=False, indent=2)}

**Specifikace materiálů z výkresů:**
{json.dumps(simplified_specs, ensure_ascii=False, indent=2)}

**Úkol:**
1. Najdi odpovídající specifikaci materiálu z výkresů pro tuto pozici
2. Proveď fuzzy matching podle názvu materiálu (ne všechny názvy budou přesně stejné)
3. Extrahuj technické parametry ze specifikace
4. Vrať strukturovaný JSON

**Pravidla matchingu:**
- Pozice "základní deska C30/37" odpovídá specifikaci "beton základů C30/37"
- Pozice "zdivo z tvárnic" odpovídá specifikaci "zdivo betonové tvárnice"
- Pokud třídy betonu nebo oceli se shodují → silný match
- Pokud je podobný popis materiálu → částečný match
- Pokud žádná shoda → unmatched

**Formát odpovědi (pouze validní JSON, bez markdown, bez vysvětlení):**
{{
  "matched": true/false,
  "matching_confidence": 0.0-1.0,
  "matching_reason": "Krátké vysvětlení proč/proč ne",
  "matched_spec_index": 0,
  "technical_specs": {{
    "concrete_class": "C30/37",
    "exposure_classes": ["XA1", "XC2", "XF2"],
    "concrete_cover_mm": 50,
    "surface_finish": "hladká",
    "steel_class": "B500B",
    "thickness_mm": 100,
    "other_params": {{}}
  }},
  "source_reference": {{
    "drawing": "SO1-01.pdf",
    "page": 3,
    "table": 1
  }},
  "compliance_notes": ["Třída expozice odpovídá ČSN EN 206", "Krytí výztuže dostatečné"]
}}

Pokud nenajdeš žádnou odpovídající specifikaci, vrať:
{{
  "matched": false,
  "matching_confidence": 0.0,
  "matching_reason": "Nenalezena odpovídající specifikace materiálu ve výkresech",
  "technical_specs": {{}},
  "source_reference": null
}}
"""
        
        return prompt
    
    def _parse_enrichment_response(self, response: str) -> Dict[str, Any]:
        """
        Parse Claude's response and extract enrichment data
        
        Args:
            response: Raw response from Claude
            
        Returns:
            Parsed enrichment data
        """
        try:
            # Remove markdown code blocks if present
            response = response.strip()
            if response.startswith('```'):
                response = response.split('```')[1]
                if response.startswith('json'):
                    response = response[4:]
                response = response.strip()
            
            # Parse JSON
            enrichment_data = json.loads(response)
            
            return enrichment_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            logger.debug(f"Response was: {response[:500]}")
            
            # Return unmatched status on parsing error
            return {
                'matched': False,
                'matching_confidence': 0.0,
                'matching_reason': 'Failed to parse AI response',
                'technical_specs': {},
                'source_reference': None
            }
    
    def _merge_enrichment(
        self,
        position: Dict[str, Any],
        enrichment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge enrichment data into position
        
        Args:
            position: Original position
            enrichment_data: Enrichment data from Claude
            
        Returns:
            Merged position with enrichment
        """
        # Copy original position
        enriched = position.copy()
        
        # Determine enrichment status
        if enrichment_data.get('matched') and enrichment_data.get('matching_confidence', 0) >= 0.7:
            enriched['enrichment_status'] = 'matched'
        elif enrichment_data.get('matched') and enrichment_data.get('matching_confidence', 0) >= 0.4:
            enriched['enrichment_status'] = 'partial'
        else:
            enriched['enrichment_status'] = 'unmatched'
        
        # Add enrichment metadata
        enriched['enrichment_confidence'] = enrichment_data.get('matching_confidence', 0.0)
        enriched['enrichment_reason'] = enrichment_data.get('matching_reason', '')
        
        # Add technical specifications if matched
        if enrichment_data.get('technical_specs'):
            enriched['technical_specs'] = enrichment_data['technical_specs']
        
        # Add source reference
        if enrichment_data.get('source_reference'):
            enriched['drawing_source'] = enrichment_data['source_reference']
        
        # Add compliance notes
        if enrichment_data.get('compliance_notes'):
            enriched['compliance_notes'] = enrichment_data['compliance_notes']
        
        return enriched
    
    async def enrich_with_specific_drawing(
        self,
        position: Dict[str, Any],
        drawing_path: Path
    ) -> Dict[str, Any]:
        """
        Enrich position with specifications from a specific drawing
        
        Convenience method for enriching from single drawing
        
        Args:
            position: Position to enrich
            drawing_path: Path to specific drawing PDF
            
        Returns:
            Enriched position
        """
        from app.parsers.drawing_specs_parser import DrawingSpecsParser
        
        # Parse drawing
        parser = DrawingSpecsParser()
        result = parser.parse(drawing_path)
        
        if not result.get('specifications'):
            logger.warning(f"No specifications found in {drawing_path.name}")
            position['enrichment_status'] = 'unmatched'
            position['enrichment_reason'] = 'No specifications in drawing'
            return position
        
        # Enrich with these specifications
        return await self.enrich_single_position(position, result['specifications'])


# ==============================================================================
# USAGE EXAMPLE
# ==============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test_enrichment():
        # Example position from estimate
        position = {
            "position_number": "1.1",
            "description": "základní deska C30/37",
            "quantity": 89,
            "unit": "m³",
            "code": "121-01-001"
        }
        
        # Example drawing specifications
        drawing_specs = [
            {
                "material": "beton základů C30/37",
                "material_type": "concrete",
                "concrete_class": "C30/37",
                "exposure_classes": ["XA1", "XC2", "XF2"],
                "concrete_cover_mm": 50,
                "surface": "hladká",
                "_source": {
                    "drawing": "SO1-01_Základy.pdf",
                    "page": 3,
                    "table": 1
                }
            },
            {
                "material": "výztuž základů B500B",
                "material_type": "reinforcement",
                "steel_class": "B500B",
                "_source": {
                    "drawing": "SO1-01_Základy.pdf",
                    "page": 3,
                    "table": 1
                }
            }
        ]
        
        # Enrich
        enricher = PositionEnricher()
        enriched = await enricher.enrich_single_position(position, drawing_specs)
        
        print("\n📊 Enrichment Result:")
        print(json.dumps(enriched, ensure_ascii=False, indent=2))
    
    asyncio.run(test_enrichment())
