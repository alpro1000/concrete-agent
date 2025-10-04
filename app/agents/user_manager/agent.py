"""
User Manager Agent - User Management and Authentication
Handles user authentication, authorization, preferences, and history
"""

from typing import Dict, Any, List, Optional
import logging
import json
from pathlib import Path
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)


class UserManagerAgent:
    """
    User Manager Agent
    
    Manages:
    - User authentication
    - User authorization
    - User preferences
    - Analysis history
    """
    
    name = "user_manager"
    supported_types = [
        "user_management",
        "authentication",
        "user_preferences",
        "user_history"
    ]
    
    def __init__(self):
        """Initialize User Manager Agent"""
        logger.info("UserManagerAgent initialized")
        self.users_file = Path("/home/runner/work/concrete-agent/concrete-agent/storage/users.json")
        self.users_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_users(self) -> Dict[str, Any]:
        """Load users database"""
        if self.users_file.exists():
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load users: {e}")
        
        return {"users": []}
    
    def _save_users(self, users_data: Dict[str, Any]) -> bool:
        """Save users database"""
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(users_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Failed to save users: {e}")
            return False
    
    def _hash_password(self, password: str) -> str:
        """Hash password for storage"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user credentials"""
        users_data = self._load_users()
        password_hash = self._hash_password(password)
        
        for user in users_data.get("users", []):
            if user.get("username") == username and user.get("password_hash") == password_hash:
                return {
                    "user_id": user.get("user_id"),
                    "username": user.get("username"),
                    "email": user.get("email"),
                    "role": user.get("role", "user")
                }
        
        return None
    
    def _create_user(self, username: str, password: str, email: str, role: str = "user") -> Dict[str, Any]:
        """Create new user"""
        users_data = self._load_users()
        
        # Check if user exists
        for user in users_data.get("users", []):
            if user.get("username") == username:
                raise ValueError(f"User '{username}' already exists")
        
        # Create new user
        user_id = f"user_{len(users_data.get('users', [])) + 1}"
        new_user = {
            "user_id": user_id,
            "username": username,
            "password_hash": self._hash_password(password),
            "email": email,
            "role": role,
            "created_at": datetime.now().isoformat(),
            "preferences": {
                "language": "cs",
                "theme": "light"
            },
            "history": []
        }
        
        users_data.setdefault("users", []).append(new_user)
        self._save_users(users_data)
        
        return {
            "user_id": user_id,
            "username": username,
            "email": email,
            "role": role
        }
    
    def _get_user_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's analysis history"""
        users_data = self._load_users()
        
        for user in users_data.get("users", []):
            if user.get("user_id") == user_id:
                return user.get("history", [])
        
        return []
    
    def _update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update user preferences"""
        users_data = self._load_users()
        
        for user in users_data.get("users", []):
            if user.get("user_id") == user_id:
                user.setdefault("preferences", {}).update(preferences)
                return self._save_users(users_data)
        
        return False
    
    async def analyze(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle user management requests.
        
        Args:
            request: Dictionary with:
                - action: Action to perform (authenticate/create/history/preferences)
                - ... action-specific parameters
            
        Returns:
            Dictionary with action results
        """
        try:
            action = request.get("action", "")
            
            if action == "authenticate":
                username = request.get("username")
                password = request.get("password")
                user = self._authenticate_user(username, password)
                
                if user:
                    return {
                        "success": True,
                        "user": user,
                        "processing_metadata": {
                            "agent": self.name,
                            "action": "authenticate"
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": "Invalid credentials",
                        "processing_metadata": {
                            "agent": self.name,
                            "action": "authenticate"
                        }
                    }
            
            elif action == "create":
                username = request.get("username")
                password = request.get("password")
                email = request.get("email")
                role = request.get("role", "user")
                
                user = self._create_user(username, password, email, role)
                return {
                    "success": True,
                    "user": user,
                    "processing_metadata": {
                        "agent": self.name,
                        "action": "create"
                    }
                }
            
            elif action == "history":
                user_id = request.get("user_id")
                history = self._get_user_history(user_id)
                return {
                    "success": True,
                    "history": history,
                    "processing_metadata": {
                        "agent": self.name,
                        "action": "history"
                    }
                }
            
            elif action == "preferences":
                user_id = request.get("user_id")
                preferences = request.get("preferences", {})
                success = self._update_user_preferences(user_id, preferences)
                return {
                    "success": success,
                    "processing_metadata": {
                        "agent": self.name,
                        "action": "preferences"
                    }
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "processing_metadata": {
                        "agent": self.name
                    }
                }
            
        except Exception as e:
            logger.error(f"User management failed: {e}")
            return {
                "success": False,
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
        return f"UserManagerAgent(name='{self.name}', supported_types={self.supported_types})"
