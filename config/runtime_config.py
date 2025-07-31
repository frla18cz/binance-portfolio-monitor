#!/usr/bin/env python3
"""
Runtime Configuration Service

Provides dynamic configuration management with database storage,
caching, and fallback to JSON file configuration.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union
from pathlib import Path
from threading import Lock
import os

from utils.database_manager import DatabaseManager
from config import settings as static_settings

logger = logging.getLogger(__name__)


class ConfigCache:
    """Thread-safe configuration cache with TTL."""
    
    def __init__(self, ttl_seconds: int = 300):  # 5 minutes default
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
        self.ttl_seconds = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if datetime.now() < entry['expires_at']:
                    return entry['value']
                else:
                    del self._cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache with expiration."""
        with self._lock:
            self._cache[key] = {
                'value': value,
                'expires_at': datetime.now() + timedelta(seconds=self.ttl_seconds)
            }
    
    def invalidate(self, key: Optional[str] = None) -> None:
        """Invalidate specific key or entire cache."""
        with self._lock:
            if key:
                self._cache.pop(key, None)
            else:
                self._cache.clear()
    
    def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate all keys matching pattern."""
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self._cache[key]


class RuntimeConfigService:
    """
    Service for managing runtime configuration with database storage.
    
    Features:
    - Database-backed dynamic configuration
    - In-memory caching with TTL
    - Account-specific overrides
    - Automatic fallback to static JSON config
    - Configuration change history
    """
    
    def __init__(self, cache_ttl: int = 300):
        self.db = DatabaseManager()
        self.cache = ConfigCache(ttl_seconds=cache_ttl)
        self.static_config = static_settings.raw_config
        self._initialized = False
        
    def _ensure_initialized(self) -> None:
        """Lazy initialization of database connection."""
        if not self._initialized:
            try:
                # Test database connection
                self.db._client.table('runtime_config').select('key').limit(1).execute()
                self._initialized = True
            except Exception as e:
                logger.warning(f"Runtime config database not available: {e}")
                self._initialized = False
    
    def get(self, key: str, account_id: Optional[str] = None, 
            default: Any = None, use_cache: bool = True) -> Any:
        """
        Get configuration value with fallback chain:
        1. Account-specific override (if account_id provided)
        2. Global runtime config from database
        3. Static config from JSON file
        4. Default value
        
        Args:
            key: Configuration key in dot notation (e.g., 'scheduling.update_interval')
            account_id: Optional account ID for account-specific overrides
            default: Default value if key not found
            use_cache: Whether to use cache (disable for real-time requirements)
            
        Returns:
            Configuration value
        """
        # Check cache first
        cache_key = f"{account_id}:{key}" if account_id else key
        if use_cache:
            cached_value = self.cache.get(cache_key)
            if cached_value is not None:
                return cached_value
        
        # Try database
        value = self._get_from_database(key, account_id)
        
        # Fallback to static config
        if value is None:
            value = self._get_from_static_config(key)
        
        # Use default if still not found
        if value is None:
            value = default
        
        # Cache the result
        if use_cache and value is not None:
            self.cache.set(cache_key, value)
        
        return value
    
    def _get_from_database(self, key: str, account_id: Optional[str] = None) -> Optional[Any]:
        """Get configuration from database with account overrides."""
        self._ensure_initialized()
        if not self._initialized:
            return None
        
        try:
            # Check account-specific override first
            if account_id:
                response = self.db._client.table('account_config_overrides')\
                    .select('value')\
                    .eq('account_id', account_id)\
                    .eq('config_key', key)\
                    .eq('is_active', True)\
                    .execute()
                
                if response.data:
                    return response.data[0]['value']
            
            # Get global config
            response = self.db._client.table('runtime_config')\
                .select('value')\
                .eq('key', key)\
                .eq('is_active', True)\
                .execute()
            
            if response.data:
                return response.data[0]['value']
                
        except Exception as e:
            logger.error(f"Error getting runtime config for {key}: {e}")
        
        return None
    
    def _get_from_static_config(self, key: str) -> Optional[Any]:
        """Get configuration from static JSON config using dot notation."""
        parts = key.split('.')
        value = self.static_config
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None
        
        return value
    
    def set(self, key: str, value: Any, account_id: Optional[str] = None,
            description: Optional[str] = None, category: Optional[str] = None,
            updated_by: str = 'system') -> bool:
        """
        Set configuration value in database.
        
        Args:
            key: Configuration key
            value: Configuration value (will be stored as JSON)
            account_id: Optional account ID for account-specific override
            description: Optional description of the change
            category: Configuration category (e.g., 'scheduling', 'financial')
            updated_by: User/system making the change
            
        Returns:
            True if successful, False otherwise
        """
        self._ensure_initialized()
        if not self._initialized:
            logger.error("Cannot set runtime config - database not available")
            return False
        
        try:
            if account_id:
                # Set account-specific override
                self.db._client.table('account_config_overrides').upsert({
                    'account_id': account_id,
                    'config_key': key,
                    'value': value,
                    'updated_by': updated_by,
                    'is_active': True
                }).execute()
            else:
                # Set global config
                existing = self.db._client.table('runtime_config')\
                    .select('id')\
                    .eq('key', key)\
                    .execute()
                
                if existing.data:
                    # Update existing
                    self.db._client.table('runtime_config')\
                        .update({
                            'value': value,
                            'description': description,
                            'updated_by': updated_by,
                            'updated_at': datetime.now().isoformat()
                        })\
                        .eq('key', key)\
                        .execute()
                else:
                    # Insert new
                    self.db._client.table('runtime_config').insert({
                        'key': key,
                        'value': value,
                        'description': description,
                        'category': category or self._infer_category(key),
                        'updated_by': updated_by,
                        'is_active': True
                    }).execute()
            
            # Invalidate cache
            cache_key = f"{account_id}:{key}" if account_id else key
            self.cache.invalidate(cache_key)
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting runtime config for {key}: {e}")
            return False
    
    def _infer_category(self, key: str) -> str:
        """Infer category from configuration key."""
        if '.' in key:
            return key.split('.')[0]
        return 'general'
    
    def get_all(self, category: Optional[str] = None, 
                account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all configuration values, optionally filtered by category.
        
        Args:
            category: Optional category filter
            account_id: Optional account ID for account-specific configs
            
        Returns:
            Dictionary of configuration key-value pairs
        """
        self._ensure_initialized()
        
        # Start with static config
        result = {}
        if category:
            # Filter static config by category
            if category in self.static_config:
                result = {f"{category}.{k}": v 
                         for k, v in self.static_config[category].items()}
        else:
            # Flatten all static config
            result = self._flatten_dict(self.static_config)
        
        # Override with database config
        if self._initialized:
            try:
                # Get global runtime config
                query = self.db._client.table('runtime_config')\
                    .select('key, value')\
                    .eq('is_active', True)
                
                if category:
                    query = query.eq('category', category)
                
                response = query.execute()
                
                for item in response.data:
                    result[item['key']] = item['value']
                
                # Apply account overrides if specified
                if account_id:
                    overrides = self.db._client.table('account_config_overrides')\
                        .select('config_key, value')\
                        .eq('account_id', account_id)\
                        .eq('is_active', True)\
                        .execute()
                    
                    for item in overrides.data:
                        if not category or item['config_key'].startswith(f"{category}."):
                            result[item['config_key']] = item['value']
                            
            except Exception as e:
                logger.error(f"Error getting all runtime configs: {e}")
        
        return result
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '') -> Dict[str, Any]:
        """Flatten nested dictionary using dot notation."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict) and not k.endswith('_metadata'):
                items.extend(self._flatten_dict(v, new_key).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def get_history(self, key: Optional[str] = None, 
                    limit: int = 100) -> list:
        """
        Get configuration change history.
        
        Args:
            key: Optional key to filter history
            limit: Maximum number of records to return
            
        Returns:
            List of configuration changes
        """
        self._ensure_initialized()
        if not self._initialized:
            return []
        
        try:
            query = self.db._client.table('runtime_config_history')\
                .select('*')\
                .order('changed_at', desc=True)\
                .limit(limit)
            
            if key:
                query = query.eq('key', key)
            
            response = query.execute()
            return response.data
            
        except Exception as e:
            logger.error(f"Error getting config history: {e}")
            return []
    
    def delete(self, key: str, account_id: Optional[str] = None) -> bool:
        """
        Soft delete a configuration (sets is_active=False).
        
        Args:
            key: Configuration key to delete
            account_id: Optional account ID for account-specific override
            
        Returns:
            True if successful, False otherwise
        """
        self._ensure_initialized()
        if not self._initialized:
            return False
        
        try:
            if account_id:
                self.db._client.table('account_config_overrides')\
                    .update({'is_active': False})\
                    .eq('account_id', account_id)\
                    .eq('config_key', key)\
                    .execute()
            else:
                self.db._client.table('runtime_config')\
                    .update({'is_active': False})\
                    .eq('key', key)\
                    .execute()
            
            # Invalidate cache
            cache_key = f"{account_id}:{key}" if account_id else key
            self.cache.invalidate(cache_key)
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting runtime config for {key}: {e}")
            return False


# Global instance
_runtime_config = None

def get_runtime_config() -> RuntimeConfigService:
    """Get global runtime configuration service instance."""
    global _runtime_config
    if _runtime_config is None:
        _runtime_config = RuntimeConfigService()
    return _runtime_config