#!/usr/bin/env python3
"""
NAV Data Cleanup Utility

Provides functionality to clean up NAV history and related data for specified
accounts within a given time range. Used by admin panel and CLI.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database_manager import DatabaseManager
from api.logger import get_logger, LogCategory

logger = get_logger()


class NavDataCleaner:
    """Handles cleanup of NAV history and related data."""
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize the cleaner.
        
        Args:
            dry_run: If True, only simulate the cleanup without making changes
        """
        self.db = DatabaseManager()
        self.dry_run = dry_run
        
    def preview_cleanup(
        self, 
        account_ids: List[str],
        from_timestamp: datetime,
        to_timestamp: Optional[datetime] = None
    ) -> Dict[str, int]:
        """
        Preview what would be deleted without actually deleting.
        
        Args:
            account_ids: List of account IDs to clean
            from_timestamp: Start of deletion range
            to_timestamp: End of deletion range (None = now)
            
        Returns:
            Dictionary with counts of records that would be deleted
        """
        if to_timestamp is None:
            to_timestamp = datetime.now(timezone.utc)
            
        counts = {}
        
        # Count nav_history records
        query = self.db._client.table('nav_history').select('id', count='exact')
        query = query.in_('account_id', account_ids)
        query = query.gte('timestamp', from_timestamp.isoformat())
        query = query.lte('timestamp', to_timestamp.isoformat())
        result = query.execute()
        counts['nav_history'] = result.count if result else 0
        
        # Count processed_transactions
        query = self.db._client.table('processed_transactions').select('id', count='exact')
        query = query.in_('account_id', account_ids)
        query = query.gte('timestamp', from_timestamp.isoformat())
        query = query.lte('timestamp', to_timestamp.isoformat())
        result = query.execute()
        counts['processed_transactions'] = result.count if result else 0
        
        # Count benchmark_modifications
        query = self.db._client.table('benchmark_modifications').select('id', count='exact')
        query = query.in_('account_id', account_ids)
        query = query.gte('modification_timestamp', from_timestamp.isoformat())
        query = query.lte('modification_timestamp', to_timestamp.isoformat())
        result = query.execute()
        counts['benchmark_modifications'] = result.count if result else 0
        
        # Count benchmark_rebalance_history
        query = self.db._client.table('benchmark_rebalance_history').select('id', count='exact')
        query = query.in_('account_id', account_ids)
        query = query.gte('rebalance_timestamp', from_timestamp.isoformat())
        query = query.lte('rebalance_timestamp', to_timestamp.isoformat())
        result = query.execute()
        counts['benchmark_rebalance_history'] = result.count if result else 0
        
        # Count fee_tracking (by period_end)
        query = self.db._client.table('fee_tracking').select('id', count='exact')
        query = query.in_('account_id', account_ids)
        query = query.gte('period_end', from_timestamp.date().isoformat())
        query = query.lte('period_end', to_timestamp.date().isoformat())
        result = query.execute()
        counts['fee_tracking'] = result.count if result else 0
        
        # Show benchmark_configs that will be reset
        counts['benchmark_configs_to_reset'] = len(account_ids)
        
        return counts
    
    def cleanup_data(
        self,
        account_ids: List[str],
        from_timestamp: datetime,
        to_timestamp: Optional[datetime] = None,
        reset_processing_status: bool = True,
        reset_benchmark: bool = True
    ) -> Tuple[Dict[str, int], List[str]]:
        """
        Clean up NAV history and related data.
        
        Args:
            account_ids: List of account IDs to clean
            from_timestamp: Start of deletion range
            to_timestamp: End of deletion range (None = now)
            reset_processing_status: Whether to reset account processing status
            reset_benchmark: Whether to reset benchmark_configs to last valid state
            
        Returns:
            Tuple of (deleted counts, list of errors)
        """
        if to_timestamp is None:
            to_timestamp = datetime.now(timezone.utc)
            
        deleted_counts = {}
        errors = []
        
        # Log the operation
        logger.info(
            LogCategory.SYSTEM,
            "data_cleanup_started",
            f"Starting cleanup for {len(account_ids)} accounts from {from_timestamp} to {to_timestamp}",
            data={
                "account_ids": account_ids,
                "from_timestamp": from_timestamp.isoformat(),
                "to_timestamp": to_timestamp.isoformat(),
                "dry_run": self.dry_run
            }
        )
        
        try:
            # 1. Clear FK references in benchmark_configs
            if not self.dry_run:
                # Get modification IDs that will be deleted
                mods_query = self.db._client.table('benchmark_modifications').select('id')
                mods_query = mods_query.in_('account_id', account_ids)
                mods_query = mods_query.gte('modification_timestamp', from_timestamp.isoformat())
                mods_query = mods_query.lte('modification_timestamp', to_timestamp.isoformat())
                mods_result = mods_query.execute()
                
                if mods_result.data:
                    mod_ids = [m['id'] for m in mods_result.data]
                    # Clear references
                    self.db._client.table('benchmark_configs')\
                        .update({'last_modification_id': None})\
                        .in_('last_modification_id', mod_ids)\
                        .execute()
            
            # 2. Delete nav_history
            if not self.dry_run:
                result = self.db._client.table('nav_history')\
                    .delete()\
                    .in_('account_id', account_ids)\
                    .gte('timestamp', from_timestamp.isoformat())\
                    .lte('timestamp', to_timestamp.isoformat())\
                    .execute()
                deleted_counts['nav_history'] = len(result.data) if result.data else 0
            else:
                deleted_counts['nav_history'] = self.preview_cleanup(account_ids, from_timestamp, to_timestamp)['nav_history']
            
            # 3. Delete processed_transactions
            if not self.dry_run:
                result = self.db._client.table('processed_transactions')\
                    .delete()\
                    .in_('account_id', account_ids)\
                    .gte('timestamp', from_timestamp.isoformat())\
                    .lte('timestamp', to_timestamp.isoformat())\
                    .execute()
                deleted_counts['processed_transactions'] = len(result.data) if result.data else 0
            else:
                deleted_counts['processed_transactions'] = self.preview_cleanup(account_ids, from_timestamp, to_timestamp)['processed_transactions']
            
            # 4. Delete benchmark_modifications
            if not self.dry_run:
                result = self.db._client.table('benchmark_modifications')\
                    .delete()\
                    .in_('account_id', account_ids)\
                    .gte('modification_timestamp', from_timestamp.isoformat())\
                    .lte('modification_timestamp', to_timestamp.isoformat())\
                    .execute()
                deleted_counts['benchmark_modifications'] = len(result.data) if result.data else 0
            else:
                deleted_counts['benchmark_modifications'] = self.preview_cleanup(account_ids, from_timestamp, to_timestamp)['benchmark_modifications']
            
            # 5. Delete benchmark_rebalance_history
            if not self.dry_run:
                result = self.db._client.table('benchmark_rebalance_history')\
                    .delete()\
                    .in_('account_id', account_ids)\
                    .gte('rebalance_timestamp', from_timestamp.isoformat())\
                    .lte('rebalance_timestamp', to_timestamp.isoformat())\
                    .execute()
                deleted_counts['benchmark_rebalance_history'] = len(result.data) if result.data else 0
            else:
                deleted_counts['benchmark_rebalance_history'] = self.preview_cleanup(account_ids, from_timestamp, to_timestamp)['benchmark_rebalance_history']
            
            # 6. Delete fee_tracking
            if not self.dry_run:
                result = self.db._client.table('fee_tracking')\
                    .delete()\
                    .in_('account_id', account_ids)\
                    .gte('period_end', from_timestamp.date().isoformat())\
                    .lte('period_end', to_timestamp.date().isoformat())\
                    .execute()
                deleted_counts['fee_tracking'] = len(result.data) if result.data else 0
            else:
                deleted_counts['fee_tracking'] = self.preview_cleanup(account_ids, from_timestamp, to_timestamp)['fee_tracking']
            
            # 7. Reset benchmark_configs and processing status to enforce replay
            if reset_benchmark and not self.dry_run:
                from datetime import timedelta
                benchmark_reset_count = 0
                # Unconditionally enforce the replay start time
                replay_init_at = (from_timestamp - timedelta(seconds=1))
                replay_start_checkpoint = replay_init_at.isoformat()

                for account_id in account_ids:
                    # A. Enforce replay checkpoint
                    upsert_payload = {
                        'account_id': account_id,
                        'last_processed_timestamp': replay_start_checkpoint
                    }
                    self.db._client.table('account_processing_status').upsert(upsert_payload).execute()

                    # B. ELEGANTNÍ ŘEŠENÍ: Nejdřív zkusíme najít snapshot v benchmark_modifications
                    last_valid_mod = self.db._client.table('benchmark_modifications')\
                        .select('btc_units_after, eth_units_after, modification_timestamp')\
                        .eq('account_id', account_id)\
                        .lt('modification_timestamp', from_timestamp.isoformat())\
                        .order('modification_timestamp', desc=True)\
                        .limit(1)\
                        .execute()

                    # Pokud existuje záznam v benchmark_modifications, použijeme ho
                    if last_valid_mod.data:
                        btc_units = last_valid_mod.data[0]['btc_units_after']
                        eth_units = last_valid_mod.data[0]['eth_units_after']
                        source_timestamp = last_valid_mod.data[0]['modification_timestamp']
                        source = "snapshot_modification"
                    else:
                        # POKUD NE, použijeme AKTUÁLNÍ stav z benchmark_configs, pokud je validní (není None)
                        current_config = self.db._client.table('benchmark_configs')\
                            .select('btc_units, eth_units')\
                            .eq('account_id', account_id)\
                            .execute()
                        
                        btc_units = None
                        eth_units = None
                        source_timestamp = None
                        source = None
                        if current_config.data and current_config.data[0].get('btc_units') is not None and current_config.data[0].get('eth_units') is not None:
                            btc_units = current_config.data[0]['btc_units']
                            eth_units = current_config.data[0]['eth_units']
                            source = "current_config"
                            logger.info(
                                LogCategory.SYSTEM,
                                "using_current_benchmark_state",
                                f"No historical snapshot found, using current benchmark state as baseline",
                                data={
                                    "account_id": account_id,
                                    "btc_units": btc_units,
                                    "eth_units": eth_units
                                }
                            )
                        else:
                            # NEPŘEPISUJ jednotky vůbec – ponech původní, zabráníme tím nastavení na nulu
                            logger.warning(
                                LogCategory.SYSTEM,
                                "no_benchmark_units_to_set",
                                f"No historical snapshot or valid current units found – leaving btc/eth units unchanged",
                                data={"account_id": account_id}
                            )

                    update_payload = {
                        'initialized_at': replay_init_at.isoformat(),
                        'last_modification_id': None,
                        'last_modification_timestamp': source_timestamp,
                        'last_modification_type': None,
                        'last_modification_amount': None,
                    }
                    # Jednotky zapíšeme pouze pokud máme validní zdroj
                    if btc_units is not None and eth_units is not None:
                        update_payload['btc_units'] = btc_units
                        update_payload['eth_units'] = eth_units

                    result = self.db._client.table('benchmark_configs').update(update_payload).eq('account_id', account_id).execute()

                    if result.data:
                        benchmark_reset_count += 1

                deleted_counts['benchmark_configs_reset'] = benchmark_reset_count
            

            # Note: Initialized_at and last_processed_timestamp were set above to enforce replay. Do not override them again here.

            # Log success
            logger.info(
                LogCategory.SYSTEM,
                "data_cleanup_completed",
                f"Cleanup completed successfully",
                data={
                    "deleted_counts": deleted_counts,
                    "dry_run": self.dry_run
                }
            )
            
        except Exception as e:
            error_msg = f"Error during cleanup: {str(e)}"
            errors.append(error_msg)
            logger.error(
                LogCategory.SYSTEM,
                "data_cleanup_error",
                error_msg,
                data={"error": str(e)}
            )
        
        return deleted_counts, errors


def main():
    """CLI interface for data cleanup."""
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description='Clean up NAV history data')
    parser.add_argument('--accounts', nargs='+', required=True, help='Account names to clean')
    parser.add_argument('--from', dest='from_date', required=True, help='From timestamp (ISO format)')
    parser.add_argument('--to', dest='to_date', help='To timestamp (ISO format, default: now)')
    parser.add_argument('--dry-run', action='store_true', help='Preview without deleting')
    parser.add_argument('--no-reset-status', action='store_true', help='Do not reset processing status')
    parser.add_argument('--no-reset-benchmark', action='store_true', help='Do not reset benchmark configs')
    
    args = parser.parse_args()
    
    # Parse timestamps
    from_timestamp = datetime.fromisoformat(args.from_date.replace('Z', '+00:00'))
    to_timestamp = None
    if args.to_date:
        to_timestamp = datetime.fromisoformat(args.to_date.replace('Z', '+00:00'))
    
    # Get account IDs
    db = DatabaseManager()
    accounts = db._client.table('binance_accounts')\
        .select('id, account_name')\
        .in_('account_name', args.accounts)\
        .execute()
    
    if not accounts.data:
        print(f"No accounts found matching: {args.accounts}")
        return
    
    account_ids = [a['id'] for a in accounts.data]
    account_names = [a['account_name'] for a in accounts.data]
    
    # Initialize cleaner
    cleaner = NavDataCleaner(dry_run=args.dry_run)
    
    # Preview first
    print("\n" + "="*60)
    print(f"{'DRY RUN - ' if args.dry_run else ''}Data Cleanup Preview")
    print("="*60)
    print(f"Accounts: {', '.join(account_names)}")
    print(f"From: {from_timestamp}")
    print(f"To: {to_timestamp or 'Now'}")
    print(f"Reset processing status: {not args.no_reset_status}")
    print(f"Reset benchmark configs: {not args.no_reset_benchmark}")
    print("\nRecords to be deleted:")
    
    preview = cleaner.preview_cleanup(account_ids, from_timestamp, to_timestamp)
    total = 0
    for table, count in preview.items():
        print(f"  {table}: {count:,}")
        total += count
    print(f"  TOTAL: {total:,}")
    
    if args.dry_run:
        print("\n[DRY RUN] No data was deleted.")
        return
    
    # Confirm
    print("\n" + "!"*60)
    response = input("Are you sure you want to delete this data? Type 'YES' to confirm: ")
    if response != 'YES':
        print("Cleanup cancelled.")
        return
    
    # Execute cleanup
    print("\nExecuting cleanup...")
    deleted, errors = cleaner.cleanup_data(
        account_ids, 
        from_timestamp, 
        to_timestamp,
        reset_processing_status=not args.no_reset_status,
        reset_benchmark=not args.no_reset_benchmark
    )
    
    print("\n" + "="*60)
    print("Cleanup Results")
    print("="*60)
    print("Deleted records:")
    for table, count in deleted.items():
        print(f"  {table}: {count:,}")
    
    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n✅ Cleanup completed successfully!")


if __name__ == "__main__":
    main()