#!/usr/bin/env python3
"""
Manual fee calculation runner with flexible options.
Useful for testing and manual fee calculations.
"""

import argparse
import sys
import os
from datetime import datetime, timedelta, UTC

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from api.fee_calculator import FeeCalculator
from api.logger import get_logger, LogCategory
from config import settings


def main():
    parser = argparse.ArgumentParser(description='Run fee calculations manually')
    parser.add_argument('--month', type=str, help='Specific month to calculate (YYYY-MM format)')
    parser.add_argument('--account', type=str, help='Specific account ID (optional)')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    parser.add_argument('--list-accounts', action='store_true', help='List all accounts')
    parser.add_argument('--show-config', action='store_true', help='Show fee configuration')
    parser.add_argument('--last-n-months', type=int, help='Calculate for last N months')
    
    args = parser.parse_args()
    logger = get_logger()
    
    # Initialize calculator
    calculator = FeeCalculator()
    
    # Show configuration
    if args.show_config:
        print("\n=== Fee Management Configuration ===")
        print(f"Default Performance Fee Rate: {settings.fee_management.default_performance_fee_rate * 100:.1f}%")
        print(f"Calculation Schedule: {settings.fee_management.calculation_schedule}")
        print(f"Calculation Day: {settings.fee_management.calculation_day}")
        print(f"Calculation Hour: {settings.fee_management.calculation_hour}:00 UTC")
        print(f"Test Mode Enabled: {settings.fee_management.test_mode.enabled}")
        if settings.fee_management.test_mode.enabled:
            print(f"Test Interval: {settings.fee_management.test_mode.interval_minutes} minutes")
        print()
        return
    
    # List accounts
    if args.list_accounts:
        try:
            accounts = calculator.db.table('binance_accounts').select('id, account_name, performance_fee_rate').execute()
            print("\n=== Binance Accounts ===")
            for account in accounts.data:
                fee_rate = account.get('performance_fee_rate', settings.fee_management.default_performance_fee_rate)
                print(f"ID: {account['id']}")
                print(f"Name: {account['account_name']}")
                print(f"Performance Fee Rate: {fee_rate * 100:.1f}%")
                print("-" * 40)
            print()
        except Exception as e:
            print(f"Error listing accounts: {e}")
        return
    
    # Calculate fees
    try:
        if args.test:
            print("Running in TEST MODE - calculations will be logged but not affect production")
            
        if args.last_n_months:
            # Calculate for multiple months
            end_date = datetime.now(UTC).date().replace(day=1)
            for i in range(args.last_n_months):
                month_date = (end_date - timedelta(days=i * 30)).replace(day=1)
                print(f"\nCalculating fees for {month_date.strftime('%B %Y')}...")
                
                if args.account:
                    # Single account
                    account_result = calculator.db.table('binance_accounts').select('account_name').eq('id', args.account).single().execute()
                    if account_result.data:
                        calculator._calculate_account_fees(args.account, account_result.data['account_name'], month_date)
                    else:
                        print(f"Account not found: {args.account}")
                        return
                else:
                    # All accounts
                    calculator.calculate_fees_for_all_accounts(month_date)
                    
        else:
            # Single month calculation
            month_date = None
            if args.month:
                try:
                    month_date = datetime.strptime(args.month + '-01', '%Y-%m-%d').date()
                except ValueError:
                    print(f"Invalid month format: {args.month}. Use YYYY-MM format.")
                    return
            
            if args.account:
                # Single account
                account_result = calculator.db.table('binance_accounts').select('account_name').eq('id', args.account).single().execute()
                if account_result.data:
                    account_name = account_result.data['account_name']
                    print(f"Calculating fees for account: {account_name}")
                    calculator._calculate_account_fees(args.account, account_name, month_date or calculator.get_calculation_period())
                else:
                    print(f"Account not found: {args.account}")
                    return
            else:
                # All accounts
                print(f"Calculating fees for all accounts...")
                calculator.calculate_fees_for_all_accounts(month_date)
        
        print("\nFee calculation completed successfully!")
        
        # Show summary
        if not args.account:
            pending_fees = calculator.get_pending_fees()
            if pending_fees:
                total_pending = sum(f['performance_fee'] for f in pending_fees)
                print(f"\nTotal pending fees across all accounts: ${total_pending:,.2f}")
        
    except Exception as e:
        logger.error(LogCategory.SYSTEM, "manual_fee_calc_error", f"Error during manual fee calculation: {str(e)}", error=str(e))
        print(f"\nError during fee calculation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()