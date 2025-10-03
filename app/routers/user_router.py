"""
User Router - handles user authentication, history, and profile management
"""

from fastapi import APIRouter, HTTPException, Header
from typing import List, Optional
import json
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/user", tags=["user"])

# Mock user data
MOCK_USER = {
    "id": 1,
    "name": "Demo User",
    "email": "demo@stav-agent.com",
    "language": "en",
    "created_at": "2025-01-15T10:00:00Z",
    "token": "mock_jwt_token_12345"
}

STORAGE_BASE = "storage"


def validate_token(authorization: Optional[str]) -> dict:
    """Validate mock JWT token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized - No token provided")
    
    token = authorization.replace("Bearer ", "")
    if token != "mock_jwt_token_12345":
        raise HTTPException(status_code=401, detail="Unauthorized - Invalid token")
    
    return {"user_id": 1}


@router.get("/login")
async def login():
    """Mock login endpoint - returns demo user credentials"""
    logger.info("Mock login request")
    return MOCK_USER


@router.get("/history")
async def get_history(authorization: Optional[str] = Header(None)):
    """Get user's analysis history"""
    user = validate_token(authorization)
    user_id = user["user_id"]
    
    history_path = os.path.join(STORAGE_BASE, str(user_id), "history.json")
    
    try:
        if os.path.exists(history_path):
            with open(history_path, 'r') as f:
                history = json.load(f)
            logger.info(f"Loaded {len(history)} analyses for user {user_id}")
            return history
        else:
            logger.info(f"No history found for user {user_id}")
            return []
    except Exception as e:
        logger.error(f"Error loading history: {e}")
        raise HTTPException(status_code=500, detail="Failed to load history")


@router.delete("/history/{analysis_id}")
async def delete_analysis(analysis_id: str, authorization: Optional[str] = Header(None)):
    """Delete an analysis from user's history"""
    user = validate_token(authorization)
    user_id = user["user_id"]
    
    history_path = os.path.join(STORAGE_BASE, str(user_id), "history.json")
    
    try:
        if not os.path.exists(history_path):
            raise HTTPException(status_code=404, detail="History not found")
        
        with open(history_path, 'r') as f:
            history = json.load(f)
        
        # Filter out the deleted analysis
        updated_history = [h for h in history if h["id"] != analysis_id]
        
        if len(updated_history) == len(history):
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        with open(history_path, 'w') as f:
            json.dump(updated_history, f, indent=2)
        
        logger.info(f"Deleted analysis {analysis_id} for user {user_id}")
        return {"message": "Analysis deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete analysis")
