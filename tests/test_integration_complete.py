"""
Complete integration tests for Agent Zero Gemini
"""
import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, AsyncMock
import json

from main import AgentZeroGemini
from storage.json_storage import JSONStorage

class TestCompleteIntegration:
    """Complete system integration tests"""
    
    @pytest.fixture
    async def full_app(self):
        """Create complete application instance"""
        app = AgentZeroGemini()
        
        # Mock Gemini client to avoid API calls
        with patch('core.gemini_client.GeminiClient.generate_response') as mock_generate:
            mock_generate.return_value = "This is a test response from Agent Zero Gemini."
            
            await app.start()
            yield app
            await app.stop()
    
    @pytest.mark.asyncio
    async def test_application_startup_shutdown(self):
        """Test application startup and shutdown"""
        app = AgentZeroGemini()
        
        # Test startup
        await app.start()
        assert app.is_running is True
        assert app.root_agent is not None
        assert app.storage is not None
        assert app.tool_manager is not None
        
        # Test status
        status = await app.get_status()
        assert status["running"] is True
        assert "root_agent" in status
        
        # Test shutdown
        await app.stop()
        assert app.is_running is False
    
    @pytest.mark.asyncio
    async def test_user_input_processing(self, full_app):
        """Test complete user input processing flow"""
        with patch.object(full_app.gemini_client, 'generate_response') as mock_generate:
            mock_generate.return_value = "Hello! I'm Agent Zero Gemini. How can I help you today?"
            
            response = await full_app.process_user_input("Hello, who are you?")
            
            assert response is not None
            assert len(response) > 0
            assert "Agent Zero Gemini" in response
    
    @pytest.mark.asyncio
    async def test_tool_execution_flow(self, full_app):
        """Test complete tool execution flow"""
        with patch.object(full_app.gemini_client, 'generate_response') as mock_generate:
            # Mock response that includes tool usage
            mock_generate.return_value = "I'll execute some Python code for you. The result is: Hello World"
            
            # Test code execution through agent
            response = await full_app.process_user_input("Execute print('Hello World')")
            
            assert response is not None
            assert len(response) > 0
    
    @pytest.mark.asyncio
    async def test_memory_integration(self, full_app):
        """Test memory system integration"""
        # Store some facts
        await full_app.root_agent.memory_manager.store_fact("Python is a programming language")
        await full_app.root_agent.memory_manager.store_fact("Agent Zero is an AI framework")
        
        # Test memory retrieval
        memories = await full_app.root_agent.memory_manager.search_memories("Python")
        assert len(memories) >= 1
        assert any("Python" in memory.content for memory in memories)
        
        # Test memory stats
        stats = await full_app.root_agent.memory_manager.get_memory_stats()
        assert stats["total"] >= 2
        assert stats["facts"] >= 2
    
    @pytest.mark.asyncio
    async def test_agent_hierarchy_integration(self, full_app):
        """Test agent hierarchy integration"""
        # Test hierarchy stats
        hierarchy_stats = await full_app.hierarchy_manager.get_hierarchy_stats()
        assert hierarchy_stats["total_agents"] >= 1
        assert hierarchy_stats["root_agents"] >= 1
        
        # Test creating subordinate
        subordinate_config = {
            "name": "Test Subordinate",
            "role": "assistant",
            "capabilities": ["basic_operations"]
        }
        
        subordinate_id = await full_app.hierarchy_manager.create_subordinate_agent(
            "root_agent", subordinate_config
        )
        
        assert subordinate_id is not None
        
        # Verify hierarchy updated
        updated_stats = await full_app.hierarchy_manager.get_hierarchy_stats()
        assert updated_stats["total_agents"] >= 2
    
    @pytest.mark.asyncio
    async def test_tool_statistics_integration(self, full_app):
        """Test tool statistics integration"""
        # Execute some tools
        await full_app.root_agent.tool_manager.execute_tool(
            "code_execution",
            {"code": "print('Statistics test')"}
        )
        
        # Check statistics
        stats = await full_app.root_agent.tool_manager.get_tool_statistics()
        
        assert "statistics" in stats
        assert "code_execution" in stats["statistics"]
        assert stats["statistics"]["code_execution"]["total_calls"] >= 1
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, full_app):
        """Test error handling integration"""
        # Test tool execution error
        result = await full_app.root_agent.tool_manager.execute_tool(
            "nonexistent_tool",
            {"param": "value"}
        )
        
        assert result["success"] is False
        assert "not found" in result["error"]
        
        # Test invalid user input handling
        with patch.object(full_app.gemini_client, 'generate_response') as mock_generate:
            mock_generate.side_effect = Exception("API Error")
            
            response = await full_app.process_user_input("Test error handling")
            
            # Should handle error gracefully
            assert response is not None
            assert "error" in response.lower()
    
    @pytest.mark.asyncio
    async def test_storage_persistence_integration(self, full_app):
        """Test storage persistence integration"""
        # Store some data
        await full_app.root_agent.memory_manager.store_fact("Persistent test fact")
        
        # Verify data is stored
        memories = await full_app.root_agent.memory_manager.search_memories("Persistent")
        assert len(memories) >= 1
        
        # Test that data persists in storage
        memory_data = await full_app.storage.read("memory")
        assert "facts" in memory_data
        assert len(memory_data["facts"]) >= 1
    
    @pytest.mark.asyncio
    async def test_configuration_integration(self, full_app):
        """Test configuration integration"""
        # Test that configuration is properly loaded
        assert full_app.root_agent.name == "Agent Zero Gemini"  # From config
        assert full_app.root_agent.role == "root"
        
        # Test tool manager has correct configuration
        assert len(full_app.tool_manager.tools) > 0
        
        # Test storage configuration
        assert full_app.storage is not None
    
    @pytest.mark.asyncio
    async def test_web_ui_integration(self, full_app):
        """Test web UI integration"""
        from web_ui.app import create_app
        
        # Create web app
        web_app = create_app(full_app)
        
        # Test that app is created successfully
        assert web_app is not None
        
        # Test that routes are registered
        routes = [route.path for route in web_app.routes]
        expected_routes = ["/", "/api/status", "/api/tools", "/ws"]
        
        for expected_route in expected_routes:
            assert any(expected_route in route for route in routes)
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, full_app):
        """Test concurrent operations"""
        with patch.object(full_app.gemini_client, 'generate_response') as mock_generate:
            mock_generate.return_value = "Concurrent response"
            
            # Run multiple operations concurrently
            tasks = [
                full_app.process_user_input(f"Test message {i}")
                for i in range(5)
            ]
            
            responses = await asyncio.gather(*tasks)
            
            # All should complete successfully
            assert len(responses) == 5
            assert all(response is not None for response in responses)
    
    @pytest.mark.asyncio
    async def test_memory_search_integration(self, full_app):
        """Test memory search integration"""
        # Store various types of memories
        await full_app.root_agent.memory_manager.store_fact("Python is great for AI")
        await full_app.root_agent.memory_manager.store_skill("python_coding", "How to write Python code")
        await full_app.root_agent.memory_manager.store_experience("Solved a coding problem", "Successfully debugged the issue")
        
        # Test searching across all memory types
        python_memories = await full_app.root_agent.memory_manager.search_memories("Python")
        assert len(python_memories) >= 2
        
        # Test searching specific memory type
        facts = await full_app.root_agent.memory_manager.search_memories("Python", memory_type="fact")
        assert len(facts) >= 1
        assert all(memory.type == "fact" for memory in facts)
    
    @pytest.mark.asyncio
    async def test_tool_health_integration(self, full_app):
        """Test tool health monitoring integration"""
        # Test tool health validation
        health_report = await full_app.root_agent.tool_manager.validate_tool_health()
        
        assert "healthy_tools" in health_report
        assert "unhealthy_tools" in health_report
        assert "total_tools" in health_report
        
        # Should have healthy tools
        assert len(health_report["healthy_tools"]) > 0
        
        # Core tools should be healthy
        core_tools = ["code_execution", "terminal", "web_search", "file_operations"]
        healthy_tools = health_report["healthy_tools"]
        
        for tool in core_tools:
            assert tool in healthy_tools
    
    @pytest.mark.asyncio
    async def test_backup_and_recovery_integration(self, full_app):
        """Test backup and recovery integration"""
        # Store some data
        await full_app.root_agent.memory_manager.store_fact("Backup test fact")
        
        # Test tool data backup
        backup_path = await full_app.root_agent.tool_manager.backup_tool_data()
        assert backup_path is not None
        assert Path(backup_path).exists()
        
        # Verify backup contains data
        with open(backup_path, 'r') as f:
            backup_data = json.load(f)
        
        assert "tools_data" in backup_data
        assert "available_tools" in backup_data
        
        # Cleanup
        Path(backup_path).unlink()
    
    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, full_app):
        """Test complete conversation flow"""
        with patch.object(full_app.gemini_client, 'generate_response') as mock_generate:
            # Simulate a multi-turn conversation
            conversation = [
                ("Hello, what can you do?", "I'm Agent Zero Gemini, I can help with coding, research, and more!"),
                ("Can you write Python code?", "Yes, I can execute Python code. Let me show you."),
                ("What do you remember about our conversation?", "I remember you asked about my capabilities and Python coding.")
            ]
            
            for user_input, expected_response in conversation:
                mock_generate.return_value = expected_response
                
                response = await full_app.process_user_input(user_input)
                
                assert response is not None
                assert len(response) > 0
                
                # Store interaction in memory
                await full_app.root_agent.memory_manager.store_interaction(
                    role="user",
                    content=user_input
                )
                await full_app.root_agent.memory_manager.store_interaction(
                    role="assistant",
                    content=response
                )
            
            # Verify conversation is stored in memory
            interactions = await full_app.root_agent.memory_manager.get_recent_interactions(limit=10)
            assert len(interactions) >= 6  # 3 user + 3 assistant messages
