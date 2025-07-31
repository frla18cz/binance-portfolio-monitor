-- Migration: Add runtime configuration tables
-- Purpose: Enable dynamic configuration management without application restarts
-- Author: System
-- Date: 2025-01-31

-- Table for global runtime configuration
CREATE TABLE IF NOT EXISTS runtime_config (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    key VARCHAR(255) NOT NULL UNIQUE,
    value JSONB NOT NULL,
    description TEXT,
    category VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255),
    version INTEGER DEFAULT 1
);

-- Table for configuration change history (audit trail)
CREATE TABLE IF NOT EXISTS runtime_config_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    config_id UUID REFERENCES runtime_config(id) ON DELETE CASCADE,
    key VARCHAR(255) NOT NULL,
    old_value JSONB,
    new_value JSONB NOT NULL,
    change_reason TEXT,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    changed_by VARCHAR(255) NOT NULL,
    version INTEGER NOT NULL
);

-- Table for account-specific configuration overrides
CREATE TABLE IF NOT EXISTS account_config_overrides (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    account_id UUID REFERENCES binance_accounts(id) ON DELETE CASCADE,
    config_key VARCHAR(255) NOT NULL,
    value JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255),
    UNIQUE(account_id, config_key)
);

-- Create indexes for performance
CREATE INDEX idx_runtime_config_key ON runtime_config(key) WHERE is_active = true;
CREATE INDEX idx_runtime_config_category ON runtime_config(category) WHERE is_active = true;
CREATE INDEX idx_runtime_config_updated ON runtime_config(updated_at);
CREATE INDEX idx_config_history_key ON runtime_config_history(key);
CREATE INDEX idx_config_history_changed ON runtime_config_history(changed_at);
CREATE INDEX idx_account_overrides_account ON account_config_overrides(account_id) WHERE is_active = true;
CREATE INDEX idx_account_overrides_key ON account_config_overrides(config_key) WHERE is_active = true;

-- Function to automatically track configuration changes
CREATE OR REPLACE FUNCTION track_config_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND OLD.value IS DISTINCT FROM NEW.value THEN
        INSERT INTO runtime_config_history (
            config_id,
            key,
            old_value,
            new_value,
            change_reason,
            changed_by,
            version
        ) VALUES (
            NEW.id,
            NEW.key,
            OLD.value,
            NEW.value,
            COALESCE(NEW.description, 'Configuration updated'),
            COALESCE(NEW.updated_by, 'system'),
            NEW.version
        );
        
        NEW.version = OLD.version + 1;
        NEW.updated_at = CURRENT_TIMESTAMP;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic history tracking
CREATE TRIGGER runtime_config_changes
    BEFORE UPDATE ON runtime_config
    FOR EACH ROW
    EXECUTE FUNCTION track_config_changes();

-- Function to get effective configuration (with account overrides)
CREATE OR REPLACE FUNCTION get_effective_config(
    p_account_id UUID DEFAULT NULL,
    p_key VARCHAR(255) DEFAULT NULL
)
RETURNS TABLE (
    key VARCHAR(255),
    value JSONB,
    source VARCHAR(50),
    category VARCHAR(100)
) AS $$
BEGIN
    RETURN QUERY
    WITH global_config AS (
        SELECT 
            rc.key,
            rc.value,
            'global'::VARCHAR(50) as source,
            rc.category
        FROM runtime_config rc
        WHERE rc.is_active = true
        AND (p_key IS NULL OR rc.key = p_key)
    ),
    account_config AS (
        SELECT 
            aco.config_key as key,
            aco.value,
            'account'::VARCHAR(50) as source,
            gc.category
        FROM account_config_overrides aco
        LEFT JOIN global_config gc ON gc.key = aco.config_key
        WHERE aco.is_active = true
        AND aco.account_id = p_account_id
        AND (p_key IS NULL OR aco.config_key = p_key)
    )
    SELECT 
        COALESCE(ac.key, gc.key) as key,
        COALESCE(ac.value, gc.value) as value,
        COALESCE(ac.source, gc.source) as source,
        COALESCE(ac.category, gc.category) as category
    FROM global_config gc
    FULL OUTER JOIN account_config ac ON gc.key = ac.key
    ORDER BY key;
END;
$$ LANGUAGE plpgsql;

-- Row Level Security
ALTER TABLE runtime_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE runtime_config_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE account_config_overrides ENABLE ROW LEVEL SECURITY;

-- Policies for service role
CREATE POLICY "Service role can manage runtime config" ON runtime_config
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Service role can view config history" ON runtime_config_history
    FOR SELECT
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage account overrides" ON account_config_overrides
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Comments for documentation
COMMENT ON TABLE runtime_config IS 'Global runtime configuration that can be changed without application restart';
COMMENT ON TABLE runtime_config_history IS 'Audit trail of all configuration changes';
COMMENT ON TABLE account_config_overrides IS 'Account-specific configuration overrides';

COMMENT ON COLUMN runtime_config.key IS 'Unique configuration key (e.g., scheduling.update_interval_minutes)';
COMMENT ON COLUMN runtime_config.value IS 'Configuration value stored as JSONB for flexibility';
COMMENT ON COLUMN runtime_config.category IS 'Configuration category for grouping (e.g., scheduling, financial, api)';
COMMENT ON COLUMN runtime_config.is_active IS 'Soft delete flag';
COMMENT ON COLUMN runtime_config.version IS 'Version number incremented on each update';

COMMENT ON FUNCTION get_effective_config IS 'Returns effective configuration with account-specific overrides applied';