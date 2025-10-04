"""
Chat API Router
Provides conversational interface for project assistance
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class ChatMessage(BaseModel):
    """Chat message model"""
    message: str
    conversation_id: Optional[str] = "default"
    project_context: Optional[Dict[str, Any]] = None
    provider: Optional[str] = "claude"


@router.get("/")
async def chat_root():
    """Chat API information"""
    return {
        "service": "Chat API",
        "version": "1.0.0",
        "description": "Conversational interface for construction project assistance",
        "endpoints": {
            "chat": "POST /api/v1/chat/message"
        }
    }


@router.post("/message")
async def send_message(chat_msg: ChatMessage):
    """
    Send a chat message and get AI response
    
    - **message**: User message
    - **conversation_id**: Conversation identifier (optional)
    - **project_context**: Project data for context (optional)
    - **provider**: LLM provider - claude or openai (optional, default: claude)
    """
    try:
        from app.agents.chat_agent import ChatAgent
        
        agent = ChatAgent()
        result = await agent.analyze({
            "message": chat_msg.message,
            "conversation_id": chat_msg.conversation_id,
            "project_context": chat_msg.project_context,
            "provider": chat_msg.provider
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Chat message failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
