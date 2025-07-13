"""
Vercel-native cron handler for Binance Portfolio Monitor.
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def handler(request, response):
    """Handle cron trigger from Vercel."""
    try:
        # Import here to ensure proper path setup
        from api.index import process_all_accounts
        from api.logger import get_logger, LogCategory
        
        logger = get_logger()
        logger.info(LogCategory.SYSTEM, "vercel_cron_trigger", "Vercel native cron handler triggered")
        
        # Run the monitoring process
        process_all_accounts()
        
        response.status_code = 200
        return {"status": "success", "message": "Monitoring completed"}
        
    except Exception as e:
        import traceback
        error_msg = f"Cron handler error: {str(e)}\n{traceback.format_exc()}"
        
        # Try to log if possible
        try:
            from api.logger import get_logger, LogCategory
            logger = get_logger()
            logger.error(LogCategory.SYSTEM, "vercel_cron_error", error_msg)
        except:
            pass
            
        response.status_code = 500
        return {"status": "error", "message": str(e)}