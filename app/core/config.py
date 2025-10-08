"""
Configuration for Czech Building Audit System
UPDATED: Compatible with new .env.example
"""
from pathlib import Path
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MultiRoleConfig(BaseSettings):
    """Multi-Role Expert System Configuration"""
    
    enabled: bool = Field(default=True, description="Enable multi-role analysis")
    
    # Adaptive depth per classification
    green_roles: List[str] = Field(
        default=["SME", "ARCH_LIGHT", "ENG_LIGHT", "SUP_LIGHT"],
        description="Roles for GREEN classification"
    )
    amber_roles: List[str] = Field(
        default=["SME", "ARCH", "ENG", "SUP_LIGHT"],
        description="Roles for AMBER classification"
    )
    red_roles: List[str] = Field(
        default=["SME", "ARCH", "ENG", "SUP"],
        description="Roles for RED classification"
    )
    
    # HITL triggers
    hitl_on_red: bool = Field(
        default=True,
        description="Require HITL for RED classifications"
    )
    hitl_price_threshold: float = Field(
        default=0.15,
        description="Price difference threshold for HITL (0.15 = 15%)"
    )
    hitl_on_conflict_levels: List[int] = Field(
        default=[1, 2],
        description="Priority levels that trigger HITL (1=Safety, 2=Structural)"
    )
    
    # Consensus rules
    require_agreement_roles: List[str] = Field(
        default=["ENG", "SME"],
        description="Roles that must agree"
    )
    consensus_max_iterations: int = Field(
        default=3,
        description="Max iterations for consensus"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="MULTI_ROLE_",
        case_sensitive=False
    )


class Settings(BaseSettings):
    """Main application settings"""
    
    # ==========================================
    # PROJECT PATHS
    # ==========================================
    BASE_DIR: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent
    )
    DATA_DIR: Path = Field(default=None)
    KB_DIR: Path = Field(default=None)
    PROMPTS_DIR: Path = Field(default=None)
    LOGS_DIR: Path = Field(default=None)
    WEB_DIR: Path = Field(default=None)
    
    # ==========================================
    # API KEYS (REQUIRED)
    # ==========================================
    ANTHROPIC_API_KEY: str = Field(default="", description="Anthropic Claude API key")
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key (optional)")
    
    # ==========================================
    # AI MODELS
    # ==========================================
    CLAUDE_MODEL: str = Field(
        default="claude-sonnet-4-20250514",
        description="Claude model to use"
    )
    GPT4_MODEL: str = Field(
        default="gpt-4-vision-preview",
        description="GPT-4 model to use"
    )
    CLAUDE_MAX_TOKENS: int = Field(default=4000, description="Max tokens for Claude")
    GPT4_MAX_TOKENS: int = Field(default=4000, description="Max tokens for GPT-4")
    
    # ==========================================
    # WORKFLOW FEATURE FLAGS
    # ==========================================
    ENABLE_WORKFLOW_A: bool = Field(
        default=True,
        description="Enable Workflow A (with výkaz)"
    )
    ENABLE_WORKFLOW_B: bool = Field(
        default=False,
        description="Enable Workflow B (without výkaz)"
    )
    ENABLE_KROS_MATCHING: bool = Field(
        default=True,
        description="Enable KROS code matching"
    )
    ENABLE_RTS_MATCHING: bool = Field(
        default=True,
        description="Enable RTS code matching"
    )
    ENABLE_RESOURCE_CALCULATION: bool = Field(
        default=True,
        description="Enable resource calculation (TOV)"
    )
    
    # ==========================================
    # RESOURCE CALCULATION
    # ==========================================
    ALLOW_WEB_SEARCH: bool = Field(
        default=True,
        description="Allow web search for equipment specs"
    )
    USE_OFFICIAL_NORMS: bool = Field(
        default=True,
        description="Prefer official norms over practical rates"
    )
    
    # ==========================================
    # AUDIT CONFIGURATION
    # ==========================================
    AUDIT_GREEN_THRESHOLD: float = Field(
        default=0.80,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for GREEN (0.8 = 80%)"
    )
    AUDIT_AMBER_THRESHOLD: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for AMBER (0.5 = 50%)"
    )
    
    # ==========================================
    # PRICES CONFIGURATION
    # ==========================================
    AUTO_UPDATE_PRICES: bool = Field(
        default=False,
        description="Auto-update prices from sources"
    )
    PRICE_UPDATE_INTERVAL_DAYS: int = Field(
        default=90,
        description="Days between price updates"
    )
    
    # ==========================================
    # LOGGING
    # ==========================================
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG/INFO/WARNING/ERROR)"
    )
    LOG_CLAUDE_CALLS: bool = Field(
        default=True,
        description="Log all Claude API calls"
    )
    LOG_GPT4_CALLS: bool = Field(
        default=True,
        description="Log all GPT-4 API calls"
    )
    
    # ==========================================
    # ENVIRONMENT
    # ==========================================
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment type (development/production)"
    )
    DEBUG: bool = Field(
        default=False,
        description="Debug mode (verbose logging)"
    )
    
    # ==========================================
    # MULTI-ROLE CONFIGURATION
    # ==========================================
    multi_role: MultiRoleConfig = Field(default_factory=MultiRoleConfig)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra fields from .env
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Set default paths if not provided
        if self.DATA_DIR is None:
            self.DATA_DIR = self.BASE_DIR / "data"
        if self.KB_DIR is None:
            self.KB_DIR = self.BASE_DIR / "app" / "knowledge_base"
        if self.PROMPTS_DIR is None:
            self.PROMPTS_DIR = self.BASE_DIR / "app" / "prompts"
        if self.LOGS_DIR is None:
            self.LOGS_DIR = self.BASE_DIR / "logs"
        if self.WEB_DIR is None:
            self.WEB_DIR = self.BASE_DIR / "web"
        
        # Create directories if they don't exist
        self.DATA_DIR.mkdir(exist_ok=True)
        (self.DATA_DIR / "raw").mkdir(exist_ok=True)
        (self.DATA_DIR / "processed").mkdir(exist_ok=True)
        (self.DATA_DIR / "results").mkdir(exist_ok=True)
        self.LOGS_DIR.mkdir(exist_ok=True)
        (self.LOGS_DIR / "claude_calls").mkdir(exist_ok=True)
        (self.LOGS_DIR / "gpt4_calls").mkdir(exist_ok=True)
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT.lower() == "development"


# Global settings instance
settings = Settings()

# Validation on import
if not settings.ANTHROPIC_API_KEY and settings.ENABLE_WORKFLOW_A:
    import warnings
    warnings.warn(
        "ANTHROPIC_API_KEY not set! Workflow A will not work. "
        "Set it in .env file or environment variables.",
        RuntimeWarning
    )
