"""
JSON-based storage system for Agent Zero Gemini
"""
import json
import asyncio
import logging
import fcntl
import os
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager
import aiofiles
import aiofiles.os

from config import config

logger = logging.getLogger(__name__)

class JSONStorage:
    """JSON-based storage system with file locking and atomic operations"""
    
    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize JSON storage"""
        self.storage_path = storage_path or Path(config.storage.path if hasattr(config, 'storage') else "./data")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Storage files
        self.files = {
            "agents": self.storage_path / "agents.json",
            "memory": self.storage_path / "memory.json", 
            "tools": self.storage_path / "tools.json",
            "sessions": self.storage_path / "sessions.json",
            "knowledge": self.storage_path / "knowledge.json",
            "instruments": self.storage_path / "instruments.json"
        }
        
        # File locks
        self._locks = {name: asyncio.Lock() for name in self.files.keys()}
        
        # Initialize files
        asyncio.create_task(self._initialize_files())
        
        logger.info(f"Initialized JSON storage at {self.storage_path}")
    
    async def _initialize_files(self):
        """Initialize storage files with default structure"""
        default_structures = {
            "agents": {
                "agents": {},
                "hierarchy": {},
                "metadata": {
                    "created": datetime.now().isoformat(),
                    "version": "1.0.0"
                }
            },
            "memory": {
                "interactions": [],
                "facts": [],
                "skills": [],
                "experiences": [],
                "metadata": {
                    "total_interactions": 0,
                    "last_cleanup": datetime.now().isoformat()
                }
            },
            "tools": {
                "tool_configs": {},
                "usage_logs": [],
                "custom_tools": {},
                "metadata": {
                    "total_executions": 0,
                    "last_updated": datetime.now().isoformat()
                }
            },
            "sessions": {
                "active_sessions": {},
                "session_history": [],
                "metadata": {
                    "total_sessions": 0,
                    "current_session": None
                }
            },
            "knowledge": {
                "facts": {},
                "procedures": {},
                "concepts": {},
                "relationships": {},
                "metadata": {
                    "knowledge_count": 0,
                    "last_updated": datetime.now().isoformat()
                }
            },
            "instruments": {
                "custom_instruments": {},
                "procedures": {},
                "workflows": {},
                "metadata": {
                    "instrument_count": 0,
                    "last_updated": datetime.now().isoformat()
                }
            }
        }
        
        for name, structure in default_structures.items():
            file_path = self.files[name]
            if not file_path.exists():
                await self._write_file(file_path, structure)
                logger.debug(f"Initialized {name}.json with default structure")
    
    @asynccontextmanager
    async def _file_lock(self, file_path: Path):
        """Async context manager for file locking"""
        lock_file = file_path.with_suffix('.lock')
        
        # Wait for lock to be available
        while lock_file.exists():
            await asyncio.sleep(0.01)
        
        try:
            # Create lock file
            lock_file.touch()
            yield
        finally:
            # Remove lock file
            if lock_file.exists():
                lock_file.unlink()
    
    async def _read_file(self, file_path: Path) -> Dict[str, Any]:
        """Read JSON file with error handling"""
        try:
            if not file_path.exists():
                return {}
            
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content) if content.strip() else {}
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {file_path}: {e}")
            # Try to recover from backup
            backup_path = file_path.with_suffix('.backup')
            if backup_path.exists():
                logger.info(f"Attempting to recover from backup: {backup_path}")
                try:
                    async with aiofiles.open(backup_path, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        return json.loads(content)
                except Exception as backup_error:
                    logger.error(f"Backup recovery failed: {backup_error}")
            return {}
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return {}
    
    async def _write_file(self, file_path: Path, data: Dict[str, Any]):
        """Write JSON file atomically"""
        try:
            # Create backup first
            if file_path.exists():
                backup_path = file_path.with_suffix('.backup')
                await aiofiles.os.rename(str(file_path), str(backup_path))
            
            # Write to temporary file first
            temp_path = file_path.with_suffix('.tmp')
            async with aiofiles.open(temp_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2, ensure_ascii=False, default=str))
                await f.flush()
                await aiofiles.os.fsync(f.fileno())
            
            # Atomic rename
            await aiofiles.os.rename(str(temp_path), str(file_path))
            
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            # Clean up temp file if it exists
            temp_path = file_path.with_suffix('.tmp')
            if temp_path.exists():
                temp_path.unlink()
            raise
    
    async def read(self, storage_type: str) -> Dict[str, Any]:
        """Read data from storage"""
        if storage_type not in self.files:
            raise ValueError(f"Unknown storage type: {storage_type}")
        
        async with self._locks[storage_type]:
            async with self._file_lock(self.files[storage_type]):
                return await self._read_file(self.files[storage_type])
    
    async def write(self, storage_type: str, data: Dict[str, Any]):
        """Write data to storage"""
        if storage_type not in self.files:
            raise ValueError(f"Unknown storage type: {storage_type}")
        
        async with self._locks[storage_type]:
            async with self._file_lock(self.files[storage_type]):
                await self._write_file(self.files[storage_type], data)
    
    async def update(self, storage_type: str, updates: Dict[str, Any]):
        """Update specific fields in storage"""
        async with self._locks[storage_type]:
            async with self._file_lock(self.files[storage_type]):
                current_data = await self._read_file(self.files[storage_type])
                
                # Deep merge updates
                def deep_merge(base: Dict, updates: Dict) -> Dict:
                    result = base.copy()
                    for key, value in updates.items():
                        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                            result[key] = deep_merge(result[key], value)
                        else:
                            result[key] = value
                    return result
                
                updated_data = deep_merge(current_data, updates)
                await self._write_file(self.files[storage_type], updated_data)
    
    async def append(self, storage_type: str, key: str, item: Any):
        """Append item to a list in storage"""
        async with self._locks[storage_type]:
            async with self._file_lock(self.files[storage_type]):
                current_data = await self._read_file(self.files[storage_type])
                
                if key not in current_data:
                    current_data[key] = []
                
                if not isinstance(current_data[key], list):
                    raise ValueError(f"Key '{key}' is not a list")
                
                current_data[key].append(item)
                await self._write_file(self.files[storage_type], current_data)
    
    async def remove(self, storage_type: str, key: str, condition: Optional[callable] = None):
        """Remove items from storage"""
        async with self._locks[storage_type]:
            async with self._file_lock(self.files[storage_type]):
                current_data = await self._read_file(self.files[storage_type])
                
                if condition is None:
                    # Remove key entirely
                    if key in current_data:
                        del current_data[key]
                else:
                    # Remove items matching condition
                    if key in current_data and isinstance(current_data[key], list):
                        current_data[key] = [item for item in current_data[key] if not condition(item)]
                
                await self._write_file(self.files[storage_type], current_data)
    
    async def search(self, storage_type: str, query: Dict[str, Any]) -> List[Any]:
        """Search for items in storage"""
        data = await self.read(storage_type)
        results = []
        
        def matches_query(item: Any, query: Dict[str, Any]) -> bool:
            if not isinstance(item, dict):
                return False
            
            for key, value in query.items():
                if key not in item:
                    return False
                
                if isinstance(value, str) and isinstance(item[key], str):
                    if value.lower() not in item[key].lower():
                        return False
                elif item[key] != value:
                    return False
            
            return True
        
        # Search through all lists in the data
        for key, value in data.items():
            if isinstance(value, list):
                for item in value:
                    if matches_query(item, query):
                        results.append(item)
        
        return results
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        stats = {
            "storage_path": str(self.storage_path),
            "files": {},
            "total_size": 0
        }
        
        for name, file_path in self.files.items():
            if file_path.exists():
                file_size = file_path.stat().st_size
                stats["files"][name] = {
                    "size": file_size,
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                }
                stats["total_size"] += file_size
            else:
                stats["files"][name] = {"size": 0, "modified": None}
        
        return stats
    
    async def backup_all(self, backup_dir: Optional[Path] = None) -> Path:
        """Create backup of all storage files"""
        if backup_dir is None:
            backup_dir = self.storage_path / "backups"
        
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"backup_{timestamp}"
        backup_path.mkdir(exist_ok=True)
        
        for name, file_path in self.files.items():
            if file_path.exists():
                backup_file = backup_path / f"{name}.json"
                data = await self.read(name)
                async with aiofiles.open(backup_file, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(data, indent=2, ensure_ascii=False, default=str))
        
        logger.info(f"Created backup at {backup_path}")
        return backup_path
    
    async def restore_from_backup(self, backup_path: Path):
        """Restore from backup"""
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup path does not exist: {backup_path}")
        
        for name in self.files.keys():
            backup_file = backup_path / f"{name}.json"
            if backup_file.exists():
                async with aiofiles.open(backup_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    data = json.loads(content)
                    await self.write(name, data)
        
        logger.info(f"Restored from backup: {backup_path}")
    
    async def cleanup_old_backups(self, keep_count: int = 10):
        """Clean up old backup files"""
        backup_dir = self.storage_path / "backups"
        if not backup_dir.exists():
            return
        
        # Get all backup directories
        backup_dirs = [d for d in backup_dir.iterdir() if d.is_dir() and d.name.startswith("backup_")]
        backup_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Remove old backups
        for old_backup in backup_dirs[keep_count:]:
            import shutil
            shutil.rmtree(old_backup)
            logger.debug(f"Removed old backup: {old_backup}")
    
    async def close(self):
        """Close storage and cleanup"""
        # Create final backup
        await self.backup_all()
        
        # Cleanup old backups
        await self.cleanup_old_backups()
        
        logger.info("JSON storage closed")
