"""
Universal Position Normalizer
Конвертирует позиции из любого формата в стандартный
"""
import logging
from typing import Dict, Any, List, Optional
import re

logger = logging.getLogger(__name__)


class PositionNormalizer:
    """Normalize positions from different sources into standard format"""
    
    # Mapping различных вариантов названий полей к стандартным
    FIELD_MAPPING = {
        # Description field
        "description": "description",
        "desc": "description",
        "popis": "description",
        "opis": "description",
        "nazev": "description",
        "name": "description",
        "text": "description",
        "работа": "description",
        
        # Position number
        "position_number": "position_number",
        "pos_number": "position_number",
        "number": "position_number",
        "cislo": "position_number",
        "c": "position_number",
        "№": "position_number",
        "no": "position_number",
        
        # Code field (KROS/ÚRS)
        "code": "code",
        "kod": "code",
        "kód": "code",
        "urs_code": "code",
        "kros_code": "code",
        
        # Quantity field
        "quantity": "quantity",
        "qty": "quantity",
        "mnozstvi": "quantity",
        "množství": "quantity",
        "amount": "quantity",
        "pocet": "quantity",
        "mn": "quantity",
        "количество": "quantity",
        
        # Unit field
        "unit": "unit",
        "mj": "unit",
        "jednotka": "unit",
        "measure": "unit",
        "ед": "unit",
        
        # Unit price field
        "unit_price": "unit_price",
        "price": "unit_price",
        "cena": "unit_price",
        "cena_jednotkova": "unit_price",
        "jednotkova_cena": "unit_price",
        "price_per_unit": "unit_price",
        "цена": "unit_price",
        
        # Total price field
        "total_price": "total_price",
        "total": "total_price",
        "celkem": "total_price",
        "celkova_cena": "total_price",
        "price_total": "total_price",
        "итого": "total_price",
    }
    
    @classmethod
    def normalize(cls, position: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Normalize a single position to standard format
        
        Args:
            position: Raw position data with any field names
            
        Returns:
            Normalized position or None if invalid
        """
        if not isinstance(position, dict):
            logger.warning(f"Position is not a dict: {type(position)}")
            return None
        
        normalized = {}
        
        # Normalize field names
        for key, value in position.items():
            if not key:
                continue
                
            # Clean key: lowercase, strip whitespace
            clean_key = str(key).lower().strip()
            
            # Map to standard field name
            standard_key = cls.FIELD_MAPPING.get(clean_key, clean_key)
            
            # Clean value
            clean_value = cls._clean_value(value)
            
            if clean_value is not None:
                normalized[standard_key] = clean_value
        
        # Try to extract required fields if missing
        normalized = cls._extract_missing_fields(normalized, position)
        
        # Convert types
        normalized = cls._convert_types(normalized)
        
        # Validate required fields
        if not cls._has_required_fields(normalized):
            logger.debug(
                f"Position missing required fields. "
                f"Available: {list(normalized.keys())}. "
                f"Data: {str(normalized)[:200]}"
            )
            return None
        
        return normalized
    
    @staticmethod
    def _clean_value(value: Any) -> Any:
        """Clean a single value"""
        if value is None:
            return None
        
        # Convert to string and clean
        if isinstance(value, str):
            value = value.strip()
            # Remove multiple spaces
            value = re.sub(r'\s+', ' ', value)
            # Return None for empty strings
            if not value or value in ['', '-', 'N/A', 'null', 'None']:
                return None
        
        return value
    
    @classmethod
    def _extract_missing_fields(
        cls, 
        normalized: Dict[str, Any], 
        original: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Try to extract missing required fields from original data
        
        For example, if 'description' is missing but position has
        a field with 'Beton' in the name, use that.
        """
        
        # If description missing, try to find text-like field
        if 'description' not in normalized or not normalized['description']:
            for key, value in original.items():
                if isinstance(value, str) and len(value) > 5:
                    # Skip numeric-looking fields
                    if not re.match(r'^[\d\s\.,\-]+$', value):
                        normalized['description'] = value
                        logger.debug(f"Extracted description from field '{key}': {value[:50]}")
                        break
        
        # If code missing, try to find code-like field
        if 'code' not in normalized or not normalized['code']:
            for key, value in original.items():
                if isinstance(value, str):
                    # Look for patterns like "121-01-001" or "XXX.XX.XXX"
                    if re.match(r'^\d{2,3}[\-\.]\d{2}[\-\.]\d{3}$', value):
                        normalized['code'] = value
                        logger.debug(f"Extracted code from field '{key}': {value}")
                        break
        
        return normalized
    
    @staticmethod
    def _convert_types(position: Dict[str, Any]) -> Dict[str, Any]:
        """Convert fields to appropriate types"""
        
        # Convert quantity to float
        if 'quantity' in position:
            try:
                # Handle Czech/European number format (comma as decimal)
                qty_str = str(position['quantity']).replace(',', '.').replace(' ', '')
                position['quantity'] = float(qty_str)
            except (ValueError, TypeError):
                logger.warning(f"Cannot convert quantity to float: {position['quantity']}")
                position['quantity'] = 0.0
        
        # Convert unit_price to float
        if 'unit_price' in position:
            try:
                price_str = str(position['unit_price']).replace(',', '.').replace(' ', '')
                position['unit_price'] = float(price_str)
            except (ValueError, TypeError):
                logger.warning(f"Cannot convert unit_price to float: {position['unit_price']}")
                position['unit_price'] = None
        
        # Convert total_price to float
        if 'total_price' in position:
            try:
                total_str = str(position['total_price']).replace(',', '.').replace(' ', '')
                position['total_price'] = float(total_str)
            except (ValueError, TypeError):
                logger.warning(f"Cannot convert total_price to float: {position['total_price']}")
                position['total_price'] = None
        
        return position
    
    @staticmethod
    def _has_required_fields(position: Dict[str, Any]) -> bool:
        """Check if position has all required fields"""
        
        # Minimum required: description and quantity
        has_description = (
            'description' in position and 
            position['description'] and
            len(str(position['description'])) > 0
        )
        
        has_quantity = (
            'quantity' in position and
            position['quantity'] is not None and
            float(position['quantity']) > 0
        )
        
        return has_description and has_quantity
    
    @classmethod
    def normalize_list(cls, positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize a list of positions
        
        Args:
            positions: List of raw position dicts
            
        Returns:
            List of normalized positions (invalid ones filtered out)
        """
        normalized = []
        skipped = 0
        
        for idx, pos in enumerate(positions):
            result = cls.normalize(pos)
            if result:
                # Add index if position_number missing
                if 'position_number' not in result:
                    result['position_number'] = str(idx + 1)
                normalized.append(result)
            else:
                skipped += 1
                logger.debug(f"Skipped position {idx + 1}: {str(pos)[:100]}")
        
        logger.info(
            f"Normalized {len(normalized)} positions "
            f"({skipped} invalid/skipped)"
        )
        
        if skipped > 0:
            logger.warning(
                f"⚠️ {skipped} positions were skipped during normalization. "
                f"Check logs for details."
            )
        
        return normalized


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def normalize_position(position: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Convenience function to normalize a single position
    
    Usage:
        normalized = normalize_position(raw_position)
    """
    return PositionNormalizer.normalize(position)


def normalize_positions(positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convenience function to normalize a list of positions
    
    Usage:
        normalized = normalize_positions(raw_positions)
    """
    return PositionNormalizer.normalize_list(positions)


# ==============================================================================
# USAGE EXAMPLES
# ==============================================================================

if __name__ == "__main__":
    # Example 1: Excel format
    excel_position = {
        "c": "1.1",
        "popis": "Beton C25/30",
        "mnozstvi": "12,5",
        "mj": "m³",
        "cena": "2450"
    }
    
    normalized = normalize_position(excel_position)
    print("Excel format normalized:", normalized)
    # Output: {
    #   'position_number': '1.1',
    #   'description': 'Beton C25/30',
    #   'quantity': 12.5,
    #   'unit': 'm³',
    #   'unit_price': 2450.0
    # }
    
    # Example 2: KROS XML format
    kros_position = {
        "Cislo": "2",
        "Kod": "121-01-001",
        "Popis": "Základové pasy",
        "Mnozstvi": "8.75",
        "MJ": "m³"
    }
    
    normalized = normalize_position(kros_position)
    print("KROS format normalized:", normalized)
    
    # Example 3: PDF table format
    pdf_position = {
        "№": "3",
        "Opis": "Zdivo z tvárnic",
        "MJ": "m²",
        "Množství": "145"
    }
    
    normalized = normalize_position(pdf_position)
    print("PDF format normalized:", normalized)
    
    # Example 4: Invalid position (missing required fields)
    invalid_position = {
        "number": "4",
        "price": "1000"
    }
    
    normalized = normalize_position(invalid_position)
    print("Invalid position:", normalized)  # None
