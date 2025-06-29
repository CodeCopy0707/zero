"""
Configuration management for Agent Zero Gemini
"""
import os
from typing import Optional, List
from pydantic import BaseSettings, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class GeminiConfig(BaseSettings):
    """Gemini AI configuration"""
    api_key: str = Field(..., env="GEMINI_API_KEY")
    model: str = Field("gemini-2.0-flash-exp", env="GEMINI_MODEL")
    temperature: float = Field(0.7, env="GEMINI_TEMPERATURE")
    max_tokens: int = Field(8192, env="GEMINI_MAX_TOKENS")
    
    class Config:
        env_prefix = "GEMINI_"

class AgentConfig(BaseSettings):
    """Agent configuration"""
    name: str = Field("Agent Zero Gemini", env="AGENT_NAME")
    description: str = Field("A powerful AI agent powered by Gemini AI", env="AGENT_DESCRIPTION")
    max_iterations: int = Field(50, env="MAX_ITERATIONS")
    max_subordinate_agents: int = Field(5, env="MAX_SUBORDINATE_AGENTS")
    memory_limit: int = Field(1000, env="MEMORY_LIMIT")
    
    class Config:
        env_prefix = "AGENT_"

class WebUIConfig(BaseSettings):
    """Web UI configuration"""
    host: str = Field("0.0.0.0", env="WEB_UI_HOST")
    port: int = Field(8080, env="WEB_UI_PORT")
    debug: bool = Field(False, env="WEB_UI_DEBUG")
    
    class Config:
        env_prefix = "WEB_UI_"

class DatabaseConfig(BaseSettings):
    """Database configuration"""
    url: str = Field("sqlite:///./agent_zero.db", env="DATABASE_URL")
    
    class Config:
        env_prefix = "DATABASE_"

class SearchConfig(BaseSettings):
    """Search configuration"""
    engine: str = Field("duckduckgo", env="SEARCH_ENGINE")
    max_results: int = Field(10, env="MAX_SEARCH_RESULTS")
    
    class Config:
        env_prefix = "SEARCH_"

class AudioConfig(BaseSettings):
    """Audio configuration"""
    tts_enabled: bool = Field(True, env="TTS_ENABLED")
    stt_enabled: bool = Field(True, env="STT_ENABLED")
    device_index: int = Field(0, env="AUDIO_DEVICE_INDEX")
    
    class Config:
        env_prefix = "AUDIO_"

class SecurityConfig(BaseSettings):
    """Security configuration"""
    secret_key: str = Field(..., env="SECRET_KEY")
    allowed_hosts: List[str] = Field(["localhost", "127.0.0.1"], env="ALLOWED_HOSTS")
    
    class Config:
        env_prefix = "SECURITY_"

class StorageConfig(BaseSettings):
    """Storage configuration"""
    type: str = Field("json", env="STORAGE_TYPE")
    path: str = Field("./data", env="STORAGE_PATH")
    backup_enabled: bool = Field(True, env="BACKUP_ENABLED")
    backup_interval: int = Field(3600, env="BACKUP_INTERVAL")

    class Config:
        env_prefix = "STORAGE_"

class LoggingConfig(BaseSettings):
    """Logging configuration"""
    level: str = Field("INFO", env="LOG_LEVEL")
    file: str = Field("logs/agent_zero.log", env="LOG_FILE")

    class Config:
        env_prefix = "LOG_"

class Config:
    """Main configuration class"""
    
    def __init__(self):
        self.gemini = GeminiConfig()
        self.agent = AgentConfig()
        self.web_ui = WebUIConfig()
        self.database = DatabaseConfig()
        self.search = SearchConfig()
        self.audio = AudioConfig()
        self.security = SecurityConfig()
        self.storage = StorageConfig()
        self.logging = LoggingConfig()
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return os.getenv("ENVIRONMENT", "development") == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return os.getenv("ENVIRONMENT", "development") == "production"

# Global configuration instance
config = Config()
