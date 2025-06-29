"""
Core component tests for Agent Zero Gemini
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import tempfile
import json

from core.agent import Agent, AgentState
from core.gemini_client import GeminiClient
from core.memory import MemoryManager, Memory
from core.tools import ToolManager
from core.communication import CommunicationManager, AgentHierarchyManager
from storage.json_storage import JSONStorage
from config import config

class TestGeminiClient:
    """Test Gemini AI client"""
    
    @pytest.fixture
    def gemini_client(self):
        """Create Gemini client for testing"""
        return GeminiClient()
    
    @pytest.mark.asyncio
    async def test_generate_response(self, gemini_client):
        """Test response generation"""
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_response = Mock()
            mock_response.text = "Test response"
            mock_model.return_value.generate_content_async.return_value = mock_response
            
            response = await gemini_client.generate_response("Test prompt")
            assert response == "Test response"
    
    @pytest.mark.asyncio
    async def test_generate_response_with_tools(self, gemini_client):
        """Test response generation with tools"""
        tools = [{"name": "test_tool", "description": "Test tool"}]
        
        with patch('google.generativeai.GenerativeModel') as mock_model:
            mock_response = Mock()
            mock_response.text = "Tool response"
            mock_model.return_value.generate_content_async.return_value = mock_response
            
            response = await gemini_client.generate_response("Test prompt", tools=tools)
            assert response == "Tool response"
    
    def test_format_tools(self, gemini_client):
        """Test tool formatting"""
        tools = [
            {"name": "test_tool", "description": "Test tool", "parameters": {"param1": "value1"}}
        ]
        
        formatted = gemini_client._format_tools(tools)
        assert isinstance(formatted, list)
        assert len(formatted) > 0

class TestMemoryManager:
    """Test memory management"""
    
    @pytest.fixture
    async def memory_manager(self):
        """Create memory manager for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = JSONStorage(Path(temp_dir))
            await storage.initialize()
            yield MemoryManager("test_agent", storage)
    
    @pytest.mark.asyncio
    async def test_store_memory(self, memory_manager):
        """Test memory storage"""
        memory = Memory(
            type="fact",
            content="Test fact",
            importance=0.8
        )
        
        memory_id = await memory_manager.store_memory(memory)
        assert memory_id is not None
        assert len(memory_id) > 0
    
    @pytest.mark.asyncio
    async def test_retrieve_memory(self, memory_manager):
        """Test memory retrieval"""
        memory = Memory(
            type="fact",
            content="Test fact",
            importance=0.8
        )
        
        memory_id = await memory_manager.store_memory(memory)
        retrieved = await memory_manager.retrieve_memory(memory_id)
        
        assert retrieved is not None
        assert retrieved.content == "Test fact"
        assert retrieved.type == "fact"
    
    @pytest.mark.asyncio
    async def test_search_memories(self, memory_manager):
        """Test memory search"""
        # Store test memories
        memories = [
            Memory(type="fact", content="Python is a programming language", importance=0.8),
            Memory(type="fact", content="JavaScript is used for web development", importance=0.7),
            Memory(type="skill", content="How to write Python functions", importance=0.9)
        ]
        
        for memory in memories:
            await memory_manager.store_memory(memory)
        
        # Search for Python-related memories
        results = await memory_manager.search_memories("Python")
        assert len(results) >= 2
        
        # Search for specific type
        results = await memory_manager.search_memories("Python", memory_type="fact")
        assert len(results) >= 1
        assert all(m.type == "fact" for m in results)
    
    @pytest.mark.asyncio
    async def test_store_interaction(self, memory_manager):
        """Test interaction storage"""
        memory_id = await memory_manager.store_interaction(
            role="user",
            content="Hello, how are you?",
            metadata={"session_id": "test_session"}
        )
        
        assert memory_id is not None
        
        # Retrieve and verify
        memory = await memory_manager.retrieve_memory(memory_id)
        assert memory.type == "interaction"
        assert memory.metadata["role"] == "user"
    
    @pytest.mark.asyncio
    async def test_memory_stats(self, memory_manager):
        """Test memory statistics"""
        # Store some test memories
        await memory_manager.store_fact("Test fact 1")
        await memory_manager.store_fact("Test fact 2")
        await memory_manager.store_skill("test_skill", "How to test")
        
        stats = await memory_manager.get_memory_stats()
        
        assert stats["agent_id"] == "test_agent"
        assert stats["facts"] >= 2
        assert stats["skills"] >= 1
        assert stats["total"] >= 3

class TestToolManager:
    """Test tool management"""
    
    @pytest.fixture
    async def tool_manager(self):
        """Create tool manager for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = JSONStorage(Path(temp_dir))
            await storage.initialize()
            yield ToolManager(storage)
    
    @pytest.mark.asyncio
    async def test_tool_registration(self, tool_manager):
        """Test tool registration"""
        from core.tools import BaseTool
        
        class TestTool(BaseTool):
            def __init__(self):
                super().__init__("test_tool", "Test tool for testing")
            
            async def execute(self, **kwargs):
                return {"success": True, "result": "test_result"}
            
            def get_parameters(self):
                return {"param1": {"type": "string", "description": "Test parameter"}}
        
        test_tool = TestTool()
        tool_manager.register_tool(test_tool)
        
        assert "test_tool" in tool_manager.tools
        assert tool_manager.get_tool("test_tool") == test_tool
    
    @pytest.mark.asyncio
    async def test_tool_execution(self, tool_manager):
        """Test tool execution"""
        from core.tools import BaseTool
        
        class TestTool(BaseTool):
            def __init__(self):
                super().__init__("test_tool", "Test tool for testing")
            
            async def execute(self, test_param="default"):
                return {"success": True, "result": f"executed with {test_param}"}
            
            def get_parameters(self):
                return {"test_param": {"type": "string", "description": "Test parameter"}}
        
        test_tool = TestTool()
        tool_manager.register_tool(test_tool)
        
        result = await tool_manager.execute_tool("test_tool", test_param="custom_value")
        
        assert result["success"] is True
        assert "executed with custom_value" in result["result"]
    
    @pytest.mark.asyncio
    async def test_tool_validation(self, tool_manager):
        """Test tool parameter validation"""
        from core.tools import BaseTool
        
        class TestTool(BaseTool):
            def __init__(self):
                super().__init__("test_tool", "Test tool for testing")
            
            async def execute(self, required_param):
                return {"success": True, "result": required_param}
            
            def get_parameters(self):
                return {
                    "required_param": {
                        "type": "string", 
                        "description": "Required parameter",
                        "required": True
                    }
                }
        
        test_tool = TestTool()
        tool_manager.register_tool(test_tool)
        
        # Test with missing required parameter
        result = await tool_manager.execute_tool("test_tool")
        assert result["success"] is False
        assert "required" in result["error"].lower()
    
    def test_get_available_tools(self, tool_manager):
        """Test getting available tools"""
        tools = tool_manager.get_available_tools()
        assert isinstance(tools, list)
        # Should have at least the default tools
        assert len(tools) > 0

class TestCommunicationManager:
    """Test communication management"""
    
    @pytest.fixture
    async def comm_manager(self):
        """Create communication manager for testing"""
        manager = CommunicationManager()
        await manager.start()
        yield manager
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_create_channel(self, comm_manager):
        """Test channel creation"""
        channel = comm_manager.create_channel("test_channel", ["agent1", "agent2"])
        
        assert channel.channel_id == "test_channel"
        assert "agent1" in channel.participants
        assert "agent2" in channel.participants
        assert channel.is_active
    
    @pytest.mark.asyncio
    async def test_send_message(self, comm_manager):
        """Test message sending"""
        from core.communication import MessageType
        
        channel = comm_manager.create_channel("test_channel", ["agent1", "agent2"])
        
        message_id = await comm_manager.send_message(
            channel_id="test_channel",
            message_type=MessageType.AGENT_COMMUNICATION,
            sender="agent1",
            recipient="agent2",
            content="Test message"
        )
        
        assert message_id is not None
        
        # Wait a bit for message processing
        await asyncio.sleep(0.1)
        
        messages = comm_manager.get_channel_messages("test_channel")
        assert len(messages) >= 1
        assert messages[0]["content"] == "Test message"
    
    @pytest.mark.asyncio
    async def test_broadcast_message(self, comm_manager):
        """Test message broadcasting"""
        from core.communication import MessageType
        
        # Create multiple channels
        comm_manager.create_channel("channel1", ["agent1", "agent2"])
        comm_manager.create_channel("channel2", ["agent1", "agent3"])
        
        await comm_manager.broadcast_message(
            message_type=MessageType.SYSTEM_MESSAGE,
            sender="system",
            content="Broadcast test message"
        )
        
        # Wait for message processing
        await asyncio.sleep(0.1)
        
        # Check messages in both channels
        messages1 = comm_manager.get_channel_messages("channel1")
        messages2 = comm_manager.get_channel_messages("channel2")
        
        assert len(messages1) >= 1
        assert len(messages2) >= 1

class TestAgentHierarchyManager:
    """Test agent hierarchy management"""
    
    @pytest.fixture
    async def hierarchy_manager(self):
        """Create hierarchy manager for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = JSONStorage(Path(temp_dir))
            await storage.initialize()
            yield AgentHierarchyManager(storage)
    
    @pytest.mark.asyncio
    async def test_register_agent(self, hierarchy_manager):
        """Test agent registration"""
        agent_info = {
            "name": "Test Agent",
            "role": "test",
            "capabilities": ["test_capability"],
            "superior_id": None,
            "subordinate_ids": []
        }
        
        await hierarchy_manager.register_agent("test_agent_1", agent_info)
        
        registered_info = await hierarchy_manager.get_agent_info("test_agent_1")
        assert registered_info is not None
        assert registered_info["name"] == "Test Agent"
        assert registered_info["role"] == "test"
    
    @pytest.mark.asyncio
    async def test_create_subordinate(self, hierarchy_manager):
        """Test subordinate creation"""
        # Register superior agent
        superior_info = {
            "name": "Superior Agent",
            "role": "superior",
            "capabilities": ["management"],
            "superior_id": None,
            "subordinate_ids": []
        }
        
        await hierarchy_manager.register_agent("superior_1", superior_info)
        
        # Create subordinate
        subordinate_config = {
            "name": "Subordinate Agent",
            "role": "subordinate",
            "capabilities": ["execution"]
        }
        
        subordinate_id = await hierarchy_manager.create_subordinate_agent("superior_1", subordinate_config)
        
        assert subordinate_id is not None
        
        # Verify hierarchy
        subordinate_info = await hierarchy_manager.get_agent_info(subordinate_id)
        assert subordinate_info["superior_id"] == "superior_1"
        
        superior_info_updated = await hierarchy_manager.get_agent_info("superior_1")
        assert subordinate_id in superior_info_updated["subordinate_ids"]
    
    @pytest.mark.asyncio
    async def test_get_hierarchy(self, hierarchy_manager):
        """Test hierarchy retrieval"""
        # Create test hierarchy
        await hierarchy_manager.register_agent("root", {
            "name": "Root Agent",
            "role": "root",
            "capabilities": ["all"],
            "superior_id": None,
            "subordinate_ids": []
        })
        
        subordinate_id = await hierarchy_manager.create_subordinate_agent("root", {
            "name": "Sub Agent",
            "role": "subordinate",
            "capabilities": ["specific"]
        })
        
        hierarchy = await hierarchy_manager.get_hierarchy()
        
        assert "root_agents" in hierarchy
        assert "relationships" in hierarchy
        assert "root" in hierarchy["root_agents"][0]["agent_id"]
        assert "root" in hierarchy["relationships"]
        assert subordinate_id in hierarchy["relationships"]
    
    @pytest.mark.asyncio
    async def test_task_delegation(self, hierarchy_manager):
        """Test task delegation"""
        # Setup hierarchy
        await hierarchy_manager.register_agent("superior", {
            "name": "Superior",
            "role": "manager",
            "capabilities": ["management"],
            "superior_id": None,
            "subordinate_ids": []
        })
        
        subordinate_id = await hierarchy_manager.create_subordinate_agent("superior", {
            "name": "Worker",
            "role": "worker",
            "capabilities": ["execution"]
        })
        
        # Delegate task
        task = {
            "description": "Test task",
            "priority": 2,
            "deadline": None
        }
        
        task_id = await hierarchy_manager.delegate_task("superior", subordinate_id, task)
        assert task_id is not None
        
        # Report completion
        result = {"status": "completed", "output": "Task done"}
        await hierarchy_manager.report_task_completion(task_id, subordinate_id, result)

class TestJSONStorage:
    """Test JSON storage system"""
    
    @pytest.fixture
    async def storage(self):
        """Create storage for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = JSONStorage(Path(temp_dir))
            await storage.initialize()
            yield storage
    
    @pytest.mark.asyncio
    async def test_read_write(self, storage):
        """Test basic read/write operations"""
        test_data = {"test_key": "test_value", "number": 42}
        
        await storage.write("test_file", test_data)
        read_data = await storage.read("test_file")
        
        assert read_data == test_data
    
    @pytest.mark.asyncio
    async def test_update(self, storage):
        """Test data updates"""
        initial_data = {"key1": "value1", "key2": "value2"}
        await storage.write("test_file", initial_data)
        
        update_data = {"key2": "updated_value", "key3": "new_value"}
        await storage.update("test_file", update_data)
        
        result = await storage.read("test_file")
        
        assert result["key1"] == "value1"  # Unchanged
        assert result["key2"] == "updated_value"  # Updated
        assert result["key3"] == "new_value"  # New
    
    @pytest.mark.asyncio
    async def test_append(self, storage):
        """Test appending to arrays"""
        initial_data = {"items": [1, 2, 3]}
        await storage.write("test_file", initial_data)
        
        await storage.append("test_file", "items", 4)
        
        result = await storage.read("test_file")
        assert result["items"] == [1, 2, 3, 4]
    
    @pytest.mark.asyncio
    async def test_file_locking(self, storage):
        """Test file locking mechanism"""
        # This test verifies that concurrent operations are handled safely
        async def write_operation(value):
            await storage.write("concurrent_test", {"value": value})
        
        # Run multiple concurrent writes
        tasks = [write_operation(i) for i in range(10)]
        await asyncio.gather(*tasks)
        
        # Should complete without errors
        result = await storage.read("concurrent_test")
        assert "value" in result

class TestIntegration:
    """Integration tests for complete system"""

    @pytest.fixture
    async def full_system(self):
        """Create complete system for integration testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = JSONStorage(Path(temp_dir))
            await storage.initialize()

            # Create components
            gemini_client = GeminiClient()
            tool_manager = ToolManager(storage)
            await tool_manager.initialize()

            comm_manager = CommunicationManager()
            await comm_manager.start()

            memory_manager = MemoryManager("test_agent", storage)

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

            yield {
                "agent": agent,
                "storage": storage,
                "tool_manager": tool_manager,
                "comm_manager": comm_manager,
                "memory_manager": memory_manager
            }

            await comm_manager.stop()

    @pytest.mark.asyncio
    async def test_agent_tool_execution(self, full_system):
        """Test agent executing tools"""
        agent = full_system["agent"]

        # Mock Gemini response that calls a tool
        with patch.object(agent.gemini_client, 'generate_response') as mock_generate:
            mock_generate.return_value = "TOOL_CALL: code_execution(code='print(\"Hello World\")')"

            response = await agent.process_message("Execute some Python code")

            assert response is not None
            assert len(response) > 0

    @pytest.mark.asyncio
    async def test_agent_memory_integration(self, full_system):
        """Test agent memory integration"""
        agent = full_system["agent"]
        memory_manager = full_system["memory_manager"]

        # Store some facts
        await memory_manager.store_fact("Python is a programming language")
        await memory_manager.store_fact("Agent Zero is an AI framework")

        # Mock Gemini to use memory
        with patch.object(agent.gemini_client, 'generate_response') as mock_generate:
            mock_generate.return_value = "Based on my memory, Python is a programming language."

            response = await agent.process_message("What do you know about Python?")

            assert "Python" in response

    @pytest.mark.asyncio
    async def test_multi_agent_communication(self, full_system):
        """Test multi-agent communication"""
        comm_manager = full_system["comm_manager"]

        # Create communication channel
        channel = comm_manager.create_channel("test_channel", ["agent1", "agent2"])

        # Send messages
        from core.communication import MessageType

        await comm_manager.send_message(
            channel_id="test_channel",
            message_type=MessageType.AGENT_COMMUNICATION,
            sender="agent1",
            recipient="agent2",
            content="Hello from agent1"
        )

        await comm_manager.send_message(
            channel_id="test_channel",
            message_type=MessageType.AGENT_COMMUNICATION,
            sender="agent2",
            recipient="agent1",
            content="Hello back from agent2"
        )

        # Wait for processing
        await asyncio.sleep(0.1)

        # Check messages
        messages = comm_manager.get_channel_messages("test_channel")
        assert len(messages) >= 2

        # Verify message content
        contents = [msg["content"] for msg in messages]
        assert "Hello from agent1" in contents
        assert "Hello back from agent2" in contents

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, full_system):
        """Test error handling across components"""
        agent = full_system["agent"]

        # Test tool execution error
        with patch.object(agent.tool_manager, 'execute_tool') as mock_execute:
            mock_execute.side_effect = Exception("Tool execution failed")

            # Agent should handle the error gracefully
            with patch.object(agent.gemini_client, 'generate_response') as mock_generate:
                mock_generate.return_value = "TOOL_CALL: nonexistent_tool()"

                response = await agent.process_message("Use a tool")

                # Should not crash and should provide error information
                assert response is not None
                assert len(response) > 0

    @pytest.mark.asyncio
    async def test_storage_persistence(self, full_system):
        """Test data persistence across restarts"""
        storage = full_system["storage"]
        memory_manager = full_system["memory_manager"]

        # Store some data
        await memory_manager.store_fact("Persistent fact")
        await storage.write("test_data", {"persistent": True})

        # Simulate restart by creating new components with same storage
        new_memory_manager = MemoryManager("test_agent", storage)

        # Verify data persists
        stored_data = await storage.read("test_data")
        assert stored_data["persistent"] is True

        # Search for stored fact
        facts = await new_memory_manager.search_memories("Persistent")
        assert len(facts) >= 1
        assert facts[0].content == "Persistent fact"
