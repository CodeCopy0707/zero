"""
Core Agent implementation for Agent Zero Gemini
"""
import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum

from .gemini_client import GeminiClient
from .memory import MemoryManager
from .tools import ToolManager
from .communication import CommunicationManager
from config import config

logger = logging.getLogger(__name__)

class AgentState(Enum):
    """Agent states"""
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    COMMUNICATING = "communicating"
    ERROR = "error"
    TERMINATED = "terminated"

class Agent:
    """Core Agent class"""
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        name: Optional[str] = None,
        role: Optional[str] = None,
        gemini_client=None,
        tool_manager=None,
        memory_manager=None,
        communication_manager=None,
        superior_agent: Optional['Agent'] = None,
        system_prompt: Optional[str] = None
    ):
        """Initialize Agent"""
        self.agent_id = agent_id or str(uuid.uuid4())
        self.name = name or f"Agent-{self.agent_id[:8]}"
        self.role = role or "General Assistant"
        self.superior_agent = superior_agent
        self.subordinate_agents: List['Agent'] = []

        # Core components - use provided or create new
        self.gemini_client = gemini_client or GeminiClient()
        self.memory_manager = memory_manager or MemoryManager(self.agent_id)
        self.tool_manager = tool_manager or ToolManager()
        self.communication_manager = communication_manager or CommunicationManager()

        # Agent state
        self.state = AgentState.IDLE
        self.current_task: Optional[str] = None
        self.iteration_count = 0
        self.max_iterations = config.agent.max_iterations

        # Timestamps
        self.created_at = datetime.now().isoformat()
        self.last_activity = datetime.now().isoformat()

        # System prompt
        self.system_prompt = system_prompt or self._get_default_system_prompt()
        
        # Callbacks
        self.on_state_change: Optional[Callable] = None
        self.on_message: Optional[Callable] = None
        self.on_tool_call: Optional[Callable] = None
        
        logger.info(f"Initialized agent {self.name} ({self.agent_id})")
    
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt"""
        return f"""You are {self.name}, a powerful AI agent powered by Gemini AI.

Your role: {self.role}

Core capabilities:
- You can use tools to accomplish tasks
- You can create subordinate agents to help with complex tasks
- You can communicate with your superior agent for guidance
- You have persistent memory to learn and improve
- You can execute code and use the terminal
- You can search the web and access information
- You can process files and documents

Guidelines:
1. Always think step by step before acting
2. Use tools when needed to accomplish tasks
3. Create subordinate agents for complex subtasks
4. Communicate clearly with users and other agents
5. Learn from your experiences and store important information in memory
6. Be helpful, accurate, and efficient
7. Ask for clarification when tasks are unclear
8. Report progress and results clearly

When you need to use a tool, format your response as:
TOOL_CALL: tool_name(parameter1="value1", parameter2="value2")

When you need to create a subordinate agent, use:
TOOL_CALL: create_subordinate_agent(name="Agent Name", role="Specific Role", task="Task Description")

When you need to communicate with your superior, use:
TOOL_CALL: communicate_with_superior(message="Your message")

Current task: {self.current_task or "No specific task assigned"}
"""
    
    async def process_message(self, message: str, context: Optional[Dict] = None) -> str:
        """Process incoming message"""
        try:
            self._set_state(AgentState.THINKING)
            
            # Store message in memory
            await self.memory_manager.store_interaction("user", message, context)
            
            # Get conversation history
            history = await self.memory_manager.get_recent_interactions(limit=10)
            
            # Prepare context for Gemini
            conversation_context = self._prepare_conversation_context(history)
            
            # Generate response
            response_data = await self.gemini_client.generate_with_tools(
                prompt=message,
                tools=self.tool_manager.get_available_tools(),
                system_prompt=self.system_prompt + f"\n\nConversation context:\n{conversation_context}"
            )
            
            response = response_data["response"]
            tool_calls = response_data["tool_calls"]
            
            # Execute tool calls if any
            if tool_calls:
                self._set_state(AgentState.ACTING)
                tool_results = await self._execute_tool_calls(tool_calls)
                
                # Incorporate tool results into response
                if tool_results:
                    tool_summary = self._format_tool_results(tool_results)
                    response += f"\n\nTool execution results:\n{tool_summary}"
            
            # Store response in memory
            await self.memory_manager.store_interaction("assistant", response, {
                "tool_calls": tool_calls,
                "iteration": self.iteration_count
            })
            
            self.iteration_count += 1
            self._set_state(AgentState.IDLE)
            
            # Trigger callback
            if self.on_message:
                await self.on_message(self, message, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self._set_state(AgentState.ERROR)
            return f"I encountered an error while processing your message: {str(e)}"
    
    async def _execute_tool_calls(self, tool_calls: List[Dict]) -> List[Dict]:
        """Execute tool calls"""
        results = []
        
        for tool_call in tool_calls:
            try:
                tool_name = tool_call["name"]
                parameters = tool_call["parameters"]
                
                # Special handling for agent management tools
                if tool_name == "create_subordinate_agent":
                    result = await self._create_subordinate_agent(**parameters)
                elif tool_name == "communicate_with_superior":
                    result = await self._communicate_with_superior(**parameters)
                else:
                    # Execute regular tool
                    result = await self.tool_manager.execute_tool(tool_name, parameters)
                
                results.append({
                    "tool": tool_name,
                    "parameters": parameters,
                    "result": result,
                    "success": True
                })
                
                # Trigger callback
                if self.on_tool_call:
                    await self.on_tool_call(self, tool_name, parameters, result)
                    
            except Exception as e:
                logger.error(f"Error executing tool {tool_call['name']}: {e}")
                results.append({
                    "tool": tool_call["name"],
                    "parameters": tool_call["parameters"],
                    "result": str(e),
                    "success": False
                })
        
        return results
    
    async def _create_subordinate_agent(self, name: str, role: str, task: str) -> str:
        """Create a subordinate agent"""
        try:
            if len(self.subordinate_agents) >= config.agent.max_subordinate_agents:
                return f"Cannot create more subordinate agents. Maximum limit ({config.agent.max_subordinate_agents}) reached."
            
            # Create subordinate agent
            subordinate = Agent(
                name=name,
                role=role,
                superior_agent=self,
                system_prompt=f"You are {name}, a subordinate agent with the role: {role}\n\nYour current task: {task}\n\nYou report to {self.name}."
            )
            
            subordinate.current_task = task
            self.subordinate_agents.append(subordinate)
            
            logger.info(f"Created subordinate agent {name} for task: {task}")
            return f"Successfully created subordinate agent '{name}' with role '{role}' to handle task: {task}"
            
        except Exception as e:
            logger.error(f"Error creating subordinate agent: {e}")
            return f"Failed to create subordinate agent: {str(e)}"
    
    async def _communicate_with_superior(self, message: str) -> str:
        """Communicate with superior agent"""
        try:
            if not self.superior_agent:
                return "No superior agent available for communication."
            
            # Send message to superior
            response = await self.superior_agent.receive_subordinate_message(self, message)
            return f"Superior agent response: {response}"
            
        except Exception as e:
            logger.error(f"Error communicating with superior: {e}")
            return f"Failed to communicate with superior: {str(e)}"
    
    async def receive_subordinate_message(self, subordinate: 'Agent', message: str) -> str:
        """Receive message from subordinate agent"""
        try:
            self._set_state(AgentState.COMMUNICATING)
            
            # Process subordinate's message
            context = f"Message from subordinate agent {subordinate.name} ({subordinate.role}): {message}"
            response = await self.process_message(context)
            
            self._set_state(AgentState.IDLE)
            return response
            
        except Exception as e:
            logger.error(f"Error receiving subordinate message: {e}")
            return f"Error processing your message: {str(e)}"
    
    def _prepare_conversation_context(self, history: List[Dict]) -> str:
        """Prepare conversation context from history"""
        context_lines = []
        for interaction in history[-5:]:  # Last 5 interactions
            role = interaction.get("role", "unknown")
            content = interaction.get("content", "")
            timestamp = interaction.get("timestamp", "")
            context_lines.append(f"[{timestamp}] {role}: {content[:200]}...")
        
        return "\n".join(context_lines)
    
    def _format_tool_results(self, results: List[Dict]) -> str:
        """Format tool execution results"""
        formatted_results = []
        for result in results:
            status = "✓" if result["success"] else "✗"
            formatted_results.append(f"{status} {result['tool']}: {result['result']}")
        
        return "\n".join(formatted_results)
    
    def _set_state(self, new_state: AgentState):
        """Set agent state"""
        old_state = self.state
        self.state = new_state
        
        if self.on_state_change:
            asyncio.create_task(self.on_state_change(self, old_state, new_state))
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "state": self.state.value,
            "current_task": self.current_task,
            "iteration_count": self.iteration_count,
            "subordinate_count": len(self.subordinate_agents),
            "has_superior": self.superior_agent is not None,
            "memory_size": self.memory_manager.get_memory_size(),
            "available_tools": len(self.tool_manager.get_available_tools())
        }
    
    async def shutdown(self):
        """Shutdown agent and cleanup resources"""
        try:
            self._set_state(AgentState.TERMINATED)
            
            # Shutdown subordinate agents
            for subordinate in self.subordinate_agents:
                await subordinate.shutdown()
            
            # Cleanup resources
            await self.memory_manager.close()
            
            logger.info(f"Agent {self.name} shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during agent shutdown: {e}")

    async def reset(self):
        """Reset agent state"""
        try:
            logger.info(f"Resetting agent {self.name}")

            # Reset state
            self._set_state(AgentState.IDLE)
            self.current_task = None
            self.iteration_count = 0

            # Clear working memory (keep long-term memory)
            # Note: We don't clear all memories, just reset the working state

            logger.info(f"Agent {self.name} reset complete")

        except Exception as e:
            logger.error(f"Error resetting agent: {e}")
            raise

    async def save_state(self):
        """Save agent state to storage"""
        try:
            logger.debug(f"Saving state for agent {self.name}")

            # Save current state to memory
            await self.memory_manager.store_experience(
                experience=f"Agent session ended",
                outcome=f"State: {self.state.value}, Iterations: {self.iteration_count}",
                metadata={
                    "agent_id": self.agent_id,
                    "final_state": self.state.value,
                    "total_iterations": self.iteration_count,
                    "current_task": self.current_task
                }
            )

            logger.debug(f"State saved for agent {self.name}")

        except Exception as e:
            logger.error(f"Error saving agent state: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "state": self.state.value,
            "current_task": self.current_task,
            "iteration_count": self.iteration_count,
            "subordinate_count": len(self.subordinate_agents),
            "created_at": getattr(self, 'created_at', None),
            "last_activity": getattr(self, 'last_activity', None)
        }

    async def create_subordinate(self, name: str, role: str, task: Optional[str] = None) -> 'Agent':
        """Create a subordinate agent"""
        try:
            logger.info(f"Creating subordinate agent: {name}")

            # Create subordinate agent
            subordinate = Agent(
                name=name,
                role=role,
                gemini_client=self.gemini_client,
                tool_manager=self.tool_manager,
                memory_manager=self.memory_manager,  # Share memory manager for now
                communication_manager=self.communication_manager,
                superior_agent=self
            )

            # Add to subordinates
            self.subordinate_agents.append(subordinate)

            # Assign task if provided
            if task:
                subordinate.current_task = task

            logger.info(f"Created subordinate agent: {name} for {self.name}")
            return subordinate

        except Exception as e:
            logger.error(f"Error creating subordinate agent: {e}")
            raise

    async def delegate_task(self, subordinate: 'Agent', task: str) -> str:
        """Delegate task to subordinate"""
        try:
            logger.info(f"Delegating task to {subordinate.name}: {task}")

            # Set task for subordinate
            subordinate.current_task = task

            # Process the task
            result = await subordinate.process_message(f"Your assigned task: {task}")

            # Store delegation in memory
            await self.memory_manager.store_experience(
                experience=f"Delegated task to {subordinate.name}",
                outcome=f"Task: {task}, Result: {result[:100]}...",
                metadata={
                    "subordinate_id": subordinate.agent_id,
                    "task": task,
                    "delegation_type": "task_assignment"
                }
            )

            return result

        except Exception as e:
            logger.error(f"Error delegating task: {e}")
            raise


class AgentManager:
    """Manager for multiple agents"""
    
    def __init__(self):
        """Initialize AgentManager"""
        self.agents: Dict[str, Agent] = {}
        self.root_agent: Optional[Agent] = None
        
    async def create_root_agent(self, name: str = "Agent Zero", role: str = "Primary Assistant") -> Agent:
        """Create root agent"""
        if self.root_agent:
            await self.root_agent.shutdown()
        
        self.root_agent = Agent(name=name, role=role)
        self.agents[self.root_agent.agent_id] = self.root_agent
        
        logger.info(f"Created root agent: {name}")
        return self.root_agent
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        return self.agents.get(agent_id)
    
    def get_all_agents(self) -> List[Agent]:
        """Get all agents"""
        return list(self.agents.values())
    
    async def shutdown_all(self):
        """Shutdown all agents"""
        for agent in self.agents.values():
            await agent.shutdown()
        
        self.agents.clear()
        self.root_agent = None
        
        logger.info("All agents shutdown complete")
