#!/usr/bin/env python3
"""
DEPRECATED: Legacy Configuration File

This file is deprecated and maintained only for backward compatibility.
Please use the new configuration system in config/ directory:

New Usage:
    from config import settings
    
    # Instead of: SUPABASE_URL
    # Use: settings.database.supabase_url
    
    # Instead of: get_benchmark_allocation()
    # Use: settings.get_benchmark_allocation()

The new system provides:
- Environment-specific configurations
- Type safety and validation
- Better organization and structure
- Helper functions and computed values
"""

import warnings
import os
from config import settings as new_settings

# Issue deprecation warning
warnings.warn(
    "The root config.py file is deprecated. Please migrate to 'from config import settings'",
    DeprecationWarning,
    stacklevel=2
)

# Legacy exports for backward compatibility - delegating to new config system
SUPABASE_URL = new_settings.database.supabase_url
SUPABASE_ANON_KEY = new_settings.database.supabase_key
BINANCE_TLD = new_settings.api.binance.tld
SUPPORTED_SYMBOLS = new_settings.api.binance.supported_symbols
SUPPORTED_STABLECOINS = new_settings.api.binance.supported_stablecoins
DEFAULT_BENCHMARK_ALLOCATION = new_settings.financial.benchmark_allocation
DEFAULT_REBALANCE_FREQUENCY = new_settings.financial.rebalance_frequency
MINIMUM_BALANCE_THRESHOLD = new_settings.financial.minimum_balance_threshold
MINIMUM_USD_VALUE_THRESHOLD = new_settings.financial.minimum_usd_value_threshold
DEFAULT_HISTORICAL_PERIOD_DAYS = new_settings.scheduling.historical_period_days
MAX_HISTORICAL_PERIOD_DAYS = new_settings.scheduling.max_historical_period_days
DASHBOARD_HOST = new_settings.dashboard.host
DASHBOARD_PORT = new_settings.dashboard.port
DASHBOARD_TITLE = new_settings.dashboard.title
LOG_LEVEL = new_settings.logging.level
LOG_FORMAT = new_settings.logging.format
API_TIMEOUT_SECONDS = new_settings.api.binance.timeout_seconds
DATABASE_TIMEOUT_SECONDS = new_settings.database.timeout_seconds
MAX_RETRIES = new_settings.database.max_retries
CHART_COLORS = new_settings.dashboard.chart_colors
CHART_PERIODS = new_settings.dashboard.chart_periods
CORS_ALLOWED_ORIGINS = new_settings.dashboard.cors_allowed_origins

# Legacy environment variable reads
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
NOTIFICATION_ENABLED = os.environ.get("NOTIFICATION_ENABLED", "false").lower() == "true"
API_RATE_LIMIT_REQUESTS = 100  # Kept as legacy constant
API_RATE_LIMIT_PERIOD = 60

# Legacy functions delegating to new system
def validate_config():
    """DEPRECATED: Use settings.validate() instead."""
    return new_settings.validate()

def get_benchmark_allocation():
    """DEPRECATED: Use settings.get_benchmark_allocation() instead."""
    return new_settings.get_benchmark_allocation()

def get_supported_symbols():
    """DEPRECATED: Use settings.get_supported_symbols() instead."""
    return new_settings.get_supported_symbols()

def get_supported_stablecoins():
    """DEPRECATED: Use settings.get_supported_stablecoins() instead."""
    return new_settings.get_supported_stablecoins()

def get_chart_config():
    """DEPRECATED: Use settings.get_chart_config() instead."""
    return new_settings.get_chart_config()

def get_dashboard_url():
    """DEPRECATED: Use settings.get_dashboard_url() instead."""
    return new_settings.get_dashboard_url()