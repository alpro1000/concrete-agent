import re, math

def safe_float(x) -> float | None:
    try:
        return float(str(x).replace(",", ".").replace(" ", ""))
    except:
        return None

def normalize_string(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())
