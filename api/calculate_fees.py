"""
Monthly fee calculation endpoint for cron job.
Runs on the 1st of each month to calculate fees for the previous month.
"""

from http.server import BaseHTTPRequestHandler
from datetime import timedelta
from api.fee_calculator import FeeCalculator
from api.logger import get_logger, LogCategory
import json


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        logger = get_logger()
        
        try:
            # Initialize fee calculator
            calculator = FeeCalculator()
            
            # Check if calculation should run
            should_run = calculator.should_calculate_fees()
            
            logger.info(LogCategory.SYSTEM, "fee_calculation_cron", 
                       f"Fee calculation cron triggered. Should run: {should_run}")
            
            if not should_run and not calculator.config.test_mode.enabled:
                # Not scheduled time
                summary = {
                    "status": "skipped",
                    "message": f"Not scheduled time for {calculator.config.calculation_schedule} calculation",
                    "next_run": self._get_next_run_time(calculator.config)
                }
            else:
                # Calculate fees for all accounts
                calculator.calculate_fees_for_all_accounts()
                
                summary = {
                    "status": "success",
                    "message": f"Fee calculation completed ({calculator.config.calculation_schedule})",
                    "test_mode": calculator.config.test_mode.enabled
                }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(summary).encode('utf-8'))
            
            logger.info(LogCategory.SYSTEM, "fee_calculation_cron_complete", 
                       f"Fee calculation cron completed: {summary['status']}")
            
        except Exception as e:
            logger.error(LogCategory.SYSTEM, "fee_calculation_cron_error", 
                        f"Fee calculation cron failed: {str(e)}", error=str(e))
            
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_response = {
                "status": "error",
                "message": f"Fee calculation failed: {str(e)}"
            }
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
    
    def _get_next_run_time(self, config):
        """Calculate next scheduled run time."""
        from datetime import datetime, UTC
        now = datetime.now(UTC)
        
        if config.calculation_schedule == "monthly":
            # Next month, configured day and hour
            if now.day >= config.calculation_day:
                # Next month
                if now.month == 12:
                    next_run = now.replace(year=now.year + 1, month=1, day=config.calculation_day, 
                                         hour=config.calculation_hour, minute=0, second=0)
                else:
                    next_run = now.replace(month=now.month + 1, day=config.calculation_day,
                                         hour=config.calculation_hour, minute=0, second=0)
            else:
                # This month
                next_run = now.replace(day=config.calculation_day, hour=config.calculation_hour, 
                                     minute=0, second=0)
        elif config.calculation_schedule == "daily":
            # Tomorrow at configured hour
            next_run = (now + timedelta(days=1)).replace(hour=config.calculation_hour, minute=0, second=0)
        else:
            # Next hour
            next_run = (now + timedelta(hours=1)).replace(minute=0, second=0)
        
        return next_run.isoformat()


# For local testing
if __name__ == "__main__":
    from api.fee_calculator import FeeCalculator
    
    print("Running monthly fee calculation...")
    calculator = FeeCalculator()
    calculator.calculate_fees_for_all_accounts()
    print("Done!")