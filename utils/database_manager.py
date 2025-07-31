"""
Centralized database connection manager with singleton pattern.
Provides thread-safe access to Supabase client with connection pooling.
"""
import threading
import time
from typing import Optional, Dict, Any
from functools import wraps
from supabase import create_client, Client
import os
try:
    from config import settings
except ImportError:
    # Fallback for Vercel environment
    class Settings:
        class Database:
            supabase_url = os.getenv('SUPABASE_URL', '')
            supabase_key = os.getenv('SUPABASE_ANON_KEY', '')
    settings = Settings()
    settings.database = Settings.Database()


class DatabaseManager:
    """Singleton database manager for Supabase connections."""
    
    _instance = None
    _lock = threading.Lock()
    _client: Optional[Client] = None
    _config = None
    _last_health_check: float = 0
    _health_check_interval: int = 60  # seconds
    _retry_count: int = 3
    _retry_delay: int = 1  # seconds
    
    def __new__(cls):
        """Ensure singleton pattern."""
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the database manager."""
        if not self._client:
            self._config = settings
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Supabase client with retry logic."""
        for attempt in range(self._retry_count):
            try:
                # Use service role key if available for admin operations
                supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', self._config.database.supabase_key)
                
                self._client = create_client(
                    self._config.database.supabase_url,
                    supabase_key
                )
                self._last_health_check = time.time()
                return
            except Exception as e:
                if attempt < self._retry_count - 1:
                    time.sleep(self._retry_delay * (attempt + 1))
                else:
                    raise ConnectionError(f"Failed to initialize Supabase client after {self._retry_count} attempts: {str(e)}")
    
    @property
    def client(self) -> Client:
        """Get the Supabase client with health check."""
        current_time = time.time()
        
        # Perform health check if interval has passed
        if current_time - self._last_health_check > self._health_check_interval:
            self._perform_health_check()
        
        if not self._client:
            self._initialize_client()
            
        return self._client
    
    def _perform_health_check(self):
        """Perform a health check on the database connection."""
        try:
            # Simple health check - try to query system_metadata
            self._client.table('system_metadata').select('key').limit(1).execute()
            self._last_health_check = time.time()
        except Exception:
            # Connection might be stale, reinitialize
            self._initialize_client()
    
    def execute_with_retry(self, operation, *args, **kwargs):
        """Execute a database operation with retry logic."""
        last_exception = None
        
        for attempt in range(self._retry_count):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self._retry_count - 1:
                    time.sleep(self._retry_delay * (attempt + 1))
                    # Check if we need to reinitialize the client
                    if "connection" in str(e).lower():
                        self._initialize_client()
        
        raise last_exception
    
    def transaction(self, operations: list):
        """Execute multiple operations in a transaction-like manner.
        
        Note: Supabase doesn't support true transactions via REST API,
        but we can ensure all operations use the same connection.
        """
        results = []
        for operation in operations:
            result = self.execute_with_retry(operation)
            results.append(result)
        return results


def with_database_retry(func):
    """Decorator to add retry logic to database operations."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        db = DatabaseManager()
        return db.execute_with_retry(func, *args, **kwargs)
    return wrapper


# Global instance for easy access
db_manager = DatabaseManager()


def get_supabase_client() -> Client:
    """Get the shared Supabase client instance."""
    return db_manager.client