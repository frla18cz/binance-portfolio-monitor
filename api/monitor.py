"""
Fresh cron endpoint for Binance Portfolio Monitor.
This endpoint bypasses any potential cache issues with the original /api/index endpoint.
"""

import os
import sys
import traceback
from contextlib import nullcontext
from datetime import datetime, timedelta, UTC
from http.server import BaseHTTPRequestHandler
from binance.client import Client as BinanceClient
from api.logger import get_logger, LogCategory, OperationTimer

# Add project root to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Try to load config, fallback to environment variables for Vercel
try:
    from config import settings
except ValueError as e:
    if "SUPABASE_URL" in str(e) or "SUPABASE_ANON_KEY" in str(e):
        # Create minimal settings for Vercel environment
        class MinimalSettings:
            class Database:
                supabase_url = os.getenv('SUPABASE_URL', '')
                supabase_key = os.getenv('SUPABASE_ANON_KEY', '')
        settings = MinimalSettings()
        settings.database = MinimalSettings.Database()
        print(f"Using fallback settings for Vercel: URL={bool(settings.database.supabase_url)}, KEY={bool(settings.database.supabase_key)}")
    else:
        raise

from utils.log_cleanup import run_log_cleanup
from utils.database_manager import get_supabase_client, with_database_retry

# Import main processing logic
from api.index import process_all_accounts

# Global clients
try:
    supabase = get_supabase_client()
except Exception as e:
    print(f"ERROR initializing Supabase client: {str(e)}")
    import traceback
    traceback.print_exc()
    supabase = None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Early error check
        if supabase is None:
            self.send_response(500)
            self.send_header('Content-type','text/plain')
            self.end_headers()
            self.wfile.write('Error: Database connection failed during initialization'.encode('utf-8'))
            return
            
        try:
            logger = get_logger()
            logger.info(LogCategory.SYSTEM, "cron_trigger_new", "NEW cron endpoint triggered - starting monitoring process")
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type','text/plain')
            self.end_headers()
            self.wfile.write(f'Logger initialization error: {str(e)}'.encode('utf-8'))
            return
        
        try:
            with OperationTimer(logger, LogCategory.SYSTEM, "full_monitoring_cycle_new"):
                process_all_accounts()
            
            self.send_response(200)
            self.send_header('Content-type','text/plain')
            self.end_headers()
            self.wfile.write('NEW cron monitoring process completed successfully.'.encode('utf-8'))
            
            logger.info(LogCategory.SYSTEM, "cron_complete_new", "NEW cron monitoring process completed successfully")
            
        except Exception as e:
            logger.error(LogCategory.SYSTEM, "cron_error_new", f"NEW cron process failed: {str(e)}", error=str(e))
            traceback.print_exc()
            
            self.send_response(500)
            self.send_header('Content-type','text/plain')
            self.end_headers()
            self.wfile.write(f'Error: {e}'.encode('utf-8'))
        return