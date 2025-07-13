#!/usr/bin/env python3
"""
Centralized Configuration System for Binance Portfolio Monitor

This module provides a comprehensive configuration management system that:
1. Loads configuration from JSON files
2. Supports environment-specific overrides
3. Provides type validation and defaults
4. Offers convenient helper functions

Usage:
    from config import settings
    
    # Direct access
    interval = settings.scheduling.cron_interval_minutes
    
    # Helper functions  
    colors = settings.get_chart_colors()
    allocation = settings.get_benchmark_allocation()
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class DatabaseConfig:
    supabase_url: str
    supabase_key: str
    timeout_seconds: int
    max_retries: int

@dataclass
class SchedulingConfig:
    cron_interval_minutes: int
    cron_schedule: str
    daemon_interval_seconds: int
    vercel_schedule: str
    log_retention_hours: int
    log_retention_entries: int
    historical_period_days: int
    max_historical_period_days: int
    thread_join_timeout_seconds: int

@dataclass
class FinancialConfig:
    minimum_balance_threshold: float
    minimum_usd_value_threshold: float
    benchmark_allocation: Dict[str, float]
    rebalance_frequency: str
    performance_alert_thresholds: Dict[str, float]

@dataclass
class BinanceConfig:
    tld: str
    data_api_url: str
    supported_symbols: list
    supported_stablecoins: list
    timeout_seconds: int
    max_retries: int

@dataclass
class ProxyConfig:
    enabled_on_vercel: bool
    url_env: str
    timeout_seconds: int
    verify_ssl: bool
    description: str = ""
    
    @property
    def url(self) -> Optional[str]:
        """Get proxy URL from environment variable."""
        return os.environ.get(self.url_env)
    
    @property
    def is_active(self) -> bool:
        """Check if proxy should be active (Vercel environment + URL configured)."""
        is_vercel = bool(os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'))
        return self.enabled_on_vercel and is_vercel and bool(self.url)

@dataclass
class APIConfig:
    binance: BinanceConfig
    rate_limiting: Dict[str, int]

@dataclass
class DashboardConfig:
    host: str
    port: int
    title: str
    cors_allowed_origins: list
    chart_colors: Dict[str, str]
    chart_periods: Dict[str, str]

@dataclass
class LoggingConfig:
    level: str
    format: str
    file_paths: Dict[str, str]
    rotation: Dict[str, int]
    recent_logs_limit: int
    tail_lines: int
    destination: str = "file"
    database_logging: Dict[str, Any] = None

@dataclass
class FileSystemConfig:
    directories: Dict[str, str]
    scripts: Dict[str, str]
    dashboard_html: str

@dataclass
class Settings:
    """Main configuration container with all settings."""
    
    def __init__(self, config_data: Dict[str, Any]):
        self.metadata = config_data.get("metadata", {})
        
        # Database configuration
        db_config = config_data.get("database", {})
        self.database = DatabaseConfig(
            supabase_url=os.environ.get(db_config.get("supabase_url_env", "SUPABASE_URL"), ""),
            supabase_key=os.environ.get(db_config.get("supabase_key_env", "SUPABASE_ANON_KEY"), ""),
            timeout_seconds=db_config.get("timeout_seconds", 10),
            max_retries=db_config.get("max_retries", 3)
        )
        
        # Scheduling configuration
        sched_config = config_data.get("scheduling", {})
        self.scheduling = SchedulingConfig(
            cron_interval_minutes=sched_config.get("cron_interval_minutes", 60),
            cron_schedule=sched_config.get("cron_schedule", "0 * * * *"),
            daemon_interval_seconds=sched_config.get("daemon_interval_seconds", 3600),
            vercel_schedule=sched_config.get("vercel_schedule", "0 * * * *"),
            log_retention_hours=sched_config.get("log_retention_hours", 24),
            log_retention_entries=sched_config.get("log_retention_entries", 10000),
            historical_period_days=sched_config.get("historical_period_days", 30),
            max_historical_period_days=sched_config.get("max_historical_period_days", 365),
            thread_join_timeout_seconds=sched_config.get("thread_join_timeout_seconds", 5)
        )
        
        # Financial configuration
        fin_config = config_data.get("financial", {})
        self.financial = FinancialConfig(
            minimum_balance_threshold=fin_config.get("minimum_balance_threshold", 0.001),
            minimum_usd_value_threshold=fin_config.get("minimum_usd_value_threshold", 0.1),
            benchmark_allocation=fin_config.get("benchmark_allocation", {"BTC": 0.5, "ETH": 0.5}),
            rebalance_frequency=fin_config.get("rebalance_frequency", "weekly"),
            performance_alert_thresholds=fin_config.get("performance_alert_thresholds", {
                "nav_difference_warning": 5000,
                "nav_difference_critical": 10000
            })
        )
        
        # API configuration
        api_config = config_data.get("api", {})
        binance_config = api_config.get("binance", {})
        self.api = APIConfig(
            binance=BinanceConfig(
                tld=binance_config.get("tld", "com"),
                data_api_url=binance_config.get("data_api_url", "https://data-api.binance.vision/api"),
                supported_symbols=binance_config.get("supported_symbols", ["BTCUSDT", "ETHUSDT"]),
                supported_stablecoins=binance_config.get("supported_stablecoins", ["USDT", "BUSD", "USDC", "BNFCR"]),
                timeout_seconds=binance_config.get("timeout_seconds", 30),
                max_retries=binance_config.get("max_retries", 3)
            ),
            rate_limiting=api_config.get("rate_limiting", {"requests_per_minute": 100, "period_seconds": 60})
        )
        
        # Proxy configuration
        proxy_config = config_data.get("proxy", {})
        self.proxy = ProxyConfig(
            enabled_on_vercel=proxy_config.get("enabled_on_vercel", False),
            url_env=proxy_config.get("url_env", "OXYLABS_PROXY_URL"),
            timeout_seconds=proxy_config.get("timeout_seconds", 30),
            verify_ssl=proxy_config.get("verify_ssl", True),
            description=proxy_config.get("description", "")
        )
        
        # Dashboard configuration
        dash_config = config_data.get("dashboard", {})
        self.dashboard = DashboardConfig(
            host=dash_config.get("host", "localhost"),
            port=dash_config.get("port", 8001),
            title=dash_config.get("title", "Binance Portfolio Monitor"),
            cors_allowed_origins=dash_config.get("cors_allowed_origins", ["*"]),
            chart_colors=dash_config.get("chart_colors", {
                "portfolio": "#667eea",
                "benchmark": "#764ba2",
                "portfolio_fill": "rgba(102, 126, 234, 0.1)",
                "benchmark_fill": "rgba(118, 75, 162, 0.1)"
            }),
            chart_periods=dash_config.get("chart_periods", {
                "inception": "Od začátku",
                "1w": "1 týden", 
                "1m": "1 měsíc",
                "1y": "1 rok",
                "ytd": "Tento rok",
                "custom": "Vlastní"
            })
        )
        
        # Logging configuration
        log_config = config_data.get("logging", {})
        self.logging = LoggingConfig(
            level=log_config.get("level", "INFO"),
            format=log_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            file_paths=log_config.get("file_paths", {
                "main_log": "logs/monitor.log",
                "cron_log": "logs/cron.log"
            }),
            rotation=log_config.get("rotation", {"max_size_mb": 10, "backup_count": 5}),
            recent_logs_limit=log_config.get("recent_logs_limit", 100),
            tail_lines=log_config.get("tail_lines", 5),
            destination=log_config.get("destination", "file"),
            database_logging=log_config.get("database_logging", {
                "enabled": False,
                "table_name": "system_logs",
                "max_entries": 100000,
                "retention_days": 365,
                "log_levels": ["INFO", "WARNING", "ERROR", "CRITICAL"]
            })
        )
        
        # File system configuration
        fs_config = config_data.get("file_system", {})
        self.file_system = FileSystemConfig(
            directories=fs_config.get("directories", {"logs": "logs", "data": "data"}),
            scripts=fs_config.get("scripts", {
                "scrape_data": "scrape_data.py",
                "api_index": "api/index.py"
            }),
            dashboard_html=fs_config.get("dashboard_html", "dashboard.html")
        )
        
        # Store raw config for additional access
        self.raw_config = config_data
    
    # Helper methods for backward compatibility and convenience
    def get_benchmark_allocation(self) -> Dict[str, float]:
        """Get benchmark allocation dictionary."""
        return self.financial.benchmark_allocation.copy()
    
    def get_supported_symbols(self) -> list:
        """Get list of supported trading symbols."""
        return self.api.binance.supported_symbols.copy()
    
    def get_supported_stablecoins(self) -> list:
        """Get list of supported stablecoins."""
        return self.api.binance.supported_stablecoins.copy()
    
    def get_chart_config(self) -> Dict[str, Dict]:
        """Get chart configuration for UI."""
        return {
            'colors': self.dashboard.chart_colors.copy(),
            'periods': self.dashboard.chart_periods.copy()
        }
    
    def get_dashboard_url(self) -> str:
        """Get full dashboard URL."""
        return f"http://{self.dashboard.host}:{self.dashboard.port}"
    
    def get_cron_schedule(self) -> str:
        """Get cron schedule string."""
        return self.scheduling.cron_schedule
    
    def get_log_file_path(self, log_type: str = "main_log") -> str:
        """Get path to specific log file."""
        return self.logging.file_paths.get(log_type, "logs/monitor.log")
    
    def validate(self) -> bool:
        """Validate configuration values."""
        errors = []
        
        # Database validation
        if not self.database.supabase_url:
            errors.append("SUPABASE_URL environment variable is not set")
        if not self.database.supabase_key:
            errors.append("SUPABASE_ANON_KEY environment variable is not set")
        
        # Financial validation
        if self.financial.minimum_balance_threshold <= 0:
            errors.append("minimum_balance_threshold must be positive")
        
        # Benchmark allocation validation
        allocation_sum = sum(self.financial.benchmark_allocation.values())
        if abs(allocation_sum - 1.0) > 0.001:
            errors.append(f"benchmark_allocation must sum to 1.0, got {allocation_sum}")
        
        # Port validation
        if not (1 <= self.dashboard.port <= 65535):
            errors.append(f"dashboard port must be between 1-65535, got {self.dashboard.port}")
        
        if errors:
            raise ValueError(f"Configuration validation errors: {', '.join(errors)}")
        
        return True


class ConfigurationLoader:
    """Handles loading and merging configuration files."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            config_dir = Path(__file__).parent
        self.config_dir = config_dir
        
    def load_settings(self, environment: Optional[str] = None) -> Settings:
        """Load configuration with optional environment override."""
        
        # Load base configuration
        base_config_path = self.config_dir / "settings.json"
        if not base_config_path.exists():
            raise FileNotFoundError(f"Base configuration file not found: {base_config_path}")
        
        with open(base_config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # Apply environment-specific overrides
        if environment:
            env_config_path = self.config_dir / "environments" / f"{environment}.json"
            if env_config_path.exists():
                with open(env_config_path, 'r', encoding='utf-8') as f:
                    env_config = json.load(f)
                config_data = self._merge_configs(config_data, env_config)
        
        # Check for environment variable override
        env_from_var = os.environ.get("BINANCE_MONITOR_ENV")
        if env_from_var and env_from_var != environment:
            env_config_path = self.config_dir / "environments" / f"{env_from_var}.json"
            if env_config_path.exists():
                with open(env_config_path, 'r', encoding='utf-8') as f:
                    env_config = json.load(f)
                config_data = self._merge_configs(config_data, env_config)
        
        return Settings(config_data)
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result


# Global configuration instance
_loader = ConfigurationLoader()
_settings = None

def get_settings(environment: Optional[str] = None, force_reload: bool = False) -> Settings:
    """Get global settings instance."""
    global _settings
    
    if _settings is None or force_reload:
        _settings = _loader.load_settings(environment)
        _settings.validate()
    
    return _settings

# Convenience exports for backward compatibility
settings = get_settings()

# Legacy exports - for gradual migration
SUPABASE_URL = settings.database.supabase_url
SUPABASE_ANON_KEY = settings.database.supabase_key
BINANCE_TLD = settings.api.binance.tld
DEFAULT_BENCHMARK_ALLOCATION = settings.financial.benchmark_allocation
DEFAULT_REBALANCE_FREQUENCY = settings.financial.rebalance_frequency
MINIMUM_BALANCE_THRESHOLD = settings.financial.minimum_balance_threshold
MINIMUM_USD_VALUE_THRESHOLD = settings.financial.minimum_usd_value_threshold
DEFAULT_HISTORICAL_PERIOD_DAYS = settings.scheduling.historical_period_days
DASHBOARD_HOST = settings.dashboard.host
DASHBOARD_PORT = settings.dashboard.port
CORS_ALLOWED_ORIGINS = settings.dashboard.cors_allowed_origins

# Helper functions for backward compatibility
def get_benchmark_allocation():
    return settings.get_benchmark_allocation()

def get_supported_symbols():
    return settings.get_supported_symbols()

def get_supported_stablecoins():
    return settings.get_supported_stablecoins()

def get_chart_config():
    return settings.get_chart_config()

def get_dashboard_url():
    return settings.get_dashboard_url()

def validate_config():
    return settings.validate()