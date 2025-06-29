"""
Memory management system for Agent Zero Gemini
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import uuid

from config import config
from storage.json_storage import JSONStorage

logger = logging.getLogger(__name__)

@dataclass
class Memory:
    """Memory entry"""
    id: Optional[str] = None
    agent_id: str = ""
    type: str = "interaction"  # interaction, fact, skill, experience
    content: str = ""
    metadata: Dict[str, Any] = None
    importance: float = 0.5  # 0.0 to 1.0
    timestamp: datetime = None
    last_accessed: datetime = None
    access_count: int = 0
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.last_accessed is None:
            self.last_accessed = self.timestamp
        if self.metadata is None:
            self.metadata = {}

class MemoryManager:
    """Manages agent memory storage and retrieval using JSON storage"""

    def __init__(self, agent_id: str):
        """Initialize MemoryManager"""
        self.agent_id = agent_id
        self.storage = JSONStorage()

        # Memory limits
        self.max_memories = config.agent.memory_limit
        self.cleanup_threshold = int(self.max_memories * 1.2)

        logger.info(f"Initialized memory manager for agent {agent_id}")
    
    async def _ensure_memory_structure(self):
        """Ensure memory data structure exists"""
        try:
            memory_data = await self.storage.read("memory")

            # Ensure agent-specific sections exist
            if self.agent_id not in memory_data.get("interactions", {}):
                await self.storage.update("memory", {
                    "interactions": {
                        **memory_data.get("interactions", {}),
                        self.agent_id: []
                    }
                })

            if self.agent_id not in memory_data.get("facts", {}):
                await self.storage.update("memory", {
                    "facts": {
                        **memory_data.get("facts", {}),
                        self.agent_id: []
                    }
                })

        except Exception as e:
            logger.error(f"Error ensuring memory structure: {e}")
            raise
    
    async def store_memory(self, memory: Memory) -> str:
        """Store a memory"""
        try:
            await self._ensure_memory_structure()

            memory.agent_id = self.agent_id
            if not memory.id:
                memory.id = str(uuid.uuid4())

            # Convert to storage format
            memory_dict = {
                "id": memory.id,
                "agent_id": memory.agent_id,
                "type": memory.type,
                "content": memory.content,
                "metadata": memory.metadata,
                "importance": memory.importance,
                "timestamp": memory.timestamp.isoformat(),
                "last_accessed": memory.last_accessed.isoformat(),
                "access_count": memory.access_count
            }

            # Store based on memory type
            if memory.type == "interaction":
                await self.storage.append("memory", "interactions", memory_dict)
            elif memory.type == "fact":
                await self.storage.append("memory", "facts", memory_dict)
            elif memory.type == "skill":
                await self.storage.append("memory", "skills", memory_dict)
            elif memory.type == "experience":
                await self.storage.append("memory", "experiences", memory_dict)

            # Update metadata
            await self._update_memory_metadata()

            # Cleanup if needed
            await self._cleanup_old_memories()

            logger.debug(f"Stored memory: {memory.id}")
            return memory.id

        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            raise

    async def _update_memory_metadata(self):
        """Update memory metadata"""
        try:
            memory_data = await self.storage.read("memory")

            total_interactions = len(memory_data.get("interactions", []))
            total_facts = len(memory_data.get("facts", []))
            total_skills = len(memory_data.get("skills", []))
            total_experiences = len(memory_data.get("experiences", []))

            metadata_update = {
                "metadata": {
                    "total_interactions": total_interactions,
                    "total_facts": total_facts,
                    "total_skills": total_skills,
                    "total_experiences": total_experiences,
                    "last_updated": datetime.now().isoformat(),
                    "last_cleanup": memory_data.get("metadata", {}).get("last_cleanup", datetime.now().isoformat())
                }
            }

            await self.storage.update("memory", metadata_update)

        except Exception as e:
            logger.error(f"Error updating memory metadata: {e}")

    async def retrieve_memory(self, memory_id: str) -> Optional[Memory]:
        """Retrieve a specific memory by ID"""
        try:
            memory_data = await self.storage.read("memory")

            # Search through all memory types
            for memory_type in ["interactions", "facts", "skills", "experiences"]:
                memories = memory_data.get(memory_type, [])
                for mem_dict in memories:
                    if mem_dict.get("id") == memory_id:
                        return self._dict_to_memory(mem_dict)

            return None

        except Exception as e:
            logger.error(f"Error retrieving memory {memory_id}: {e}")
            return None

    async def search_memories(self, query: str, memory_type: Optional[str] = None, limit: int = 10) -> List[Memory]:
        """Search memories by content"""
        try:
            memory_data = await self.storage.read("memory")
            results = []

            # Determine which memory types to search
            types_to_search = [memory_type] if memory_type else ["interactions", "facts", "skills", "experiences"]

            for mem_type in types_to_search:
                memories = memory_data.get(mem_type, [])
                for mem_dict in memories:
                    # Simple text search in content
                    if query.lower() in mem_dict.get("content", "").lower():
                        memory = self._dict_to_memory(mem_dict)
                        if memory:
                            # Update access count
                            memory.access_count += 1
                            memory.last_accessed = datetime.now()
                            await self._update_memory_access(memory)
                            results.append(memory)

            # Sort by importance and recency
            results.sort(key=lambda m: (m.importance, m.timestamp), reverse=True)

            return results[:limit]

        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return []

    async def get_recent_interactions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent interactions for this agent"""
        try:
            memory_data = await self.storage.read("memory")
            interactions = memory_data.get("interactions", [])

            # Filter by agent_id and sort by timestamp
            agent_interactions = [
                interaction for interaction in interactions
                if interaction.get("agent_id") == self.agent_id
            ]

            # Sort by timestamp (most recent first)
            agent_interactions.sort(
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )

            return agent_interactions[:limit]

        except Exception as e:
            logger.error(f"Error getting recent interactions: {e}")
            return []

    async def store_interaction(self, role: str, content: str, metadata: Optional[Dict] = None) -> str:
        """Store an interaction (conversation turn)"""
        interaction = Memory(
            type="interaction",
            content=content,
            metadata={
                "role": role,
                **(metadata or {})
            },
            importance=0.5,  # Default importance for interactions
            agent_id=self.agent_id
        )

        return await self.store_memory(interaction)

    async def store_fact(self, fact: str, importance: float = 0.7, metadata: Optional[Dict] = None) -> str:
        """Store a learned fact"""
        fact_memory = Memory(
            type="fact",
            content=fact,
            metadata=metadata or {},
            importance=importance,
            agent_id=self.agent_id
        )

        return await self.store_memory(fact_memory)

    async def store_skill(self, skill_name: str, skill_description: str, importance: float = 0.8, metadata: Optional[Dict] = None) -> str:
        """Store a learned skill or procedure"""
        skill_memory = Memory(
            type="skill",
            content=f"{skill_name}: {skill_description}",
            metadata={
                "skill_name": skill_name,
                **(metadata or {})
            },
            importance=importance,
            agent_id=self.agent_id
        )

        return await self.store_memory(skill_memory)

    async def store_experience(self, experience: str, outcome: str, importance: float = 0.6, metadata: Optional[Dict] = None) -> str:
        """Store an experience with its outcome"""
        experience_memory = Memory(
            type="experience",
            content=f"Experience: {experience}\nOutcome: {outcome}",
            metadata={
                "outcome": outcome,
                **(metadata or {})
            },
            importance=importance,
            agent_id=self.agent_id
        )

        return await self.store_memory(experience_memory)

    def _dict_to_memory(self, mem_dict: Dict[str, Any]) -> Optional[Memory]:
        """Convert dictionary to Memory object"""
        try:
            return Memory(
                id=mem_dict.get("id"),
                type=mem_dict.get("type"),
                content=mem_dict.get("content"),
                metadata=mem_dict.get("metadata", {}),
                importance=mem_dict.get("importance", 0.5),
                timestamp=datetime.fromisoformat(mem_dict.get("timestamp")),
                last_accessed=datetime.fromisoformat(mem_dict.get("last_accessed")),
                access_count=mem_dict.get("access_count", 0),
                agent_id=mem_dict.get("agent_id")
            )
        except Exception as e:
            logger.error(f"Error converting dict to memory: {e}")
            return None

    async def _update_memory_access(self, memory: Memory):
        """Update memory access information"""
        try:
            memory_data = await self.storage.read("memory")

            # Find and update the memory
            for memory_type in ["interactions", "facts", "skills", "experiences"]:
                memories = memory_data.get(memory_type, [])
                for i, mem_dict in enumerate(memories):
                    if mem_dict.get("id") == memory.id:
                        memories[i]["access_count"] = memory.access_count
                        memories[i]["last_accessed"] = memory.last_accessed.isoformat()

                        # Update storage
                        await self.storage.update("memory", {memory_type: memories})
                        return

        except Exception as e:
            logger.error(f"Error updating memory access: {e}")

    async def _cleanup_old_memories(self):
        """Clean up old memories if limit exceeded"""
        try:
            memory_data = await self.storage.read("memory")

            # Count total memories for this agent
            total_memories = 0
            for memory_type in ["interactions", "facts", "skills", "experiences"]:
                memories = memory_data.get(memory_type, [])
                agent_memories = [m for m in memories if m.get("agent_id") == self.agent_id]
                total_memories += len(agent_memories)

            if total_memories > self.cleanup_threshold:
                logger.info(f"Cleaning up old memories for agent {self.agent_id}")

                # Remove oldest, least important interactions first
                interactions = memory_data.get("interactions", [])
                agent_interactions = [m for m in interactions if m.get("agent_id") == self.agent_id]

                if len(agent_interactions) > self.max_memories // 2:
                    # Sort by importance and age, remove least important old ones
                    agent_interactions.sort(key=lambda m: (
                        m.get("importance", 0),
                        m.get("timestamp", "")
                    ))

                    # Keep most recent and important ones
                    to_keep = agent_interactions[-(self.max_memories // 2):]
                    other_interactions = [m for m in interactions if m.get("agent_id") != self.agent_id]

                    memory_data["interactions"] = other_interactions + to_keep
                    await self.storage.update("memory", {"interactions": memory_data["interactions"]})

                await self._update_memory_metadata()

        except Exception as e:
            logger.error(f"Error cleaning up memories: {e}")

    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics for this agent"""
        try:
            memory_data = await self.storage.read("memory")

            stats = {
                "agent_id": self.agent_id,
                "interactions": 0,
                "facts": 0,
                "skills": 0,
                "experiences": 0,
                "total": 0
            }

            for memory_type in ["interactions", "facts", "skills", "experiences"]:
                memories = memory_data.get(memory_type, [])
                agent_memories = [m for m in memories if m.get("agent_id") == self.agent_id]
                stats[memory_type] = len(agent_memories)
                stats["total"] += len(agent_memories)

            return stats

        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {"error": str(e)}

    async def clear_memories(self, memory_type: Optional[str] = None):
        """Clear memories for this agent"""
        try:
            memory_data = await self.storage.read("memory")

            if memory_type:
                # Clear specific type
                memories = memory_data.get(memory_type, [])
                filtered_memories = [m for m in memories if m.get("agent_id") != self.agent_id]
                memory_data[memory_type] = filtered_memories
            else:
                # Clear all types
                for mem_type in ["interactions", "facts", "skills", "experiences"]:
                    memories = memory_data.get(mem_type, [])
                    filtered_memories = [m for m in memories if m.get("agent_id") != self.agent_id]
                    memory_data[mem_type] = filtered_memories

            await self.storage.write("memory", memory_data)
            await self._update_memory_metadata()

            logger.info(f"Cleared memories for agent {self.agent_id}")

        except Exception as e:
            logger.error(f"Error clearing memories: {e}")
            raise
    
    def _store_memory_sync(self, memory_data: Dict):
        """Store memory synchronously"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memories 
                (id, agent_id, type, content, metadata, importance, timestamp, last_accessed, access_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory_data["id"],
                memory_data["agent_id"],
                memory_data["type"],
                memory_data["content"],
                memory_data["metadata"],
                memory_data["importance"],
                memory_data["timestamp"],
                memory_data["last_accessed"],
                memory_data["access_count"]
            ))
            conn.commit()
    
    async def store_interaction(self, role: str, content: str, metadata: Optional[Dict] = None) -> str:
        """Store an interaction memory"""
        memory = Memory(
            type="interaction",
            content=f"{role}: {content}",
            metadata=metadata or {},
            importance=0.6 if role == "user" else 0.4
        )
        return await self.store_memory(memory)
    
    async def store_fact(self, fact: str, importance: float = 0.8, metadata: Optional[Dict] = None) -> str:
        """Store a fact memory"""
        memory = Memory(
            type="fact",
            content=fact,
            metadata=metadata or {},
            importance=importance
        )
        return await self.store_memory(memory)
    
    async def store_skill(self, skill: str, importance: float = 0.9, metadata: Optional[Dict] = None) -> str:
        """Store a skill memory"""
        memory = Memory(
            type="skill",
            content=skill,
            metadata=metadata or {},
            importance=importance
        )
        return await self.store_memory(memory)
    
    async def retrieve_memories(
        self, 
        query: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 10,
        min_importance: float = 0.0
    ) -> List[Memory]:
        """Retrieve memories based on criteria"""
        try:
            memories = await asyncio.to_thread(
                self._retrieve_memories_sync, 
                query, memory_type, limit, min_importance
            )
            
            # Update access information
            for memory in memories:
                await self._update_access_info(memory.id)
            
            return memories
            
        except Exception as e:
            logger.error(f"Error retrieving memories: {e}")
            return []
    
    def _retrieve_memories_sync(
        self, 
        query: Optional[str],
        memory_type: Optional[str],
        limit: int,
        min_importance: float
    ) -> List[Memory]:
        """Retrieve memories synchronously"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Build query
            sql = "SELECT * FROM memories WHERE agent_id = ? AND importance >= ?"
            params = [self.agent_id, min_importance]
            
            if memory_type:
                sql += " AND type = ?"
                params.append(memory_type)
            
            if query:
                sql += " AND content LIKE ?"
                params.append(f"%{query}%")
            
            sql += " ORDER BY importance DESC, timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            
            # Convert to Memory objects
            memories = []
            for row in rows:
                memory = Memory(
                    id=row["id"],
                    agent_id=row["agent_id"],
                    type=row["type"],
                    content=row["content"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    importance=row["importance"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    last_accessed=datetime.fromisoformat(row["last_accessed"]),
                    access_count=row["access_count"]
                )
                memories.append(memory)
            
            return memories
    
    async def get_recent_interactions(self, limit: int = 10) -> List[Dict]:
        """Get recent interactions"""
        memories = await self.retrieve_memories(
            memory_type="interaction",
            limit=limit
        )
        
        interactions = []
        for memory in memories:
            # Parse interaction content
            content = memory.content
            if ": " in content:
                role, message = content.split(": ", 1)
                interactions.append({
                    "role": role,
                    "content": message,
                    "timestamp": memory.timestamp.isoformat(),
                    "metadata": memory.metadata
                })
        
        return list(reversed(interactions))  # Return in chronological order
    
    async def search_memories(self, query: str, limit: int = 5) -> List[Memory]:
        """Search memories by content"""
        return await self.retrieve_memories(query=query, limit=limit)
    
    async def get_important_memories(self, limit: int = 20) -> List[Memory]:
        """Get most important memories"""
        return await self.retrieve_memories(min_importance=0.7, limit=limit)
    
    async def _update_access_info(self, memory_id: str):
        """Update memory access information"""
        try:
            await asyncio.to_thread(self._update_access_info_sync, memory_id)
        except Exception as e:
            logger.error(f"Error updating access info: {e}")
    
    def _update_access_info_sync(self, memory_id: str):
        """Update access info synchronously"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE memories 
                SET last_accessed = ?, access_count = access_count + 1
                WHERE id = ?
            """, (datetime.now().isoformat(), memory_id))
            conn.commit()
    
    async def _cleanup_old_memories(self):
        """Cleanup old memories when limit is exceeded"""
        try:
            memory_count = await asyncio.to_thread(self._get_memory_count)
            
            if memory_count > self.cleanup_threshold:
                # Remove least important and oldest memories
                await asyncio.to_thread(self._cleanup_memories_sync)
                logger.info(f"Cleaned up old memories, count was {memory_count}")
                
        except Exception as e:
            logger.error(f"Error during memory cleanup: {e}")
    
    def _get_memory_count(self) -> int:
        """Get total memory count"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM memories WHERE agent_id = ?", (self.agent_id,))
            return cursor.fetchone()[0]
    
    def _cleanup_memories_sync(self):
        """Cleanup memories synchronously"""
        with sqlite3.connect(self.db_path) as conn:
            # Keep the most important memories and recent interactions
            conn.execute("""
                DELETE FROM memories 
                WHERE agent_id = ? AND id NOT IN (
                    SELECT id FROM memories 
                    WHERE agent_id = ? 
                    ORDER BY 
                        CASE WHEN type = 'interaction' THEN timestamp ELSE importance END DESC,
                        importance DESC
                    LIMIT ?
                )
            """, (self.agent_id, self.agent_id, self.max_memories))
            conn.commit()
    
    def get_memory_size(self) -> int:
        """Get current memory size"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM memories WHERE agent_id = ?", (self.agent_id,))
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting memory size: {e}")
            return 0
    
    async def close(self):
        """Close memory manager"""
        # Perform final cleanup if needed
        await self._cleanup_old_memories()
        logger.info(f"Memory manager closed for agent {self.agent_id}")
