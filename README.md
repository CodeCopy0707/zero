# Agent Zero Gemini

A complete replica of the original Agent Zero framework powered by Google's Gemini AI. This implementation maintains 100% feature parity with the original while leveraging Gemini's advanced capabilities and using JSON-based local storage.

## 🚀 Features

### Core Capabilities
- **Gemini AI Integration**: Powered by Google's latest Gemini models
- **Multi-Agent Architecture**: Hierarchical agent system with superior-subordinate relationships
- **Persistent Memory**: Intelligent memory management with learning capabilities
- **Dynamic Tool System**: Extensible tool framework for code execution, web search, file operations, and more
- **Real-time Web UI**: Modern, responsive web interface with WebSocket communication
- **Streaming Responses**: Real-time response streaming for better user experience

### Advanced Features
- **Code Execution**: Execute Python code and terminal commands safely
- **Web Search**: Integrated web search capabilities
- **File Operations**: Read, write, and manage files and directories
- **Agent Communication**: Agents can communicate with each other and create subordinates
- **Memory Learning**: Agents learn from interactions and store important information
- **Tool Creation**: Create custom tools and instruments for specific tasks

### Architecture Highlights
- **Transparent & Customizable**: All prompts and behaviors are configurable
- **Safety First**: Built-in safety measures for code execution and command running
- **Scalable**: Support for multiple concurrent agents
- **Extensible**: Easy to add new tools and capabilities

## 📋 Requirements

- Python 3.8 or higher
- Google Gemini API key
- 4GB+ RAM recommended
- Internet connection for web search and Gemini API

## 🛠️ Installation

### Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/agent-zero-gemini.git
cd agent-zero-gemini
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment**
```bash
cp .env.example .env
# Edit .env file with your Gemini API key
```

4. **Run the application**
```bash
# CLI interface
python main.py cli

# Web interface
python main.py web

# Basic test
python main.py test
```

### Environment Configuration

Create a `.env` file with the following configuration:

```env
# Gemini AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash-exp
GEMINI_TEMPERATURE=0.7
GEMINI_MAX_TOKENS=8192

# Agent Configuration
AGENT_NAME=Agent Zero Gemini
AGENT_DESCRIPTION=A powerful AI agent powered by Gemini AI
MAX_ITERATIONS=50
MAX_SUBORDINATE_AGENTS=5
MEMORY_LIMIT=1000

# Web UI Configuration
WEB_UI_HOST=0.0.0.0
WEB_UI_PORT=8080
WEB_UI_DEBUG=false

# Security
SECRET_KEY=your_secret_key_here
ALLOWED_HOSTS=localhost,127.0.0.1
```

## 🎯 Usage

### CLI Interface

```bash
python main.py cli
```

The CLI provides a simple text-based interface to interact with the agent:
- Type your messages and press Enter
- Use `status` to see agent status
- Use `quit` or `exit` to stop
- Use `help` for more commands

### Web Interface

```bash
python main.py web
```

Then open your browser to `http://localhost:8080` for a modern web interface featuring:
- Real-time chat with the agent
- Live status monitoring
- Tool usage visualization
- Agent hierarchy display
- Memory exploration

### API Usage

You can also use Agent Zero Gemini programmatically:

```python
import asyncio
from main import AgentZeroGemini

async def main():
    # Create and start the agent
    app = AgentZeroGemini()
    await app.start()
    
    # Send a message
    response = await app.process_user_input("Hello! Can you help me with a Python script?")
    print(response)
    
    # Stop the agent
    await app.stop()

asyncio.run(main())
```

## 🔧 Configuration

### System Prompts

All agent behavior is controlled by prompts in the `prompts/` directory:
- `system_prompts.py`: Core system prompts
- Custom prompts can be added as YAML, JSON, or text files

### Tools

Tools are defined in `core/tools.py`. Built-in tools include:
- **Code Execution**: Execute Python code safely
- **Terminal Commands**: Run shell commands with safety checks
- **Web Search**: Search the web using DuckDuckGo
- **File Operations**: Read, write, list, and manage files

### Memory System

The memory system stores:
- **Interactions**: Conversation history
- **Facts**: Important information learned
- **Skills**: Procedures and techniques
- **Experiences**: Past problem-solving approaches

## 🏗️ Architecture

```
Agent Zero Gemini/
├── core/                   # Core agent system
│   ├── agent.py           # Main agent implementation
│   ├── gemini_client.py   # Gemini AI integration
│   ├── memory.py          # Memory management
│   ├── tools.py           # Tool system
│   └── communication.py   # Agent communication
├── prompts/               # System prompts
├── web_ui/                # Web interface
│   ├── app.py            # FastAPI application
│   ├── templates/        # HTML templates
│   └── static/           # CSS/JS assets
├── utils/                 # Utility functions
├── config.py             # Configuration management
└── main.py               # Application entry point
```

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by the original [Agent Zero](https://github.com/frdel/agent-zero) framework
- Powered by Google's Gemini AI
- Built with modern Python async/await patterns
- UI inspired by modern chat interfaces

## 🔗 Links

- [Original Agent Zero](https://github.com/frdel/agent-zero)
- [Google Gemini AI](https://ai.google.dev/)
- [Documentation](docs/)
- [Examples](examples/)

## 📞 Support

If you encounter any issues or have questions:
1. Check the [documentation](docs/)
2. Search existing [issues](https://github.com/yourusername/agent-zero-gemini/issues)
3. Create a new issue if needed

---

**Agent Zero Gemini** - Bringing the power of Gemini AI to autonomous agent systems! 🤖✨
# zero
