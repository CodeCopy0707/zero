"""
Command Line Interface for Agent Zero Gemini
"""
import asyncio
import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path

from core.agent import Agent
from core.gemini_client import GeminiClient
from core.memory import MemoryManager
from core.tools import ToolManager
from core.communication import CommunicationManager, AgentHierarchyManager
from storage.json_storage import JSONStorage
from config import config
from utils.logging_setup import setup_logging

logger = logging.getLogger(__name__)

class CLIInterface:
    """Command Line Interface for Agent Zero Gemini"""
    
    def __init__(self, app_instance=None):
        """Initialize CLI interface"""
        self.app_instance = app_instance
        self.running = False
        self.commands = {
            "help": self.show_help,
            "status": self.show_status,
            "memory": self.memory_commands,
            "tools": self.tools_commands,
            "agents": self.agents_commands,
            "clear": self.clear_screen,
            "history": self.show_history,
            "export": self.export_data,
            "config": self.config_commands,
            "debug": self.debug_commands,
            "quit": self.quit_cli,
            "exit": self.quit_cli
        }
        
        self.conversation_history = []
        
        logger.info("Initialized CLI interface")
    
    async def run(self):
        """Run the CLI interface"""
        try:
            self.running = True
            
            # Initialize if not provided
            if not self.app_instance:
                await self._initialize_app()
            
            # Show welcome message
            self._show_welcome()
            
            # Main CLI loop
            while self.running:
                try:
                    user_input = input("\n🤖 Agent Zero > ").strip()
                    
                    if not user_input:
                        continue
                    
                    # Check for commands
                    if user_input.startswith("/"):
                        await self._handle_command(user_input[1:])
                    else:
                        # Regular conversation
                        await self._handle_conversation(user_input)
                
                except KeyboardInterrupt:
                    print("\n\nUse '/quit' to exit gracefully.")
                    continue
                except EOFError:
                    break
                except Exception as e:
                    logger.error(f"Error in CLI loop: {e}")
                    print(f"❌ Error: {e}")
        
        except Exception as e:
            logger.error(f"Error running CLI: {e}")
            print(f"❌ Failed to start CLI: {e}")
        
        finally:
            if self.app_instance:
                await self.app_instance.stop()
    
    async def _initialize_app(self):
        """Initialize the application"""
        print("🚀 Initializing Agent Zero Gemini...")
        
        try:
            # Import the main application class
            from main import AgentZeroGemini
            
            self.app_instance = AgentZeroGemini()
            await self.app_instance.start()
            
            print("✅ Initialization complete!")
            
        except Exception as e:
            logger.error(f"Error initializing app: {e}")
            print(f"❌ Initialization failed: {e}")
            sys.exit(1)
    
    def _show_welcome(self):
        """Show welcome message"""
        welcome_text = f"""
╔══════════════════════════════════════════════════════════════╗
║                    🤖 Agent Zero Gemini                      ║
║                  Command Line Interface                      ║
╠══════════════════════════════════════════════════════════════╣
║  Agent: {config.agent.name:<48} ║
║  Model: {config.gemini.model:<48} ║
║  Storage: JSON-based                                         ║
╚══════════════════════════════════════════════════════════════╝

💡 Tips:
  • Type your message to chat with the agent
  • Use /help to see available commands
  • Use /quit to exit

Ready to assist! What would you like to do?
"""
        print(welcome_text)
    
    async def _handle_command(self, command_input: str):
        """Handle CLI commands"""
        parts = command_input.split()
        if not parts:
            return
        
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        if command in self.commands:
            try:
                await self.commands[command](args)
            except Exception as e:
                logger.error(f"Error executing command {command}: {e}")
                print(f"❌ Error executing command: {e}")
        else:
            print(f"❌ Unknown command: {command}")
            print("💡 Use /help to see available commands")
    
    async def _handle_conversation(self, user_input: str):
        """Handle regular conversation"""
        try:
            print("🤔 Thinking...")
            
            # Add to history
            self.conversation_history.append({
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().isoformat()
            })
            
            # Get response from agent
            response = await self.app_instance.process_user_input(user_input)
            
            # Add response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().isoformat()
            })
            
            # Display response
            print(f"\n🤖 {config.agent.name}:")
            print(f"   {response}")
            
        except Exception as e:
            logger.error(f"Error in conversation: {e}")
            print(f"❌ Error: {e}")
    
    async def show_help(self, args):
        """Show help information"""
        help_text = """
📚 Available Commands:

🔧 System Commands:
  /help                 - Show this help message
  /status               - Show system status
  /clear                - Clear screen
  /quit, /exit          - Exit the CLI

💾 Memory Commands:
  /memory stats         - Show memory statistics
  /memory search <query> - Search memories
  /memory clear         - Clear all memories
  /memory export        - Export memories to file

🛠️  Tool Commands:
  /tools list           - List available tools
  /tools stats          - Show tool usage statistics
  /tools test <tool>    - Test a specific tool

👥 Agent Commands:
  /agents list          - List all agents
  /agents hierarchy     - Show agent hierarchy
  /agents create <role> - Create subordinate agent

📊 Data Commands:
  /history              - Show conversation history
  /export chat          - Export chat history
  /export all           - Export all data

⚙️  Configuration:
  /config show          - Show current configuration
  /config set <key> <value> - Set configuration value

🐛 Debug Commands:
  /debug logs           - Show recent logs
  /debug errors         - Show error statistics
  /debug performance    - Show performance metrics

💡 Tips:
  • Commands are case-insensitive
  • Use Tab completion where available
  • Most commands support additional arguments
"""
        print(help_text)
    
    async def show_status(self, args):
        """Show system status"""
        try:
            status = await self.app_instance.get_status()
            
            print("\n📊 System Status:")
            print("=" * 50)
            print(f"🟢 Running: {status.get('running', False)}")
            
            if status.get('root_agent'):
                agent_info = status['root_agent']
                print(f"🤖 Agent: {agent_info.get('name', 'Unknown')}")
                print(f"📍 State: {agent_info.get('state', 'Unknown')}")
                print(f"🔄 Iterations: {agent_info.get('iterations', 0)}")
            
            print(f"👥 Total Agents: {status.get('total_agents', 0)}")
            print(f"🛠️  Tools Available: {status.get('tools_count', 0)}")
            
            if status.get('memory_stats'):
                memory = status['memory_stats']
                print(f"🧠 Memory Items: {memory.get('total', 0)}")
                print(f"   - Interactions: {memory.get('interactions', 0)}")
                print(f"   - Facts: {memory.get('facts', 0)}")
                print(f"   - Skills: {memory.get('skills', 0)}")
            
        except Exception as e:
            print(f"❌ Error getting status: {e}")
    
    async def memory_commands(self, args):
        """Handle memory-related commands"""
        if not args:
            print("💡 Usage: /memory [stats|search|clear|export] [args]")
            return
        
        subcommand = args[0].lower()
        
        try:
            if subcommand == "stats":
                memory_manager = self.app_instance.root_agent.memory_manager
                stats = await memory_manager.get_memory_stats()
                
                print("\n🧠 Memory Statistics:")
                print("=" * 30)
                for key, value in stats.items():
                    print(f"{key}: {value}")
            
            elif subcommand == "search":
                if len(args) < 2:
                    print("💡 Usage: /memory search <query>")
                    return
                
                query = " ".join(args[1:])
                memory_manager = self.app_instance.root_agent.memory_manager
                results = await memory_manager.search_memories(query, limit=10)
                
                print(f"\n🔍 Search Results for '{query}':")
                print("=" * 40)
                
                if results:
                    for i, memory in enumerate(results, 1):
                        print(f"{i}. [{memory.type}] {memory.content[:100]}...")
                        print(f"   Importance: {memory.importance:.2f}")
                        print()
                else:
                    print("No results found.")
            
            elif subcommand == "clear":
                confirm = input("⚠️  Are you sure you want to clear all memories? (y/N): ")
                if confirm.lower() == 'y':
                    memory_manager = self.app_instance.root_agent.memory_manager
                    await memory_manager.clear_memories()
                    print("✅ Memories cleared.")
                else:
                    print("❌ Operation cancelled.")
            
            elif subcommand == "export":
                # Export memories to file
                memory_manager = self.app_instance.root_agent.memory_manager
                stats = await memory_manager.get_memory_stats()
                
                filename = f"memories_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                with open(filename, 'w') as f:
                    json.dump(stats, f, indent=2)
                
                print(f"✅ Memories exported to {filename}")
            
            else:
                print(f"❌ Unknown memory command: {subcommand}")
        
        except Exception as e:
            print(f"❌ Error in memory command: {e}")
    
    async def tools_commands(self, args):
        """Handle tool-related commands"""
        if not args:
            print("💡 Usage: /tools [list|stats|test] [args]")
            return
        
        subcommand = args[0].lower()
        
        try:
            tool_manager = self.app_instance.root_agent.tool_manager
            
            if subcommand == "list":
                tools = tool_manager.get_available_tools()
                
                print("\n🛠️  Available Tools:")
                print("=" * 30)
                
                for tool in tools:
                    print(f"• {tool['name']}: {tool['description']}")
            
            elif subcommand == "stats":
                stats = await tool_manager.get_tool_statistics()
                
                print("\n📊 Tool Statistics:")
                print("=" * 30)
                print(f"Total Tools: {stats.get('total_tools', 0)}")
                
                if stats.get('statistics'):
                    print("\nUsage Statistics:")
                    for tool_name, tool_stats in stats['statistics'].items():
                        print(f"  {tool_name}:")
                        print(f"    Calls: {tool_stats.get('total_calls', 0)}")
                        print(f"    Success Rate: {tool_stats.get('successful_calls', 0)}/{tool_stats.get('total_calls', 0)}")
                        print(f"    Avg Time: {tool_stats.get('average_execution_time', 0):.3f}s")
            
            elif subcommand == "test":
                if len(args) < 2:
                    print("💡 Usage: /tools test <tool_name>")
                    return
                
                tool_name = args[1]
                print(f"🧪 Testing tool: {tool_name}")
                
                # Simple test execution
                result = await tool_manager.execute_tool(tool_name)
                
                if result.get('success'):
                    print("✅ Tool test successful")
                    print(f"Result: {result.get('result', 'No result')}")
                else:
                    print("❌ Tool test failed")
                    print(f"Error: {result.get('error', 'Unknown error')}")
            
            else:
                print(f"❌ Unknown tools command: {subcommand}")
        
        except Exception as e:
            print(f"❌ Error in tools command: {e}")
    
    async def agents_commands(self, args):
        """Handle agent-related commands"""
        if not args:
            print("💡 Usage: /agents [list|hierarchy|create] [args]")
            return
        
        subcommand = args[0].lower()
        
        try:
            hierarchy_manager = self.app_instance.hierarchy_manager
            
            if subcommand == "list":
                hierarchy = await hierarchy_manager.get_hierarchy()
                
                print("\n👥 Active Agents:")
                print("=" * 30)
                
                for agent_id, info in hierarchy.get('relationships', {}).items():
                    print(f"• {agent_id}")
                    print(f"  Role: {info.get('role', 'Unknown')}")
                    print(f"  Level: {info.get('level', 0)}")
                    print(f"  Status: {info.get('status', 'Unknown')}")
                    print()
            
            elif subcommand == "hierarchy":
                hierarchy = await hierarchy_manager.get_hierarchy()
                
                print("\n🌳 Agent Hierarchy:")
                print("=" * 30)
                
                # Display hierarchy tree
                self._display_hierarchy_tree(hierarchy)
            
            elif subcommand == "create":
                if len(args) < 2:
                    print("💡 Usage: /agents create <role>")
                    return
                
                role = args[1]
                
                # Create subordinate agent
                subordinate_config = {
                    "name": f"{role.title()} Agent",
                    "role": role,
                    "capabilities": ["basic_operations"]
                }
                
                subordinate_id = await hierarchy_manager.create_subordinate_agent(
                    "root_agent", subordinate_config
                )
                
                print(f"✅ Created subordinate agent: {subordinate_id}")
                print(f"Role: {role}")
            
            else:
                print(f"❌ Unknown agents command: {subcommand}")
        
        except Exception as e:
            print(f"❌ Error in agents command: {e}")
    
    def _display_hierarchy_tree(self, hierarchy: Dict[str, Any]):
        """Display agent hierarchy as a tree"""
        relationships = hierarchy.get('relationships', {})
        root_agents = hierarchy.get('root_agents', [])
        
        def print_agent(agent_id: str, level: int = 0):
            indent = "  " * level
            info = relationships.get(agent_id, {})
            
            print(f"{indent}├─ {agent_id}")
            print(f"{indent}   Role: {info.get('role', 'Unknown')}")
            print(f"{indent}   Status: {info.get('status', 'Unknown')}")
            
            # Print subordinates
            subordinates = info.get('subordinates', [])
            for subordinate_id in subordinates:
                print_agent(subordinate_id, level + 1)
        
        for root_agent in root_agents:
            print_agent(root_agent['agent_id'])
    
    async def clear_screen(self, args):
        """Clear the screen"""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
    
    async def show_history(self, args):
        """Show conversation history"""
        print("\n📜 Conversation History:")
        print("=" * 50)
        
        for i, entry in enumerate(self.conversation_history[-10:], 1):  # Last 10 entries
            role = "👤 You" if entry['role'] == 'user' else f"🤖 {config.agent.name}"
            timestamp = entry['timestamp'][:19]  # Remove microseconds
            content = entry['content'][:100] + "..." if len(entry['content']) > 100 else entry['content']
            
            print(f"{i}. [{timestamp}] {role}:")
            print(f"   {content}")
            print()
    
    async def export_data(self, args):
        """Export data"""
        if not args:
            print("💡 Usage: /export [chat|all]")
            return
        
        export_type = args[0].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        try:
            if export_type == "chat":
                filename = f"chat_export_{timestamp}.json"
                
                with open(filename, 'w') as f:
                    json.dump(self.conversation_history, f, indent=2)
                
                print(f"✅ Chat history exported to {filename}")
            
            elif export_type == "all":
                # Export all system data
                export_dir = Path(f"export_{timestamp}")
                export_dir.mkdir(exist_ok=True)
                
                # Export conversation history
                with open(export_dir / "chat_history.json", 'w') as f:
                    json.dump(self.conversation_history, f, indent=2)
                
                # Export system status
                status = await self.app_instance.get_status()
                with open(export_dir / "system_status.json", 'w') as f:
                    json.dump(status, f, indent=2)
                
                print(f"✅ All data exported to {export_dir}/")
            
            else:
                print(f"❌ Unknown export type: {export_type}")
        
        except Exception as e:
            print(f"❌ Error exporting data: {e}")
    
    async def config_commands(self, args):
        """Handle configuration commands"""
        if not args:
            print("💡 Usage: /config [show|set] [args]")
            return
        
        subcommand = args[0].lower()
        
        if subcommand == "show":
            print("\n⚙️  Current Configuration:")
            print("=" * 40)
            print(f"Agent Name: {config.agent.name}")
            print(f"Gemini Model: {config.gemini.model}")
            print(f"Temperature: {config.gemini.temperature}")
            print(f"Max Tokens: {config.gemini.max_tokens}")
            print(f"Storage Path: {config.storage.path}")
            print(f"Log Level: {config.logging.level}")
        
        elif subcommand == "set":
            print("⚠️  Configuration changes require restart to take effect.")
        
        else:
            print(f"❌ Unknown config command: {subcommand}")
    
    async def debug_commands(self, args):
        """Handle debug commands"""
        if not args:
            print("💡 Usage: /debug [logs|errors|performance]")
            return
        
        subcommand = args[0].lower()
        
        if subcommand == "logs":
            print("📋 Recent logs would be displayed here")
            # Implementation would read from log files
        
        elif subcommand == "errors":
            print("🐛 Error statistics would be displayed here")
            # Implementation would show error handler statistics
        
        elif subcommand == "performance":
            print("⚡ Performance metrics would be displayed here")
            # Implementation would show performance data
        
        else:
            print(f"❌ Unknown debug command: {subcommand}")
    
    async def quit_cli(self, args):
        """Quit the CLI"""
        print("\n👋 Goodbye! Thanks for using Agent Zero Gemini!")
        self.running = False
