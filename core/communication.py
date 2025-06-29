"""
Communication system for Agent Zero Gemini
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

class MessageType(Enum):
    """Message types"""
    USER_INPUT = "user_input"
    AGENT_RESPONSE = "agent_response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    AGENT_COMMUNICATION = "agent_communication"
    SYSTEM_MESSAGE = "system_message"
    ERROR = "error"

@dataclass
class Message:
    """Communication message"""
    id: str
    type: MessageType
    sender: str
    recipient: str
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "type": self.type.value,
            "sender": self.sender,
            "recipient": self.recipient,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create from dictionary"""
        return cls(
            id=data["id"],
            type=MessageType(data["type"]),
            sender=data["sender"],
            recipient=data["recipient"],
            content=data["content"],
            metadata=data["metadata"],
            timestamp=datetime.fromisoformat(data["timestamp"])
        )

class CommunicationChannel:
    """Communication channel between agents or with users"""
    
    def __init__(self, channel_id: str, participants: List[str]):
        """Initialize communication channel"""
        self.channel_id = channel_id
        self.participants = participants
        self.messages: List[Message] = []
        self.message_handlers: Dict[str, List[Callable]] = {}
        self.is_active = True
        
        logger.debug(f"Created communication channel {channel_id} with participants: {participants}")
    
    async def send_message(self, message: Message):
        """Send message through channel"""
        if not self.is_active:
            raise RuntimeError("Communication channel is not active")
        
        # Store message
        self.messages.append(message)
        
        # Notify handlers
        await self._notify_handlers(message)
        
        logger.debug(f"Sent message {message.id} in channel {self.channel_id}")
    
    async def _notify_handlers(self, message: Message):
        """Notify message handlers"""
        handlers = self.message_handlers.get(message.recipient, [])
        for handler in handlers:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")
    
    def add_message_handler(self, participant: str, handler: Callable):
        """Add message handler for participant"""
        if participant not in self.message_handlers:
            self.message_handlers[participant] = []
        self.message_handlers[participant].append(handler)
    
    def remove_message_handler(self, participant: str, handler: Callable):
        """Remove message handler"""
        if participant in self.message_handlers:
            try:
                self.message_handlers[participant].remove(handler)
            except ValueError:
                pass
    
    def get_messages(self, participant: Optional[str] = None, limit: Optional[int] = None) -> List[Message]:
        """Get messages for participant"""
        messages = self.messages
        
        if participant:
            messages = [msg for msg in messages if msg.recipient == participant or msg.sender == participant]
        
        if limit:
            messages = messages[-limit:]
        
        return messages
    
    def close(self):
        """Close communication channel"""
        self.is_active = False
        self.message_handlers.clear()
        logger.debug(f"Closed communication channel {self.channel_id}")

class CommunicationManager:
    """Manages communication between agents and users"""
    
    def __init__(self):
        """Initialize CommunicationManager"""
        self.channels: Dict[str, CommunicationChannel] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.is_running = False
        self.message_processor_task: Optional[asyncio.Task] = None
        
        logger.info("Initialized CommunicationManager")
    
    async def start(self):
        """Start communication manager"""
        if self.is_running:
            return
        
        self.is_running = True
        self.message_processor_task = asyncio.create_task(self._process_messages())
        
        logger.info("Started CommunicationManager")
    
    async def stop(self):
        """Stop communication manager"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.message_processor_task:
            self.message_processor_task.cancel()
            try:
                await self.message_processor_task
            except asyncio.CancelledError:
                pass
        
        # Close all channels
        for channel in self.channels.values():
            channel.close()
        
        logger.info("Stopped CommunicationManager")
    
    def create_channel(self, channel_id: str, participants: List[str]) -> CommunicationChannel:
        """Create communication channel"""
        if channel_id in self.channels:
            raise ValueError(f"Channel {channel_id} already exists")
        
        channel = CommunicationChannel(channel_id, participants)
        self.channels[channel_id] = channel
        
        logger.info(f"Created communication channel: {channel_id}")
        return channel
    
    def get_channel(self, channel_id: str) -> Optional[CommunicationChannel]:
        """Get communication channel"""
        return self.channels.get(channel_id)
    
    def remove_channel(self, channel_id: str):
        """Remove communication channel"""
        if channel_id in self.channels:
            self.channels[channel_id].close()
            del self.channels[channel_id]
            logger.info(f"Removed communication channel: {channel_id}")
    
    async def send_message(
        self,
        channel_id: str,
        message_type: MessageType,
        sender: str,
        recipient: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Send message through channel"""
        channel = self.get_channel(channel_id)
        if not channel:
            raise ValueError(f"Channel {channel_id} not found")
        
        # Create message
        message = Message(
            id=f"{channel_id}_{datetime.now().timestamp()}",
            type=message_type,
            sender=sender,
            recipient=recipient,
            content=content,
            metadata=metadata or {},
            timestamp=datetime.now()
        )
        
        # Queue message for processing
        await self.message_queue.put((channel_id, message))
        
        return message.id
    
    async def _process_messages(self):
        """Process messages from queue"""
        while self.is_running:
            try:
                # Get message from queue
                channel_id, message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=1.0
                )
                
                # Send through channel
                channel = self.get_channel(channel_id)
                if channel:
                    await channel.send_message(message)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    async def broadcast_message(
        self,
        message_type: MessageType,
        sender: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Broadcast message to all channels"""
        for channel_id, channel in self.channels.items():
            for participant in channel.participants:
                if participant != sender:
                    await self.send_message(
                        channel_id=channel_id,
                        message_type=message_type,
                        sender=sender,
                        recipient=participant,
                        content=content,
                        metadata=metadata
                    )
    
    def get_channel_messages(
        self,
        channel_id: str,
        participant: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get messages from channel"""
        channel = self.get_channel(channel_id)
        if not channel:
            return []
        
        messages = channel.get_messages(participant, limit)
        return [msg.to_dict() for msg in messages]
    
    def get_active_channels(self) -> List[str]:
        """Get list of active channel IDs"""
        return [cid for cid, channel in self.channels.items() if channel.is_active]
    
    def get_channel_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get channel information"""
        channel = self.get_channel(channel_id)
        if not channel:
            return None
        
        return {
            "channel_id": channel.channel_id,
            "participants": channel.participants,
            "message_count": len(channel.messages),
            "is_active": channel.is_active,
            "last_message": channel.messages[-1].to_dict() if channel.messages else None
        }

class StreamingCommunicator:
    """Handles streaming communication for real-time responses"""
    
    def __init__(self):
        """Initialize StreamingCommunicator"""
        self.active_streams: Dict[str, asyncio.Queue] = {}
        self.stream_handlers: Dict[str, List[Callable]] = {}
        
    async def create_stream(self, stream_id: str) -> asyncio.Queue:
        """Create streaming queue"""
        if stream_id in self.active_streams:
            raise ValueError(f"Stream {stream_id} already exists")
        
        queue = asyncio.Queue()
        self.active_streams[stream_id] = queue
        
        logger.debug(f"Created stream: {stream_id}")
        return queue
    
    async def send_to_stream(self, stream_id: str, data: Any):
        """Send data to stream"""
        if stream_id not in self.active_streams:
            raise ValueError(f"Stream {stream_id} not found")
        
        await self.active_streams[stream_id].put(data)
    
    async def close_stream(self, stream_id: str):
        """Close stream"""
        if stream_id in self.active_streams:
            # Send end signal
            await self.active_streams[stream_id].put(None)
            del self.active_streams[stream_id]
            
            logger.debug(f"Closed stream: {stream_id}")
    
    def get_stream(self, stream_id: str) -> Optional[asyncio.Queue]:
        """Get stream queue"""
        return self.active_streams.get(stream_id)
    
    def list_active_streams(self) -> List[str]:
        """List active stream IDs"""
        return list(self.active_streams.keys())

class AgentHierarchyManager:
    """Manages agent hierarchy and subordinate relationships"""

    def __init__(self, storage=None):
        """Initialize AgentHierarchyManager"""
        from storage.json_storage import JSONStorage
        self.storage = storage or JSONStorage()
        self.active_agents: Dict[str, Dict[str, Any]] = {}
        self.hierarchy: Dict[str, Dict[str, Any]] = {}

        logger.info("Initialized AgentHierarchyManager")

    async def register_agent(self, agent_id: str, agent_info: Dict[str, Any]):
        """Register an agent in the hierarchy"""
        try:
            self.active_agents[agent_id] = {
                "agent_id": agent_id,
                "name": agent_info.get("name", f"Agent {agent_id}"),
                "role": agent_info.get("role", "agent"),
                "status": "active",
                "capabilities": agent_info.get("capabilities", []),
                "superior_id": agent_info.get("superior_id"),
                "subordinate_ids": agent_info.get("subordinate_ids", []),
                "created": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat()
            }

            # Update hierarchy
            await self._update_hierarchy(agent_id)

            # Store in persistent storage
            await self._save_agent_registry()

            logger.info(f"Registered agent: {agent_id}")

        except Exception as e:
            logger.error(f"Error registering agent {agent_id}: {e}")
            raise

    async def create_subordinate_agent(self, superior_id: str, subordinate_config: Dict[str, Any]) -> str:
        """Create a subordinate agent"""
        try:
            import uuid

            # Generate subordinate ID
            subordinate_id = f"agent_{uuid.uuid4().hex[:8]}"

            # Create subordinate info
            subordinate_info = {
                "name": subordinate_config.get("name", f"Subordinate {subordinate_id[-8:]}"),
                "role": subordinate_config.get("role", "subordinate"),
                "capabilities": subordinate_config.get("capabilities", []),
                "superior_id": superior_id,
                "subordinate_ids": []
            }

            # Register subordinate
            await self.register_agent(subordinate_id, subordinate_info)

            # Update superior's subordinate list
            if superior_id in self.active_agents:
                self.active_agents[superior_id]["subordinate_ids"].append(subordinate_id)
                await self._save_agent_registry()

            logger.info(f"Created subordinate {subordinate_id} for {superior_id}")
            return subordinate_id

        except Exception as e:
            logger.error(f"Error creating subordinate agent: {e}")
            raise

    async def remove_agent(self, agent_id: str):
        """Remove an agent from hierarchy"""
        try:
            if agent_id not in self.active_agents:
                return

            agent_info = self.active_agents[agent_id]

            # Handle subordinates
            for subordinate_id in agent_info.get("subordinate_ids", []):
                if subordinate_id in self.active_agents:
                    # Reassign to superior or make independent
                    superior_id = agent_info.get("superior_id")
                    if superior_id:
                        self.active_agents[subordinate_id]["superior_id"] = superior_id
                        if superior_id in self.active_agents:
                            self.active_agents[superior_id]["subordinate_ids"].append(subordinate_id)
                    else:
                        self.active_agents[subordinate_id]["superior_id"] = None

            # Remove from superior's subordinate list
            superior_id = agent_info.get("superior_id")
            if superior_id and superior_id in self.active_agents:
                subordinates = self.active_agents[superior_id]["subordinate_ids"]
                if agent_id in subordinates:
                    subordinates.remove(agent_id)

            # Remove agent
            del self.active_agents[agent_id]
            if agent_id in self.hierarchy:
                del self.hierarchy[agent_id]

            await self._save_agent_registry()

            logger.info(f"Removed agent: {agent_id}")

        except Exception as e:
            logger.error(f"Error removing agent {agent_id}: {e}")

    async def get_hierarchy(self) -> Dict[str, Any]:
        """Get complete agent hierarchy"""
        try:
            hierarchy = {
                "root_agents": [],
                "relationships": {},
                "levels": {}
            }

            for agent_id, agent_info in self.active_agents.items():
                # Calculate level
                level = self._calculate_level(agent_id)

                # Add to hierarchy
                hierarchy["relationships"][agent_id] = {
                    "superior": agent_info.get("superior_id"),
                    "subordinates": agent_info.get("subordinate_ids", []),
                    "level": level,
                    "name": agent_info.get("name"),
                    "role": agent_info.get("role"),
                    "status": agent_info.get("status")
                }

                # Track levels
                if level not in hierarchy["levels"]:
                    hierarchy["levels"][level] = []
                hierarchy["levels"][level].append(agent_id)

                # Root agents (no superior)
                if not agent_info.get("superior_id"):
                    hierarchy["root_agents"].append(agent_id)

            return hierarchy

        except Exception as e:
            logger.error(f"Error getting hierarchy: {e}")
            return {"root_agents": [], "relationships": {}, "levels": {}}

    async def delegate_task(self, superior_id: str, subordinate_id: str, task: Dict[str, Any]) -> str:
        """Delegate task to subordinate"""
        try:
            import uuid

            task_id = str(uuid.uuid4())

            # Validate hierarchy
            if subordinate_id not in self.active_agents:
                raise ValueError(f"Subordinate {subordinate_id} not found")

            subordinate_info = self.active_agents[subordinate_id]
            if subordinate_info.get("superior_id") != superior_id:
                raise ValueError(f"Agent {subordinate_id} is not a subordinate of {superior_id}")

            # Create task delegation record
            delegation = {
                "task_id": task_id,
                "superior_id": superior_id,
                "subordinate_id": subordinate_id,
                "task": task,
                "status": "delegated",
                "created": datetime.now().isoformat(),
                "deadline": task.get("deadline"),
                "priority": task.get("priority", 2)
            }

            # Store delegation
            await self._store_delegation(delegation)

            logger.info(f"Task {task_id} delegated from {superior_id} to {subordinate_id}")
            return task_id

        except Exception as e:
            logger.error(f"Error delegating task: {e}")
            raise

    async def report_task_completion(self, task_id: str, subordinate_id: str, result: Dict[str, Any]):
        """Report task completion"""
        try:
            # Update delegation record
            delegations_data = await self.storage.read("sessions")
            delegations = delegations_data.get("task_delegations", [])

            for delegation in delegations:
                if delegation.get("task_id") == task_id and delegation.get("subordinate_id") == subordinate_id:
                    delegation["status"] = "completed"
                    delegation["result"] = result
                    delegation["completed"] = datetime.now().isoformat()
                    break

            await self.storage.update("sessions", {"task_delegations": delegations})

            logger.info(f"Task {task_id} completed by {subordinate_id}")

        except Exception as e:
            logger.error(f"Error reporting task completion: {e}")

    async def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent information"""
        return self.active_agents.get(agent_id)

    async def get_subordinates(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get subordinates of an agent"""
        if agent_id not in self.active_agents:
            return []

        subordinate_ids = self.active_agents[agent_id].get("subordinate_ids", [])
        subordinates = []

        for sub_id in subordinate_ids:
            if sub_id in self.active_agents:
                subordinates.append(self.active_agents[sub_id])

        return subordinates

    async def get_superior(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get superior of an agent"""
        if agent_id not in self.active_agents:
            return None

        superior_id = self.active_agents[agent_id].get("superior_id")
        if superior_id and superior_id in self.active_agents:
            return self.active_agents[superior_id]

        return None

    def _calculate_level(self, agent_id: str) -> int:
        """Calculate hierarchy level of agent"""
        level = 0
        current_id = agent_id
        visited = set()

        while current_id and current_id not in visited:
            visited.add(current_id)
            if current_id in self.active_agents:
                superior_id = self.active_agents[current_id].get("superior_id")
                if superior_id:
                    level += 1
                    current_id = superior_id
                else:
                    break
            else:
                break

        return level

    async def _update_hierarchy(self, agent_id: str):
        """Update hierarchy information"""
        if agent_id in self.active_agents:
            agent_info = self.active_agents[agent_id]

            self.hierarchy[agent_id] = {
                "level": self._calculate_level(agent_id),
                "superior": agent_info.get("superior_id"),
                "subordinates": agent_info.get("subordinate_ids", []),
                "updated": datetime.now().isoformat()
            }

    async def _save_agent_registry(self):
        """Save agent registry to storage"""
        try:
            agents_data = await self.storage.read("agents")
            agents_data["agents"] = self.active_agents
            agents_data["hierarchy"] = self.hierarchy
            agents_data["last_updated"] = datetime.now().isoformat()

            await self.storage.write("agents", agents_data)

        except Exception as e:
            logger.error(f"Error saving agent registry: {e}")

    async def _store_delegation(self, delegation: Dict[str, Any]):
        """Store task delegation"""
        try:
            sessions_data = await self.storage.read("sessions")

            if "task_delegations" not in sessions_data:
                sessions_data["task_delegations"] = []

            sessions_data["task_delegations"].append(delegation)

            await self.storage.write("sessions", sessions_data)

        except Exception as e:
            logger.error(f"Error storing delegation: {e}")

    async def load_from_storage(self):
        """Load agent registry from storage"""
        try:
            agents_data = await self.storage.read("agents")

            self.active_agents = agents_data.get("agents", {})
            self.hierarchy = agents_data.get("hierarchy", {})

            # Filter only active agents
            active_agents = {}
            for agent_id, agent_info in self.active_agents.items():
                if agent_info.get("status") == "active":
                    active_agents[agent_id] = agent_info

            self.active_agents = active_agents

            logger.info(f"Loaded {len(self.active_agents)} active agents from storage")

        except Exception as e:
            logger.error(f"Error loading from storage: {e}")

    async def get_hierarchy_stats(self) -> Dict[str, Any]:
        """Get hierarchy statistics"""
        try:
            stats = {
                "total_agents": len(self.active_agents),
                "root_agents": 0,
                "subordinate_agents": 0,
                "max_depth": 0,
                "agents_by_role": {},
                "agents_by_level": {}
            }

            for agent_id, agent_info in self.active_agents.items():
                # Count by hierarchy position
                if not agent_info.get("superior_id"):
                    stats["root_agents"] += 1
                else:
                    stats["subordinate_agents"] += 1

                # Count by role
                role = agent_info.get("role", "unknown")
                stats["agents_by_role"][role] = stats["agents_by_role"].get(role, 0) + 1

                # Count by level
                level = self._calculate_level(agent_id)
                stats["agents_by_level"][level] = stats["agents_by_level"].get(level, 0) + 1
                stats["max_depth"] = max(stats["max_depth"], level)

            return stats

        except Exception as e:
            logger.error(f"Error getting hierarchy stats: {e}")
            return {"error": str(e)}

    async def create_subordinate_agent(self, superior_id: str, subordinate_config: Dict[str, Any]) -> str:
        """Create a subordinate agent"""
        try:
            import uuid

            # Generate subordinate ID
            subordinate_id = str(uuid.uuid4())

            # Create subordinate configuration
            subordinate_info = {
                "name": subordinate_config.get("name", f"Agent-{subordinate_id[:8]}"),
                "role": subordinate_config.get("role", "subordinate"),
                "capabilities": subordinate_config.get("capabilities", []),
                "superior_id": superior_id,
                "subordinate_ids": [],
                "created_at": datetime.now().isoformat(),
                "status": "active"
            }

            # Register subordinate
            await self.register_agent(subordinate_id, subordinate_info)

            # Update superior's subordinate list
            if superior_id in self.active_agents:
                self.active_agents[superior_id]["subordinate_ids"].append(subordinate_id)
                await self.save_to_storage()

            logger.info(f"Created subordinate agent {subordinate_id} for {superior_id}")
            return subordinate_id

        except Exception as e:
            logger.error(f"Error creating subordinate agent: {e}")
            raise

    def _calculate_level(self, agent_id: str) -> int:
        """Calculate agent level in hierarchy"""
        try:
            if agent_id not in self.active_agents:
                return 0

            agent_info = self.active_agents[agent_id]
            superior_id = agent_info.get("superior_id")

            if not superior_id:
                return 0  # Root agent

            return 1 + self._calculate_level(superior_id)

        except Exception as e:
            logger.error(f"Error calculating level for {agent_id}: {e}")
            return 0
