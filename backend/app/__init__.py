"""
Stav Agent / Concrete Agent
===========================

Modulární inteligentní systém pro analýzu stavebních projektů.
Architektura založená na agenty (TZD, BOQ, Drawing, Resource, Foreman, KnowledgeBase, Chat, Export, UserManager)
s centrálním orchestrátorem a přístupem k LLM (Claude, GPT).

© 2025 Stav Systems. Všechna práva vyhrazena.
"""

from __future__ import annotations
import logging
from pathlib import Path
from dotenv import load_dotenv

# === Inicializace prostředí ===
# ------------------------------------
# Načte proměnné z .env souboru, pokud běžíme lokálně.
load_dotenv()

# === Nastavení logování ===
# ------------------------------------
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("app")
logger.info("✅ Modul 'app' inicializován.")


# === Dynamické načtení modulů ===
# ------------------------------------
# (Nepřímé importy, aby se předešlo cyklickým závislostem)
try:
    import app.core.config  # typ: ignore
    import app.core.database  # typ: ignore
    import app.core.logging_config  # typ: ignore
except ImportError as e:
    logger.warning(f"⚠️  Některé moduly nebylo možné načíst: {e}")


# === Registrace namespace ===
# ------------------------------------
__all__ = [
    "core",
    "models",
    "schemas",
    "routers",
    "agents",
    "services",
    "prompts",
]

# === Informativní banner ===
logger.info(
    "🧠 Stav Agent inicializován.\n"
    "Struktura připravena pro víceagentní orchestraci.\n"
    "Použití vědecké metody: Hypotéza → Analýza → Verifikace → Závěr → Report."
)
