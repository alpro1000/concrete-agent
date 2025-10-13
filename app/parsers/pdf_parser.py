from pathlib import Path
from typing import List, Dict


class PDFParser:
    def parse(self, pdf_path: Path) -> List[Dict]:
        specs = self.extract_specifications(pdf_path)
        return specs

    def extract_specifications(self, pdf_path: Path) -> List[Dict]:
        return []


__all__ = ["PDFParser"]
