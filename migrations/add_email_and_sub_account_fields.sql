-- Add email and sub-account tracking fields to binance_accounts table

-- Add email column for identifying accounts in sub-account transfers
ALTER TABLE binance_accounts 
ADD COLUMN IF NOT EXISTS email TEXT;

-- Add is_sub_account flag
ALTER TABLE binance_accounts 
ADD COLUMN IF NOT EXISTS is_sub_account BOOLEAN DEFAULT FALSE;

-- Add reference to master account for sub-accounts
ALTER TABLE binance_accounts 
ADD COLUMN IF NOT EXISTS master_account_id UUID REFERENCES binance_accounts(id);

-- Add comment to document the fields
COMMENT ON COLUMN binance_accounts.email IS 'Email address associated with the Binance account, used for sub-account transfer identification';
COMMENT ON COLUMN binance_accounts.is_sub_account IS 'True if this is a sub-account, false for main accounts';
COMMENT ON COLUMN binance_accounts.master_account_id IS 'Reference to the master account if this is a sub-account';

-- Update existing accounts based on their names
UPDATE binance_accounts 
SET is_sub_account = TRUE,
    email = 'ondra_sub1@example.com'  -- This needs to be the actual Binance email
WHERE account_name = 'ondra_osobni_sub_acc1';

-- Note: Email addresses need to be manually updated with actual Binance account emails
-- These are required for sub-account transfer detection to work properly