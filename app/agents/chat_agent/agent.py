"""
Chat Agent - Conversational AI Interface
Provides conversational interface for natural language queries about projects
"""

from typing import Dict, Any, List, Optional
import logging
import json
from pathlib import Path
import sys

logger = logging.getLogger(__name__)


class ChatAgent:
    """
    Chat Agent
    
    Provides:
    - Natural language queries
    - Context-aware responses
    - Multi-turn conversations
    - Project-specific assistance
    """
    
    name = "chat_agent"
    supported_types = [
        "chat",
        "conversation",
        "query",
        "qa"
    ]
    
    def __init__(self):
        """Initialize Chat Agent"""
        sys.path.append('/home/runner/work/concrete-agent/concrete-agent')
        
        try:
            from app.core.llm_service import get_llm_service
            from app.core.prompt_loader import get_prompt_loader
            self.llm_service = get_llm_service()
            self.prompt_loader = get_prompt_loader()
            self.use_llm_service = True
            logger.info("ChatAgent initialized with LLM service")
        except Exception as e:
            logger.warning(f"Failed to load LLM service: {e}")
            self.use_llm_service = False
        
        self.conversation_history = {}
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for chat"""
        return """Jsi Stav Agent - inteligentní asistent pro stavební projekty.

Pomáháš uživatelům s:
- Analýzou technických zadání
- Výkladem norem a standardů (ČSN EN, ГОСТ, СНиП)
- Odhadem materiálů a nákladů
- Plánováním stavebních prací
- Technickými dotazy ke stavebnictví

Odpovídej v češtině, pokud není požadován jiný jazyk.
Buď konkrétní, profesionální a užitečný.
Pokud nevíš odpověď, přiznej to a navrhni alternativu."""
    
    def _build_conversation_context(self, conversation_id: str, project_context: Optional[Dict[str, Any]] = None) -> str:
        """Build context from conversation history and project data"""
        context_parts = []
        
        # Add project context if available
        if project_context:
            if "project_object" in project_context:
                context_parts.append(f"Projekt: {project_context['project_object']}")
            
            if "requirements" in project_context and project_context["requirements"]:
                context_parts.append(f"Požadavky: {', '.join(project_context['requirements'][:3])}")
            
            if "total_cost" in project_context:
                context_parts.append(f"Rozpočet: {project_context['total_cost']} CZK")
        
        # Add recent conversation history
        if conversation_id in self.conversation_history:
            history = self.conversation_history[conversation_id]
            for turn in history[-3:]:  # Last 3 turns
                context_parts.append(f"Uživatel: {turn['user']}")
                context_parts.append(f"Agent: {turn['assistant']}")
        
        return "\n".join(context_parts)
    
    async def _get_llm_response(self, message: str, context: str, provider: str = "claude") -> str:
        """Get response from LLM service"""
        if not self.use_llm_service:
            return "Chat je dočasně nedostupný. Zkuste to prosím později."
        
        try:
            system_prompt = self._get_system_prompt()
            if context:
                system_prompt += f"\n\nKontext projektu:\n{context}"
            
            response = await self.llm_service.run_prompt(
                provider=provider,
                prompt=message,
                system_prompt=system_prompt,
                max_tokens=1000
            )
            
            if response.get("success"):
                return response.get("content", "Nepodařilo se získat odpověď.")
            else:
                logger.error(f"LLM service error: {response.get('error')}")
                return "Omlouvám se, vyskytla se chyba. Zkuste otázku přeformulovat."
        
        except Exception as e:
            logger.error(f"Chat LLM request failed: {e}")
            return "Omlouvám se, vyskytla se technická chyba."
    
    def _save_conversation_turn(self, conversation_id: str, user_message: str, assistant_response: str):
        """Save conversation turn to history"""
        if conversation_id not in self.conversation_history:
            self.conversation_history[conversation_id] = []
        
        self.conversation_history[conversation_id].append({
            "user": user_message,
            "assistant": assistant_response
        })
        
        # Keep only last 10 turns
        if len(self.conversation_history[conversation_id]) > 10:
            self.conversation_history[conversation_id] = self.conversation_history[conversation_id][-10:]
    
    async def analyze(self, chat_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle chat conversation.
        
        Args:
            chat_request: Dictionary with:
                - message: User message
                - conversation_id: Conversation identifier
                - project_context: Optional project data for context
                - provider: LLM provider (claude/openai)
            
        Returns:
            Dictionary with chat response
        """
        try:
            message = chat_request.get("message", "")
            conversation_id = chat_request.get("conversation_id", "default")
            project_context = chat_request.get("project_context")
            provider = chat_request.get("provider", "claude")
            
            if not message:
                return {
                    "response": "Prosím zadejte zprávu.",
                    "processing_metadata": {
                        "agent": self.name,
                        "status": "empty_message"
                    }
                }
            
            # Build context
            context = self._build_conversation_context(conversation_id, project_context)
            
            # Get LLM response
            response = await self._get_llm_response(message, context, provider)
            
            # Save to history
            self._save_conversation_turn(conversation_id, message, response)
            
            result = {
                "response": response,
                "conversation_id": conversation_id,
                "turn_number": len(self.conversation_history.get(conversation_id, [])),
                "processing_metadata": {
                    "agent": self.name,
                    "provider": provider,
                    "status": "success"
                }
            }
            
            logger.info(f"Chat response generated for conversation {conversation_id}")
            return result
            
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            return {
                "response": "Omlouvám se, vyskytla se chyba při zpracování vaší zprávy.",
                "error": str(e),
                "processing_metadata": {
                    "agent": self.name,
                    "status": "failed"
                }
            }
    
    def supports_type(self, file_type: str) -> bool:
        """Check if this agent supports a given file type"""
        return file_type.lower() in [t.lower() for t in self.supported_types]
    
    def __repr__(self) -> str:
        """String representation of the agent"""
        return f"ChatAgent(name='{self.name}', supported_types={self.supported_types})"
