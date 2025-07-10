# Migration to Hourly Data Collection

## Overview
This migration changes the monitoring interval from 2 minutes to 60 minutes (hourly), reducing data volume by 97%.

## Steps to Apply

1. **Backup your data** (if needed)
   - Export any historical data you want to keep before running the migration

2. **Run the SQL migration**
   - Execute `cleanup_for_hourly_data.sql` in your Supabase SQL editor
   - This will:
     - Drop `nav_history`, `price_history`, and `processed_transactions` tables
     - Clear `system_logs` table
     - Reset system metadata

3. **Deploy the code changes**
   - The monitoring interval has been updated to 60 minutes
   - Cron schedule changed to `0 * * * *` (every hour at minute 0)

## Changes Made

- **Monitoring interval**: 2 minutes → 60 minutes
- **Daily records per account**: 720 → 24 (97% reduction)
- **Dropped tables**: All historical data tables
- **Kept tables**: Configuration and account tables

## Benefits

- Significantly reduced database usage
- Faster dashboard loading
- Lower Supabase bandwidth costs
- Simpler data management

## Note
After applying this migration, the system will start collecting fresh data at hourly intervals.