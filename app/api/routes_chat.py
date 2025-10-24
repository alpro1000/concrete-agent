"""
Chat API Routes
Interactive conversational interface with AI agents
"""
from typing import Any, Dict, Optional, Tuple
from datetime import datetime
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.state.project_store import project_store
from app.models.project import ProjectStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ============================================================================
# ARTIFACT HELPERS
# ============================================================================


def _current_timestamp() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _artifact_metadata(project: Dict[str, Any], generated_by: str = "system") -> Dict[str, Any]:
    return {
        "generated_at": _current_timestamp(),
        "project_id": project.get("project_id") or project.get("id"),
        "project_name": project.get("project_name") or project.get("name"),
        "generated_by": generated_by,
    }


def _artifact_actions(project: Dict[str, Any], artifact_type: str) -> list[Dict[str, Any]]:
    project_id = project.get("project_id") or project.get("id") or "project"
    base_path = f"/api/projects/{project_id}/artifacts/{artifact_type}"
    return [
        {
            "id": "export_pdf",
            "label": "Stáhnout PDF",
            "icon": "📥",
            "endpoint": f"{base_path}/export?format=pdf",
        },
        {
            "id": "export_excel",
            "label": "Exportovat XLSX",
            "icon": "📊",
            "endpoint": f"{base_path}/export?format=xlsx",
        },
        {"id": "share", "label": "Sdílet", "icon": "🔗"},
    ]


def _build_audit_positions_artifact(
    project: Dict[str, Any],
    options: Optional[Dict[str, Any]] = None,
    *,
    generated_by: str = "system",
) -> Tuple[str, Dict[str, Any]]:
    opts = options or {}
    positions_total = project.get("positions_total") or 145
    verified = project.get("green_count") or 132
    warnings = project.get("amber_count") or 10
    critical = project.get("red_count") or 3

    data = {
        "status": "WARNING" if critical else "OK",
        "summary": f"Zkontrolováno {positions_total} pozic. {critical} kritických, {warnings} s varováním.",
        "statistics": {
            "total_positions": positions_total,
            "verified": verified,
            "with_warnings": warnings,
            "critical_issues": critical,
        },
        "issues": [
            {
                "position_id": "pos-001",
                "code": "214125",
                "description": "Armatura 10505",
                "severity": "RED",
                "problem": "Kód nenalezen v OTSKP",
                "suggestion": "Doporučujeme prověřit OTSKP 222xxx",
                "sources": ["OTSKP v2024", "Internal KB"],
            },
            {
                "position_id": "pos-002",
                "code": "305214",
                "description": "Betonáž říms",
                "severity": "AMBER",
                "problem": "Chybí vazba na ČSN 73 1201",
                "suggestion": "Doplnit normu a technologický postup",
                "sources": ["ČSN 73 1201", "Projektová dokumentace"],
            },
        ],
        "statistics_by_severity": {"GREEN": verified, "AMBER": warnings, "RED": critical},
    }

    artifact = {
        "type": "audit_result",
        "title": "Kontrola pozic",
        "data": data,
        "metadata": _artifact_metadata(project, generated_by=generated_by),
        "navigation": {
            "title": "Kontrola pozic - výsledky",
            "sections": [
                {"id": "summary", "label": "Přehled", "icon": "📊"},
                {"id": "issues", "label": "Problémy", "icon": "⚠️"},
                {"id": "details", "label": "Detail", "icon": "🔍"},
            ],
            "active_section": "summary",
        },
        "actions": _artifact_actions(project, "audit_result"),
        "status": "WARNING" if critical else "OK",
        "warnings": [
            {
                "level": "INFO",
                "message": f"Audit proveden s volbami: normy={opts.get('check_norms', True)}, katalog={opts.get('check_catalog', True)}",
            },
            {
                "level": "WARNING",
                "message": "3 pozice vyžadují okamžitou pozornost",
            },
        ],
        "ui_hints": {
            "display_mode": "table",
            "expandable_sections": True,
            "sortable_columns": True,
            "filterable": True,
            "searchable": True,
        },
    }

    response = (
        f"Audit dokončen. Ověřeno {positions_total} pozic, "
        f"kritické: {critical}, varování: {warnings}."
    )
    return response, artifact


def _build_vykaz_vymer_artifact(
    project: Dict[str, Any],
    options: Optional[Dict[str, Any]] = None,
    *,
    generated_by: str = "system",
) -> Tuple[str, Dict[str, Any]]:
    data = {
        "project_name": project.get("project_name", "Most přes potok - fáze 1"),
        "sections": [
            {
                "section_id": "SO-202",
                "section_title": "Monolit a křídla",
                "works": [
                    {
                        "work_id": "w-001",
                        "code": "214125",
                        "description": "Armatura B500B",
                        "unit": "t",
                        "quantity_total": 245.5,
                        "unit_price": 8500,
                        "total_price": 2_086_750,
                        "quantity_by_material": [
                            {"material": "B500B Ø12", "qty": 125.3, "unit": "t"},
                            {"material": "B500B Ø14", "qty": 87.2, "unit": "t"},
                            {"material": "B500B Ø16", "qty": 33.0, "unit": "t"},
                        ],
                    },
                    {
                        "work_id": "w-002",
                        "code": "315204",
                        "description": "Betonáž říms C30/37",
                        "unit": "m3",
                        "quantity_total": 120.0,
                        "unit_price": 2100,
                        "total_price": 252_000,
                        "quantity_by_material": [
                            {"material": "C30/37", "qty": 120, "unit": "m3"},
                        ],
                    },
                ],
                "section_total": 12_450_000,
            }
        ],
        "grand_total": 45_780_000,
        "totals_by_type": {
            "Beton": {"qty": 1200, "unit": "m3"},
            "Armatura": {"qty": 245.5, "unit": "t"},
            "Oppalubka": {"qty": 3500, "unit": "m2"},
        },
    }

    artifact = {
        "type": "vykaz_vymer",
        "title": "Výkaz výměr",
        "data": data,
        "metadata": _artifact_metadata(project, generated_by=generated_by),
        "navigation": {
            "title": "Výkaz výměr - přehled",
            "sections": [
                {"id": "sections", "label": "Sekce", "icon": "🏗️"},
                {"id": "totals", "label": "Souhrny", "icon": "🧮"},
            ],
            "active_section": "sections",
        },
        "actions": _artifact_actions(project, "vykaz_vymer"),
        "status": "OK",
        "warnings": [
            {
                "level": "INFO",
                "message": "Výkaz generován podle sekcí" if options and options.get("by_section", True) else "Výkaz generován bez členění",
            }
        ],
        "ui_hints": {
            "display_mode": "table",
            "expandable_sections": True,
            "sortable_columns": True,
            "filterable": True,
            "searchable": True,
        },
    }

    response = "Výkaz výměr připraven. Dostupné součty podle typů materiálů."
    return response, artifact


def _build_materials_detailed_artifact(
    project: Dict[str, Any],
    options: Optional[Dict[str, Any]] = None,
    *,
    generated_by: str = "system",
) -> Tuple[str, Dict[str, Any]]:
    opts = options or {}
    filter_label = opts.get("filter_by") or opts.get("material_type")
    data = {
        "materials": [
            {
                "id": "mat-001",
                "type": "Beton",
                "brand": "C30/37",
                "characteristics": {
                    "strength": "30 MPa",
                    "workability": "S4",
                    "exposure": "XC3",
                    "slump": "160-210 mm",
                    "density": "2350-2450 kg/m³",
                },
                "norms": ["ČSN EN 206-1", "ČSN 73 1201"],
                "quantity": {"total": 450.0, "unit": "m3"},
                "used_in": [
                    {"section": "SO-202", "work": "Betonáž říms", "qty": 240, "unit": "m3"},
                    {"section": "SO-202", "work": "Betonáž křídel", "qty": 210, "unit": "m3"},
                ],
                "suppliers": [
                    {
                        "name": "Betonářský závod Brno",
                        "distance": "45 km",
                        "price": 2100,
                        "delivery": "Po-Pá",
                    }
                ],
                "sources": ["PDF smlouva.pdf", "Specifikace materiálů.xlsx"],
            },
            {
                "id": "mat-002",
                "type": "Armatura",
                "brand": "B500B",
                "characteristics": {
                    "yield_strength": "500 MPa",
                    "surface_type": "Vlnité",
                    "standards": "ČSN EN 10080",
                },
                "variants": [
                    {"diameter": "Ø10", "qty": 85.3, "unit": "t"},
                    {"diameter": "Ø12", "qty": 125.3, "unit": "t"},
                    {"diameter": "Ø14", "qty": 87.2, "unit": "t"},
                ],
                "total_quantity": 245.5,
                "unit": "t",
                "suppliers": [
                    {
                        "name": "Ocel Servis s.r.o.",
                        "distance": "32 km",
                        "price": 18_500,
                        "delivery": "Expres 48 h",
                    }
                ],
                "sources": ["Materiály.xlsx", "KB Armatura.pdf"],
            },
        ],
        "summary": {
            "total_materials": 24,
            "material_types": ["Beton", "Armatura", "Oppalubka", "Hydroizolace"],
            "total_cost": 1_850_000,
            "critical_materials": ["C30/37", "B500B"],
        },
    }

    artifact = {
        "type": "materials_detailed",
        "title": "Materiály",
        "data": data,
        "metadata": _artifact_metadata(project, generated_by=generated_by),
        "navigation": {
            "title": "Materiály - detailní přehled",
            "sections": [
                {"id": "summary", "label": "Souhrn", "icon": "📦"},
                {"id": "materials", "label": "Materiály", "icon": "🧱"},
            ],
            "active_section": "materials",
        },
        "actions": _artifact_actions(project, "materials_detailed"),
        "status": "OK",
        "warnings": [
            {
                "level": "INFO",
                "message": f"Filtrované podle: {filter_label}" if filter_label else "Bez filtru",
            }
        ],
        "ui_hints": {
            "display_mode": "card",
            "expandable_sections": True,
            "sortable_columns": True,
            "filterable": True,
            "searchable": True,
        },
    }

    response = "Materiálový přehled připraven. Zahrnuje charakteristiky a dodavatele."
    return response, artifact


def _build_resource_sheet_artifact(
    project: Dict[str, Any],
    options: Optional[Dict[str, Any]] = None,
    *,
    generated_by: str = "system",
) -> Tuple[str, Dict[str, Any]]:
    data = {
        "project_name": project.get("project_name", "Most přes potok"),
        "summary": {
            "total_labor_hours": 8450,
            "total_equipment_hours": 2340,
            "total_materials_cost": 45_780_000,
            "estimated_duration_days": 120,
        },
        "by_section": [
            {
                "section": "SO-202",
                "section_title": "Moností a křídla",
                "labor": {
                    "total_hours": 4250,
                    "by_trade": {
                        "Tesař (oppalubka)": {"hours": 1850, "workers": 4, "duration_days": 45},
                        "Zedník (beton)": {"hours": 1200, "workers": 3, "duration_days": 30},
                        "Armovač": {"hours": 800, "workers": 2, "duration_days": 25},
                        "Pomocný pracovník": {"hours": 400, "workers": 2},
                    },
                },
                "equipment": {
                    "total_hours": 1240,
                    "by_type": {
                        "Jeřáb mobilní 60t": {"hours": 480, "daily_rate": 8000},
                        "Autobetonárna": {"hours": 340, "load_m3": 125},
                        "Vibrátor povrchový": {"hours": 280},
                        "Ponorný vibrátor": {"hours": 140},
                    },
                },
                "materials_cost": 23_450_000,
                "timeline": {
                    "start_day": 1,
                    "end_day": 60,
                    "critical_path": "Oppalubka → Armování → Betonáž",
                },
            }
        ],
        "team_composition": {
            "Mistr": 1,
            "Tesaři": 8,
            "Betonáři": 6,
            "Armovači": 4,
            "Pomocníci": 5,
        },
        "equipment_schedule": {
            "Jeřáb mobilní": "Den 1-60 (nepřetržitě)",
            "Autobetonárna": "Den 20-40",
            "Vibrátory": "Den 18-45",
        },
        "cost_breakdown": {
            "Práce": 2_120_000,
            "Technika": 780_000,
            "Materiály": 45_780_000,
            "Režie": 1_200_000,
            "Rezerva": 1_500_000,
        },
    }

    artifact = {
        "type": "resource_sheet",
        "title": "Zdroje",
        "data": data,
        "metadata": _artifact_metadata(project, generated_by=generated_by),
        "navigation": {
            "title": "Zdroje - přehled",
            "sections": [
                {"id": "summary", "label": "Souhrn", "icon": "📊"},
                {"id": "labor", "label": "Práce", "icon": "👷"},
                {"id": "equipment", "label": "Technika", "icon": "🚜"},
            ],
            "active_section": "summary",
        },
        "actions": _artifact_actions(project, "resource_sheet"),
        "status": "OK",
        "warnings": [
            {
                "level": "INFO",
                "message": "Zahrnut harmonogram" if options and options.get("include_timeline", True) else "Harmonogram vynechán",
            }
        ],
        "ui_hints": {
            "display_mode": "card",
            "expandable_sections": True,
            "sortable_columns": False,
            "filterable": True,
            "searchable": True,
        },
    }

    response = "Zdroje vypočteny včetně harmonogramu a nákladů."
    return response, artifact


def _build_project_summary_artifact(
    project: Dict[str, Any],
    options: Optional[Dict[str, Any]] = None,
    *,
    generated_by: str = "system",
) -> Tuple[str, Dict[str, Any]]:
    data = {
        "basic_info": {
            "project_name": project.get("project_name", "Most přes potok - stavba mostovky"),
            "object_type": "Mosty a propustky",
            "investor": "NAKI s.r.o.",
            "designer": "Ing. Novotný",
            "location": "u Brna, okres Brno-venkov",
            "started": "2025-03-01",
            "planned_completion": "2025-09-30",
        },
        "scope": {
            "total_positions": project.get("positions_total", 145),
            "main_sections": ["SO-202", "SO-203", "SO-204"],
            "main_activities": [
                {"activity": "Oppalubka", "qty": 3500, "unit": "m2"},
                {"activity": "Armování", "qty": 245.5, "unit": "t"},
                {"activity": "Betonáž", "qty": 1200, "unit": "m3"},
            ],
        },
        "budget": {
            "total_budget": 50_680_000,
            "breakdown": {
                "Materiály": 45_780_000,
                "Práce": 2_120_000,
                "Technika": 780_000,
                "Režie": 1_200_000,
                "Rezerva": 800_000,
            },
        },
        "kpe": {
            "cost_per_m2": 3_850,
            "duration_weeks": 17,
            "team_size": 24,
            "equipment_count": 8,
            "main_risks": [
                {
                    "risk": "Nepříznivé počasí",
                    "probability": "HIGH",
                    "mitigation": "Provizorní krytí",
                },
                {
                    "risk": "Zpoždění dodavatele",
                    "probability": "MEDIUM",
                    "mitigation": "Smluvní penalizace",
                },
                {
                    "risk": "Nedostatek armovačů",
                    "probability": "MEDIUM",
                    "mitigation": "Externa agentura",
                },
            ],
        },
        "source_documents": {
            "count": 8,
            "types": ["PDF smlouvy", "XLSX rozpočet", "TXT specifikace"],
            "last_updated": "2025-10-20",
        },
        "compliance": {
            "norms_used": ["ČSN EN 206-1", "ČSN 73 1201", "TKP 18"],
            "standards_applied": "Plné",
            "compliance_status": "OK",
        },
        "recommendations": [
            "Zvážit prefabrikované prvky pro urychlení",
            "Zvýšit rezervu na počasí o 2 dny",
            "Připravit záložní tým armovačů",
        ],
    }

    artifact = {
        "type": "project_summary",
        "title": "Shrnutí projektu",
        "data": data,
        "metadata": _artifact_metadata(project, generated_by=generated_by),
        "navigation": {
            "title": "Projekt - shrnutí",
            "sections": [
                {"id": "info", "label": "Informace", "icon": "ℹ️"},
                {"id": "scope", "label": "Rozsah", "icon": "📋"},
                {"id": "budget", "label": "Rozpočet", "icon": "💰"},
            ],
            "active_section": "info",
        },
        "actions": _artifact_actions(project, "project_summary"),
        "status": "OK",
        "warnings": [
            {
                "level": "INFO",
                "message": f"Detail: {options.get('detail_level')}" if options and options.get("detail_level") else "Plný detail",
            }
        ],
        "ui_hints": {
            "display_mode": "card",
            "expandable_sections": True,
            "sortable_columns": False,
            "filterable": False,
            "searchable": True,
        },
    }

    response = "Shrnutí projektu připraveno včetně KPI a rizik."
    return response, artifact


def _build_tech_card_artifact(
    project: Dict[str, Any],
    position_id: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
    *,
    generated_by: str = "system",
) -> Tuple[str, Dict[str, Any]]:
    pos_id = position_id or (options.get("position_id") if options else None)
    data = {
        "work_id": pos_id or "w-001",
        "title": "Bednění říms Bd/C1a",
        "position_code": "214125",
        "description": "Bednění říms - pilíře",
        "steps": [
            {
                "step_num": 1,
                "title": "Příprava podkladu",
                "description": "Očistit povrch od prachu a ošetřit odvlhčujícím činidlem.",
                "duration_minutes": 45,
                "workers": 2,
                "equipment": ["Kartáč drátěný", "Hadice na vodu"],
            },
            {
                "step_num": 2,
                "title": "Osazení bednic",
                "description": "Uložit bednicí desky WBP podle výkresu a zajistit rozpěry.",
                "duration_minutes": 120,
                "workers": 4,
                "equipment": ["Jeřáb mobilní 20t", "Rozpěry"],
            },
            {
                "step_num": 3,
                "title": "Kontrola vertikality",
                "description": "Zkontrolovat svislost a vodorovnost měřidlem.",
                "duration_minutes": 30,
                "workers": 1,
                "equipment": ["Vodováha", "Měřidlo"],
            },
        ],
        "norms": [
            {
                "ref": "ČSN 73 1201",
                "clause": "Kap. 3.2",
                "requirement": "Odchylka od svislosti max. 1:500",
                "tolerance": "±10 mm na 5 m",
            },
            {
                "ref": "TKP 18 Bd pohledový",
                "clause": "Kap. 2.4",
                "requirement": "Kvalita povrchu třídy A",
                "tolerances": ["Nerovnosti ≤ 2 mm na 2 m", "Vlhkost < 15%"],
            },
        ],
        "quality_checks": [
            {
                "check": "Vizuální kontrola povrchu",
                "timing": "Po každé fázi",
                "pass": "Bez viditelných vad",
            },
            {
                "check": "Měření svislosti",
                "timing": "Před betonáží",
                "pass": "Odchylka max. ±10 mm",
            },
        ],
        "safety_requirements": [
            "Práce ve výšce pouze s jištěním",
            "Zákaz vstupu pod zavěšeným břemenem",
            "Osvětlení minimálně 200 lux",
            "Hluk max. 85 dB",
        ],
        "materials_used": [
            {"material": "Bednicí desky WBP", "qty": 140, "unit": "m2"},
            {"material": "Rozpěry d32", "qty": 280, "unit": "ks"},
            {"material": "Odlučovač", "qty": 50, "unit": "l"},
        ],
        "sources": [
            {"type": "NORM", "ref": "ČSN 73 1201"},
            {"type": "NORM", "ref": "TKP 18 Bd pohledový"},
            {"type": "KB", "ref": "Bedenie-teorie-1.2.pdf"},
            {"type": "PROJECT", "ref": "Výkresy D-001, D-002"},
        ],
    }

    artifact = {
        "type": "tech_card",
        "title": "Technologická karta",
        "data": data,
        "metadata": _artifact_metadata(project, generated_by=generated_by),
        "navigation": {
            "title": "Technologická karta",
            "sections": [
                {"id": "steps", "label": "Postup", "icon": "🛠️"},
                {"id": "norms", "label": "Normy", "icon": "📐"},
                {"id": "quality", "label": "Kontroly", "icon": "✅"},
            ],
            "active_section": "steps",
        },
        "actions": _artifact_actions(project, "tech_card"),
        "status": "OK",
        "warnings": [
            {
                "level": "INFO",
                "message": f"Pozice: {pos_id or data['position_code']}",
            }
        ],
        "ui_hints": {
            "display_mode": "timeline",
            "expandable_sections": True,
            "sortable_columns": False,
            "filterable": True,
            "searchable": True,
        },
    }

    response = "Technologická karta připravena včetně kroků a požadavků."
    return response, artifact


def _handle_action(
    action: str,
    project: Dict[str, Any],
    options: Optional[Dict[str, Any]] = None,
    *,
    position_id: Optional[str] = None,
    generated_by: str = "system",
) -> Tuple[str, Dict[str, Any]]:
    if action == "audit_positions":
        return _build_audit_positions_artifact(project, options, generated_by=generated_by)
    if action == "vykaz_vymer":
        return _build_vykaz_vymer_artifact(project, options, generated_by=generated_by)
    if action == "materials_detailed":
        return _build_materials_detailed_artifact(project, options, generated_by=generated_by)
    if action == "resource_sheet":
        return _build_resource_sheet_artifact(project, options, generated_by=generated_by)
    if action == "project_summary":
        return _build_project_summary_artifact(project, options, generated_by=generated_by)
    if action == "tech_card":
        return _build_tech_card_artifact(project, position_id=position_id, options=options, generated_by=generated_by)
    raise ValueError(f"Unknown action: {action}")


def _detect_action_from_query(query: str) -> Tuple[Optional[str], Dict[str, Any]]:
    lowered = query.lower()
    options: Dict[str, Any] = {}

    if "techn" in lowered and "karta" in lowered:
        tokens = [token.strip(",. ") for token in query.split()]
        position = next((token for token in tokens if any(char.isdigit() for char in token)), None)
        if position:
            options["position_id"] = position
        return "tech_card", options

    if "shrn" in lowered or "souhrn" in lowered or "projekt" in lowered:
        options["detail_level"] = "full"
        return "project_summary", options

    if "zdroj" in lowered or "pracovní" in lowered or "pracovnik" in lowered or "pracovníků" in lowered:
        options["include_timeline"] = True
        return "resource_sheet", options

    if "materi" in lowered or "beton" in lowered or "armatur" in lowered:
        if "beton" in lowered:
            options["filter_by"] = "beton"
        return "materials_detailed", options

    if "výkaz" in lowered or "výměr" in lowered or "sumar" in lowered:
        return "vykaz_vymer", options

    if "audit" in lowered or "kontrol" in lowered or "norm" in lowered:
        options["check_norms"] = True
        options["check_catalog"] = True
        return "audit_positions", options

    return None, {}

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class ChatMessageRequest(BaseModel):
    """Request for sending a chat message"""

    project_id: str
    message: str
    include_history: bool = True


class ChatActionRequest(BaseModel):
    """Request for triggering a quick action"""

    project_id: str
    action: str
    position_id: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    free_form_query: Optional[str] = None


class ChatResponse(BaseModel):
    """Unified chat response"""

    response: str
    artifact: Optional[Dict[str, Any]] = None


class CreateProjectRequest(BaseModel):
    """Request for creating a new project"""

    name: str
    workflow: str = "A"


# ============================================================================
# CHAT ENDPOINTS
# ============================================================================


@router.post("/message", response_model=ChatResponse)
async def send_chat_message(request: ChatMessageRequest):
    """
    Send a chat message and get AI response

    The AI can:
    - Answer questions about the project
    - Explain construction standards (ČSN)
    - Provide OTSKP/KROS/RTS code information
    - Analyze positions and materials
    - Suggest improvements

    Example messages:
    - "Co je pozice HSV.001?"
    - "Jaké jsou požadavky ČSN pro beton C25/30?"
    - "Analyzuj materiály v projektu"
    """
    try:
        # Validate project exists
        if request.project_id not in project_store:
            raise HTTPException(404, f"Project {request.project_id} not found")

        project = project_store[request.project_id]

        logger.info(
            f"💬 Chat message from {request.project_id}: "
            f"{request.message[:50]}..."
        )

        detected_action, detected_options = _detect_action_from_query(request.message)

        if detected_action:
            options = dict(detected_options or {})
            position_id = options.pop("position_id", None)
            response_text, artifact = _handle_action(
                detected_action,
                project,
                options=options,
                position_id=position_id,
                generated_by="user_request",
            )
            return ChatResponse(response=response_text, artifact=artifact)

        # Fallback generic response
        return ChatResponse(
            response=(
                f"Zpráva přijata: '{request.message}'. "
                f"Projekt: {project['project_name']} ({project['workflow']}). "
                "Mohu pomoct s auditem, materiály, zdroji nebo technologickými kartami. "
                "Zeptej se konkrétně, například 'Kontrola pozic' nebo 'Technická karta 214125'."
            ),
            artifact=None,
        )

    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover - defensive logging
        logger.error(f"Chat message error: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Chat error: {str(e)}")


@router.post("/action", response_model=ChatResponse)
async def trigger_action(request: ChatActionRequest):
    """
    Trigger a predefined quick action

    Available actions:
    - **audit_positions**: Kontrola pozic podle norem
    - **vykaz_vymer**: Přehled výkazu výměr
    - **materials_detailed**: Detailní seznam materiálů
    - **resource_sheet**: Přehled zdrojů (práce, technika)
    - **project_summary**: Souhrn projektu a KPI
    - **tech_card**: Technologická karta pro pozici

    Returns results with interactive artifact visualization.
    """
    try:
        # Validate project exists
        if request.project_id not in project_store:
            raise HTTPException(404, f"Project {request.project_id} not found")

        project = project_store[request.project_id]

        logger.info(
            f"🎬 Action '{request.action}' triggered for {request.project_id}"
        )

        options = dict(request.options or {})
        if request.free_form_query:
            options.setdefault("free_form_query", request.free_form_query)
        position_id = request.position_id or options.pop("position_id", None)

        try:
            response_text, artifact = _handle_action(
                request.action,
                project,
                options=options,
                position_id=position_id,
                generated_by="system",
            )
        except ValueError:
            raise HTTPException(400, f"Unknown action '{request.action}'")

        return ChatResponse(response=response_text, artifact=artifact)

    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover - defensive logging
        logger.error(f"Action error: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Action failed: {str(e)}")


# ============================================================================
# PROJECT MANAGEMENT (missing from routes.py)
# ============================================================================


@router.post("/projects", response_model=Dict[str, Any])
async def create_project(request: CreateProjectRequest):
    """
    Create a new empty project

    Projects must be created before uploading files.
    After creation, use POST /api/upload to add files.
    """
    try:
        import uuid

        # Generate project ID
        project_id = f"proj_{uuid.uuid4().hex[:12]}"

        # Validate workflow
        workflow = request.workflow.upper()
        if workflow not in ["A", "B"]:
            raise HTTPException(400, "workflow must be 'A' or 'B'")

        logger.info(f"📁 Creating new project: {request.name} ({workflow})")

        # Create project in store
        project_store[project_id] = {
            "project_id": project_id,
            "project_name": request.name,
            "workflow": workflow,
            "status": ProjectStatus.UPLOADED,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "progress": 0,
            "positions_total": 0,
            "positions_processed": 0,
            "green_count": 0,
            "amber_count": 0,
            "red_count": 0,
            "files": {},
            "message": "Project created. Upload files to start processing.",
        }

        return {
            "success": True,
            "project_id": project_id,
            "project_name": request.name,
            "workflow": workflow,
            "status": ProjectStatus.UPLOADED,
            "created_at": datetime.now().isoformat(),
            "message": "Project created successfully",
        }

    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover - defensive logging
        logger.error(f"Create project error: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Failed to create project: {str(e)}")
