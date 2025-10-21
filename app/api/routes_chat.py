"""
Chat API Routes
Interactive conversational interface with AI agents
"""
from typing import Any, Dict, Optional
from datetime import datetime
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.state.project_store import project_store
from app.models.project import ProjectStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


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

        # TODO: Implement AI chat logic with Claude/GPT
        # For now, return intelligent placeholder based on message content

        message_lower = request.message.lower()

        # Smart responses based on keywords
        if "pozic" in message_lower or "position" in message_lower:
            return ChatResponse(
                response=(
                    f"Projekt '{project['project_name']}' obsahuje "
                    f"{project.get('positions_total', 0)} pozic. "
                    "Mohu provést audit, rozklad nebo analýzu materiálů. "
                    "Co by tě zajímalo?"
                ),
                artifact=None,
            )

        elif "materiál" in message_lower or "material" in message_lower:
            return ChatResponse(
                response=(
                    "Mohu vygenerovat přehled všech materiálů v projektu. "
                    "Klikni na tlačítko 'Materiály' nebo napiš 'zobraz materiály'."
                ),
                artifact=None,
            )

        elif "čsn" in message_lower or "norma" in message_lower:
            return ChatResponse(
                response=(
                    "Mám přístup k aktuálním normám ČSN. "
                    "Můžeš se zeptat na konkrétní normu nebo požadavky, "
                    "například: 'Jaké jsou požadavky pro beton C30/37?'"
                ),
                artifact=None,
            )

        else:
            # Generic response
            return ChatResponse(
                response=(
                    f"Zpráva přijata: '{request.message}'. "
                    f"Projekt: {project['project_name']} ({project['workflow']}). "
                    "Mohu pomoct s auditem, analýzou materiálů nebo technickými dotazy. "
                    "Co potřebuješ zjistit?"
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
    - **audit_positions**: Audit all positions against ČSN standards
    - **breakdown_structure**: Break down SO structure into positions
    - **materials_summary**: Generate complete materials list
    - **calculate_resources**: Calculate labor hours and equipment

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

        # Get audit results if available
        audit_results = project.get("audit_results", {})

        # Action handlers with real data when available
        if request.action == "audit_positions":
            positions_total = project.get("positions_total", 0)
            green = project.get("green_count", 0)
            amber = project.get("amber_count", 0)
            red = project.get("red_count", 0)

            # Check if audit was performed
            if positions_total > 0 and (green + amber + red) > 0:
                # Real audit results
                issues = []
                if audit_results and isinstance(audit_results, dict):
                    preview = audit_results.get("preview", [])
                    for pos in preview[:5]:  # First 5 issues
                        if pos.get("status") == "RED":
                            issues.append(
                                {
                                    "code": pos.get("code", "N/A"),
                                    "description": pos.get("description", ""),
                                    "problem": pos.get(
                                        "validation_message", "Neshoda zjištěna"
                                    ),
                                }
                            )

                return ChatResponse(
                    response=f"Audit dokončen. Zkontrolováno {positions_total} pozic.",
                    artifact={
                        "type": "audit_result",
                        "title": "Výsledky auditu",
                        "data": {
                            "green": green,
                            "amber": amber,
                            "red": red,
                            "issues": issues,
                        },
                    },
                )
            else:
                # Audit not yet performed
                return ChatResponse(
                    response=(
                        "Audit pozic bude proveden. "
                        f"Projekt obsahuje {positions_total} pozic k analýze."
                    ),
                    artifact=None,
                )

        elif request.action == "materials_summary":
            return ChatResponse(
                response="Generuji přehled všech materiálů v projektu...",
                artifact={
                    "type": "materials_summary",
                    "title": "Přehled materiálů",
                    "data": {
                        "materials": [
                            {"name": "Beton C25/30", "quantity": 150, "unit": "m³"},
                            {"name": "Výztuž B500B", "quantity": 8500, "unit": "kg"},
                            {"name": "Bednění", "quantity": 850, "unit": "m²"},
                        ],
                        "total_weight": 150,
                    },
                },
            )

        elif request.action == "breakdown_structure":
            return ChatResponse(
                response="Rozebírám strukturu stavebního objektu na pozice...",
                artifact={
                    "type": "position_breakdown",
                    "title": "Rozklad pozic",
                    "data": {
                        "positions": [
                            {
                                "code": "HSV.001.01",
                                "description": "Výkopy základů",
                                "unit": "m³",
                                "quantity": 250,
                                "materials": [
                                    {"name": "Práce bagrem", "quantity": 40, "unit": "hod"}
                                ],
                            },
                            {
                                "code": "HSV.002.01",
                                "description": "Betonáž základů",
                                "unit": "m³",
                                "quantity": 80,
                                "materials": [
                                    {"name": "Beton C25/30", "quantity": 80, "unit": "m³"},
                                    {"name": "Výztuž", "quantity": 2400, "unit": "kg"},
                                ],
                            },
                        ]
                    },
                },
            )

        elif request.action == "calculate_resources":
            return ChatResponse(
                response="Vypočítávám potřebné zdroje (práce, technika, materiály)...",
                artifact={
                    "type": "resources_calc",
                    "title": "Výpočet zdrojů",
                    "data": {
                        "labor_hours": 480,
                        "equipment": [
                            {"name": "Bagr JCB", "hours": 40},
                            {"name": "Autodomíchávač", "hours": 12},
                        ],
                        "materials_cost": 850000,
                    },
                },
            )

        else:
            # Unknown action
            return ChatResponse(
                response=(
                    "Akce '{request.action}' není rozpoznána. Dostupné akce: "
                    "audit_positions, materials_summary, breakdown_structure, "
                    "calculate_resources"
                ).format(request=request),
                artifact=None,
            )

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
            "status": ProjectStatus.PENDING,
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
            "status": ProjectStatus.PENDING,
            "created_at": datetime.now().isoformat(),
            "message": "Project created successfully",
        }

    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover - defensive logging
        logger.error(f"Create project error: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Failed to create project: {str(e)}")
