from http.server import BaseHTTPRequestHandler
import json
import os
import sys

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Test endpoint to debug settings loading."""
        results = {
            'env_vars': {
                'SUPABASE_URL': bool(os.getenv('SUPABASE_URL')),
                'SUPABASE_ANON_KEY': bool(os.getenv('SUPABASE_ANON_KEY')),
                'VERCEL': os.getenv('VERCEL', 'false')
            },
            'settings_test': {}
        }
        
        try:
            # Add path
            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            
            # Try to import settings
            try:
                from config import settings
                results['settings_test']['import_success'] = True
                results['settings_test']['has_database'] = hasattr(settings, 'database')
                results['settings_test']['has_api'] = hasattr(settings, 'api')
                results['settings_test']['has_financial'] = hasattr(settings, 'financial')
                results['settings_test']['has_scheduling'] = hasattr(settings, 'scheduling')
                results['settings_test']['has_get_supported_symbols'] = hasattr(settings, 'get_supported_symbols')
                results['settings_test']['has_get_supported_stablecoins'] = hasattr(settings, 'get_supported_stablecoins')
                
                # Test data API URL
                if hasattr(settings, 'api') and hasattr(settings.api, 'binance'):
                    results['settings_test']['data_api_url'] = getattr(settings.api.binance, 'data_api_url', 'not set')
                    
            except Exception as e:
                results['settings_test']['import_success'] = False
                results['settings_test']['import_error'] = str(e)
                results['settings_test']['error_type'] = type(e).__name__
                
            # Test MinimalSettings creation
            try:
                class MinimalSettings:
                    class Database:
                        supabase_url = os.getenv('SUPABASE_URL', '')
                        supabase_key = os.getenv('SUPABASE_ANON_KEY', '')
                    class Api:
                        class Binance:
                            data_api_url = 'https://data-api.binance.vision/api'
                            tld = 'com'
                            supported_symbols = ['BTCUSDT', 'ETHUSDT']
                            supported_stablecoins = ['USDT', 'BUSD', 'USDC', 'BNFCR']
                    class Financial:
                        minimum_balance_threshold = 0.00001
                        minimum_usd_value_threshold = 0.1
                    class Scheduling:
                        historical_period_days = 30
                    
                    def get_supported_symbols(self):
                        return self.api.binance.supported_symbols
                        
                    def get_supported_stablecoins(self):
                        return self.api.binance.supported_stablecoins
                        
                minimal = MinimalSettings()
                minimal.database = MinimalSettings.Database()
                minimal.api = MinimalSettings.Api()
                minimal.api.binance = MinimalSettings.Api.Binance()
                minimal.financial = MinimalSettings.Financial()
                minimal.scheduling = MinimalSettings.Scheduling()
                
                results['minimal_settings_test'] = {
                    'creation_success': True,
                    'database_url_set': bool(minimal.database.supabase_url),
                    'database_key_set': bool(minimal.database.supabase_key),
                    'data_api_url': minimal.api.binance.data_api_url
                }
            except Exception as e:
                results['minimal_settings_test'] = {
                    'creation_success': False,
                    'error': str(e)
                }
                
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            self.wfile.write(json.dumps(results, indent=2).encode('utf-8'))
            
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