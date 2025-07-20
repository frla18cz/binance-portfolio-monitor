"""
Process lock utility to prevent duplicate runs.
Uses file-based locking for simplicity and portability.
"""

import os
import time
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any


class ProcessLock:
    """Simple file-based process lock to prevent duplicate runs."""
    
    def __init__(self, lock_name: str = "binance_monitor", lock_dir: str = "/tmp"):
        self.lock_name = lock_name
        self.lock_file = Path(lock_dir) / f".{lock_name}.lock"
        self.pid = os.getpid()
        
    def acquire(self, max_age_seconds: int = 3600) -> bool:
        """
        Try to acquire lock. Returns True if successful, False if another process holds it.
        
        Args:
            max_age_seconds: Maximum age of lock file before considering it stale (default 1 hour)
        """
        # Check if lock file exists
        if self.lock_file.exists():
            try:
                # Read lock info
                with open(self.lock_file, 'r') as f:
                    lock_info = json.load(f)
                
                # Check if process is still running
                old_pid = lock_info.get('pid')
                if old_pid and self._is_process_running(old_pid):
                    # Check if lock is stale
                    lock_time = datetime.fromisoformat(lock_info.get('timestamp', ''))
                    age = (datetime.now(timezone.utc) - lock_time).total_seconds()
                    
                    if age < max_age_seconds:
                        return False  # Lock is held by another running process
                    
                # Lock is stale or process is dead, we can take it
            except Exception:
                # Lock file is corrupted, we can take it
                pass
        
        # Write our lock
        lock_info = {
            'pid': self.pid,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'hostname': os.uname().nodename
        }
        
        try:
            with open(self.lock_file, 'w') as f:
                json.dump(lock_info, f)
            return True
        except Exception:
            return False
    
    def release(self):
        """Release the lock."""
        try:
            if self.lock_file.exists():
                # Only remove if it's our lock
                with open(self.lock_file, 'r') as f:
                    lock_info = json.load(f)
                
                if lock_info.get('pid') == self.pid:
                    self.lock_file.unlink()
        except Exception:
            pass
    
    def _is_process_running(self, pid: int) -> bool:
        """Check if a process with given PID is running."""
        try:
            os.kill(pid, 0)  # Signal 0 doesn't kill, just checks
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            # Process exists but we don't have permission
            return True
    
    def __enter__(self):
        """Context manager support."""
        if not self.acquire():
            raise RuntimeError(f"Could not acquire lock for {self.lock_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self.release()