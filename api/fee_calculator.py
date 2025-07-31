"""
Fee Calculator Module
Handles monthly fee calculations and accruals for investor accounts.
"""

import os
import sys
from datetime import datetime, UTC, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from api.logger import get_logger, LogCategory, OperationTimer
from utils.database_manager import get_supabase_client


class FeeCalculator:
    """Handles fee calculations and accruals."""
    
    def __init__(self):
        self.logger = get_logger()
        self.db = get_supabase_client()
        # Load from settings
        from config import settings
        self.settings = settings
        # Keep backward compatibility with config attribute
        self.config = settings.fee_management
        self.default_performance_fee_rate = Decimal(str(self.config.default_performance_fee_rate))
    
    def should_calculate_fees(self):
        """Check if fees should be calculated based on schedule."""
        now = datetime.now(UTC)
        
        # Get dynamic configuration
        test_mode = self.settings.get_dynamic('fee_management.test_mode', default=self.config.test_mode)
        if test_mode.get('enabled', False):
            # In test mode, always return True (manual control)
            return True
        
        # Get schedule configuration dynamically
        calculation_schedule = self.settings.get_dynamic(
            'fee_management.calculation_schedule', 
            default=self.config.calculation_schedule
        )
        calculation_day = self.settings.get_dynamic(
            'fee_management.calculation_day',
            default=self.config.calculation_day
        )
        calculation_hour = self.settings.get_dynamic(
            'fee_management.calculation_hour',
            default=self.config.calculation_hour
        )
        
        # Check if it's the scheduled day and hour
        if calculation_schedule == "monthly":
            return (now.day == calculation_day and 
                   now.hour == calculation_hour)
        elif calculation_schedule == "daily":
            return now.hour == calculation_hour
        elif calculation_schedule == "hourly":
            return True  # Calculate every hour
        
        return False
    
    def get_calculation_period(self, reference_date=None):
        """Get the period to calculate based on schedule."""
        # Get schedule configuration dynamically
        calculation_schedule = self.settings.get_dynamic(
            'fee_management.calculation_schedule', 
            default=self.config.calculation_schedule
        )
        if reference_date is None:
            reference_date = datetime.now(UTC).date()
        
        if calculation_schedule == "monthly":
            # Previous month
            return (reference_date.replace(day=1) - timedelta(days=1)).replace(day=1)
        elif calculation_schedule == "daily":
            # Previous day
            return reference_date - timedelta(days=1)
        elif calculation_schedule == "hourly":
            # Current month up to now
            return reference_date.replace(day=1)
        
        return reference_date.replace(day=1)
    
    def calculate_fees_for_all_accounts(self, month_date=None):
        """
        Calculate fees for all accounts for a given month.
        If month_date is None, calculates based on schedule configuration.
        """
        if month_date is None:
            month_date = self.get_calculation_period()
        
        self.logger.info(LogCategory.SYSTEM, "fee_calculation_start", 
                        f"Starting fee calculation for month: {month_date.strftime('%Y-%m')}")
        
        # Get all active accounts
        try:
            accounts = self.db.table('binance_accounts').select('id, account_name').execute()
            
            if not accounts.data:
                self.logger.warning(LogCategory.SYSTEM, "no_accounts", 
                                  "No accounts found for fee calculation")
                return
            
            success_count = 0
            error_count = 0
            
            for account in accounts.data:
                account_id = account['id']
                account_name = account['account_name']
                
                try:
                    self._calculate_account_fees(account_id, account_name, month_date)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    self.logger.error(LogCategory.SYSTEM, "account_fee_error",
                                    f"Error calculating fees for {account_name}: {str(e)}",
                                    account_id=account_id, error=str(e))
            
            self.logger.info(LogCategory.SYSTEM, "fee_calculation_complete",
                           f"Fee calculation complete. Success: {success_count}, Errors: {error_count}")
                           
        except Exception as e:
            self.logger.error(LogCategory.SYSTEM, "fee_calculation_error",
                            f"Fatal error in fee calculation: {str(e)}", error=str(e))
            raise
    
    def _calculate_account_fees(self, account_id, account_name, month_date):
        """Calculate fees for a single account."""
        
        with OperationTimer(self.logger, LogCategory.SYSTEM, "calculate_account_fees", 
                          account_id, account_name):
            
            # Check if fees already calculated for this period
            existing = self.db.table('fee_tracking').select('id, status').eq(
                'account_id', account_id
            ).eq('period_start', month_date).execute()
            
            if existing.data:
                self.logger.info(LogCategory.SYSTEM, "fees_already_calculated",
                               f"Fees already calculated for {account_name} for {month_date}",
                               account_id=account_id, status=existing.data[0]['status'])
                return
            
            # Get account's fee rate
            account_data = self.db.table('binance_accounts').select('performance_fee_rate').eq(
                'id', account_id
            ).single().execute()
            
            fee_rate = None
            if account_data.data and account_data.data.get('performance_fee_rate'):
                fee_rate = float(account_data.data['performance_fee_rate'])
            
            # Call the SQL function to calculate fees
            params = {
                'p_account_id': account_id,
                'p_month': month_date.isoformat()
            }
            if fee_rate is not None:
                params['p_fee_rate'] = fee_rate
                
            result = self.db.rpc('calculate_monthly_fees', params).execute()
            
            if not result.data or len(result.data) == 0:
                self.logger.warning(LogCategory.SYSTEM, "no_fee_data",
                                  f"No data returned from fee calculation for {account_name}",
                                  account_id=account_id)
                return
            
            fee_data = result.data[0]
            
            # Prepare fee tracking record
            fee_record = {
                'account_id': account_id,
                'period_start': fee_data['period_start'],
                'period_end': fee_data['period_end'],
                'avg_nav': float(fee_data.get('avg_nav') or 0),
                'starting_nav': float(fee_data.get('starting_nav') or 0),
                'ending_nav': float(fee_data.get('ending_nav') or 0),
                'starting_hwm': float(fee_data.get('starting_hwm') or 0),
                'ending_hwm': float(fee_data.get('ending_hwm') or 0),
                'portfolio_twr': float(fee_data.get('portfolio_twr') or 0),
                'benchmark_twr': float(fee_data.get('benchmark_twr') or 0),
                'alpha_pct': float(fee_data.get('alpha_twr') or 0),
                'performance_fee': float(fee_data.get('performance_fee') or 0),
                'status': 'ACCRUED'
            }
            
            # Insert fee record
            insert_result = self.db.table('fee_tracking').insert(fee_record).execute()
            
            if insert_result.data:
                self.logger.info(LogCategory.SYSTEM, "fees_calculated",
                               f"Fees calculated for {account_name}: "
                               f"Performance fee: ${fee_record['performance_fee']:.2f}",
                               account_id=account_id,
                               data={
                                   'month': month_date.isoformat(),
                                   'alpha': fee_record['alpha_pct'],
                                   'ending_nav': fee_record['ending_nav'],
                                   'ending_hwm': fee_record['ending_hwm'],
                                   'performance_fee': fee_record['performance_fee']
                               })
    
    def mark_fee_as_collected(self, account_id, period_start, withdrawal_tx_id):
        """
        Mark a fee as collected when it's actually withdrawn.
        This should be called when processing a FEE_WITHDRAWAL transaction.
        """
        try:
            update_result = self.db.table('fee_tracking').update({
                'status': 'COLLECTED',
                'collected_at': datetime.now(UTC).isoformat(),
                'collection_tx_id': withdrawal_tx_id
            }).eq('account_id', account_id).eq('period_start', period_start).execute()
            
            if update_result.data:
                self.logger.info(LogCategory.SYSTEM, "fee_marked_collected",
                               f"Fee marked as collected for period {period_start}",
                               account_id=account_id, 
                               data={'period': period_start, 'tx_id': withdrawal_tx_id})
                return True
            else:
                self.logger.warning(LogCategory.SYSTEM, "fee_not_found",
                                  f"No fee record found for period {period_start}",
                                  account_id=account_id)
                return False
                
        except Exception as e:
            self.logger.error(LogCategory.SYSTEM, "mark_collected_error",
                            f"Error marking fee as collected: {str(e)}",
                            account_id=account_id, error=str(e))
            return False
    
    def get_pending_fees(self, account_id=None):
        """Get all pending (ACCRUED) fees, optionally filtered by account."""
        query = self.db.table('fee_tracking').select('*').eq('status', 'ACCRUED')
        
        if account_id:
            query = query.eq('account_id', account_id)
        
        result = query.order('period_start', desc=True).execute()
        return result.data if result.data else []
    
    def get_fee_summary(self, account_id, start_date=None, end_date=None):
        """Get fee summary for an account over a period."""
        query = self.db.table('fee_tracking').select('*').eq('account_id', account_id)
        
        if start_date:
            query = query.gte('period_start', start_date.isoformat())
        if end_date:
            query = query.lte('period_end', end_date.isoformat())
        
        result = query.order('period_start', desc=True).execute()
        
        if not result.data:
            return {
                'total_performance_fees': 0,
                'collected_fees': 0,
                'pending_fees': 0,
                'periods': []
            }
        
        periods = result.data
        total_perf = sum(p['performance_fee'] for p in periods)
        collected = sum(p['performance_fee'] for p in periods if p['status'] == 'COLLECTED')
        pending = sum(p['performance_fee'] for p in periods if p['status'] == 'ACCRUED')
        
        return {
            'total_performance_fees': total_perf,
            'collected_fees': collected,
            'pending_fees': pending,
            'periods': periods
        }


# CLI interface for manual execution
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Calculate monthly fees')
    parser.add_argument('--month', type=str, help='Month to calculate (YYYY-MM format)')
    parser.add_argument('--account', type=str, help='Specific account ID (optional)')
    
    args = parser.parse_args()
    
    calculator = FeeCalculator()
    
    # Parse month if provided
    month_date = None
    if args.month:
        try:
            month_date = datetime.strptime(args.month + '-01', '%Y-%m-%d').date()
        except ValueError:
            print(f"Invalid month format: {args.month}. Use YYYY-MM format.")
            sys.exit(1)
    
    # Run calculation
    if args.account:
        # Get account name
        account_result = calculator.db.table('binance_accounts').select('account_name').eq('id', args.account).single().execute()
        if account_result.data:
            account_name = account_result.data['account_name']
            print(f"Calculating fees for account: {account_name}")
            calculator._calculate_account_fees(args.account, account_name, month_date or datetime.now(UTC).date().replace(day=1))
        else:
            print(f"Account not found: {args.account}")
    else:
        print(f"Calculating fees for all accounts for month: {month_date or 'previous month'}")
        calculator.calculate_fees_for_all_accounts(month_date)