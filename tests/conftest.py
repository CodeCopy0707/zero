"""
Pytest configuration and fixtures for Agent Zero Gemini tests
"""
import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

# Set test environment
os.environ["TESTING"] = "true"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["GEMINI_API_KEY"] = "test_api_key"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

@pytest.fixture
def mock_gemini_client():
    """Mock Gemini client for testing"""
    with patch('core.gemini_client.GeminiClient') as mock_client:
        mock_instance = Mock()
        mock_instance.generate_response = Mock(return_value="Mocked response")
        mock_client.return_value = mock_instance
        yield mock_instance

@pytest.fixture
async def test_storage(temp_dir):
    """Create test storage instance"""
    from storage.json_storage import JSONStorage
    
    storage = JSONStorage(temp_dir)
    await storage.initialize()
    yield storage

@pytest.fixture
async def test_memory_manager(test_storage):
    """Create test memory manager"""
    from core.memory import MemoryManager
    
    memory_manager = MemoryManager("test_agent", test_storage)
    yield memory_manager

@pytest.fixture
async def test_tool_manager(test_storage):
    """Create test tool manager"""
    from core.tools import ToolManager
    
    tool_manager = ToolManager(test_storage)
    await tool_manager.initialize()
    yield tool_manager

@pytest.fixture
async def test_communication_manager():
    """Create test communication manager"""
    from core.communication import CommunicationManager
    
    comm_manager = CommunicationManager()
    await comm_manager.start()
    yield comm_manager
    await comm_manager.stop()

@pytest.fixture
async def test_agent(mock_gemini_client, test_tool_manager, test_memory_manager, test_communication_manager):
    """Create test agent"""
    from core.agent import Agent
    
    agent = Agent(
        agent_id="test_agent",
        name="Test Agent",
        role="test",
        gemini_client=mock_gemini_client,
        tool_manager=test_tool_manager,
        memory_manager=test_memory_manager,
        communication_manager=test_communication_manager
    )
    
    yield agent

@pytest.fixture
def sample_memory_data():
    """Sample memory data for testing"""
    return {
        "interactions": [
            {
                "id": "interaction_1",
                "agent_id": "test_agent",
                "type": "interaction",
                "content": "Hello, how are you?",
                "metadata": {"role": "user"},
                "importance": 0.5,
                "timestamp": "2024-01-01T00:00:00",
                "last_accessed": "2024-01-01T00:00:00",
                "access_count": 1
            }
        ],
        "facts": [
            {
                "id": "fact_1",
                "agent_id": "test_agent",
                "type": "fact",
                "content": "Python is a programming language",
                "metadata": {},
                "importance": 0.8,
                "timestamp": "2024-01-01T00:00:00",
                "last_accessed": "2024-01-01T00:00:00",
                "access_count": 1
            }
        ],
        "skills": [],
        "experiences": [],
        "metadata": {
            "total_interactions": 1,
            "total_facts": 1,
            "total_skills": 0,
            "total_experiences": 0,
            "last_updated": "2024-01-01T00:00:00"
        }
    }

@pytest.fixture
def sample_agent_data():
    """Sample agent data for testing"""
    return {
        "agents": {
            "test_agent": {
                "agent_id": "test_agent",
                "name": "Test Agent",
                "role": "test",
                "status": "active",
                "capabilities": ["test_capability"],
                "superior_id": None,
                "subordinate_ids": [],
                "created": "2024-01-01T00:00:00",
                "last_seen": "2024-01-01T00:00:00"
            }
        },
        "hierarchy": {
            "test_agent": {
                "superior": None,
                "subordinates": [],
                "level": 0
            }
        },
        "last_updated": "2024-01-01T00:00:00"
    }

@pytest.fixture
def sample_tools_data():
    """Sample tools data for testing"""
    return {
        "usage_history": [
            {
                "tool_name": "test_tool",
                "parameters": {"param1": "value1"},
                "result": {"success": True, "output": "test_output"},
                "execution_time": 0.1,
                "timestamp": "2024-01-01T00:00:00",
                "success": True
            }
        ],
        "statistics": {
            "test_tool": {
                "total_calls": 1,
                "successful_calls": 1,
                "failed_calls": 0,
                "total_execution_time": 0.1,
                "average_execution_time": 0.1,
                "last_used": "2024-01-01T00:00:00"
            }
        },
        "custom_tools": []
    }

@pytest.fixture
def sample_sessions_data():
    """Sample sessions data for testing"""
    return {
        "messages": [
            {
                "id": "msg_1",
                "type": "user_input",
                "sender": "user",
                "recipient": "test_agent",
                "content": "Hello",
                "metadata": {},
                "timestamp": "2024-01-01T00:00:00",
                "status": "delivered"
            }
        ],
        "task_delegations": [],
        "active_sessions": {}
    }

@pytest.fixture
def sample_knowledge_data():
    """Sample knowledge data for testing"""
    return {
        "facts": [
            {
                "id": "knowledge_fact_1",
                "content": "The capital of France is Paris",
                "category": "geography",
                "confidence": 0.9,
                "source": "general_knowledge",
                "created": "2024-01-01T00:00:00"
            }
        ],
        "procedures": [
            {
                "id": "procedure_1",
                "name": "How to greet users",
                "steps": ["Say hello", "Ask how they are", "Offer help"],
                "category": "communication",
                "created": "2024-01-01T00:00:00"
            }
        ],
        "categories": ["geography", "communication"],
        "last_updated": "2024-01-01T00:00:00"
    }

@pytest.fixture
async def populated_storage(test_storage, sample_memory_data, sample_agent_data, 
                           sample_tools_data, sample_sessions_data, sample_knowledge_data):
    """Storage populated with sample data"""
    await test_storage.write("memory", sample_memory_data)
    await test_storage.write("agents", sample_agent_data)
    await test_storage.write("tools", sample_tools_data)
    await test_storage.write("sessions", sample_sessions_data)
    await test_storage.write("knowledge", sample_knowledge_data)
    
    yield test_storage

# Test markers
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "network: mark test as requiring network access"
    )

# Test collection hooks
def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    # Add markers based on test names/paths
    for item in items:
        # Mark integration tests
        if "integration" in item.nodeid or "test_integration" in item.name:
            item.add_marker(pytest.mark.integration)
        
        # Mark unit tests
        elif "test_" in item.name and "integration" not in item.nodeid:
            item.add_marker(pytest.mark.unit)
        
        # Mark slow tests
        if "slow" in item.name or "benchmark" in item.name:
            item.add_marker(pytest.mark.slow)
        
        # Mark network tests
        if "network" in item.name or "api" in item.name:
            item.add_marker(pytest.mark.network)

# Async test support
@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio backend for anyio"""
    return "asyncio"

# Cleanup hooks
@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """Cleanup after each test"""
    yield
    # Cleanup any global state if needed
    pass

# Mock external services
@pytest.fixture(autouse=True)
def mock_external_services():
    """Mock external services for testing"""
    with patch('requests.get') as mock_get, \
         patch('requests.post') as mock_post, \
         patch('httpx.AsyncClient') as mock_httpx:
        
        # Setup default responses
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"status": "ok"}
        
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"status": "ok"}
        
        mock_httpx_instance = Mock()
        mock_httpx_instance.get.return_value.status_code = 200
        mock_httpx_instance.post.return_value.status_code = 200
        mock_httpx.return_value.__aenter__.return_value = mock_httpx_instance
        
        yield {
            "requests_get": mock_get,
            "requests_post": mock_post,
            "httpx_client": mock_httpx
        }
