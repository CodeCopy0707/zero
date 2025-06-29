"""
Logging setup for Agent Zero Gemini
"""
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime

from config import config

def setup_logging():
    """Setup logging configuration"""
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.logging.level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for all logs
    file_handler = logging.handlers.RotatingFileHandler(
        filename=config.logging.file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        filename=logs_dir / "errors.log",
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # Agent-specific handler
    agent_handler = logging.handlers.RotatingFileHandler(
        filename=logs_dir / "agents.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    agent_handler.setLevel(logging.DEBUG)
    agent_handler.setFormatter(detailed_formatter)
    
    # Add agent handler to agent loggers
    agent_logger = logging.getLogger("core.agent")
    agent_logger.addHandler(agent_handler)
    
    # Gemini client logger
    gemini_logger = logging.getLogger("core.gemini_client")
    gemini_logger.addHandler(agent_handler)
    
    # Tools logger
    tools_logger = logging.getLogger("core.tools")
    tools_logger.addHandler(agent_handler)
    
    # Memory logger
    memory_logger = logging.getLogger("core.memory")
    memory_logger.addHandler(agent_handler)
    
    # Communication logger
    comm_logger = logging.getLogger("core.communication")
    comm_logger.addHandler(agent_handler)
    
    # Suppress some noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # Log startup message
    startup_logger = logging.getLogger("startup")
    startup_logger.info("=" * 60)
    startup_logger.info(f"Agent Zero Gemini - Logging initialized")
    startup_logger.info(f"Log level: {config.logging.level}")
    startup_logger.info(f"Log file: {config.logging.file}")
    startup_logger.info("=" * 60)
