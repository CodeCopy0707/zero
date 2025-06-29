"""
Comprehensive validation script for Agent Zero Gemini
"""
import asyncio
import sys
import logging
import traceback
from pathlib import Path
import tempfile
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import config
from utils.logging_setup import setup_logging

logger = logging.getLogger(__name__)

class ValidationRunner:
    """Comprehensive validation runner"""
    
    def __init__(self):
        """Initialize validation runner"""
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0
            }
        }
        
        setup_logging()
        logger.info("Initialized validation runner")
    
    async def run_all_validations(self):
        """Run all validation tests"""
        try:
            logger.info("Starting comprehensive validation...")
            
            # Core component validations
            await self.validate_storage_system()
            await self.validate_gemini_client()
            await self.validate_memory_system()
            await self.validate_tool_system()
            await self.validate_communication_system()
            await self.validate_agent_system()
            await self.validate_web_ui()
            await self.validate_integration()
            
            # Generate report
            self.generate_report()
            
            logger.info("Validation complete!")
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            traceback.print_exc()
    
    async def validate_storage_system(self):
        """Validate JSON storage system"""
        test_name = "Storage System"
        logger.info(f"Validating {test_name}...")
        
        try:
            from storage.json_storage import JSONStorage
            
            with tempfile.TemporaryDirectory() as temp_dir:
                storage = JSONStorage(Path(temp_dir))
                await storage.initialize()
                
                # Test basic operations
                test_data = {"test": "data", "number": 42}
                await storage.write("test_file", test_data)
                
                read_data = await storage.read("test_file")
                assert read_data == test_data
                
                # Test updates
                await storage.update("test_file", {"new_field": "value"})
                updated_data = await storage.read("test_file")
                assert updated_data["new_field"] == "value"
                
                # Test append
                await storage.append("test_file", "items", "new_item")
                
                self.record_test_result(test_name, True, "All storage operations successful")
                
        except Exception as e:
            self.record_test_result(test_name, False, str(e))
    
    async def validate_gemini_client(self):
        """Validate Gemini AI client"""
        test_name = "Gemini Client"
        logger.info(f"Validating {test_name}...")
        
        try:
            from core.gemini_client import GeminiClient
            
            client = GeminiClient()
            
            # Test client initialization
            assert client.model_name is not None
            assert client.generation_config is not None
            
            # Test tool formatting
            tools = [{"name": "test_tool", "description": "Test tool"}]
            formatted_tools = client._format_tools(tools)
            assert isinstance(formatted_tools, list)
            
            self.record_test_result(test_name, True, "Gemini client validation successful")
            
        except Exception as e:
            self.record_test_result(test_name, False, str(e))
    
    async def validate_memory_system(self):
        """Validate memory management system"""
        test_name = "Memory System"
        logger.info(f"Validating {test_name}...")
        
        try:
            from core.memory import MemoryManager, Memory
            from storage.json_storage import JSONStorage
            
            with tempfile.TemporaryDirectory() as temp_dir:
                storage = JSONStorage(Path(temp_dir))
                await storage.initialize()
                
                memory_manager = MemoryManager("test_agent", storage)
                
                # Test memory storage
                memory = Memory(
                    type="fact",
                    content="Test fact",
                    importance=0.8
                )
                
                memory_id = await memory_manager.store_memory(memory)
                assert memory_id is not None
                
                # Test memory retrieval
                retrieved = await memory_manager.retrieve_memory(memory_id)
                assert retrieved is not None
                assert retrieved.content == "Test fact"
                
                # Test memory search
                results = await memory_manager.search_memories("Test")
                assert len(results) >= 1
                
                # Test memory statistics
                stats = await memory_manager.get_memory_stats()
                assert stats["total"] >= 1
                
                self.record_test_result(test_name, True, "Memory system validation successful")
                
        except Exception as e:
            self.record_test_result(test_name, False, str(e))
    
    async def validate_tool_system(self):
        """Validate tool management system"""
        test_name = "Tool System"
        logger.info(f"Validating {test_name}...")
        
        try:
            from core.tools import ToolManager
            from storage.json_storage import JSONStorage
            
            with tempfile.TemporaryDirectory() as temp_dir:
                storage = JSONStorage(Path(temp_dir))
                await storage.initialize()
                
                tool_manager = ToolManager(storage)
                await tool_manager.initialize()
                
                # Test tool availability
                tools = tool_manager.get_available_tools()
                assert len(tools) > 0
                
                # Test core tools are present
                core_tools = ["code_execution", "terminal", "web_search", "file_operations"]
                available_tool_names = [tool["name"] for tool in tools]
                
                for tool_name in core_tools:
                    assert tool_name in available_tool_names
                
                # Test tool execution
                result = await tool_manager.execute_tool(
                    "code_execution",
                    {"code": "print('Tool validation test')"}
                )
                assert result["success"] is True
                
                # Test tool statistics
                stats = await tool_manager.get_tool_statistics()
                assert "statistics" in stats
                
                self.record_test_result(test_name, True, "Tool system validation successful")
                
        except Exception as e:
            self.record_test_result(test_name, False, str(e))
    
    async def validate_communication_system(self):
        """Validate communication system"""
        test_name = "Communication System"
        logger.info(f"Validating {test_name}...")
        
        try:
            from core.communication import CommunicationManager, AgentHierarchyManager
            from storage.json_storage import JSONStorage
            
            with tempfile.TemporaryDirectory() as temp_dir:
                storage = JSONStorage(Path(temp_dir))
                await storage.initialize()
                
                # Test communication manager
                comm_manager = CommunicationManager()
                await comm_manager.start()
                
                # Test hierarchy manager
                hierarchy_manager = AgentHierarchyManager(storage)
                
                # Test agent registration
                await hierarchy_manager.register_agent("test_agent", {
                    "name": "Test Agent",
                    "role": "test",
                    "capabilities": ["test_capability"],
                    "superior_id": None,
                    "subordinate_ids": []
                })
                
                # Test hierarchy retrieval
                hierarchy = await hierarchy_manager.get_hierarchy()
                assert "root_agents" in hierarchy
                assert "relationships" in hierarchy
                
                await comm_manager.stop()
                
                self.record_test_result(test_name, True, "Communication system validation successful")
                
        except Exception as e:
            self.record_test_result(test_name, False, str(e))
    
    async def validate_agent_system(self):
        """Validate agent system"""
        test_name = "Agent System"
        logger.info(f"Validating {test_name}...")
        
        try:
            from core.agent import Agent, AgentState
            from core.gemini_client import GeminiClient
            from core.memory import MemoryManager
            from core.tools import ToolManager
            from core.communication import CommunicationManager
            from storage.json_storage import JSONStorage
            
            with tempfile.TemporaryDirectory() as temp_dir:
                storage = JSONStorage(Path(temp_dir))
                await storage.initialize()
                
                # Create components
                gemini_client = GeminiClient()
                tool_manager = ToolManager(storage)
                await tool_manager.initialize()
                memory_manager = MemoryManager("test_agent", storage)
                comm_manager = CommunicationManager()
                await comm_manager.start()
                
                # Create agent
                agent = Agent(
                    agent_id="test_agent",
                    name="Test Agent",
                    role="test",
                    gemini_client=gemini_client,
                    tool_manager=tool_manager,
                    memory_manager=memory_manager,
                    communication_manager=comm_manager
                )
                
                # Test agent properties
                assert agent.agent_id == "test_agent"
                assert agent.name == "Test Agent"
                assert agent.state == AgentState.IDLE
                
                # Test agent status
                status = agent.get_status()
                assert status["agent_id"] == "test_agent"
                assert status["state"] == AgentState.IDLE.value
                
                # Test agent reset
                await agent.reset()
                assert agent.state == AgentState.IDLE
                
                await comm_manager.stop()
                
                self.record_test_result(test_name, True, "Agent system validation successful")
                
        except Exception as e:
            self.record_test_result(test_name, False, str(e))
    
    async def validate_web_ui(self):
        """Validate web UI components"""
        test_name = "Web UI"
        logger.info(f"Validating {test_name}...")
        
        try:
            from web_ui.app import create_app
            from main import AgentZeroGemini
            
            # Test app creation
            app_instance = AgentZeroGemini()
            web_app = create_app(app_instance)
            
            assert web_app is not None
            
            # Test that routes are registered
            routes = [route.path for route in web_app.routes]
            expected_routes = ["/", "/api/status", "/api/tools", "/ws"]
            
            for expected_route in expected_routes:
                assert any(expected_route in route for route in routes)
            
            self.record_test_result(test_name, True, "Web UI validation successful")
            
        except Exception as e:
            self.record_test_result(test_name, False, str(e))
    
    async def validate_integration(self):
        """Validate full system integration"""
        test_name = "System Integration"
        logger.info(f"Validating {test_name}...")
        
        try:
            from main import AgentZeroGemini
            
            # Test application initialization
            app = AgentZeroGemini()
            await app.start()
            
            # Test status retrieval
            status = await app.get_status()
            assert status["running"] is True
            assert "root_agent" in status
            
            # Test basic functionality
            if status.get("root_agent"):
                # Test that we can get a response (mock the Gemini call)
                with self.mock_gemini_response():
                    response = await app.process_user_input("Hello, test message")
                    assert response is not None
                    assert len(response) > 0
            
            await app.stop()
            
            self.record_test_result(test_name, True, "System integration validation successful")
            
        except Exception as e:
            self.record_test_result(test_name, False, str(e))
    
    def mock_gemini_response(self):
        """Mock Gemini response for testing"""
        from unittest.mock import patch
        
        return patch('core.gemini_client.GeminiClient.generate_response', 
                    return_value="This is a test response from the agent.")
    
    def record_test_result(self, test_name: str, passed: bool, message: str):
        """Record test result"""
        self.results["tests"][test_name] = {
            "passed": passed,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        self.results["summary"]["total"] += 1
        if passed:
            self.results["summary"]["passed"] += 1
            logger.info(f"✅ {test_name}: PASSED - {message}")
        else:
            self.results["summary"]["failed"] += 1
            logger.error(f"❌ {test_name}: FAILED - {message}")
    
    def generate_report(self):
        """Generate validation report"""
        report_file = Path("validation_report.json")
        
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Print summary
        summary = self.results["summary"]
        total = summary["total"]
        passed = summary["passed"]
        failed = summary["failed"]
        
        print("\n" + "="*60)
        print("AGENT ZERO GEMINI VALIDATION REPORT")
        print("="*60)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/total*100):.1f}%" if total > 0 else "0%")
        print("="*60)
        
        if failed == 0:
            print("🎉 ALL VALIDATIONS PASSED! Agent Zero Gemini is ready for use.")
        else:
            print("⚠️  Some validations failed. Check the detailed report.")
        
        print(f"\nDetailed report saved to: {report_file}")

async def main():
    """Main validation function"""
    runner = ValidationRunner()
    await runner.run_all_validations()

if __name__ == "__main__":
    asyncio.run(main())
