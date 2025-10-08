"""
Configuration for Czech Building Audit System
FIXED: Proper Path defaults for Render deployment
"""
from pathlib import Path
from typing import Optional
from pydantic import Field
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
    hitl_price_threshold: float = 0.15
    hitl_on_conflict_levels: list[int] = [1, 2]
    
    # Consensus rules
    require_agreement_roles: list[str] = ["ENG", "SME"]
    consensus_max_iterations: int = 3
    
    model_config = SettingsConfigDict(env_prefix="MULTI_ROLE_")


class Settings(BaseSettings):
    """Main application settings"""
    
    # ==========================================
    # BASE PATH - вычисляется динамически
    # ==========================================
    @property
    def BASE_DIR(self) -> Path:
        """Base directory of the project"""
        return Path(__file__).resolve().parent.parent.parent
    
    # ==========================================
    # PROJECT PATHS - используют BASE_DIR
    # ==========================================
    # Эти поля теперь Optional и вычисляются в __init__
    DATA_DIR: Optional[Path] = None
    KB_DIR: Optional[Path] = None
    PROMPTS_DIR: Optional[Path] = None
    LOGS_DIR: Optional[Path] = None
    WEB_DIR: Optional[Path] = None
    
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
        default=False,
        description="Allow web search for missing norms"
    )
    USE_OFFICIAL_NORMS: bool = Field(
        default=True,
        description="Prioritize official Czech norms"
    )
    
    # ==========================================
    # AUDIT CONFIGURATION
    # ==========================================
    AUDIT_GREEN_THRESHOLD: float = Field(
        default=0.95,
        description="Threshold for GREEN classification"
    )
    AUDIT_AMBER_THRESHOLD: float = Field(
        default=0.75,
        description="Threshold for AMBER classification"
    )
    
    # ==========================================
    # PRICE MANAGEMENT
    # ==========================================
    AUTO_UPDATE_PRICES: bool = Field(
        default=False,
        description="Auto-update prices from sources"
    )
    PRICE_UPDATE_INTERVAL_DAYS: int = Field(
        default=90,
        description="Price update interval in days"
    )
    
    # ==========================================
    # LOGGING
    # ==========================================
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_CLAUDE_CALLS: bool = Field(default=True, description="Log Claude API calls")
    LOG_GPT4_CALLS: bool = Field(default=True, description="Log GPT-4 API calls")
    
    # ==========================================
    # ENVIRONMENT
    # ==========================================
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment: development, staging, production"
    )
    
    # ==========================================
    # MULTI-ROLE CONFIGURATION
    # ==========================================
    multi_role: MultiRoleConfig = Field(default_factory=MultiRoleConfig)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    def __init__(self, **kwargs):
        """Initialize settings with proper path defaults"""
        super().__init__(**kwargs)
        
        # Set paths if not provided via environment
        base = self.BASE_DIR
        
        if self.DATA_DIR is None:
            self.DATA_DIR = base / "data"
        if self.KB_DIR is None:
            self.KB_DIR = base / "app" / "knowledge_base"
        if self.PROMPTS_DIR is None:
            self.PROMPTS_DIR = base / "app" / "prompts"
        if self.LOGS_DIR is None:
            self.LOGS_DIR = base / "logs"
        if self.WEB_DIR is None:
            self.WEB_DIR = base / "web"
        
        # Create directories if they don't exist
        try:
            self.DATA_DIR.mkdir(parents=True, exist_ok=True)
            (self.DATA_DIR / "raw").mkdir(exist_ok=True)
            (self.DATA_DIR / "processed").mkdir(exist_ok=True)
            (self.DATA_DIR / "results").mkdir(exist_ok=True)
            
            self.LOGS_DIR.mkdir(parents=True, exist_ok=True)
            (self.LOGS_DIR / "claude_calls").mkdir(exist_ok=True)
            (self.LOGS_DIR / "gpt4_calls").mkdir(exist_ok=True)
        except Exception as e:
            import warnings
            warnings.warn(f"Could not create directories: {e}")
    
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
        UserWarning
    )
