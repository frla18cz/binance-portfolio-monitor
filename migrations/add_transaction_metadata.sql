-- Add metadata column to processed_transactions table
-- This column will store additional transaction information like transfer type, network, etc.

ALTER TABLE processed_transactions 
ADD COLUMN IF NOT EXISTS metadata JSONB;

COMMENT ON COLUMN processed_transactions.metadata IS 
'Additional transaction data: transfer_type (0=external,1=internal), tx_id, coin, network';

-- Create index on metadata for faster queries on transfer_type
CREATE INDEX IF NOT EXISTS idx_processed_transactions_metadata_transfer_type 
ON processed_transactions ((metadata->>'transfer_type'))
WHERE metadata IS NOT NULL;

-- Add index on transaction_type for faster filtering
CREATE INDEX IF NOT EXISTS idx_processed_transactions_type 
ON processed_transactions(transaction_type);