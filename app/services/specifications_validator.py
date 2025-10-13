"""
Specifications Validator
Проверяет соответствие технических спецификаций стандартам ČSN
"""
import logging
from typing import Dict, Any, List, Optional
import re

logger = logging.getLogger(__name__)


class SpecificationsValidator:
    """
    Validate technical specifications against Czech standards (ČSN)
    
    Проверяет:
    - Соответствие классов exposure для бетона (ČSN EN 206)
    - Достаточность толщины покрытия
    - Соответствие классов арматуры
    - Другие требования стандартов
    """
    
    # ČSN EN 206: Minimum concrete cover for exposure classes
    EXPOSURE_CLASS_MIN_COVER = {
        'XC1': 15,  # mm
        'XC2': 25,
        'XC3': 25,
        'XC4': 30,
        'XD1': 40,
        'XD2': 45,
        'XD3': 50,
        'XS1': 45,
        'XS2': 50,
        'XS3': 55,
        'XF1': 25,
        'XF2': 25,
        'XF3': 30,
        'XF4': 35,
        'XA1': 25,
        'XA2': 35,
        'XA3': 45
    }
    
    # ČSN EN 206: Minimum concrete classes for exposure classes
    EXPOSURE_CLASS_MIN_CONCRETE = {
        'XC1': 'C20/25',
        'XC2': 'C25/30',
        'XC3': 'C30/37',
        'XC4': 'C30/37',
        'XD1': 'C30/37',
        'XD2': 'C35/45',
        'XD3': 'C35/45',
        'XS1': 'C30/37',
        'XS2': 'C35/45',
        'XS3': 'C35/45',
        'XF1': 'C30/37',
        'XF2': 'C25/30',
        'XF3': 'C30/37',
        'XF4': 'C30/37',
        'XA1': 'C30/37',
        'XA2': 'C35/45',
        'XA3': 'C40/50'
    }
    
    # Concrete class strength mapping (for comparison)
    CONCRETE_CLASS_STRENGTH = {
        'C12/15': 12,
        'C16/20': 16,
        'C20/25': 20,
        'C25/30': 25,
        'C30/37': 30,
        'C35/45': 35,
        'C40/50': 40,
        'C45/55': 45,
        'C50/60': 50
    }
    
    def validate_position(
        self,
        position: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate position with technical specifications
        
        Args:
            position: Position with technical_specs
            
        Returns:
            Position with validation results added
        """
        if 'technical_specs' not in position:
            logger.debug("Position has no technical specs to validate")
            position['validation_status'] = 'no_specs'
            return position
        
        specs = position['technical_specs']
        validation_results = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'info': []
        }
        
        # Validate concrete specifications
        if specs.get('concrete_class'):
            concrete_validation = self._validate_concrete(specs)
            self._merge_validation(validation_results, concrete_validation)
        
        # Validate reinforcement specifications
        if specs.get('steel_class'):
            reinforcement_validation = self._validate_reinforcement(specs)
            self._merge_validation(validation_results, reinforcement_validation)
        
        # Determine overall validation status
        if validation_results['errors']:
            validation_results['is_valid'] = False
            position['validation_status'] = 'failed'
        elif validation_results['warnings']:
            position['validation_status'] = 'warning'
        else:
            position['validation_status'] = 'passed'
        
        position['validation_results'] = validation_results
        
        logger.debug(
            f"Position validated: {position.get('description', 'N/A')[:30]} - "
            f"Status: {position['validation_status']}"
        )
        
        return position
    
    def _validate_concrete(self, specs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate concrete specifications against ČSN EN 206
        
        Checks:
        - Exposure classes are valid
        - Concrete class is sufficient for exposure classes
        - Concrete cover is adequate
        """
        validation = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'info': []
        }
        
        concrete_class = specs.get('concrete_class', '')
        exposure_classes = specs.get('exposure_classes', [])
        concrete_cover = specs.get('concrete_cover_mm')
        
        # Validate exposure classes
        if exposure_classes:
            for exp_class in exposure_classes:
                if exp_class not in self.EXPOSURE_CLASS_MIN_COVER:
                    validation['warnings'].append(
                        f"Neznámá třída expozice: {exp_class} (není v ČSN EN 206)"
                    )
                else:
                    validation['info'].append(
                        f"Třída expozice {exp_class} rozpoznána"
                    )
        
        # Validate concrete class for exposure classes
        if concrete_class and exposure_classes:
            for exp_class in exposure_classes:
                if exp_class in self.EXPOSURE_CLASS_MIN_CONCRETE:
                    required_class = self.EXPOSURE_CLASS_MIN_CONCRETE[exp_class]
                    
                    if not self._is_concrete_class_sufficient(concrete_class, required_class):
                        validation['errors'].append(
                            f"Beton {concrete_class} nedostatečný pro expozici {exp_class}. "
                            f"Minimální požadavek: {required_class} (ČSN EN 206)"
                        )
                    else:
                        validation['info'].append(
                            f"Beton {concrete_class} vyhovuje pro expozici {exp_class}"
                        )
        
        # Validate concrete cover
        if concrete_cover is not None and exposure_classes:
            for exp_class in exposure_classes:
                if exp_class in self.EXPOSURE_CLASS_MIN_COVER:
                    min_cover = self.EXPOSURE_CLASS_MIN_COVER[exp_class]
                    
                    if concrete_cover < min_cover:
                        validation['errors'].append(
                            f"Krytí výztuže {concrete_cover}mm nedostatečné pro {exp_class}. "
                            f"Minimální požadavek: {min_cover}mm (ČSN EN 206)"
                        )
                    else:
                        validation['info'].append(
                            f"Krytí výztuže {concrete_cover}mm vyhovuje pro {exp_class}"
                        )
        
        # Check if cover is specified when exposure classes present
        if exposure_classes and concrete_cover is None:
            validation['warnings'].append(
                "Krytí výztuže není specifikováno, ale jsou definovány třídy expozice"
            )
        
        return validation
    
    def _validate_reinforcement(self, specs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate reinforcement specifications
        
        Checks:
        - Steel class is valid
        - Diameter is reasonable
        """
        validation = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'info': []
        }
        
        steel_class = specs.get('steel_class', '')
        diameter = specs.get('diameter_mm')
        
        # Validate steel class
        valid_steel_classes = ['B500A', 'B500B', 'B500C']
        
        if steel_class:
            if steel_class in valid_steel_classes:
                validation['info'].append(
                    f"Třída oceli {steel_class} rozpoznána (ČSN EN 1992)"
                )
            else:
                validation['warnings'].append(
                    f"Neznámá třída oceli: {steel_class}. "
                    f"Běžné třídy: {', '.join(valid_steel_classes)}"
                )
        
        # Validate diameter
        if diameter:
            if diameter < 6 or diameter > 40:
                validation['warnings'].append(
                    f"Neobvyklý průměr výztuže: {diameter}mm. "
                    f"Běžný rozsah: 6-40mm"
                )
            else:
                validation['info'].append(
                    f"Průměr výztuže {diameter}mm je v běžném rozsahu"
                )
        
        return validation
    
    def _is_concrete_class_sufficient(
        self,
        actual_class: str,
        required_class: str
    ) -> bool:
        """
        Check if actual concrete class is sufficient compared to required
        
        Args:
            actual_class: Actual concrete class (e.g., "C30/37")
            required_class: Required minimum class (e.g., "C25/30")
            
        Returns:
            True if actual >= required
        """
        actual_strength = self.CONCRETE_CLASS_STRENGTH.get(actual_class.upper())
        required_strength = self.CONCRETE_CLASS_STRENGTH.get(required_class.upper())
        
        if actual_strength is None or required_strength is None:
            logger.warning(
                f"Cannot compare concrete classes: {actual_class} vs {required_class}"
            )
            return True  # Assume OK if cannot compare
        
        return actual_strength >= required_strength
    
    def _merge_validation(
        self,
        target: Dict[str, Any],
        source: Dict[str, Any]
    ):
        """Merge validation results from source into target"""
        target['warnings'].extend(source['warnings'])
        target['errors'].extend(source['errors'])
        target['info'].extend(source['info'])
        
        if source['errors']:
            target['is_valid'] = False
    
    def validate_positions_batch(
        self,
        positions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Validate multiple positions
        
        Args:
            positions: List of positions to validate
            
        Returns:
            List of positions with validation results
        """
        logger.info(f"Validating {len(positions)} positions...")
        
        validated = []
        stats = {
            'passed': 0,
            'warning': 0,
            'failed': 0,
            'no_specs': 0
        }
        
        for position in positions:
            validated_position = self.validate_position(position)
            validated.append(validated_position)
            
            status = validated_position.get('validation_status', 'no_specs')
            stats[status] = stats.get(status, 0) + 1
        
        logger.info(
            f"✅ Validation complete: "
            f"passed={stats['passed']}, "
            f"warning={stats['warning']}, "
            f"failed={stats['failed']}, "
            f"no_specs={stats['no_specs']}"
        )
        
        return validated


# ==============================================================================
# USAGE EXAMPLE
# ==============================================================================

if __name__ == "__main__":
    import json
    
    # Example position with technical specs
    position = {
        "position_number": "1.1",
        "description": "základní deska C30/37",
        "quantity": 89,
        "unit": "m³",
        "technical_specs": {
            "concrete_class": "C30/37",
            "exposure_classes": ["XA1", "XC2", "XF2"],
            "concrete_cover_mm": 50,
            "surface_finish": "hladká"
        }
    }
    
    validator = SpecificationsValidator()
    validated = validator.validate_position(position)
    
    print("\n✅ Validation Result:")
    print(json.dumps(validated, ensure_ascii=False, indent=2))
