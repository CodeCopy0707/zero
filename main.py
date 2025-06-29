"""
Main entry point for Agent Zero Gemini
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core import AgentManager
from config import config
from utils.logging_setup import setup_logging

logger = logging.getLogger(__name__)

class AgentZeroGemini:
    """Main application class"""

    def __init__(self):
        """Initialize Agent Zero Gemini"""
        self.storage = None
        self.gemini_client = None
        self.tool_manager = None
        self.communication_manager = None
        self.hierarchy_manager = None
        self.root_agent = None
        self.is_running = False

    async def start(self):
        """Start the application"""
        try:
            # Setup logging
            setup_logging()

            logger.info("Starting Agent Zero Gemini...")

            # Initialize storage
            from storage.json_storage import JSONStorage
            self.storage = JSONStorage()
            await self.storage.initialize()

            # Initialize Gemini client
            from core.gemini_client import GeminiClient
            self.gemini_client = GeminiClient()

            # Initialize tool manager
            from core.tools import ToolManager
            self.tool_manager = ToolManager(self.storage)
            await self.tool_manager.initialize()

            # Initialize communication manager
            from core.communication import CommunicationManager, AgentHierarchyManager
            self.communication_manager = CommunicationManager()
            await self.communication_manager.start()

            # Initialize hierarchy manager
            self.hierarchy_manager = AgentHierarchyManager(self.storage)
            await self.hierarchy_manager.load_from_storage()

            # Create root agent
            from core.agent import Agent
            from core.memory import MemoryManager

            memory_manager = MemoryManager("root_agent", self.storage)

            self.root_agent = Agent(
                agent_id="root_agent",
                name=config.agent.name,
                role="root",
                gemini_client=self.gemini_client,
                tool_manager=self.tool_manager,
                memory_manager=memory_manager,
                communication_manager=self.communication_manager
            )

            # Register in hierarchy
            await self.hierarchy_manager.register_agent("root_agent", {
                "name": config.agent.name,
                "role": "root",
                "capabilities": ["code_execution", "web_search", "file_operations", "agent_creation"],
                "superior_id": None,
                "subordinate_ids": []
            })

            self.is_running = True
            logger.info("Agent Zero Gemini started successfully")

        except Exception as e:
            logger.error(f"Failed to start Agent Zero Gemini: {e}")
            raise

    async def stop(self):
        """Stop the application"""
        try:
            logger.info("Stopping Agent Zero Gemini...")

            self.is_running = False

            # Stop communication manager
            if self.communication_manager:
                await self.communication_manager.stop()

            # Save final state
            if self.root_agent:
                await self.root_agent.save_state()

            logger.info("Agent Zero Gemini stopped")

        except Exception as e:
            logger.error(f"Error stopping Agent Zero Gemini: {e}")

    async def process_user_input(self, message: str) -> str:
        """Process user input and return response"""
        if not self.is_running or not self.root_agent:
            return "Agent Zero is not running. Please start the application first."

        try:
            response = await self.root_agent.process_message(message)
            return response

        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            return f"I encountered an error while processing your message: {str(e)}"

    async def get_status(self) -> dict:
        """Get application status"""
        try:
            status = {
                "running": self.is_running,
                "root_agent": None,
                "total_agents": 0,
                "tools_count": 0,
                "memory_stats": {},
                "hierarchy_stats": {}
            }

            if self.root_agent:
                status["root_agent"] = {
                    "agent_id": self.root_agent.agent_id,
                    "name": self.root_agent.name,
                    "state": self.root_agent.state.value if hasattr(self.root_agent.state, 'value') else str(self.root_agent.state),
                    "iterations": getattr(self.root_agent, 'iteration_count', 0)
                }

                # Get memory stats
                if self.root_agent.memory_manager:
                    status["memory_stats"] = await self.root_agent.memory_manager.get_memory_stats()

                # Get tools count
                if self.tool_manager:
                    status["tools_count"] = len(self.tool_manager.tools)

            # Get hierarchy stats
            if self.hierarchy_manager:
                status["hierarchy_stats"] = await self.hierarchy_manager.get_hierarchy_stats()
                status["total_agents"] = status["hierarchy_stats"].get("total_agents", 0)

            return status

        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {"error": str(e), "running": self.is_running}

async def run_cli():
    """Run CLI interface"""
    app = AgentZeroGemini()
    
    try:
        # Start the application
        await app.start()
        
        print("🤖 Agent Zero Gemini - CLI Interface")
        print("Type 'quit' or 'exit' to stop")
        print("Type 'status' to see agent status")
        print("Type 'help' for more commands")
        print("-" * 50)
        
        while app.is_running:
            try:
                # Get user input
                user_input = input("\n👤 You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() in ['quit', 'exit']:
                    break
                elif user_input.lower() == 'status':
                    status = app.get_status()
                    print(f"\n📊 Status: {status}")
                    continue
                elif user_input.lower() == 'help':
                    print("\n📋 Available commands:")
                    print("  quit/exit - Stop the application")
                    print("  status    - Show agent status")
                    print("  help      - Show this help message")
                    print("  Any other input will be sent to the agent")
                    continue
                
                # Process with agent
                print("\n🤖 Agent Zero: ", end="", flush=True)
                response = await app.process_user_input(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\n\nReceived interrupt signal...")
                break
            except EOFError:
                print("\n\nReceived EOF signal...")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
        
    except Exception as e:
        logger.error(f"CLI error: {e}")
        print(f"❌ Failed to start Agent Zero Gemini: {e}")
    
    finally:
        # Stop the application
        await app.stop()
        print("\n👋 Goodbye!")

async def run_web_ui():
    """Run web UI"""
    try:
        logger.info("Starting Agent Zero Gemini Web Interface...")

        # Initialize application
        app_instance = AgentZeroGemini()
        await app_instance.start()

        # Import and create web app
        from web_ui.app import create_app
        import uvicorn

        # Create FastAPI app with application instance
        web_app = create_app(app_instance)

        logger.info(f"Web interface starting on http://{config.web_ui.host}:{config.web_ui.port}")

        # Configure uvicorn
        uvicorn_config = uvicorn.Config(
            web_app,
            host=config.web_ui.host,
            port=config.web_ui.port,
            log_level="info",
            access_log=True,
            reload=config.web_ui.debug
        )

        server = uvicorn.Server(uvicorn_config)

        # Run server
        await server.serve()

    except Exception as e:
        logger.error(f"Error running web UI: {e}")
        sys.exit(1)

async def run_tests():
    """Run tests"""
    try:
        logger.info("Running test suite...")

        import pytest

        # Test arguments
        test_args = [
            "tests/",
            "-v",
            "--tb=short",
            "--asyncio-mode=auto"
        ]

        # Add coverage if available
        try:
            import pytest_cov
            test_args.extend([
                "--cov=core",
                "--cov=tools",
                "--cov=storage",
                "--cov=web_ui",
                "--cov-report=html",
                "--cov-report=term"
            ])
        except ImportError:
            logger.info("pytest-cov not available, running without coverage")

        # Run tests
        exit_code = pytest.main(test_args)

        if exit_code == 0:
            logger.info("All tests passed!")
        else:
            logger.error("Some tests failed")

        sys.exit(exit_code)

    except ImportError:
        logger.error("pytest not installed. Install with: pip install pytest pytest-asyncio")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        sys.exit(1)

async def run_initialization():
    """Run system initialization"""
    try:
        logger.info("Running system initialization...")

        # Import and run initialization
        from initialize import main as init_main
        exit_code = await init_main()

        if exit_code == 0:
            logger.info("System initialization completed successfully")
        else:
            logger.error("System initialization failed")
            sys.exit(exit_code)

    except Exception as e:
        logger.error(f"Error during initialization: {e}")
        sys.exit(1)

def print_help():
    """Print help information"""
    help_text = """
Agent Zero Gemini - AI Agent Framework

Usage: python main.py <command> [options]

Commands:
  init    Initialize/setup the system
  web     Start web interface (default port: 8080)
  cli     Start command line interface
  test    Run test suite
  help    Show this help message

Examples:
  python main.py init                 # Setup system
  python main.py web                  # Start web UI
  python main.py cli                  # Start CLI
  python main.py test                 # Run tests

Environment Variables:
  GEMINI_API_KEY     - Your Gemini API key (required)
  WEB_UI_PORT        - Web interface port (default: 8080)
  LOG_LEVEL          - Logging level (default: INFO)
  STORAGE_PATH       - Data storage path (default: ./data)

For more information, visit: https://github.com/your-repo/agent-zero-gemini
"""
    print(help_text)

async def main():
    """Main function"""
    # Handle help command
    if len(sys.argv) > 1 and sys.argv[1].lower() in ["help", "-h", "--help"]:
        print_help()
        sys.exit(0)

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "init":
            await run_initialization()
        elif command == "cli":
            await run_cli()
        elif command == "web":
            await run_web_ui()
        elif command == "test":
            await run_tests()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python main.py [init|cli|web|test|help]")
            print("  init - Initialize/setup the system")
            print("  cli  - Run CLI interface")
            print("  web  - Run web interface")
            print("  test - Run test suite")
            print("  help - Show help message")
            sys.exit(1)
    else:
        # Default to CLI
        await run_cli()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)
