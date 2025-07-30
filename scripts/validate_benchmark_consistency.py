#!/usr/bin/env python3
"""
Benchmark Consistency Validation Script

This script validates the consistency of benchmark calculations by:
1. Recalculating benchmark from scratch using transaction history
2. Comparing with current benchmark values
3. Validating rebalancing calculations
4. Checking for any discrepancies
"""

import os
import sys
import argparse
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database_manager import get_supabase_client
from config import settings

UTC = timezone.utc

class BenchmarkValidator:
    def __init__(self, supabase_client, account_id: str, account_name: str):
        self.db = supabase_client
        self.account_id = account_id
        self.account_name = account_name
        self.discrepancies = []
        
    def validate(self) -> bool:
        """Run all validation checks and return True if all pass"""
        print(f"\n{'='*60}")
        print(f"Validating benchmark for account: {self.account_name}")
        print(f"Account ID: {self.account_id}")
        print(f"{'='*60}\n")
        
        # Get current benchmark config
        config = self._get_benchmark_config()
        if not config:
            print("ERROR: No benchmark config found!")
            return False
            
        print(f"Current benchmark state:")
        print(f"  BTC units: {config['btc_units']}")
        print(f"  ETH units: {config['eth_units']}")
        print(f"  Initialized at: {config['initialized_at']}")
        print(f"  Rebalance count: {config.get('rebalance_count', 0)}")
        
        # Validate from transaction history
        print("\nRecalculating from transaction history...")
        recalculated = self._recalculate_from_history(config)
        
        # Compare results
        print("\nValidation results:")
        is_valid = self._compare_results(config, recalculated)
        
        if self.discrepancies:
            print(f"\n⚠️  Found {len(self.discrepancies)} discrepancies:")
            for disc in self.discrepancies:
                print(f"  - {disc}")
        else:
            print("\n✅ All validations passed!")
            
        return is_valid
        
    def _get_benchmark_config(self) -> Optional[Dict]:
        """Get current benchmark configuration"""
        result = self.db.table('benchmark_configs').select('*').eq('account_id', self.account_id).execute()
        return result.data[0] if result.data else None
        
    def _recalculate_from_history(self, config: Dict) -> Dict:
        """Recalculate benchmark from scratch using transaction and rebalancing history"""
        # Get initial NAV
        initial_nav = self._get_initial_nav(config['initialized_at'])
        if not initial_nav:
            self.discrepancies.append("Could not find initial NAV at initialization time")
            return {}
            
        print(f"  Initial NAV: ${initial_nav['nav']:.2f}")
        print(f"  Initial benchmark: ${initial_nav['benchmark_value']:.2f}")
        
        # Get initial prices
        initial_prices = self._get_prices_at_time(config['initialized_at'])
        if not initial_prices:
            self.discrepancies.append("Could not find initial prices")
            return {}
            
        # Calculate initial units (50/50 split)
        investment = Decimal(str(initial_nav['nav'])) / 2
        btc_units = investment / Decimal(str(initial_prices['btc_price']))
        eth_units = investment / Decimal(str(initial_prices['eth_price']))
        
        print(f"  Initial BTC units: {btc_units}")
        print(f"  Initial ETH units: {eth_units}")
        
        # Process all modifications
        modifications = self._get_modifications_history()
        print(f"\nProcessing {len(modifications)} modifications...")
        
        for mod in modifications:
            print(f"  {mod['modification_timestamp']}: {mod['modification_type']} ${abs(mod['cashflow_amount']):.2f}")
            
            # Validate modification calculations
            expected_btc_after = Decimal(str(mod['btc_units_before']))
            expected_eth_after = Decimal(str(mod['eth_units_before']))
            
            if mod['cashflow_amount'] > 0:  # Deposit
                btc_bought = Decimal(str(mod['btc_allocation'])) / Decimal(str(mod['btc_price']))
                eth_bought = Decimal(str(mod['eth_allocation'])) / Decimal(str(mod['eth_price']))
                expected_btc_after += btc_bought
                expected_eth_after += eth_bought
            else:  # Withdrawal
                total_value = (expected_btc_after * Decimal(str(mod['btc_price'])) + 
                             expected_eth_after * Decimal(str(mod['eth_price'])))
                if total_value > 0:
                    reduction_ratio = abs(Decimal(str(mod['cashflow_amount']))) / total_value
                    expected_btc_after *= (1 - reduction_ratio)
                    expected_eth_after *= (1 - reduction_ratio)
            
            # Check if stored values match calculated
            btc_diff = abs(expected_btc_after - Decimal(str(mod['btc_units_after'])))
            eth_diff = abs(expected_eth_after - Decimal(str(mod['eth_units_after'])))
            
            if btc_diff > Decimal('0.0000001') or eth_diff > Decimal('0.0000001'):
                self.discrepancies.append(
                    f"Modification {mod['id']} calculation mismatch: "
                    f"BTC diff={btc_diff}, ETH diff={eth_diff}"
                )
            
            btc_units = Decimal(str(mod['btc_units_after']))
            eth_units = Decimal(str(mod['eth_units_after']))
        
        # Process all rebalances
        rebalances = self._get_rebalance_history()
        print(f"\nProcessing {len(rebalances)} rebalances...")
        
        for reb in rebalances:
            print(f"  {reb['rebalance_timestamp']}: {reb['status']}")
            
            # Validate rebalance calculations
            total_value = Decimal(str(reb['total_value_before']))
            expected_btc_units = (total_value / 2) / Decimal(str(reb['btc_price']))
            expected_eth_units = (total_value / 2) / Decimal(str(reb['eth_price']))
            
            btc_diff = abs(expected_btc_units - Decimal(str(reb['btc_units_after'])))
            eth_diff = abs(expected_eth_units - Decimal(str(reb['eth_units_after'])))
            
            if btc_diff > Decimal('0.0000001') or eth_diff > Decimal('0.0000001'):
                self.discrepancies.append(
                    f"Rebalance {reb['id']} calculation mismatch: "
                    f"BTC diff={btc_diff}, ETH diff={eth_diff}"
                )
            
            if reb['status'] == 'success':
                btc_units = Decimal(str(reb['btc_units_after']))
                eth_units = Decimal(str(reb['eth_units_after']))
        
        return {
            'btc_units': float(btc_units),
            'eth_units': float(eth_units)
        }
        
    def _get_initial_nav(self, initialized_at: str) -> Optional[Dict]:
        """Get NAV at initialization time"""
        result = self.db.table('nav_history').select('*').eq('account_id', self.account_id)\
            .gte('timestamp', initialized_at).order('timestamp').limit(1).execute()
        return result.data[0] if result.data else None
        
    def _get_prices_at_time(self, timestamp: str) -> Optional[Dict]:
        """Get BTC/ETH prices at specific time"""
        result = self.db.table('price_history').select('*')\
            .lte('timestamp', timestamp).order('timestamp', desc=True).limit(1).execute()
        return result.data[0] if result.data else None
        
    def _get_modifications_history(self) -> List[Dict]:
        """Get all benchmark modifications in chronological order"""
        result = self.db.table('benchmark_modifications').select('*')\
            .eq('account_id', self.account_id).order('modification_timestamp').execute()
        return result.data or []
        
    def _get_rebalance_history(self) -> List[Dict]:
        """Get all rebalances in chronological order"""
        result = self.db.table('benchmark_rebalance_history').select('*')\
            .eq('account_id', self.account_id).order('rebalance_timestamp').execute()
        return result.data or []
        
    def _compare_results(self, current: Dict, recalculated: Dict) -> bool:
        """Compare current benchmark with recalculated values"""
        if not recalculated:
            return False
            
        current_btc = Decimal(str(current['btc_units']))
        current_eth = Decimal(str(current['eth_units']))
        recalc_btc = Decimal(str(recalculated['btc_units']))
        recalc_eth = Decimal(str(recalculated['eth_units']))
        
        btc_diff = abs(current_btc - recalc_btc)
        eth_diff = abs(current_eth - recalc_eth)
        
        # Allow tiny rounding differences (less than 0.0000001)
        tolerance = Decimal('0.0000001')
        
        print(f"\nComparison:")
        print(f"  BTC units - Current: {current_btc}, Recalculated: {recalc_btc}, Diff: {btc_diff}")
        print(f"  ETH units - Current: {current_eth}, Recalculated: {recalc_eth}, Diff: {eth_diff}")
        
        if btc_diff > tolerance:
            self.discrepancies.append(f"BTC units mismatch: diff={btc_diff}")
        if eth_diff > tolerance:
            self.discrepancies.append(f"ETH units mismatch: diff={eth_diff}")
            
        return btc_diff <= tolerance and eth_diff <= tolerance


def main():
    parser = argparse.ArgumentParser(description='Validate benchmark consistency')
    parser.add_argument('--account', type=str, help='Account name to validate (optional, validates all if not specified)')
    parser.add_argument('--fix', action='store_true', help='Attempt to fix discrepancies (not implemented yet)')
    args = parser.parse_args()
    
    # Initialize
    db_client = get_supabase_client()
    
    # Get accounts to validate
    if args.account:
        result = db_client.table('binance_accounts').select('*').eq('account_name', args.account).execute()
        accounts = result.data
        if not accounts:
            print(f"Account '{args.account}' not found!")
            return
    else:
        result = db_client.table('binance_accounts').select('*').order('account_name').execute()
        accounts = result.data or []
    
    # Validate each account
    all_valid = True
    for account in accounts:
        validator = BenchmarkValidator(db_client, account['id'], account['account_name'])
        is_valid = validator.validate()
        all_valid = all_valid and is_valid
    
    # Summary
    print(f"\n{'='*60}")
    if all_valid:
        print("✅ All accounts validated successfully!")
    else:
        print("⚠️  Some accounts have discrepancies!")
        if args.fix:
            print("Fix functionality not yet implemented.")
    print(f"{'='*60}\n")
    
    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())