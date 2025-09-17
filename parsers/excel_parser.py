import pandas as pd

def parse_excel(path: str) -> dict[str, pd.DataFrame]:
    xls = pd.ExcelFile(path)
    return {sh: xls.parse(sh) for sh in xls.sheet_names}
