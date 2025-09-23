"""
smeta_parser.py
Парсинг смет (XML, Excel, CSV).
"""
import pandas as pd
import pathlib
from .xml_smeta_parser import parse_xml_smeta

def extract_smeta_positions(path):
    ext = pathlib.Path(path).suffix.lower()
    
    if ext == ".xml":
        return parse_xml_smeta(path)
    elif ext in [".xls", ".xlsx"]:
        df = pd.read_excel(path)
    elif ext == ".csv":
        df = pd.read_csv(path)
    else:
        return []

    # Нормализуем заголовки
    df.columns = [str(c).strip().lower() for c in df.columns]
    
    name_col = next((c for c in df.columns if any(keyword in c for keyword in [
        "položka", "polozka", "name", "název", "nazev", "popis", "description"
    ])), None)
    if not name_col:
        return []
    
    if name_col != "name":
        df = df.rename(columns={name_col: "name"})
    
    return df.to_dict(orient="records")
