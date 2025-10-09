"""
Configuration for Czech Building Audit System
WITH Perplexity API support for live KB
"""
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MultiRoleConfig(BaseSettings):
    """Multi-Role Expert System Configuration"""
    enabled: bool = True
    green_roles: list[str] = ["SME", "ARCH_LIGHT", "ENG_LIGHT", "SUP_LIGHT"]
    amber_roles: list[str] = ["SME", "ARCH", "ENG", "SUP_LIGHT"]
    red_roles: list[str] = ["SME", "ARCH", "ENG", "SUP"]
    hitl_on_red: bool = True
    hitl_price_threshold: float = 0.15
    hitl_on_conflict_levels: list[int] = [1, 2]
    require_agreement_roles: list[str] = ["ENG", "SME"]
    consensus_max_iterations: int = 3
    model_config = SettingsConfigDict(env_prefix="MULTI_ROLE_")


class Settings(BaseSettings):
    """Main application settings"""
    
    @property
    def BASE_DIR(self) -> Path:
        """Base directory of the project"""
        return Path(__file__).resolve().parent.parent.parent
    
    # ==========================================
    # PROJECT PATHS
    # ==========================================
    DATA_DIR: Optional[Path] = None
    KB_DIR: Optional[Path] = None
    PROMPTS_DIR: Optional[Path] = None
    LOGS_DIR: Optional[Path] = None
    WEB_DIR: Optional[Path] = None
    
    # ==========================================
    # API KEYS
    # ==========================================
    ANTHROPIC_API_KEY: str = Field(default="", description="Anthropic Claude API key")
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key (optional)")
    PERPLEXITY_API_KEY: str = Field(default="", description="Perplexity API key for live KB")
    NANONETS_API_KEY: str = Field(default="", description="Nanonets API key for document processing")
    
    # ==========================================
    # AI MODELS
    # ==========================================
    CLAUDE_MODEL: str = Field(default="claude-sonnet-4-20250514", description="Claude model")
    GPT4_MODEL: str = Field(default="gpt-4-vision-preview", description="GPT-4 model")
    CLAUDE_MAX_TOKENS: int = Field(default=4000, description="Max tokens for Claude")
    GPT4_MAX_TOKENS: int = Field(default=4000, description="Max tokens for GPT-4")
    
    # ==========================================
    # WORKFLOW FEATURE FLAGS
    # ==========================================
    ENABLE_WORKFLOW_A: bool = Field(default=True, description="Enable Workflow A")
    ENABLE_WORKFLOW_B: bool = Field(default=False, description="Enable Workflow B")
    ENABLE_KROS_MATCHING: bool = Field(default=True, description="Enable KROS matching")
    ENABLE_RTS_MATCHING: bool = Field(default=True, description="Enable RTS matching")
    ENABLE_RESOURCE_CALCULATION: bool = Field(default=True, description="Enable TOV calculation")
    
    # ==========================================
    # LIVE KNOWLEDGE BASE (Perplexity)
    # ==========================================
    ALLOW_WEB_SEARCH: bool = Field(
        default=True,
        description="Allow Perplexity API for live KB search"
    )
    USE_PERPLEXITY_PRIMARY: bool = Field(
        default=False,
        description="Use Perplexity as primary KB (vs fallback)"
    )
    PERPLEXITY_CACHE_TTL: int = Field(
        default=86400,
        description="Cache TTL for Perplexity results (seconds, default 24h)"
    )
    PERPLEXITY_SEARCH_DOMAINS: list[str] = Field(
        default=["podminky.urs.cz", "urs.cz", "cenovamapa.cz"],
        description="Allowed domains for Perplexity search"
    )
    USE_OFFICIAL_NORMS: bool = Field(
        default=True,
        description="Prioritize official Czech norms"
    )
    
    # ==========================================
    # AUDIT CONFIGURATION
    # ==========================================
    AUDIT_GREEN_THRESHOLD: float = Field(default=0.95, description="GREEN threshold")
    AUDIT_AMBER_THRESHOLD: float = Field(default=0.75, description="AMBER threshold")
    
    # ==========================================
    # PRICE MANAGEMENT
    # ==========================================
    AUTO_UPDATE_PRICES: bool = Field(default=False, description="Auto-update prices")
    
    # ==========================================
    # PARSING CONFIGURATION
    # ==========================================
    PRIMARY_PARSER: str = Field(
        default="claude",
        description="Primary parser: 'mineru', 'nanonets', 'claude'"
    )
    FALLBACK_ENABLED: bool = Field(
        default=True,
        description="Enable fallback to other parsers if primary fails"
    )
    MAX_FILE_SIZE_MB: int = Field(
        default=50,
        description="Maximum file size for upload in MB"
    )
    
    # MinerU Settings
    MINERU_OUTPUT_DIR: Optional[Path] = None
    MINERU_OCR_ENGINE: str = Field(
        default="paddle",
        description="OCR engine for MinerU: 'paddle', 'tesseract'"
    )
    
    # ==========================================
    # RATE LIMITING
    # ==========================================
    CLAUDE_TOKENS_PER_MINUTE: int = Field(
        default=25000,
        description="Claude token limit per minute (safe margin from 30k)"
    )
    GPT4_TOKENS_PER_MINUTE: int = Field(
        default=8000,
        description="GPT-4 token limit per minute (safe margin from 10k)"
    )
    NANONETS_CALLS_PER_MINUTE: int = Field(
        default=80,
        description="Nanonets API calls per minute (safe margin from 100)"
    )
    PRICE_UPDATE_INTERVAL_DAYS: int = Field(default=90, description="Update interval")
    
    # ==========================================
    # LOGGING
    # ==========================================
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_CLAUDE_CALLS: bool = Field(default=True, description="Log Claude calls")
    LOG_GPT4_CALLS: bool = Field(default=True, description="Log GPT-4 calls")
    LOG_PERPLEXITY_CALLS: bool = Field(default=True, description="Log Perplexity calls")
    
    # ==========================================
    # ENVIRONMENT
    # ==========================================
    ENVIRONMENT: str = Field(default="development", description="Environment")
    
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
        if self.MINERU_OUTPUT_DIR is None:
            self.MINERU_OUTPUT_DIR = base / "temp" / "mineru"
        
        try:
            self.DATA_DIR.mkdir(parents=True, exist_ok=True)
            (self.DATA_DIR / "raw").mkdir(exist_ok=True)
            (self.DATA_DIR / "processed").mkdir(exist_ok=True)
            (self.DATA_DIR / "results").mkdir(exist_ok=True)
            
            self.LOGS_DIR.mkdir(parents=True, exist_ok=True)
            (self.LOGS_DIR / "claude_calls").mkdir(exist_ok=True)
            (self.LOGS_DIR / "gpt4_calls").mkdir(exist_ok=True)
            (self.LOGS_DIR / "perplexity_calls").mkdir(exist_ok=True)
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
    
    @property
    def has_perplexity(self) -> bool:
        """Check if Perplexity is configured"""
        return bool(self.PERPLEXITY_API_KEY) and self.ALLOW_WEB_SEARCH


settings = Settings()

# Validation
if not settings.ANTHROPIC_API_KEY and settings.ENABLE_WORKFLOW_A:
    import warnings
    warnings.warn(
        "ANTHROPIC_API_KEY not set! Workflow A will not work.",
        UserWarning
    )

if settings.ALLOW_WEB_SEARCH and not settings.PERPLEXITY_API_KEY:
    import warnings
    warnings.warn(
        "ALLOW_WEB_SEARCH is enabled but PERPLEXITY_API_KEY not set. "
        "Will use local KB only.",
        UserWarning
    )
