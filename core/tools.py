"""
Tools system for Agent Zero Gemini
"""
import asyncio
import logging
import subprocess
import sys
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class BaseTool(ABC):
    """Base class for all tools"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool"""
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema for LLM"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.get_parameters()
        }
    
    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Get tool parameters schema"""
        pass

class CodeExecutionTool(BaseTool):
    """Tool for executing Python code"""
    
    def __init__(self):
        super().__init__(
            name="execute_python_code",
            description="Execute Python code and return the result"
        )
    
    async def execute(self, code: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute Python code"""
        try:
            # Create a temporary file for the code
            temp_file = Path("tmp") / f"code_{asyncio.get_event_loop().time()}.py"
            temp_file.parent.mkdir(exist_ok=True)
            
            # Write code to file
            with open(temp_file, "w") as f:
                f.write(code)
            
            # Execute code
            process = await asyncio.create_subprocess_exec(
                sys.executable, str(temp_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd()
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
                
                # Clean up
                temp_file.unlink(missing_ok=True)
                
                return {
                    "success": True,
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                    "return_code": process.returncode
                }
                
            except asyncio.TimeoutError:
                process.kill()
                temp_file.unlink(missing_ok=True)
                return {
                    "success": False,
                    "error": f"Code execution timed out after {timeout} seconds"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "code": {
                "type": "string",
                "description": "Python code to execute"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 30)",
                "default": 30
            }
        }

class TerminalTool(BaseTool):
    """Tool for executing terminal commands"""
    
    def __init__(self):
        super().__init__(
            name="execute_terminal_command",
            description="Execute a terminal/shell command"
        )
    
    async def execute(self, command: str, timeout: int = 30, cwd: Optional[str] = None) -> Dict[str, Any]:
        """Execute terminal command"""
        try:
            # Security check - basic command validation
            if self._is_dangerous_command(command):
                return {
                    "success": False,
                    "error": "Command blocked for security reasons"
                }
            
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd or os.getcwd()
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                return {
                    "success": True,
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                    "return_code": process.returncode
                }
                
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "success": False,
                    "error": f"Command timed out after {timeout} seconds"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _is_dangerous_command(self, command: str) -> bool:
        """Check if command is potentially dangerous"""
        dangerous_patterns = [
            "rm -rf", "del /", "format", "fdisk",
            "dd if=", "mkfs", "shutdown", "reboot",
            "sudo rm", "sudo dd", "sudo mkfs"
        ]
        
        command_lower = command.lower()
        return any(pattern in command_lower for pattern in dangerous_patterns)
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "command": {
                "type": "string",
                "description": "Terminal command to execute"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 30)",
                "default": 30
            },
            "cwd": {
                "type": "string",
                "description": "Working directory for command execution",
                "optional": True
            }
        }

class WebSearchTool(BaseTool):
    """Tool for web search"""
    
    def __init__(self):
        super().__init__(
            name="web_search",
            description="Search the web for information"
        )
    
    async def execute(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Perform web search"""
        try:
            from duckduckgo_search import DDGS
            
            # Perform search
            with DDGS() as ddgs:
                results = []
                for result in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("href", ""),
                        "snippet": result.get("body", "")
                    })
                
                return {
                    "success": True,
                    "query": query,
                    "results": results
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (default: 5)",
                "default": 5
            }
        }

class FileOperationTool(BaseTool):
    """Tool for file operations"""
    
    def __init__(self):
        super().__init__(
            name="file_operation",
            description="Perform file operations (read, write, list, etc.)"
        )
    
    async def execute(self, operation: str, path: str, content: Optional[str] = None) -> Dict[str, Any]:
        """Perform file operation"""
        try:
            file_path = Path(path)
            
            if operation == "read":
                if not file_path.exists():
                    return {"success": False, "error": "File does not exist"}
                
                content = file_path.read_text(encoding="utf-8")
                return {
                    "success": True,
                    "operation": "read",
                    "path": str(file_path),
                    "content": content
                }
            
            elif operation == "write":
                if content is None:
                    return {"success": False, "error": "Content required for write operation"}
                
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")
                return {
                    "success": True,
                    "operation": "write",
                    "path": str(file_path),
                    "message": "File written successfully"
                }
            
            elif operation == "list":
                if not file_path.exists():
                    return {"success": False, "error": "Path does not exist"}
                
                if file_path.is_file():
                    return {
                        "success": True,
                        "operation": "list",
                        "path": str(file_path),
                        "items": [file_path.name]
                    }
                
                items = []
                for item in file_path.iterdir():
                    items.append({
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else None
                    })
                
                return {
                    "success": True,
                    "operation": "list",
                    "path": str(file_path),
                    "items": items
                }
            
            elif operation == "delete":
                if not file_path.exists():
                    return {"success": False, "error": "File does not exist"}
                
                if file_path.is_file():
                    file_path.unlink()
                else:
                    import shutil
                    shutil.rmtree(file_path)
                
                return {
                    "success": True,
                    "operation": "delete",
                    "path": str(file_path),
                    "message": "File/directory deleted successfully"
                }
            
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "operation": {
                "type": "string",
                "description": "Operation to perform (read, write, list, delete)",
                "enum": ["read", "write", "list", "delete"]
            },
            "path": {
                "type": "string",
                "description": "File or directory path"
            },
            "content": {
                "type": "string",
                "description": "Content for write operation",
                "optional": True
            }
        }

class ToolManager:
    """Manages available tools"""
    
    def __init__(self):
        """Initialize ToolManager"""
        self.tools: Dict[str, BaseTool] = {}
        self._register_default_tools()
        
        logger.info(f"Initialized ToolManager with {len(self.tools)} tools")
    
    def _register_default_tools(self):
        """Register default tools"""
        # Core tools
        default_tools = [
            CodeExecutionTool(),
            TerminalTool(),
            WebSearchTool(),
            FileOperationTool()
        ]

        # Advanced tools (import dynamically to handle missing dependencies)
        # Advanced tools (import dynamically to handle missing dependencies)
        advanced_tools = [
            ("tools.browser_tools", ["BrowserTool", "WebScrapingTool"], "selenium/beautifulsoup4"),
            ("tools.audio_tools", ["TextToSpeechTool", "SpeechToTextTool", "AudioProcessingTool"], "pyttsx3/speechrecognition"),
            ("tools.document_tools", ["DocumentProcessorTool", "PDFTool", "WordTool"], "PyPDF2/python-docx"),
            ("tools.network_tools", ["HTTPRequestTool", "APITool", "WebhookTool"], "httpx"),
            ("tools.analysis_tools", ["DataAnalysisTool", "ImageAnalysisTool"], "pandas/pillow")
        ]

        for module_name, tool_classes, dependencies in advanced_tools:
            try:
                module = __import__(module_name, fromlist=tool_classes)
                for tool_class_name in tool_classes:
                    if hasattr(module, tool_class_name):
                        tool_class = getattr(module, tool_class_name)
                        tool_instance = tool_class()
                        default_tools.append(tool_instance)
                        logger.info(f"Loaded tool: {tool_class_name}")
            except ImportError as e:
                logger.warning(f"Tools from {module_name} not available (missing {dependencies}): {e}")
            except Exception as e:
                logger.error(f"Error loading tools from {module_name}: {e}")

        for tool in default_tools:
            self.register_tool(tool)

        logger.info(f"Registered {len(default_tools)} tools")

    async def reload_tools(self):
        """Reload all tools"""
        try:
            # Clear existing tools
            self.tools.clear()

            # Re-register default tools
            self._register_default_tools()

            # Load custom tools from storage
            await self._load_custom_tools()

            logger.info("Tools reloaded successfully")

        except Exception as e:
            logger.error(f"Error reloading tools: {e}")
            raise

    async def _load_custom_tools(self):
        """Load custom tools from storage"""
        try:
            tools_data = await self.storage.read("tools")
            custom_tools = tools_data.get("custom_tools", [])

            for tool_config in custom_tools:
                if tool_config.get("enabled", True):
                    # Load custom tool (implementation would depend on tool format)
                    logger.debug(f"Custom tool available: {tool_config.get('name')}")

        except Exception as e:
            logger.error(f"Error loading custom tools: {e}")

    async def save_tool_usage(self, tool_name: str, parameters: Dict[str, Any], result: Dict[str, Any], execution_time: float):
        """Save tool usage statistics"""
        try:
            usage_record = {
                "tool_name": tool_name,
                "parameters": parameters,
                "result": result,
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat(),
                "success": result.get("success", False)
            }

            tools_data = await self.storage.read("tools")

            if "usage_history" not in tools_data:
                tools_data["usage_history"] = []

            tools_data["usage_history"].append(usage_record)

            # Keep only last 1000 usage records
            if len(tools_data["usage_history"]) > 1000:
                tools_data["usage_history"] = tools_data["usage_history"][-1000:]

            # Update tool statistics
            if "statistics" not in tools_data:
                tools_data["statistics"] = {}

            if tool_name not in tools_data["statistics"]:
                tools_data["statistics"][tool_name] = {
                    "total_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "total_execution_time": 0.0,
                    "average_execution_time": 0.0,
                    "last_used": None
                }

            stats = tools_data["statistics"][tool_name]
            stats["total_calls"] += 1
            stats["total_execution_time"] += execution_time
            stats["average_execution_time"] = stats["total_execution_time"] / stats["total_calls"]
            stats["last_used"] = usage_record["timestamp"]

            if result.get("success", False):
                stats["successful_calls"] += 1
            else:
                stats["failed_calls"] += 1

            await self.storage.write("tools", tools_data)

        except Exception as e:
            logger.error(f"Error saving tool usage: {e}")

    async def get_tool_statistics(self) -> Dict[str, Any]:
        """Get tool usage statistics"""
        try:
            tools_data = await self.storage.read("tools")
            statistics = tools_data.get("statistics", {})

            # Add current tool availability
            available_tools = list(self.tools.keys())

            return {
                "available_tools": available_tools,
                "total_tools": len(available_tools),
                "statistics": statistics,
                "last_updated": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting tool statistics: {e}")
            return {"error": str(e)}

    async def get_tool_usage_history(self, tool_name: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get tool usage history"""
        try:
            tools_data = await self.storage.read("tools")
            usage_history = tools_data.get("usage_history", [])

            if tool_name:
                usage_history = [record for record in usage_history if record.get("tool_name") == tool_name]

            # Sort by timestamp (most recent first)
            usage_history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

            return usage_history[:limit]

        except Exception as e:
            logger.error(f"Error getting tool usage history: {e}")
            return []

    def get_tool_capabilities(self) -> Dict[str, List[str]]:
        """Get capabilities of all tools"""
        capabilities = {}

        for tool_name, tool in self.tools.items():
            tool_capabilities = []

            # Get tool description and parameters
            if hasattr(tool, 'description'):
                tool_capabilities.append(f"Description: {tool.description}")

            if hasattr(tool, 'get_parameters'):
                try:
                    params = tool.get_parameters()
                    if params:
                        param_names = list(params.keys())
                        tool_capabilities.append(f"Parameters: {', '.join(param_names)}")
                except Exception:
                    pass

            # Check for specific capabilities
            if hasattr(tool, 'execute'):
                tool_capabilities.append("Can execute operations")

            if hasattr(tool, 'validate_parameters'):
                tool_capabilities.append("Has parameter validation")

            capabilities[tool_name] = tool_capabilities

        return capabilities

    async def validate_tool_health(self) -> Dict[str, Any]:
        """Validate health of all tools"""
        health_report = {
            "healthy_tools": [],
            "unhealthy_tools": [],
            "total_tools": len(self.tools),
            "health_check_time": datetime.now().isoformat()
        }

        for tool_name, tool in self.tools.items():
            try:
                # Basic health check - try to get tool info
                if hasattr(tool, 'get_parameters'):
                    tool.get_parameters()

                # Check if tool has required methods
                required_methods = ['execute']
                for method in required_methods:
                    if not hasattr(tool, method):
                        raise AttributeError(f"Missing required method: {method}")

                health_report["healthy_tools"].append(tool_name)

            except Exception as e:
                health_report["unhealthy_tools"].append({
                    "tool_name": tool_name,
                    "error": str(e)
                })

        return health_report

    async def backup_tool_data(self) -> str:
        """Backup tool data"""
        try:
            tools_data = await self.storage.read("tools")

            backup_data = {
                "tools_data": tools_data,
                "available_tools": list(self.tools.keys()),
                "backup_time": datetime.now().isoformat(),
                "tool_capabilities": self.get_tool_capabilities()
            }

            # Save backup
            backup_filename = f"tools_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            import json
            from pathlib import Path

            backup_dir = Path("backups")
            backup_dir.mkdir(exist_ok=True)

            backup_path = backup_dir / backup_filename

            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2)

            logger.info(f"Tool data backed up to: {backup_path}")
            return str(backup_path)

        except Exception as e:
            logger.error(f"Error backing up tool data: {e}")
            raise
    
    def register_tool(self, tool: BaseTool):
        """Register a tool"""
        self.tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")
    
    def unregister_tool(self, tool_name: str):
        """Unregister a tool"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.debug(f"Unregistered tool: {tool_name}")
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self.tools.get(tool_name)
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools"""
        return [tool.get_schema() for tool in self.tools.values()]
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a tool with comprehensive error handling"""
        import time

        start_time = time.time()
        parameters = parameters or {}

        try:
            # Get tool
            tool = self.get_tool(tool_name)
            if not tool:
                return {
                    "success": False,
                    "error": f"Tool '{tool_name}' not found",
                    "available_tools": list(self.tools.keys())
                }

            # Validate parameters
            if hasattr(tool, 'validate_parameters'):
                validation_result = tool.validate_parameters(parameters)
                if not validation_result.get('valid', True):
                    return {
                        "success": False,
                        "error": f"Parameter validation failed: {validation_result.get('error', 'Invalid parameters')}",
                        "required_parameters": tool.get_parameters() if hasattr(tool, 'get_parameters') else {}
                    }

            # Execute tool
            logger.info(f"Executing tool: {tool_name} with parameters: {parameters}")
            result = await tool.execute(**parameters)

            execution_time = time.time() - start_time

            # Log tool usage
            await self.save_tool_usage(tool_name, parameters, {"success": True, "result": result}, execution_time)

            logger.info(f"Tool {tool_name} executed successfully in {execution_time:.3f}s")

            return {
                "success": True,
                "result": result,
                "execution_time": execution_time,
                "tool_name": tool_name
            }

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)

            # Log failed tool usage
            await self.save_tool_usage(tool_name, parameters, {"success": False, "error": error_msg}, execution_time)

            logger.error(f"Error executing tool {tool_name}: {error_msg}")

            return {
                "success": False,
                "error": error_msg,
                "execution_time": execution_time,
                "tool_name": tool_name
            }
    
    def list_tools(self) -> List[str]:
        """List all available tool names"""
        return list(self.tools.keys())

    async def save_tool_usage(self, tool_name: str, parameters: Dict[str, Any], result: Dict[str, Any], execution_time: float):
        """Save tool usage statistics"""
        try:
            # Load existing statistics
            try:
                stats_data = await self.storage.read("tool_statistics")
            except:
                stats_data = {"statistics": {}, "total_calls": 0}

            # Update statistics
            if tool_name not in stats_data["statistics"]:
                stats_data["statistics"][tool_name] = {
                    "total_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "total_execution_time": 0.0,
                    "average_execution_time": 0.0
                }

            tool_stats = stats_data["statistics"][tool_name]
            tool_stats["total_calls"] += 1
            tool_stats["total_execution_time"] += execution_time
            tool_stats["average_execution_time"] = tool_stats["total_execution_time"] / tool_stats["total_calls"]

            if result.get("success", False):
                tool_stats["successful_calls"] += 1
            else:
                tool_stats["failed_calls"] += 1

            stats_data["total_calls"] += 1

            # Save updated statistics
            await self.storage.write("tool_statistics", stats_data)

        except Exception as e:
            logger.error(f"Error saving tool usage statistics: {e}")

    async def get_tool_statistics(self) -> Dict[str, Any]:
        """Get tool usage statistics"""
        try:
            stats_data = await self.storage.read("tool_statistics")
            return stats_data
        except:
            return {"statistics": {}, "total_calls": 0}

    async def validate_tool_health(self) -> Dict[str, Any]:
        """Validate health of all tools"""
        healthy_tools = []
        unhealthy_tools = []

        for tool_name, tool in self.tools.items():
            try:
                # Test basic tool functionality
                if hasattr(tool, 'health_check'):
                    health_result = await tool.health_check()
                    if health_result.get('healthy', True):
                        healthy_tools.append(tool_name)
                    else:
                        unhealthy_tools.append({
                            "name": tool_name,
                            "error": health_result.get('error', 'Unknown health issue')
                        })
                else:
                    # Basic health check - tool exists and has required methods
                    if hasattr(tool, 'execute') and hasattr(tool, 'get_schema'):
                        healthy_tools.append(tool_name)
                    else:
                        unhealthy_tools.append({
                            "name": tool_name,
                            "error": "Missing required methods"
                        })

            except Exception as e:
                unhealthy_tools.append({
                    "name": tool_name,
                    "error": str(e)
                })

        return {
            "healthy_tools": healthy_tools,
            "unhealthy_tools": unhealthy_tools,
            "total_tools": len(self.tools),
            "health_percentage": len(healthy_tools) / len(self.tools) * 100 if self.tools else 0
        }

    def get_tool_capabilities(self) -> Dict[str, List[str]]:
        """Get capabilities of all tools"""
        capabilities = {}

        for tool_name, tool in self.tools.items():
            tool_capabilities = []

            # Get capabilities from tool description or schema
            if hasattr(tool, 'get_capabilities'):
                tool_capabilities = tool.get_capabilities()
            else:
                # Infer capabilities from tool name and description
                if 'code' in tool_name.lower():
                    tool_capabilities.append('code_execution')
                if 'terminal' in tool_name.lower():
                    tool_capabilities.append('system_access')
                if 'web' in tool_name.lower() or 'search' in tool_name.lower():
                    tool_capabilities.append('web_access')
                if 'file' in tool_name.lower():
                    tool_capabilities.append('file_operations')
                if 'browser' in tool_name.lower():
                    tool_capabilities.append('browser_automation')
                if 'audio' in tool_name.lower():
                    tool_capabilities.append('audio_processing')
                if 'document' in tool_name.lower():
                    tool_capabilities.append('document_processing')
                if 'network' in tool_name.lower() or 'http' in tool_name.lower():
                    tool_capabilities.append('network_operations')
                if 'analysis' in tool_name.lower() or 'data' in tool_name.lower():
                    tool_capabilities.append('data_analysis')

            capabilities[tool_name] = tool_capabilities

        return capabilities

    async def backup_tool_data(self) -> str:
        """Backup tool data and statistics"""
        import json
        from datetime import datetime

        try:
            # Collect tool data
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "available_tools": [tool.get_schema() for tool in self.tools.values()],
                "tool_statistics": await self.get_tool_statistics(),
                "tool_capabilities": self.get_tool_capabilities(),
                "tool_health": await self.validate_tool_health()
            }

            # Save backup
            backup_filename = f"tool_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            backup_path = Path("backups") / backup_filename
            backup_path.parent.mkdir(exist_ok=True)

            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2)

            logger.info(f"Tool data backed up to {backup_path}")
            return str(backup_path)

        except Exception as e:
            logger.error(f"Error backing up tool data: {e}")
            raise
