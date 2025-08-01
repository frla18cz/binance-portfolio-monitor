-- Add master API credentials for sub-accounts
-- These are needed to detect sub-account transfers from sub-account perspective

ALTER TABLE binance_accounts
ADD COLUMN IF NOT EXISTS master_api_key VARCHAR(255),
ADD COLUMN IF NOT EXISTS master_api_secret VARCHAR(255);

-- Add comments for clarity
COMMENT ON COLUMN binance_accounts.master_api_key IS 'Master account API key for sub-accounts to detect transfers';
COMMENT ON COLUMN binance_accounts.master_api_secret IS 'Master account API secret for sub-accounts to detect transfers';