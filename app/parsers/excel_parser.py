from pathlib import Path
import pandas as pd
from typing import List, Dict


class ExcelParser:
    def parse(self, excel_path: Path) -> List[Dict]:
        df = pd.read_excel(excel_path, dtype=str)
        items: List[Dict] = []
        for _, row in df.iterrows():
            quantity_raw = row.get("Množství")
            quantity_str = str(quantity_raw).strip() if quantity_raw is not None else ""
            price_raw = row.get("Cena")
            price_str = str(price_raw).strip() if price_raw is not None else ""

            quantity = (
                float(quantity_str.replace(",", "."))
                if quantity_str and quantity_str.lower() != "nan"
                else 0.0
            )
            unit_price = (
                float(price_str.replace(",", "."))
                if price_str and price_str.lower() != "nan"
                else None
            )

            items.append({
                "position_number": row.get("Pozice"),
                "code": row.get("Kód"),
                "description": row.get("Popis"),
                "unit": row.get("MJ"),
                "quantity": quantity,
                "unit_price": unit_price,
            })
        return items


__all__ = ["ExcelParser"]
