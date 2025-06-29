"""
Backup management for JSON storage system
"""
import asyncio
import logging
import shutil
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

class BackupManager:
    """Manages automated backups and recovery for JSON storage"""
    
    def __init__(self, storage_path: Path, backup_interval: int = 3600):
        """Initialize backup manager"""
        self.storage_path = storage_path
        self.backup_dir = storage_path / "backups"
        self.backup_interval = backup_interval  # seconds
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self._backup_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(f"Initialized backup manager with {backup_interval}s interval")
    
    async def start_automatic_backup(self):
        """Start automatic backup task"""
        if self._backup_task and not self._backup_task.done():
            return
        
        self._running = True
        self._backup_task = asyncio.create_task(self._backup_loop())
        logger.info("Started automatic backup task")
    
    async def stop_automatic_backup(self):
        """Stop automatic backup task"""
        self._running = False
        if self._backup_task:
            self._backup_task.cancel()
            try:
                await self._backup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped automatic backup task")
    
    async def _backup_loop(self):
        """Main backup loop"""
        while self._running:
            try:
                await asyncio.sleep(self.backup_interval)
                if self._running:
                    await self.create_backup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in backup loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def create_backup(self, backup_name: Optional[str] = None) -> Path:
        """Create a backup of all storage files"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = backup_name or f"auto_backup_{timestamp}"
            backup_path = self.backup_dir / backup_name
            backup_path.mkdir(exist_ok=True)
            
            # Copy all JSON files
            storage_files = list(self.storage_path.glob("*.json"))
            for file_path in storage_files:
                if file_path.name not in ["backup_index.json"]:  # Skip backup metadata
                    backup_file = backup_path / file_path.name
                    shutil.copy2(file_path, backup_file)
            
            # Create backup metadata
            metadata = {
                "created": datetime.now().isoformat(),
                "type": "automatic" if backup_name.startswith("auto_") else "manual",
                "files": [f.name for f in storage_files],
                "size": sum(f.stat().st_size for f in storage_files)
            }
            
            metadata_file = backup_path / "backup_metadata.json"
            with open(metadata_file, 'w') as f:
                import json
                json.dump(metadata, f, indent=2)
            
            # Update backup index
            await self._update_backup_index(backup_name, metadata)
            
            logger.info(f"Created backup: {backup_name}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            raise
    
    async def _update_backup_index(self, backup_name: str, metadata: Dict):
        """Update backup index file"""
        index_file = self.backup_dir / "backup_index.json"
        
        try:
            if index_file.exists():
                with open(index_file, 'r') as f:
                    import json
                    index = json.load(f)
            else:
                index = {"backups": {}, "last_updated": None}
            
            index["backups"][backup_name] = metadata
            index["last_updated"] = datetime.now().isoformat()
            
            with open(index_file, 'w') as f:
                import json
                json.dump(index, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error updating backup index: {e}")
    
    async def list_backups(self) -> List[Dict]:
        """List all available backups"""
        index_file = self.backup_dir / "backup_index.json"
        
        if not index_file.exists():
            return []
        
        try:
            with open(index_file, 'r') as f:
                import json
                index = json.load(f)
            
            backups = []
            for name, metadata in index.get("backups", {}).items():
                backup_path = self.backup_dir / name
                if backup_path.exists():
                    backups.append({
                        "name": name,
                        "path": str(backup_path),
                        "created": metadata.get("created"),
                        "type": metadata.get("type"),
                        "size": metadata.get("size", 0),
                        "files": metadata.get("files", [])
                    })
            
            # Sort by creation date (newest first)
            backups.sort(key=lambda x: x["created"], reverse=True)
            return backups
            
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            return []
    
    async def restore_backup(self, backup_name: str) -> bool:
        """Restore from a specific backup"""
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            logger.error(f"Backup not found: {backup_name}")
            return False
        
        try:
            # Create a safety backup first
            safety_backup = await self.create_backup(f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            logger.info(f"Created safety backup: {safety_backup}")
            
            # Restore files
            backup_files = list(backup_path.glob("*.json"))
            for backup_file in backup_files:
                if backup_file.name != "backup_metadata.json":
                    target_file = self.storage_path / backup_file.name
                    shutil.copy2(backup_file, target_file)
            
            logger.info(f"Restored from backup: {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring backup {backup_name}: {e}")
            return False
    
    async def delete_backup(self, backup_name: str) -> bool:
        """Delete a specific backup"""
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            logger.error(f"Backup not found: {backup_name}")
            return False
        
        try:
            shutil.rmtree(backup_path)
            
            # Update backup index
            index_file = self.backup_dir / "backup_index.json"
            if index_file.exists():
                with open(index_file, 'r') as f:
                    import json
                    index = json.load(f)
                
                if backup_name in index.get("backups", {}):
                    del index["backups"][backup_name]
                    index["last_updated"] = datetime.now().isoformat()
                    
                    with open(index_file, 'w') as f:
                        json.dump(index, f, indent=2)
            
            logger.info(f"Deleted backup: {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting backup {backup_name}: {e}")
            return False
    
    async def cleanup_old_backups(self, keep_count: int = 10, max_age_days: int = 30):
        """Clean up old backups based on count and age"""
        backups = await self.list_backups()
        
        if not backups:
            return
        
        # Sort by creation date (oldest first for deletion)
        backups.sort(key=lambda x: x["created"])
        
        deleted_count = 0
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        # Delete old backups (keep manual backups longer)
        for backup in backups:
            should_delete = False
            
            # Check age
            backup_date = datetime.fromisoformat(backup["created"])
            if backup_date < cutoff_date and backup["type"] == "automatic":
                should_delete = True
            
            # Check count (keep most recent)
            if len(backups) - deleted_count > keep_count and backup["type"] == "automatic":
                should_delete = True
            
            if should_delete:
                if await self.delete_backup(backup["name"]):
                    deleted_count += 1
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old backups")
    
    async def verify_backup(self, backup_name: str) -> Dict[str, bool]:
        """Verify backup integrity"""
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            return {"exists": False}
        
        verification_results = {"exists": True}
        
        try:
            # Check metadata file
            metadata_file = backup_path / "backup_metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    import json
                    metadata = json.load(f)
                    verification_results["metadata_valid"] = True
                    verification_results["expected_files"] = metadata.get("files", [])
            else:
                verification_results["metadata_valid"] = False
                verification_results["expected_files"] = []
            
            # Check JSON files
            json_files = list(backup_path.glob("*.json"))
            verification_results["files_found"] = [f.name for f in json_files]
            verification_results["json_valid"] = {}
            
            for json_file in json_files:
                if json_file.name != "backup_metadata.json":
                    try:
                        with open(json_file, 'r') as f:
                            import json
                            json.load(f)
                        verification_results["json_valid"][json_file.name] = True
                    except json.JSONDecodeError:
                        verification_results["json_valid"][json_file.name] = False
            
            # Overall validity
            verification_results["valid"] = (
                verification_results["metadata_valid"] and
                all(verification_results["json_valid"].values())
            )
            
        except Exception as e:
            logger.error(f"Error verifying backup {backup_name}: {e}")
            verification_results["error"] = str(e)
            verification_results["valid"] = False
        
        return verification_results
    
    async def get_backup_stats(self) -> Dict:
        """Get backup statistics"""
        backups = await self.list_backups()
        
        if not backups:
            return {
                "total_backups": 0,
                "total_size": 0,
                "automatic_backups": 0,
                "manual_backups": 0,
                "oldest_backup": None,
                "newest_backup": None
            }
        
        automatic_count = sum(1 for b in backups if b["type"] == "automatic")
        manual_count = len(backups) - automatic_count
        total_size = sum(b["size"] for b in backups)
        
        # Sort by date for oldest/newest
        sorted_backups = sorted(backups, key=lambda x: x["created"])
        
        return {
            "total_backups": len(backups),
            "total_size": total_size,
            "automatic_backups": automatic_count,
            "manual_backups": manual_count,
            "oldest_backup": sorted_backups[0]["created"] if sorted_backups else None,
            "newest_backup": sorted_backups[-1]["created"] if sorted_backups else None,
            "backup_directory": str(self.backup_dir)
        }
