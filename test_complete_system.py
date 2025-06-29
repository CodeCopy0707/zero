#!/usr/bin/env python3
"""
Complete system integration test for Agent Zero Gemini
This script tests the entire system end-to-end
"""
import asyncio
import sys
import logging
from pathlib import Path
import tempfile
import json
from unittest.mock import patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from main import AgentZeroGemini
from utils.logging_setup import setup_logging

logger = logging.getLogger(__name__)

async def test_complete_system():
    """Test the complete Agent Zero Gemini system"""
    
    print("🚀 Starting Agent Zero Gemini Complete System Test")
    print("=" * 60)
    
    # Setup logging
    setup_logging()
    
    try:
        # Initialize application
        print("📦 Initializing Agent Zero Gemini...")
        app = AgentZeroGemini()
        
        # Mock Gemini API to avoid real API calls
        with patch('core.gemini_client.GeminiClient.generate_response') as mock_generate:
            mock_generate.return_value = "Hello! I'm Agent Zero Gemini, ready to assist you with various tasks including coding, research, file operations, and more!"
            
            # Start the application
            print("🔄 Starting application...")
            await app.start()
            
            if not app.is_running:
                raise Exception("Application failed to start")
            
            print("✅ Application started successfully!")
            
            # Test 1: Basic Status Check
            print("\n🔍 Test 1: Basic Status Check")
            status = await app.get_status()
            
            assert status["running"] is True, "Application should be running"
            assert "root_agent" in status, "Root agent should be present"
            assert status["tools_count"] > 0, "Tools should be loaded"
            
            print(f"   ✅ Status: Running={status['running']}, Tools={status['tools_count']}")
            
            # Test 2: User Input Processing
            print("\n💬 Test 2: User Input Processing")
            response = await app.process_user_input("Hello, who are you and what can you do?")
            
            assert response is not None, "Response should not be None"
            assert len(response) > 0, "Response should not be empty"
            assert "Agent Zero Gemini" in response, "Response should mention Agent Zero Gemini"
            
            print(f"   ✅ Response received: {response[:100]}...")
            
            # Test 3: Tool System
            print("\n🔧 Test 3: Tool System")
            
            # Test code execution
            code_result = await app.root_agent.tool_manager.execute_tool(
                "code_execution",
                {"code": "print('Hello from Agent Zero Gemini!'); result = 2 + 2; print(f'2 + 2 = {result}')"}
            )
            
            assert code_result["success"] is True, "Code execution should succeed"
            assert "Hello from Agent Zero Gemini!" in code_result["result"]["output"], "Code output should be correct"
            
            print(f"   ✅ Code execution successful")
            
            # Test file operations
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write("Test file content for Agent Zero Gemini")
                temp_file = f.name
            
            try:
                file_result = await app.root_agent.tool_manager.execute_tool(
                    "file_operations",
                    {"operation": "read", "path": temp_file}
                )
                
                assert file_result["success"] is True, "File read should succeed"
                assert "Test file content" in file_result["result"]["content"], "File content should be correct"
                
                print(f"   ✅ File operations successful")
                
            finally:
                Path(temp_file).unlink()
            
            # Test 4: Memory System
            print("\n🧠 Test 4: Memory System")
            
            # Store some memories
            await app.root_agent.memory_manager.store_fact("Agent Zero Gemini is an advanced AI framework")
            await app.root_agent.memory_manager.store_skill("python_coding", "Expert Python programming capabilities")
            await app.root_agent.memory_manager.store_experience("system_test", "Successfully completed system integration test")
            
            # Search memories
            search_results = await app.root_agent.memory_manager.search_memories("Agent Zero")
            assert len(search_results) >= 1, "Should find memories about Agent Zero"
            
            # Get memory stats
            memory_stats = await app.root_agent.memory_manager.get_memory_stats()
            assert memory_stats["total"] >= 3, "Should have at least 3 memories"
            
            print(f"   ✅ Memory system: {memory_stats['total']} memories stored")
            
            # Test 5: Agent Hierarchy
            print("\n👥 Test 5: Agent Hierarchy")
            
            # Create subordinate agent
            subordinate_config = {
                "name": "Test Assistant",
                "role": "assistant",
                "capabilities": ["basic_operations", "text_processing"]
            }
            
            subordinate_id = await app.hierarchy_manager.create_subordinate_agent(
                "root_agent", subordinate_config
            )
            
            assert subordinate_id is not None, "Subordinate should be created"
            
            # Check hierarchy stats
            hierarchy_stats = await app.hierarchy_manager.get_hierarchy_stats()
            assert hierarchy_stats["total_agents"] >= 2, "Should have at least 2 agents"
            
            print(f"   ✅ Hierarchy: {hierarchy_stats['total_agents']} agents, {hierarchy_stats['root_agents']} root")
            
            # Test 6: Tool Statistics
            print("\n📊 Test 6: Tool Statistics")
            
            tool_stats = await app.root_agent.tool_manager.get_tool_statistics()
            assert "statistics" in tool_stats, "Should have statistics"
            assert tool_stats["total_calls"] >= 2, "Should have recorded tool calls"
            
            print(f"   ✅ Tool statistics: {tool_stats['total_calls']} total calls")
            
            # Test 7: Tool Health
            print("\n🏥 Test 7: Tool Health Check")
            
            health_report = await app.root_agent.tool_manager.validate_tool_health()
            assert len(health_report["healthy_tools"]) > 0, "Should have healthy tools"
            
            health_percentage = health_report["health_percentage"]
            print(f"   ✅ Tool health: {health_percentage:.1f}% healthy ({len(health_report['healthy_tools'])}/{health_report['total_tools']})")
            
            # Test 8: Conversation Flow
            print("\n💭 Test 8: Conversation Flow")
            
            conversation = [
                "What programming languages do you support?",
                "Can you help me with data analysis?",
                "What do you remember about our conversation?"
            ]
            
            for i, question in enumerate(conversation, 1):
                mock_generate.return_value = f"Response {i}: I can help with that! I support Python, JavaScript, and many other languages for various tasks."
                
                response = await app.process_user_input(question)
                assert response is not None, f"Response {i} should not be None"
                
                print(f"   ✅ Conversation turn {i}: Success")
            
            # Test 9: Error Handling
            print("\n⚠️  Test 9: Error Handling")
            
            # Test invalid tool
            invalid_result = await app.root_agent.tool_manager.execute_tool(
                "nonexistent_tool", {"param": "value"}
            )
            assert invalid_result["success"] is False, "Invalid tool should fail gracefully"
            
            # Test invalid code
            invalid_code_result = await app.root_agent.tool_manager.execute_tool(
                "code_execution", {"code": "undefined_variable"}
            )
            assert invalid_code_result["success"] is False, "Invalid code should fail gracefully"
            
            print(f"   ✅ Error handling: Graceful failure handling works")
            
            # Test 10: Backup and Recovery
            print("\n💾 Test 10: Backup and Recovery")
            
            backup_path = await app.root_agent.tool_manager.backup_tool_data()
            assert backup_path is not None, "Backup should be created"
            assert Path(backup_path).exists(), "Backup file should exist"
            
            # Verify backup content
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)
            
            assert "available_tools" in backup_data, "Backup should contain tools data"
            assert "tool_statistics" in backup_data, "Backup should contain statistics"
            
            print(f"   ✅ Backup created: {Path(backup_path).name}")
            
            # Cleanup backup
            Path(backup_path).unlink()
            
            # Final Status Check
            print("\n📋 Final System Status")
            final_status = await app.get_status()
            
            print(f"   • Running: {final_status['running']}")
            print(f"   • Root Agent: {final_status['root_agent']['name'] if final_status.get('root_agent') else 'None'}")
            print(f"   • Total Agents: {final_status['total_agents']}")
            print(f"   • Tools: {final_status['tools_count']}")
            print(f"   • Memory: {final_status['memory_stats'].get('total', 0)} items")
            
            # Stop the application
            print("\n🛑 Stopping application...")
            await app.stop()
            
            print("\n🎉 ALL TESTS PASSED! Agent Zero Gemini is fully functional!")
            print("=" * 60)
            print("✅ System Status: READY FOR PRODUCTION")
            print("✅ All core components working correctly")
            print("✅ Integration tests successful")
            print("✅ Error handling validated")
            print("✅ Memory and storage systems operational")
            print("✅ Tool system fully functional")
            print("✅ Agent hierarchy working")
            print("=" * 60)
            
            return True
            
    except Exception as e:
        print(f"\n❌ SYSTEM TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to stop the application if it was started
        try:
            if 'app' in locals() and app.is_running:
                await app.stop()
        except:
            pass
        
        return False

async def main():
    """Main test function"""
    success = await test_complete_system()
    
    if success:
        print("\n🚀 Agent Zero Gemini is ready to use!")
        print("   Run: python main.py --mode cli")
        print("   Or:  python main.py --mode web")
        sys.exit(0)
    else:
        print("\n💥 System test failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
