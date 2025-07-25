"""
Monthly fee calculation endpoint for cron job.
Runs on the 1st of each month to calculate fees for the previous month.
"""

from http.server import BaseHTTPRequestHandler
from api.fee_calculator import FeeCalculator
from api.logger import get_logger, LogCategory
import json


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        logger = get_logger()
        
        try:
            logger.info(LogCategory.SYSTEM, "fee_calculation_cron", 
                       "Monthly fee calculation cron triggered")
            
            # Initialize fee calculator
            calculator = FeeCalculator()
            
            # Calculate fees for all accounts for previous month
            calculator.calculate_fees_for_all_accounts()
            
            # Get summary of calculated fees
            summary = {
                "status": "success",
                "message": "Monthly fee calculation completed"
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(summary).encode('utf-8'))
            
            logger.info(LogCategory.SYSTEM, "fee_calculation_cron_complete", 
                       "Monthly fee calculation completed successfully")
            
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


# For local testing
if __name__ == "__main__":
    from api.fee_calculator import FeeCalculator
    
    print("Running monthly fee calculation...")
    calculator = FeeCalculator()
    calculator.calculate_fees_for_all_accounts()
    print("Done!")