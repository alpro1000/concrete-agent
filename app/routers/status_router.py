"""
Status router for system monitoring and health checks.
"""

from fastapi import APIRouter, HTTPException
from app.core import check_db_connection, settings, llm_service
from app.services.registry import agent_registry
from app.core.logging_config import app_logger

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "version": "1.0.0"
    }


@router.get("/status")
async def system_status():
    """
    Get detailed system status.
    
    Returns:
        System status with component health
    """
    db_status = check_db_connection()
    llm_status = llm_service.is_available()
    agents = agent_registry.list_agents()
    
    return {
        "status": "operational" if db_status and llm_status else "degraded",
        "version": "1.0.0",
        "environment": settings.environment,
        "components": {
            "database": "connected" if db_status else "disconnected",
            "llm_service": "available" if llm_status else "unavailable",
            "agent_registry": "operational"
        },
        "agents": agents,
        "agent_count": len(agents)
    }


@router.get("/metrics")
async def get_metrics():
    """
    Get system metrics.
    
    Returns:
        System metrics
    """
    try:
        from app.core.orchestrator import orchestrator
        
        history = orchestrator.get_execution_history(limit=1000)
        
        total_executions = len(history)
        successful_executions = sum(1 for h in history if h.get("success"))
        failed_executions = total_executions - successful_executions
        
        return {
            "executions": {
                "total": total_executions,
                "successful": successful_executions,
                "failed": failed_executions,
                "success_rate": (successful_executions / total_executions * 100) if total_executions > 0 else 0
            },
            "agents": {
                "registered": len(agent_registry.list_agents())
            }
        }
    except Exception as e:
        app_logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_config():
    """
    Get system configuration (non-sensitive).
    
    Returns:
        System configuration
    """
    return {
        "environment": settings.environment,
        "debug": settings.debug,
        "api_host": settings.api_host,
        "api_port": settings.api_port,
        "llm_primary_provider": settings.llm_primary_provider,
        "llm_fallback_provider": settings.llm_fallback_provider,
        "database_type": "postgresql" if "postgresql" in settings.database_url else "sqlite",
        "max_upload_size": settings.max_upload_size,
        "agent_timeout": settings.agent_timeout
    }
