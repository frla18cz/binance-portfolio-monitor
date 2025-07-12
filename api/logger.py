"""
Advanced logging system for Binance Portfolio Monitor.
Provides structured logging, real-time monitoring, and audit trails.
Supports both file-based (local) and database-based (Vercel) logging.
"""

import json
import os
import sys
import logging
import time
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path

# Add project root to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from config import settings
    CONFIG_LOADED = True
except ImportError:
    CONFIG_LOADED = False


class LogLevel(Enum):
    """Log levels for different types of events."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """Categories for different types of operations."""
    ACCOUNT_PROCESSING = "account_processing"
    API_CALL = "api_call"
    DATABASE = "database"
    BENCHMARK = "benchmark"
    TRANSACTION = "transaction"
    PRICE_UPDATE = "price_update"
    REBALANCING = "rebalancing"
    SYSTEM = "system"
    DEMO_MODE = "demo_mode"


@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: str
    level: str
    category: str
    account_id: Optional[int]
    account_name: Optional[str]
    operation: str
    message: str
    data: Optional[Dict] = None
    duration_ms: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class MonitorLogger:
    """Advanced logger for portfolio monitoring system."""
    
    def __init__(self, log_file: str = "monitor_logs.jsonl", max_entries: int = 10000):
        self.log_file = log_file
        self.max_entries = max_entries
        self.session_id = self._generate_session_id()
        self.logs: List[LogEntry] = []
        
        # Setup file logging
        self._setup_file_logging()
        
        # Load existing logs
        self._load_existing_logs()
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        return f"session_{int(time.time())}"
    
    def _setup_file_logging(self):
        """Setup file logging with rotation."""
        # Check if we can write to filesystem (not Vercel)
        try:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            # Setup standard Python logging
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_dir / "monitor.log"),
                    logging.StreamHandler()
                ]
            )
            
            self.file_path = log_dir / self.log_file
        except (OSError, PermissionError):
            # Vercel read-only filesystem - use only console logging
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[logging.StreamHandler()]
            )
            self.file_path = None
    
    def _load_existing_logs(self):
        """Load existing logs from file."""
        if self.file_path and self.file_path.exists():
            try:
                with open(self.file_path, 'r') as f:
                    lines = f.readlines()
                    # Load last N entries
                    for line in lines[-self.max_entries:]:
                        try:
                            log_data = json.loads(line.strip())
                            entry = LogEntry(**log_data)
                            self.logs.append(entry)
                        except Exception:
                            continue
            except Exception as e:
                logging.error(f"Failed to load existing logs: {e}")
    
    def _save_log_entry(self, entry: LogEntry):
        """Save log entry to file and/or database."""
        # Save to file (local development)
        self._save_to_file(entry)
        
        # Save to database (Vercel/production) if configured
        if self._should_use_database_logging():
            self._save_to_database(entry)
    
    def _save_to_file(self, entry: LogEntry):
        """Save log entry to file."""
        if not self.file_path:
            return  # Skip file logging in read-only environments like Vercel
            
        try:
            with open(self.file_path, 'a') as f:
                f.write(json.dumps(entry.to_dict()) + '\n')
        except Exception as e:
            logging.error(f"Failed to save log entry: {e}")
    
    def _should_use_database_logging(self) -> bool:
        """Determine if database logging should be used."""
        if not CONFIG_LOADED:
            return False
        
        # Use database logging if:
        # 1. Explicitly configured in settings
        # 2. Running in serverless environment (Vercel)
        # 3. No persistent file system available
        
        database_enabled = False
        try:
            database_enabled = settings.logging.database_logging.get('enabled', False)
        except (AttributeError, KeyError):
            pass
        
        # Detect Vercel environment
        is_vercel = os.environ.get('VERCEL') == '1' or os.environ.get('NOW_REGION') is not None
        
        # Detect if file system is read-only (serverless indicator)
        try:
            test_file = Path("logs") / ".write_test"
            test_file.parent.mkdir(exist_ok=True)
            test_file.touch()
            test_file.unlink()
            has_writable_fs = True
        except (OSError, PermissionError):
            has_writable_fs = False
        
        return database_enabled or is_vercel or not has_writable_fs
    
    def _save_to_database(self, entry: LogEntry):
        """Save log entry to database."""
        try:
            # Import here to avoid circular imports
            from utils.database_manager import get_supabase_client
            
            if not CONFIG_LOADED:
                return
            
            # Get database client
            supabase = get_supabase_client()
            
            # Check if log level should be saved
            log_levels = settings.logging.database_logging.get('log_levels', ['INFO', 'WARNING', 'ERROR', 'CRITICAL'])
            if entry.level not in log_levels:
                return
            
            # Prepare data for database
            log_data = {
                'timestamp': entry.timestamp,
                'level': entry.level,
                'category': entry.category,
                'account_id': entry.account_id,
                'account_name': entry.account_name,
                'operation': entry.operation,
                'message': entry.message,
                'data': entry.data,
                'duration_ms': entry.duration_ms,
                'session_id': self.session_id
            }
            
            # Save to database
            table_name = settings.logging.database_logging.get('table_name', 'system_logs')
            supabase.table(table_name).insert(log_data).execute()
            
        except Exception as e:
            # Fallback to standard logging if database fails
            logging.error(f"Failed to save log to database: {e}")
    
    def log(self, 
            level: LogLevel, 
            category: LogCategory, 
            operation: str, 
            message: str,
            account_id: Optional[int] = None,
            account_name: Optional[str] = None,
            data: Optional[Dict] = None,
            duration_ms: Optional[float] = None,
            success: bool = True,
            error: Optional[str] = None):
        """Log an event with structured data."""
        
        entry = LogEntry(
            timestamp=datetime.now(UTC).isoformat(),
            level=level.value,
            category=category.value,
            account_id=account_id,
            account_name=account_name,
            operation=operation,
            message=message,
            data=data,
            duration_ms=duration_ms,
            success=success,
            error=error
        )
        
        # Add to memory
        self.logs.append(entry)
        
        # Trim old entries
        if len(self.logs) > self.max_entries:
            self.logs = self.logs[-self.max_entries:]
        
        # Save to file
        self._save_log_entry(entry)
        
        # Standard logging
        log_level = getattr(logging, level.value)
        log_msg = f"[{category.value}] {operation}: {message}"
        if error:
            log_msg += f" | Error: {error}"
        
        logging.log(log_level, log_msg)
    
    def info(self, category: LogCategory, operation: str, message: str, **kwargs):
        """Log info message."""
        self.log(LogLevel.INFO, category, operation, message, **kwargs)
    
    def warning(self, category: LogCategory, operation: str, message: str, **kwargs):
        """Log warning message."""
        self.log(LogLevel.WARNING, category, operation, message, **kwargs)
    
    def error(self, category: LogCategory, operation: str, message: str, **kwargs):
        """Log error message."""
        self.log(LogLevel.ERROR, category, operation, message, success=False, **kwargs)
    
    def debug(self, category: LogCategory, operation: str, message: str, **kwargs):
        """Log debug message."""
        self.log(LogLevel.DEBUG, category, operation, message, **kwargs)
    
    def get_recent_logs(self, limit: int = 100, category: Optional[str] = None, 
                       account_id: Optional[int] = None) -> List[Dict]:
        """Get recent log entries with optional filtering."""
        filtered_logs = self.logs
        
        if category:
            filtered_logs = [log for log in filtered_logs if log.category == category]
        
        if account_id:
            filtered_logs = [log for log in filtered_logs if log.account_id == account_id]
        
        # Return most recent first
        recent_logs = filtered_logs[-limit:]
        return [log.to_dict() for log in reversed(recent_logs)]
    
    def get_error_logs(self, hours: int = 24) -> List[Dict]:
        """Get error logs from the last N hours."""
        cutoff_time = datetime.now(UTC).timestamp() - (hours * 3600)
        
        error_logs = []
        for log in self.logs:
            try:
                log_time = datetime.fromisoformat(log.timestamp.replace('Z', '+00:00')).timestamp()
                if log_time >= cutoff_time and not log.success:
                    error_logs.append(log.to_dict())
            except Exception:
                continue
        
        return list(reversed(error_logs))
    
    def get_performance_metrics(self) -> Dict:
        """Get performance metrics from logs."""
        if not self.logs:
            return {}
        
        # Calculate metrics
        total_operations = len(self.logs)
        successful_operations = len([log for log in self.logs if log.success])
        failed_operations = total_operations - successful_operations
        
        # Duration metrics (only for operations with duration)
        durations = [log.duration_ms for log in self.logs if log.duration_ms is not None]
        
        metrics = {
            "total_operations": total_operations,
            "successful_operations": successful_operations,
            "failed_operations": failed_operations,
            "success_rate": (successful_operations / total_operations * 100) if total_operations > 0 else 0,
            "session_id": self.session_id
        }
        
        if durations:
            metrics.update({
                "avg_duration_ms": sum(durations) / len(durations),
                "min_duration_ms": min(durations),
                "max_duration_ms": max(durations),
                "total_duration_ms": sum(durations)
            })
        
        # Category breakdown
        category_counts = {}
        for log in self.logs:
            category_counts[log.category] = category_counts.get(log.category, 0) + 1
        
        metrics["operations_by_category"] = category_counts
        
        return metrics
    
    def get_account_summary(self, account_id: int) -> Dict:
        """Get summary for specific account."""
        account_logs = [log for log in self.logs if log.account_id == account_id]
        
        if not account_logs:
            return {"account_id": account_id, "no_data": True}
        
        # Get account name from most recent log
        account_name = None
        for log in reversed(account_logs):
            if log.account_name:
                account_name = log.account_name
                break
        
        # Calculate account-specific metrics
        total_ops = len(account_logs)
        successful_ops = len([log for log in account_logs if log.success])
        
        # Recent activities
        recent_activities = []
        for log in account_logs[-10:]:  # Last 10 activities
            recent_activities.append({
                "timestamp": log.timestamp,
                "operation": log.operation,
                "success": log.success,
                "message": log.message
            })
        
        return {
            "account_id": account_id,
            "account_name": account_name,
            "total_operations": total_ops,
            "successful_operations": successful_ops,
            "success_rate": (successful_ops / total_ops * 100) if total_ops > 0 else 0,
            "recent_activities": list(reversed(recent_activities))
        }


class OperationTimer:
    """Context manager for timing operations."""
    
    def __init__(self, logger: MonitorLogger, category: LogCategory, operation: str, 
                 account_id: Optional[int] = None, account_name: Optional[str] = None):
        self.logger = logger
        self.category = category
        self.operation = operation
        self.account_id = account_id
        self.account_name = account_name
        self.start_time = None
        self.success = True
        self.error_msg = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(self.category, self.operation, "Operation started",
                         account_id=self.account_id, account_name=self.account_name)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        
        if exc_type is not None:
            self.success = False
            self.error_msg = str(exc_val)
            message = f"Operation failed: {self.error_msg}"
            level = LogLevel.ERROR
        else:
            message = f"Operation completed successfully in {duration_ms:.2f}ms"
            level = LogLevel.INFO
        
        self.logger.log(
            level=level,
            category=self.category,
            operation=self.operation,
            message=message,
            account_id=self.account_id,
            account_name=self.account_name,
            duration_ms=duration_ms,
            success=self.success,
            error=self.error_msg
        )


# Global logger instance
_global_logger = None

def get_logger() -> MonitorLogger:
    """Get global logger instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = MonitorLogger()
    return _global_logger


def log_operation(category: LogCategory, operation: str, account_id: Optional[int] = None, 
                 account_name: Optional[str] = None):
    """Decorator for timing and logging operations."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger()
            with OperationTimer(logger, category, operation, account_id, account_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


if __name__ == "__main__":
    # Test the logging system
    logger = get_logger()
    
    print("🧪 Testing Logging System")
    print("=" * 40)
    
    # Test basic logging
    logger.info(LogCategory.SYSTEM, "system_startup", "System started successfully")
    logger.info(LogCategory.ACCOUNT_PROCESSING, "account_fetch", "Processing account", 
                account_id=1, account_name="Demo Account", data={"balance": 10000})
    
    # Test error logging
    logger.error(LogCategory.API_CALL, "binance_api", "API call failed", 
                 error="Connection timeout", data={"endpoint": "/api/v3/account"})
    
    # Test operation timing
    with OperationTimer(logger, LogCategory.DATABASE, "save_nav_history", 1, "Demo Account"):
        time.sleep(0.1)  # Simulate operation
    
    # Get recent logs
    recent = logger.get_recent_logs(5)
    print(f"✅ Recent logs: {len(recent)} entries")
    
    # Get metrics
    metrics = logger.get_performance_metrics()
    print(f"✅ Metrics: {metrics['total_operations']} operations, {metrics['success_rate']:.1f}% success")
    
    # Get account summary
    summary = logger.get_account_summary(1)
    print(f"✅ Account summary: {summary['total_operations']} operations")
    
    print("✅ Logging system is working!")