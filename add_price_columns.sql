-- Add price columns to nav_history table for clean benchmark calculation
-- This enables storing historical BTC/ETH prices with each NAV record

ALTER TABLE nav_history 
ADD COLUMN btc_price NUMERIC(10,2),
ADD COLUMN eth_price NUMERIC(10,2);

-- Add comment to document the change
COMMENT ON COLUMN nav_history.btc_price IS 'BTC price in USDT at the time of NAV recording';
COMMENT ON COLUMN nav_history.eth_price IS 'ETH price in USDT at the time of NAV recording';