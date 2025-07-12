-- Migration: Add initialized_at column to benchmark_configs table
-- This prevents duplicate transaction processing by tracking when benchmark was initialized

-- Add initialized_at column to track when benchmark was first initialized
ALTER TABLE benchmark_configs 
ADD COLUMN initialized_at TIMESTAMP WITH TIME ZONE;

-- Update existing records to set initialized_at to NOW() 
-- This assumes current configs are already properly initialized
UPDATE benchmark_configs 
SET initialized_at = NOW() 
WHERE initialized_at IS NULL;

-- Add comment to explain the purpose
COMMENT ON COLUMN benchmark_configs.initialized_at IS 'Timestamp when benchmark was first initialized. Used to filter out pre-initialization transactions.';