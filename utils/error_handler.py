"""
Comprehensive error handling system for Agent Zero Gemini
"""
import logging
import traceback
import sys
from typing import Dict, Any, Optional, Callable, Type
from datetime import datetime
from functools import wraps
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class AgentError(Exception):
    """Base exception for Agent Zero errors"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "AGENT_ERROR"
        self.details = details or {}
        self.timestamp = datetime.now()

class ToolExecutionError(AgentError):
    """Error during tool execution"""
    
    def __init__(self, tool_name: str, message: str, details: Dict[str, Any] = None):
        super().__init__(message, "TOOL_EXECUTION_ERROR", details)
        self.tool_name = tool_name

class CommunicationError(AgentError):
    """Error in agent communication"""
    
    def __init__(self, message: str, sender_id: str = None, receiver_id: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "COMMUNICATION_ERROR", details)
        self.sender_id = sender_id
        self.receiver_id = receiver_id

class MemoryError(AgentError):
    """Error in memory operations"""
    
    def __init__(self, message: str, operation: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "MEMORY_ERROR", details)
        self.operation = operation

class StorageError(AgentError):
    """Error in storage operations"""
    
    def __init__(self, message: str, storage_type: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "STORAGE_ERROR", details)
        self.storage_type = storage_type

class ConfigurationError(AgentError):
    """Error in configuration"""
    
    def __init__(self, message: str, config_key: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "CONFIGURATION_ERROR", details)
        self.config_key = config_key

class ErrorHandler:
    """Comprehensive error handling system"""
    
    def __init__(self, log_errors: bool = True, store_errors: bool = True):
        """Initialize ErrorHandler"""
        self.log_errors = log_errors
        self.store_errors = store_errors
        self.error_storage: List[Dict[str, Any]] = []
        self.error_handlers: Dict[Type[Exception], Callable] = {}
        self.recovery_strategies: Dict[str, Callable] = {}
        
        # Setup default error handlers
        self._setup_default_handlers()
        
        logger.info("Initialized ErrorHandler")
    
    def _setup_default_handlers(self):
        """Setup default error handlers"""
        self.register_handler(ToolExecutionError, self._handle_tool_error)
        self.register_handler(CommunicationError, self._handle_communication_error)
        self.register_handler(MemoryError, self._handle_memory_error)
        self.register_handler(StorageError, self._handle_storage_error)
        self.register_handler(ConfigurationError, self._handle_configuration_error)
        self.register_handler(Exception, self._handle_generic_error)
    
    def register_handler(self, exception_type: Type[Exception], handler: Callable):
        """Register error handler for specific exception type"""
        self.error_handlers[exception_type] = handler
        logger.debug(f"Registered error handler for {exception_type.__name__}")
    
    def register_recovery_strategy(self, error_code: str, strategy: Callable):
        """Register recovery strategy for specific error code"""
        self.recovery_strategies[error_code] = strategy
        logger.debug(f"Registered recovery strategy for {error_code}")
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle an error with appropriate strategy"""
        try:
            # Create error record
            error_record = self._create_error_record(error, context)
            
            # Store error if enabled
            if self.store_errors:
                self.error_storage.append(error_record)
            
            # Log error if enabled
            if self.log_errors:
                self._log_error(error, error_record)
            
            # Find appropriate handler
            handler = self._find_handler(type(error))
            
            # Handle the error
            if handler:
                result = handler(error, error_record, context)
            else:
                result = self._handle_generic_error(error, error_record, context)
            
            # Attempt recovery if strategy exists
            if hasattr(error, 'error_code') and error.error_code in self.recovery_strategies:
                recovery_result = self.recovery_strategies[error.error_code](error, context)
                result.update({"recovery": recovery_result})
            
            return result
            
        except Exception as e:
            # Error in error handling - log and return basic response
            logger.critical(f"Error in error handling: {e}")
            return {
                "success": False,
                "error": "Critical error in error handling system",
                "original_error": str(error),
                "handling_error": str(e)
            }
    
    def _create_error_record(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create comprehensive error record"""
        error_record = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "error_code": getattr(error, 'error_code', 'UNKNOWN'),
            "traceback": traceback.format_exc(),
            "context": context or {},
            "system_info": {
                "python_version": sys.version,
                "platform": sys.platform
            }
        }
        
        # Add specific error details
        if hasattr(error, 'details'):
            error_record["details"] = error.details
        
        if hasattr(error, 'tool_name'):
            error_record["tool_name"] = error.tool_name
        
        if hasattr(error, 'sender_id'):
            error_record["sender_id"] = error.sender_id
        
        if hasattr(error, 'receiver_id'):
            error_record["receiver_id"] = error.receiver_id
        
        return error_record
    
    def _log_error(self, error: Exception, error_record: Dict[str, Any]):
        """Log error with appropriate level"""
        if isinstance(error, (ToolExecutionError, CommunicationError)):
            logger.error(f"{error.error_code}: {error.message}")
        elif isinstance(error, (MemoryError, StorageError)):
            logger.warning(f"{error.error_code}: {error.message}")
        elif isinstance(error, ConfigurationError):
            logger.critical(f"{error.error_code}: {error.message}")
        else:
            logger.error(f"Unhandled error: {error}")
        
        # Log full details at debug level
        logger.debug(f"Error details: {json.dumps(error_record, indent=2)}")
    
    def _find_handler(self, error_type: Type[Exception]) -> Optional[Callable]:
        """Find appropriate error handler"""
        # Check for exact match
        if error_type in self.error_handlers:
            return self.error_handlers[error_type]
        
        # Check for parent class matches
        for registered_type, handler in self.error_handlers.items():
            if issubclass(error_type, registered_type):
                return handler
        
        return None
    
    def _handle_tool_error(self, error: ToolExecutionError, record: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle tool execution errors"""
        return {
            "success": False,
            "error": f"Tool '{error.tool_name}' failed: {error.message}",
            "error_code": error.error_code,
            "tool_name": error.tool_name,
            "suggestion": "Check tool parameters and try again, or use an alternative tool",
            "recoverable": True
        }
    
    def _handle_communication_error(self, error: CommunicationError, record: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle communication errors"""
        return {
            "success": False,
            "error": f"Communication failed: {error.message}",
            "error_code": error.error_code,
            "sender_id": error.sender_id,
            "receiver_id": error.receiver_id,
            "suggestion": "Check agent connectivity and retry communication",
            "recoverable": True
        }
    
    def _handle_memory_error(self, error: MemoryError, record: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle memory errors"""
        return {
            "success": False,
            "error": f"Memory operation failed: {error.message}",
            "error_code": error.error_code,
            "operation": error.operation,
            "suggestion": "Memory system may be corrupted. Consider clearing cache or restarting",
            "recoverable": True
        }
    
    def _handle_storage_error(self, error: StorageError, record: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle storage errors"""
        return {
            "success": False,
            "error": f"Storage operation failed: {error.message}",
            "error_code": error.error_code,
            "storage_type": error.storage_type,
            "suggestion": "Check storage permissions and disk space",
            "recoverable": True
        }
    
    def _handle_configuration_error(self, error: ConfigurationError, record: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle configuration errors"""
        return {
            "success": False,
            "error": f"Configuration error: {error.message}",
            "error_code": error.error_code,
            "config_key": error.config_key,
            "suggestion": "Check configuration file and environment variables",
            "recoverable": False
        }
    
    def _handle_generic_error(self, error: Exception, record: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle generic errors"""
        return {
            "success": False,
            "error": f"Unexpected error: {str(error)}",
            "error_code": "GENERIC_ERROR",
            "error_type": type(error).__name__,
            "suggestion": "This is an unexpected error. Please report it to the developers",
            "recoverable": False
        }
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics"""
        if not self.error_storage:
            return {"total_errors": 0}
        
        stats = {
            "total_errors": len(self.error_storage),
            "error_types": {},
            "error_codes": {},
            "recent_errors": []
        }
        
        # Count by type and code
        for error_record in self.error_storage:
            error_type = error_record.get("error_type", "Unknown")
            error_code = error_record.get("error_code", "UNKNOWN")
            
            stats["error_types"][error_type] = stats["error_types"].get(error_type, 0) + 1
            stats["error_codes"][error_code] = stats["error_codes"].get(error_code, 0) + 1
        
        # Get recent errors (last 10)
        stats["recent_errors"] = self.error_storage[-10:]
        
        return stats
    
    def clear_error_history(self):
        """Clear stored error history"""
        self.error_storage.clear()
        logger.info("Cleared error history")
    
    def export_error_log(self, filepath: str):
        """Export error log to file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.error_storage, f, indent=2)
            logger.info(f"Exported error log to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export error log: {e}")

def error_handler(error_handler_instance: ErrorHandler = None):
    """Decorator for automatic error handling"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if error_handler_instance:
                    result = error_handler_instance.handle_error(e, {
                        "function": func.__name__,
                        "args": str(args),
                        "kwargs": str(kwargs)
                    })
                    return result
                else:
                    raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if error_handler_instance:
                    result = error_handler_instance.handle_error(e, {
                        "function": func.__name__,
                        "args": str(args),
                        "kwargs": str(kwargs)
                    })
                    return result
                else:
                    raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Global error handler instance
global_error_handler = ErrorHandler()

def handle_error(error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Global error handling function"""
    return global_error_handler.handle_error(error, context)
