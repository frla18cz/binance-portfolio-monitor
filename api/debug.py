from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from datetime import datetime, UTC

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Debug endpoint to check system configuration and recent logs."""
        debug_info = {
            'timestamp': datetime.now(UTC).isoformat(),
            'environment': {},
            'recent_errors': [],
            'config_status': {},
            'api_tests': {}
        }
        
        try:
            # Check environment variables
            debug_info['environment'] = {
                'SUPABASE_URL': bool(os.getenv('SUPABASE_URL')),
                'SUPABASE_ANON_KEY': bool(os.getenv('SUPABASE_ANON_KEY')),
                'VERCEL': os.getenv('VERCEL', 'false'),
                'VERCEL_REGION': os.getenv('VERCEL_REGION', 'unknown'),
                'VERCEL_ENV': os.getenv('VERCEL_ENV', 'unknown'),
                'AWS_REGION': os.getenv('AWS_REGION', 'unknown'),
                'AWS_LAMBDA_FUNCTION_NAME': os.getenv('AWS_LAMBDA_FUNCTION_NAME', 'unknown'),
                'TZ': os.getenv('TZ', 'not set')
            }
            
            # Try to import and check configuration
            try:
                sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
                from config import settings
                debug_info['config_status'] = {
                    'loaded': True,
                    'data_api_url': getattr(settings.api.binance, 'data_api_url', 'not set'),
                    'cron_interval': getattr(settings.scheduling, 'cron_interval_minutes', 'not set'),
                    'database_url_set': bool(getattr(settings.database, 'supabase_url', None))
                }
            except Exception as e:
                debug_info['config_status'] = {
                    'loaded': False,
                    'error': str(e)
                }
            
            # Test Binance client setup
            try:
                from binance.client import Client
                client = Client('', '')
                
                # Test regular API
                debug_info['api_tests']['regular_api'] = {
                    'url': client.API_URL,
                    'accessible': 'unknown'
                }
                
                # Test data API
                client.API_URL = 'https://data-api.binance.vision/api'
                debug_info['api_tests']['data_api'] = {
                    'url': client.API_URL,
                    'accessible': 'unknown'
                }
                
                # Quick price test
                try:
                    ticker = client.get_symbol_ticker(symbol='BTCUSDT')
                    debug_info['api_tests']['data_api']['accessible'] = True
                    debug_info['api_tests']['data_api']['btc_price'] = ticker['price']
                except Exception as e:
                    debug_info['api_tests']['data_api']['accessible'] = False
                    debug_info['api_tests']['data_api']['error'] = str(e)[:200]
                    
            except Exception as e:
                debug_info['api_tests']['error'] = str(e)
            
            # Try to get recent errors from database
            try:
                from utils.database_manager import get_supabase_client
                supabase = get_supabase_client()
                
                # Get last 5 errors
                result = supabase.table('system_logs').select('created_at, operation, message').eq('level', 'ERROR').order('created_at', desc=True).limit(5).execute()
                
                debug_info['recent_errors'] = [
                    {
                        'time': log['created_at'],
                        'operation': log['operation'],
                        'message': log['message'][:200] if log['message'] else 'No message'
                    }
                    for log in result.data
                ]
                
                debug_info['database_connected'] = True
                
            except Exception as e:
                debug_info['database_connected'] = False
                debug_info['database_error'] = str(e)[:200]
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            self.wfile.write(json.dumps(debug_info, indent=2).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            error_response = {
                'status': 'error',
                'message': str(e),
                'type': type(e).__name__
            }
            
            self.wfile.write(json.dumps(error_response).encode('utf-8'))