-- Migration: Populate initial runtime configuration
-- Purpose: Seed runtime_config table with dynamic settings from settings.json
-- Author: System
-- Date: 2025-01-31

-- This migration populates the runtime_config table with configuration values
-- that are suitable for dynamic management (can be changed without restart)

-- Clear existing runtime configs (if any) to start fresh
DELETE FROM runtime_config WHERE key LIKE 'scheduling.%' OR key LIKE 'financial.%' OR key LIKE 'fee_management.%';

-- Scheduling configurations
INSERT INTO runtime_config (key, value, description, category)
VALUES 
    ('scheduling.cron_interval_minutes', '60'::jsonb, 'How often to run monitoring tasks (in minutes)', 'scheduling'),
    ('scheduling.daemon_interval_seconds', '3600'::jsonb, 'Daemon loop interval (in seconds)', 'scheduling'),
    ('scheduling.log_retention_hours', '720'::jsonb, 'How long to keep logs (in hours)', 'scheduling'),
    ('scheduling.log_retention_entries', '10000000'::jsonb, 'Maximum number of log entries to keep', 'scheduling'),
    ('scheduling.historical_period_days', '90'::jsonb, 'Default period for historical data queries', 'scheduling'),
    ('scheduling.max_historical_period_days', '36500'::jsonb, 'Maximum allowed historical period', 'scheduling');

-- Financial configurations
INSERT INTO runtime_config (key, value, description, category)
VALUES 
    ('financial.minimum_balance_threshold', '0.001'::jsonb, 'Minimum balance to consider for calculations', 'financial'),
    ('financial.minimum_usd_value_threshold', '0.1'::jsonb, 'Minimum USD value to include in NAV', 'financial'),
    ('financial.benchmark_allocation', '{"BTC": 0.5, "ETH": 0.5}'::jsonb, 'Default benchmark allocation percentages', 'financial'),
    ('financial.rebalance_frequency', '"weekly"'::jsonb, 'How often to rebalance benchmark portfolio', 'financial'),
    ('financial.performance_alert_thresholds', '{"nav_difference_warning": 5000, "nav_difference_critical": 10000}'::jsonb, 'Alert thresholds for NAV differences', 'financial');

-- Fee management configurations
INSERT INTO runtime_config (key, value, description, category)
VALUES 
    ('fee_management.default_performance_fee_rate', '0.50'::jsonb, 'Default performance fee rate (50%)', 'fee_management'),
    ('fee_management.calculation_schedule', '"monthly"'::jsonb, 'Fee calculation schedule: monthly, daily, or hourly', 'fee_management'),
    ('fee_management.calculation_day', '1'::jsonb, 'Day of month for monthly calculations (1-28)', 'fee_management'),
    ('fee_management.calculation_hour', '0'::jsonb, 'Hour of day for calculations (0-23 UTC)', 'fee_management'),
    ('fee_management.test_mode', '{"enabled": false, "interval_minutes": 60}'::jsonb, 'Test mode configuration for fee calculations', 'fee_management');

-- API rate limiting
INSERT INTO runtime_config (key, value, description, category)
VALUES 
    ('api.rate_limiting.requests_per_minute', '100'::jsonb, 'Maximum API requests per minute', 'api'),
    ('api.rate_limiting.period_seconds', '60'::jsonb, 'Rate limiting period in seconds', 'api');

-- Data processing configurations
INSERT INTO runtime_config (key, value, description, category)
VALUES 
    ('data_processing.batch_size', '100'::jsonb, 'Batch size for bulk operations', 'data_processing'),
    ('data_processing.transaction_lookback_days', '30'::jsonb, 'How far back to look for transactions', 'data_processing'),
    ('data_processing.price_cache_seconds', '60'::jsonb, 'How long to cache price data', 'data_processing'),
    ('data_processing.nav_calculation_precision', '2'::jsonb, 'Decimal places for NAV calculations', 'data_processing'),
    ('data_processing.benchmark_calculation_precision', '6'::jsonb, 'Decimal places for benchmark calculations', 'data_processing');

-- Monitoring configurations
INSERT INTO runtime_config (key, value, description, category)
VALUES 
    ('monitoring.health_check_interval_seconds', '30'::jsonb, 'Health check frequency', 'monitoring'),
    ('monitoring.performance_metrics_enabled', 'true'::jsonb, 'Enable performance metrics collection', 'monitoring'),
    ('monitoring.error_threshold_count', '5'::jsonb, 'Error count threshold for alerts', 'monitoring'),
    ('monitoring.restart_delay_seconds', '10'::jsonb, 'Delay before restarting failed processes', 'monitoring');

-- Logging configurations (database logging specific)
INSERT INTO runtime_config (key, value, description, category)
VALUES 
    ('logging.database_logging.enabled', 'true'::jsonb, 'Enable database logging', 'logging'),
    ('logging.database_logging.max_entries', '1000000'::jsonb, 'Maximum log entries to keep', 'logging'),
    ('logging.database_logging.retention_days', '30'::jsonb, 'Log retention period in days', 'logging'),
    ('logging.recent_logs_limit', '500'::jsonb, 'Number of recent logs to display', 'logging');

-- Chart configuration
INSERT INTO runtime_config (key, value, description, category)
VALUES 
    ('chart_configuration.default_tension', '0.4'::jsonb, 'Chart line tension for smoothing', 'chart_configuration'),
    ('chart_configuration.point_radius', '2'::jsonb, 'Chart point radius', 'chart_configuration'),
    ('chart_configuration.point_hover_radius', '5'::jsonb, 'Chart point radius on hover', 'chart_configuration'),
    ('chart_configuration.animation_duration', '1000'::jsonb, 'Chart animation duration in ms', 'chart_configuration');

-- Development/debug settings
INSERT INTO runtime_config (key, value, description, category)
VALUES 
    ('development.debug_mode', 'false'::jsonb, 'Enable debug mode', 'development'),
    ('development.verbose_logging', 'false'::jsonb, 'Enable verbose logging', 'development'),
    ('development.mock_api_calls', 'false'::jsonb, 'Mock external API calls', 'development'),
    ('development.test_data_enabled', 'false'::jsonb, 'Use test data instead of real data', 'development');

-- Add initial history entry for tracking
INSERT INTO runtime_config_history (config_id, key, old_value, new_value, change_reason, changed_by, version)
SELECT 
    id,
    key,
    NULL,
    value,
    'Initial configuration from settings.json',
    'migration',
    1
FROM runtime_config
WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '1 minute';