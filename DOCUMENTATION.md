# Agent Zero Gemini - Complete Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Configuration](#configuration)
4. [API Reference](#api-reference)
5. [Tool System](#tool-system)
6. [Memory System](#memory-system)
7. [Multi-Agent System](#multi-agent-system)
8. [Web Interface](#web-interface)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)

## System Overview

Agent Zero Gemini is a complete replica of the original Agent Zero framework, powered by Google's Gemini AI. It provides a sophisticated multi-agent system with persistent memory, dynamic tool execution, and comprehensive web interface.

### Key Features
- **Advanced AI Reasoning**: Powered by Google Gemini AI
- **Multi-Agent Hierarchy**: Create and manage subordinate agents
- **Persistent Memory**: Long-term memory with facts, skills, and experiences
- **Dynamic Tool System**: 50+ built-in tools with extensible architecture
- **Web Interface**: Modern, responsive UI with real-time communication
- **Safety & Security**: Built-in protections and sandboxing
- **Comprehensive Testing**: Full test suite with validation

## Architecture

### Core Components

```
Agent Zero Gemini
├── main.py                    # Application entry point
├── config.py                  # Configuration management
├── core/
│   ├── agent.py              # Core agent implementation
│   ├── gemini_client.py      # Gemini AI client
│   ├── memory.py             # Memory management system
│   ├── tools.py              # Tool management framework
│   └── communication.py     # Inter-agent communication
├── tools/                    # Tool implementations
│   ├── code_execution.py     # Python code execution
│   ├── terminal.py           # Terminal command execution
│   ├── web_search.py         # Web search capabilities
│   ├── file_operations.py    # File system operations
│   ├── browser_tools.py      # Browser automation
│   ├── audio_tools.py        # Audio processing
│   ├── document_tools.py     # Document processing
│   ├── network_tools.py      # Network operations
│   └── analysis_tools.py     # Data analysis
├── storage/
│   └── json_storage.py       # JSON-based storage system
├── web_ui/                   # Web interface
│   ├── app.py               # FastAPI backend
│   ├── templates/           # HTML templates
│   └── static/              # CSS, JS, assets
├── tests/                    # Test suite
│   ├── test_*.py            # Unit tests
│   ├── test_integration_*.py # Integration tests
│   └── run_validation.py    # Validation suite
└── utils/
    └── logging_setup.py      # Logging configuration
```

### Data Flow

1. **User Input** → Agent receives message
2. **Memory Retrieval** → Agent searches relevant memories
3. **AI Processing** → Gemini AI generates response with tool calls
4. **Tool Execution** → Tools are executed as needed
5. **Memory Storage** → Interaction and results stored
6. **Response** → Final response sent to user

## Configuration

### Environment Variables

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional
AGENT_NAME="Agent Zero Gemini"
AGENT_DESCRIPTION="Advanced AI Assistant"
MAX_ITERATIONS=10
WEB_HOST=localhost
WEB_PORT=8000
LOG_LEVEL=INFO
STORAGE_PATH=./data
```

### Configuration File (config.py)

```python
class Config:
    # Agent settings
    agent = AgentConfig(
        name="Agent Zero Gemini",
        description="Advanced AI Assistant",
        max_iterations=10
    )
    
    # Gemini settings
    gemini = GeminiConfig(
        model_name="gemini-pro",
        temperature=0.7,
        max_tokens=8192
    )
    
    # Web UI settings
    web_ui = WebUIConfig(
        host="localhost",
        port=8000,
        enable_cors=True
    )
    
    # Storage settings
    storage = StorageConfig(
        type="json",
        path="./data"
    )
    
    # Security settings
    security = SecurityConfig(
        enable_code_execution=True,
        allowed_file_paths=["./workspace", "./data"],
        restricted_commands=["rm -rf", "sudo", "chmod 777"]
    )
```

## API Reference

### Main Application Class

```python
class AgentZeroGemini:
    async def start() -> None
    async def stop() -> None
    async def process_user_input(message: str) -> str
    async def get_status() -> Dict[str, Any]
```

### Agent Class

```python
class Agent:
    async def process_message(message: str, context: Optional[Dict] = None) -> str
    async def reset() -> None
    async def save_state() -> None
    def get_status() -> Dict[str, Any]
    async def create_subordinate(name: str, role: str, task: Optional[str] = None) -> Agent
    async def delegate_task(subordinate: Agent, task: str) -> str
```

### Tool Manager

```python
class ToolManager:
    async def execute_tool(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]
    def get_available_tools() -> List[Dict[str, Any]]
    async def get_tool_statistics() -> Dict[str, Any]
    async def validate_tool_health() -> Dict[str, Any]
    def get_tool_capabilities() -> Dict[str, List[str]]
    async def backup_tool_data() -> str
```

### Memory Manager

```python
class MemoryManager:
    async def store_memory(memory: Memory) -> str
    async def retrieve_memory(memory_id: str) -> Optional[Memory]
    async def search_memories(query: str, memory_type: Optional[str] = None) -> List[Memory]
    async def store_fact(content: str, importance: float = 0.5) -> str
    async def store_skill(name: str, description: str, importance: float = 0.7) -> str
    async def store_experience(experience: str, outcome: str, importance: float = 0.6) -> str
    async def store_interaction(role: str, content: str, context: Optional[Dict] = None) -> str
    async def get_memory_stats() -> Dict[str, Any]
```

## Tool System

### Built-in Tools

#### Code Execution Tool
```python
# Execute Python code
result = await tool_manager.execute_tool("code_execution", {
    "code": "print('Hello World')",
    "timeout": 30
})
```

#### Web Search Tool
```python
# Search the web
result = await tool_manager.execute_tool("web_search", {
    "query": "Python programming",
    "max_results": 5
})
```

#### File Operations Tool
```python
# Read a file
result = await tool_manager.execute_tool("file_operations", {
    "operation": "read",
    "path": "./example.txt"
})

# Write a file
result = await tool_manager.execute_tool("file_operations", {
    "operation": "write",
    "path": "./output.txt",
    "content": "Hello World"
})
```

#### Terminal Tool
```python
# Execute terminal command
result = await tool_manager.execute_tool("terminal", {
    "command": "ls",
    "args": ["-la"]
})
```

### Creating Custom Tools

```python
from core.tools import BaseTool

class CustomTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="custom_tool",
            description="A custom tool for specific tasks"
        )
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        # Tool implementation
        return {
            "success": True,
            "result": "Custom tool executed successfully"
        }
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "param1": {
                "type": "string",
                "description": "First parameter",
                "required": True
            }
        }
```

## Memory System

### Memory Types

1. **Facts**: Static information and knowledge
2. **Skills**: Learned capabilities and procedures
3. **Experiences**: Past interactions and outcomes
4. **Interactions**: Conversation history

### Memory Operations

```python
# Store different types of memories
await memory_manager.store_fact("Python is a programming language")
await memory_manager.store_skill("web_scraping", "How to scrape web pages")
await memory_manager.store_experience("debugging", "Successfully fixed the bug")

# Search memories
results = await memory_manager.search_memories("Python")
facts = await memory_manager.search_memories("Python", memory_type="fact")

# Get statistics
stats = await memory_manager.get_memory_stats()
print(f"Total memories: {stats['total']}")
```

## Multi-Agent System

### Agent Hierarchy

```python
# Create subordinate agent
subordinate = await root_agent.create_subordinate(
    name="Research Assistant",
    role="researcher",
    task="Gather information about AI trends"
)

# Delegate task
result = await root_agent.delegate_task(
    subordinate,
    "Research the latest developments in AI"
)
```

### Communication

```python
# Agents can communicate with each other
message = await subordinate.communicate_with_superior(
    "I found interesting information about AI trends"
)
```

## Web Interface

### Starting Web Server

```python
from web_ui.app import run_web_app
from main import AgentZeroGemini

app = AgentZeroGemini()
await run_web_app(app)
```

### API Endpoints

- `GET /` - Main web interface
- `GET /api/status` - Get agent status
- `GET /api/tools` - Get available tools
- `GET /api/agents` - Get agent hierarchy
- `POST /api/chat` - Send chat message
- `WebSocket /ws/{client_id}` - Real-time communication

### WebSocket Messages

```javascript
// Send message
websocket.send(JSON.stringify({
    type: "chat",
    message: "Hello, Agent!"
}));

// Receive response
websocket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "response") {
        console.log("Agent response:", data.message);
    }
};
```

## Testing

### Running Tests

```bash
# Unit tests
pytest tests/

# Integration tests
pytest tests/test_integration_*.py

# Complete system test
python test_complete_system.py

# Validation suite
python tests/run_validation.py
```

### Test Categories

1. **Unit Tests**: Individual component testing
2. **Integration Tests**: Component interaction testing
3. **System Tests**: End-to-end functionality testing
4. **Performance Tests**: Load and performance testing
5. **Security Tests**: Safety and security validation

## Troubleshooting

### Common Issues

#### 1. Gemini API Key Issues
```
Error: Invalid API key
Solution: Check GEMINI_API_KEY environment variable
```

#### 2. Tool Execution Failures
```
Error: Tool execution timeout
Solution: Increase timeout in tool configuration
```

#### 3. Memory Storage Issues
```
Error: Cannot write to storage
Solution: Check file permissions and storage path
```

#### 4. Web Interface Not Loading
```
Error: Connection refused
Solution: Check if port is available and firewall settings
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python main.py --mode cli
```

### Health Checks

```python
# Check tool health
health = await tool_manager.validate_tool_health()
print(f"Healthy tools: {len(health['healthy_tools'])}")

# Check memory stats
stats = await memory_manager.get_memory_stats()
print(f"Memory usage: {stats}")

# Check agent status
status = await app.get_status()
print(f"Agent status: {status}")
```

### Performance Monitoring

```python
# Tool statistics
stats = await tool_manager.get_tool_statistics()
print(f"Total tool calls: {stats['total_calls']}")

# Memory statistics
memory_stats = await memory_manager.get_memory_stats()
print(f"Memory efficiency: {memory_stats}")
```

---

For more detailed information, see the source code documentation and inline comments.
