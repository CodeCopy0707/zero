"""
Tool tests for Agent Zero Gemini
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import tempfile
from pathlib import Path

from core.tools import BaseTool, ToolManager
from storage.json_storage import JSONStorage

class TestBaseTool:
    """Test base tool functionality"""
    
    def test_base_tool_creation(self):
        """Test base tool creation"""
        tool = BaseTool("test_tool", "Test tool description")
        
        assert tool.name == "test_tool"
        assert tool.description == "Test tool description"
        assert tool.enabled is True
    
    def test_base_tool_parameters(self):
        """Test base tool parameters"""
        tool = BaseTool("test_tool", "Test tool description")
        
        # Base tool should return empty parameters
        params = tool.get_parameters()
        assert isinstance(params, dict)
    
    @pytest.mark.asyncio
    async def test_base_tool_execute_not_implemented(self):
        """Test base tool execute raises NotImplementedError"""
        tool = BaseTool("test_tool", "Test tool description")
        
        with pytest.raises(NotImplementedError):
            await tool.execute()

class TestCodeExecutionTool:
    """Test code execution tool"""
    
    @pytest.fixture
    def code_tool(self):
        """Create code execution tool"""
        from tools.code_execution import CodeExecutionTool
        return CodeExecutionTool()
    
    @pytest.mark.asyncio
    async def test_simple_code_execution(self, code_tool):
        """Test simple code execution"""
        code = "print('Hello, World!')"
        
        result = await code_tool.execute(code=code)
        
        assert result["success"] is True
        assert "Hello, World!" in result["output"]
    
    @pytest.mark.asyncio
    async def test_code_execution_with_variables(self, code_tool):
        """Test code execution with variables"""
        code = """
x = 10
y = 20
result = x + y
print(f"Result: {result}")
"""
        
        result = await code_tool.execute(code=code)
        
        assert result["success"] is True
        assert "Result: 30" in result["output"]
    
    @pytest.mark.asyncio
    async def test_code_execution_error_handling(self, code_tool):
        """Test code execution error handling"""
        code = "print(undefined_variable)"
        
        result = await code_tool.execute(code=code)
        
        assert result["success"] is False
        assert "error" in result
        assert "NameError" in result["error"]
    
    @pytest.mark.asyncio
    async def test_code_execution_timeout(self, code_tool):
        """Test code execution timeout"""
        code = """
import time
time.sleep(10)  # This should timeout
"""
        
        result = await code_tool.execute(code=code, timeout=1)
        
        assert result["success"] is False
        assert "timeout" in result["error"].lower()

class TestTerminalTool:
    """Test terminal tool"""
    
    @pytest.fixture
    def terminal_tool(self):
        """Create terminal tool"""
        from tools.terminal import TerminalTool
        return TerminalTool()
    
    @pytest.mark.asyncio
    async def test_simple_command(self, terminal_tool):
        """Test simple terminal command"""
        result = await terminal_tool.execute(command="echo 'Hello Terminal'")
        
        assert result["success"] is True
        assert "Hello Terminal" in result["output"]
    
    @pytest.mark.asyncio
    async def test_command_with_args(self, terminal_tool):
        """Test command with arguments"""
        result = await terminal_tool.execute(command="ls", args=["-la"])
        
        assert result["success"] is True
        assert "output" in result
    
    @pytest.mark.asyncio
    async def test_invalid_command(self, terminal_tool):
        """Test invalid command handling"""
        result = await terminal_tool.execute(command="nonexistent_command_12345")
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_restricted_command(self, terminal_tool):
        """Test restricted command handling"""
        # Test that dangerous commands are blocked
        result = await terminal_tool.execute(command="rm", args=["-rf", "/"])
        
        assert result["success"] is False
        assert "restricted" in result["error"].lower()

class TestWebSearchTool:
    """Test web search tool"""
    
    @pytest.fixture
    def search_tool(self):
        """Create web search tool"""
        from tools.web_search import WebSearchTool
        return WebSearchTool()
    
    @pytest.mark.asyncio
    async def test_web_search(self, search_tool):
        """Test web search functionality"""
        with patch('duckduckgo_search.DDGS') as mock_ddgs:
            # Mock search results
            mock_ddgs.return_value.text.return_value = [
                {
                    "title": "Test Result",
                    "href": "https://example.com",
                    "body": "Test search result body"
                }
            ]
            
            result = await search_tool.execute(query="test query")
            
            assert result["success"] is True
            assert "results" in result
            assert len(result["results"]) > 0
            assert result["results"][0]["title"] == "Test Result"
    
    @pytest.mark.asyncio
    async def test_web_search_error_handling(self, search_tool):
        """Test web search error handling"""
        with patch('duckduckgo_search.DDGS') as mock_ddgs:
            mock_ddgs.side_effect = Exception("Search failed")
            
            result = await search_tool.execute(query="test query")
            
            assert result["success"] is False
            assert "error" in result

class TestFileOperationTool:
    """Test file operation tool"""
    
    @pytest.fixture
    def file_tool(self):
        """Create file operation tool"""
        from tools.file_operations import FileOperationTool
        return FileOperationTool()
    
    @pytest.mark.asyncio
    async def test_read_file(self, file_tool):
        """Test file reading"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Test file content")
            temp_path = f.name
        
        try:
            result = await file_tool.execute(operation="read", path=temp_path)
            
            assert result["success"] is True
            assert result["content"] == "Test file content"
        finally:
            Path(temp_path).unlink()
    
    @pytest.mark.asyncio
    async def test_write_file(self, file_tool):
        """Test file writing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_file.txt"
            
            result = await file_tool.execute(
                operation="write",
                path=str(file_path),
                content="New file content"
            )
            
            assert result["success"] is True
            assert file_path.exists()
            assert file_path.read_text() == "New file content"
    
    @pytest.mark.asyncio
    async def test_list_directory(self, file_tool):
        """Test directory listing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            (Path(temp_dir) / "file1.txt").write_text("content1")
            (Path(temp_dir) / "file2.txt").write_text("content2")
            
            result = await file_tool.execute(operation="list", path=temp_dir)
            
            assert result["success"] is True
            assert "files" in result
            assert len(result["files"]) >= 2
    
    @pytest.mark.asyncio
    async def test_file_operation_error(self, file_tool):
        """Test file operation error handling"""
        result = await file_tool.execute(
            operation="read",
            path="/nonexistent/path/file.txt"
        )
        
        assert result["success"] is False
        assert "error" in result

class TestAdvancedTools:
    """Test advanced tools integration"""
    
    @pytest.mark.asyncio
    async def test_browser_tool_availability(self):
        """Test browser tool availability"""
        try:
            from tools.browser_tools import BrowserTool
            tool = BrowserTool()
            assert tool.name == "browser"
            assert tool.description is not None
        except ImportError:
            pytest.skip("Browser tools not available")
    
    @pytest.mark.asyncio
    async def test_audio_tool_availability(self):
        """Test audio tool availability"""
        try:
            from tools.audio_tools import TextToSpeechTool
            tool = TextToSpeechTool()
            assert tool.name == "text_to_speech"
            assert tool.description is not None
        except ImportError:
            pytest.skip("Audio tools not available")
    
    @pytest.mark.asyncio
    async def test_document_tool_availability(self):
        """Test document tool availability"""
        try:
            from tools.document_tools import PDFTool
            tool = PDFTool()
            assert tool.name == "pdf_processor"
            assert tool.description is not None
        except ImportError:
            pytest.skip("Document tools not available")
    
    @pytest.mark.asyncio
    async def test_network_tool_availability(self):
        """Test network tool availability"""
        try:
            from tools.network_tools import HTTPRequestTool
            tool = HTTPRequestTool()
            assert tool.name == "http_request"
            assert tool.description is not None
        except ImportError:
            pytest.skip("Network tools not available")
    
    @pytest.mark.asyncio
    async def test_analysis_tool_availability(self):
        """Test analysis tool availability"""
        try:
            from tools.analysis_tools import DataAnalysisTool
            tool = DataAnalysisTool()
            assert tool.name == "data_analysis"
            assert tool.description is not None
        except ImportError:
            pytest.skip("Analysis tools not available")

class TestToolManagerIntegration:
    """Test tool manager integration with all tools"""
    
    @pytest.fixture
    async def tool_manager(self):
        """Create tool manager for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = JSONStorage(Path(temp_dir))
            await storage.initialize()
            
            manager = ToolManager(storage)
            await manager.initialize()
            yield manager
    
    @pytest.mark.asyncio
    async def test_tool_manager_initialization(self, tool_manager):
        """Test tool manager initialization"""
        assert len(tool_manager.tools) > 0
        
        # Check that core tools are loaded
        core_tools = ["code_execution", "terminal", "web_search", "file_operations"]
        for tool_name in core_tools:
            assert tool_name in tool_manager.tools
    
    @pytest.mark.asyncio
    async def test_tool_execution_through_manager(self, tool_manager):
        """Test tool execution through manager"""
        result = await tool_manager.execute_tool(
            "code_execution",
            {"code": "print('Hello from tool manager')"}
        )
        
        assert result["success"] is True
        assert "Hello from tool manager" in result["result"]["output"]
    
    @pytest.mark.asyncio
    async def test_tool_statistics_tracking(self, tool_manager):
        """Test tool statistics tracking"""
        # Execute a tool
        await tool_manager.execute_tool(
            "code_execution",
            {"code": "print('Statistics test')"}
        )
        
        # Check statistics
        stats = await tool_manager.get_tool_statistics()
        
        assert "statistics" in stats
        assert "code_execution" in stats["statistics"]
        assert stats["statistics"]["code_execution"]["total_calls"] >= 1
    
    @pytest.mark.asyncio
    async def test_tool_health_validation(self, tool_manager):
        """Test tool health validation"""
        health_report = await tool_manager.validate_tool_health()
        
        assert "healthy_tools" in health_report
        assert "unhealthy_tools" in health_report
        assert "total_tools" in health_report
        
        # Should have at least some healthy tools
        assert len(health_report["healthy_tools"]) > 0
    
    @pytest.mark.asyncio
    async def test_tool_capabilities_reporting(self, tool_manager):
        """Test tool capabilities reporting"""
        capabilities = tool_manager.get_tool_capabilities()
        
        assert isinstance(capabilities, dict)
        assert len(capabilities) > 0
        
        # Each tool should have capabilities listed
        for tool_name, tool_capabilities in capabilities.items():
            assert isinstance(tool_capabilities, list)
    
    @pytest.mark.asyncio
    async def test_tool_backup_functionality(self, tool_manager):
        """Test tool backup functionality"""
        backup_path = await tool_manager.backup_tool_data()
        
        assert backup_path is not None
        assert Path(backup_path).exists()
        
        # Cleanup
        Path(backup_path).unlink()

class TestToolParameterValidation:
    """Test tool parameter validation"""
    
    @pytest.fixture
    def validation_tool(self):
        """Create a tool with parameter validation"""
        class ValidationTestTool(BaseTool):
            def __init__(self):
                super().__init__("validation_test", "Tool for testing parameter validation")
            
            def get_parameters(self):
                return {
                    "required_param": {
                        "type": "string",
                        "description": "A required parameter",
                        "required": True
                    },
                    "optional_param": {
                        "type": "integer",
                        "description": "An optional parameter",
                        "required": False,
                        "default": 42
                    }
                }
            
            def validate_parameters(self, parameters):
                required_params = ["required_param"]
                
                for param in required_params:
                    if param not in parameters:
                        return {
                            "valid": False,
                            "error": f"Missing required parameter: {param}"
                        }
                
                return {"valid": True}
            
            async def execute(self, **kwargs):
                return {"success": True, "parameters": kwargs}
        
        return ValidationTestTool()
    
    @pytest.mark.asyncio
    async def test_parameter_validation_success(self, validation_tool):
        """Test successful parameter validation"""
        result = await validation_tool.execute(
            required_param="test_value",
            optional_param=123
        )
        
        assert result["success"] is True
        assert result["parameters"]["required_param"] == "test_value"
        assert result["parameters"]["optional_param"] == 123
    
    def test_parameter_validation_failure(self, validation_tool):
        """Test parameter validation failure"""
        validation_result = validation_tool.validate_parameters({})
        
        assert validation_result["valid"] is False
        assert "required_param" in validation_result["error"]
    
    def test_parameter_schema(self, validation_tool):
        """Test parameter schema"""
        params = validation_tool.get_parameters()
        
        assert "required_param" in params
        assert "optional_param" in params
        assert params["required_param"]["required"] is True
        assert params["optional_param"]["required"] is False
