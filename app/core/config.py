"""
Configuration for Czech Building Audit System
"""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class MultiRoleConfig(BaseSettings):
    """Multi-Role Expert System Configuration"""
    enabled: bool = True
    
    # Adaptive depth per classification
    green_roles: list[str] = ["SME", "ARCH_LIGHT", "ENG_LIGHT", "SUP_LIGHT"]
    amber_roles: list[str] = ["SME", "ARCH", "ENG", "SUP_LIGHT"]
    red_roles: list[str] = ["SME", "ARCH", "ENG", "SUP"]
    
    # HITL triggers
    hitl_on_red: bool = True
    hitl_price_threshold: float = 0.15  # 15% price difference
    hitl_on_conflict_levels: list[int] = [1, 2]  # Safety + Structural
    
    # Consensus rules
    require_agreement_roles: list[str] = ["ENG", "SME"]
    consensus_max_iterations: int = 3
    
    model_config = SettingsConfigDict(env_prefix="MULTI_ROLE_")


class Settings(BaseSettings):
    """Main application settings"""
    
    # Project paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    KB_DIR: Path = BASE_DIR / "app" / "knowledge_base"
    PROMPTS_DIR: Path = BASE_DIR / "app" / "prompts"
    LOGS_DIR: Path = BASE_DIR / "logs"
    WEB_DIR: Path = BASE_DIR / "web"
    
    # API Keys
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    
    # Models
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    GPT4_MODEL: str = "gpt-4-vision-preview"
    
    # Limits
    CLAUDE_MAX_TOKENS: int = 4000
    GPT4_MAX_TOKENS: int = 4000
    
    # Feature Flags
    ENABLE_WORKFLOW_A: bool = True
    ENABLE_WORKFLOW_B: bool = True
    ENABLE_KROS_MATCHING: bool = True
    ENABLE_RTS_MATCHING: bool = True
    ENABLE_RESOURCE_CALCULATION: bool = True
    
    # Resource Calculation
    ALLOW_WEB_SEARCH: bool = True  # Allow searching for equipment specs
    USE_OFFICIAL_NORMS: bool = True  # Prefer official norms if available
    
    # Prices Update
    AUTO_UPDATE_PRICES: bool = False
    PRICE_UPDATE_INTERVAL_DAYS: int = 90
    
    # Multi-role configuration
    multi_role: MultiRoleConfig = MultiRoleConfig()
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if they don't exist
        self.DATA_DIR.mkdir(exist_ok=True)
        (self.DATA_DIR / "raw").mkdir(exist_ok=True)
        (self.DATA_DIR / "processed").mkdir(exist_ok=True)
        (self.DATA_DIR / "results").mkdir(exist_ok=True)
        self.LOGS_DIR.mkdir(exist_ok=True)


# Global settings instance
settings = Settings()
