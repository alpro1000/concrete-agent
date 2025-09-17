import pandas as pd
import pathlib

def extract_smeta_positions(path):
    ext = pathlib.Path(path).suffix.lower()
    if ext in [".xls", ".xlsx"]:
        df = pd.read_excel(path)
    elif ext == ".csv":
        df = pd.read_csv(path)
    else:
        return []

    df.columns = [str(c).strip().lower() for c in df.columns]
    name_col = next((c for c in df.columns if "položka" in c or "name" in c), None)
    return df.to_dict(orient="records") if name_col else []
