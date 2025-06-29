"""
File utilities for Agent Zero Gemini
"""
import os
import shutil
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any
import mimetypes

class FileUtils:
    """Utility functions for file operations"""
    
    @staticmethod
    def ensure_directory(path: Path) -> Path:
        """Ensure directory exists"""
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @staticmethod
    def get_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
        """Get file hash"""
        hash_func = hashlib.new(algorithm)
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
    
    @staticmethod
    def get_file_info(file_path: Path) -> Dict[str, Any]:
        """Get comprehensive file information"""
        if not file_path.exists():
            return {"exists": False}
        
        stat = file_path.stat()
        mime_type, encoding = mimetypes.guess_type(str(file_path))
        
        return {
            "exists": True,
            "name": file_path.name,
            "path": str(file_path.absolute()),
            "size": stat.st_size,
            "is_file": file_path.is_file(),
            "is_directory": file_path.is_dir(),
            "mime_type": mime_type,
            "encoding": encoding,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "accessed": stat.st_atime,
            "permissions": oct(stat.st_mode)[-3:],
            "hash": FileUtils.get_file_hash(file_path) if file_path.is_file() else None
        }
    
    @staticmethod
    def safe_filename(filename: str) -> str:
        """Create safe filename by removing/replacing invalid characters"""
        # Characters not allowed in filenames
        invalid_chars = '<>:"/\\|?*'
        
        # Replace invalid characters with underscore
        safe_name = filename
        for char in invalid_chars:
            safe_name = safe_name.replace(char, '_')
        
        # Remove leading/trailing spaces and dots
        safe_name = safe_name.strip(' .')
        
        # Ensure not empty
        if not safe_name:
            safe_name = "unnamed_file"
        
        return safe_name
    
    @staticmethod
    def copy_file(source: Path, destination: Path, overwrite: bool = False) -> bool:
        """Copy file with safety checks"""
        try:
            if not source.exists():
                return False
            
            if destination.exists() and not overwrite:
                return False
            
            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(source, destination)
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def move_file(source: Path, destination: Path, overwrite: bool = False) -> bool:
        """Move file with safety checks"""
        try:
            if not source.exists():
                return False
            
            if destination.exists() and not overwrite:
                return False
            
            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(source), str(destination))
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def delete_file(file_path: Path, force: bool = False) -> bool:
        """Delete file or directory"""
        try:
            if not file_path.exists():
                return True
            
            if file_path.is_file():
                file_path.unlink()
            elif file_path.is_dir():
                if force:
                    shutil.rmtree(file_path)
                else:
                    file_path.rmdir()  # Only works if empty
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def list_files(
        directory: Path, 
        pattern: str = "*",
        recursive: bool = False,
        include_dirs: bool = True
    ) -> List[Dict[str, Any]]:
        """List files in directory with information"""
        if not directory.exists() or not directory.is_dir():
            return []
        
        files = []
        
        if recursive:
            paths = directory.rglob(pattern)
        else:
            paths = directory.glob(pattern)
        
        for path in paths:
            if path.is_file() or (path.is_dir() and include_dirs):
                files.append(FileUtils.get_file_info(path))
        
        return files
    
    @staticmethod
    def read_text_file(file_path: Path, encoding: str = "utf-8") -> Optional[str]:
        """Read text file safely"""
        try:
            return file_path.read_text(encoding=encoding)
        except Exception:
            return None
    
    @staticmethod
    def write_text_file(
        file_path: Path, 
        content: str, 
        encoding: str = "utf-8",
        create_dirs: bool = True
    ) -> bool:
        """Write text file safely"""
        try:
            if create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_path.write_text(content, encoding=encoding)
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def append_to_file(
        file_path: Path, 
        content: str, 
        encoding: str = "utf-8",
        create_dirs: bool = True
    ) -> bool:
        """Append content to file"""
        try:
            if create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, "a", encoding=encoding) as f:
                f.write(content)
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def get_directory_size(directory: Path) -> int:
        """Get total size of directory"""
        if not directory.exists() or not directory.is_dir():
            return 0
        
        total_size = 0
        for path in directory.rglob("*"):
            if path.is_file():
                total_size += path.stat().st_size
        
        return total_size
    
    @staticmethod
    def cleanup_directory(
        directory: Path, 
        max_age_days: int = 30,
        max_size_mb: int = 100
    ) -> Dict[str, Any]:
        """Cleanup directory based on age and size"""
        if not directory.exists():
            return {"cleaned": False, "reason": "Directory does not exist"}
        
        import time
        from datetime import datetime, timedelta
        
        current_time = time.time()
        cutoff_time = current_time - (max_age_days * 24 * 60 * 60)
        max_size_bytes = max_size_mb * 1024 * 1024
        
        files_removed = 0
        bytes_freed = 0
        
        # Remove old files
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                file_stat = file_path.stat()
                
                # Check age
                if file_stat.st_mtime < cutoff_time:
                    file_size = file_stat.st_size
                    if FileUtils.delete_file(file_path):
                        files_removed += 1
                        bytes_freed += file_size
        
        # Check if directory is still too large
        current_size = FileUtils.get_directory_size(directory)
        
        if current_size > max_size_bytes:
            # Remove largest files first until under limit
            files_by_size = []
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    files_by_size.append((file_path.stat().st_size, file_path))
            
            files_by_size.sort(reverse=True)  # Largest first
            
            for file_size, file_path in files_by_size:
                if current_size <= max_size_bytes:
                    break
                
                if FileUtils.delete_file(file_path):
                    files_removed += 1
                    bytes_freed += file_size
                    current_size -= file_size
        
        return {
            "cleaned": True,
            "files_removed": files_removed,
            "bytes_freed": bytes_freed,
            "final_size": FileUtils.get_directory_size(directory)
        }
