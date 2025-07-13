from http.server import BaseHTTPRequestHandler
import json
from binance.client import Client

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Test endpoint to verify data API functionality."""
        results = {}
        
        try:
            # Test 1: Regular API
            client = Client('', '')
            try:
                ticker = client.get_symbol_ticker(symbol='BTCUSDT')
                results['regular_api'] = {
                    'status': 'success',
                    'price': ticker['price'],
                    'url': client.API_URL
                }
            except Exception as e:
                results['regular_api'] = {
                    'status': 'error',
                    'error': str(e),
                    'url': client.API_URL
                }
            
            # Test 2: Data API
            client.API_URL = 'https://data-api.binance.vision/api'
            try:
                ticker = client.get_symbol_ticker(symbol='BTCUSDT')
                results['data_api'] = {
                    'status': 'success',
                    'price': ticker['price'],
                    'url': client.API_URL
                }
            except Exception as e:
                results['data_api'] = {
                    'status': 'error',
                    'error': str(e),
                    'url': client.API_URL
                }
            
            # Test 3: Check settings
            try:
                import sys
                import os
                sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
                from config import settings
                results['settings'] = {
                    'data_api_url': getattr(settings.api.binance, 'data_api_url', 'not set'),
                    'tld': getattr(settings.api.binance, 'tld', 'not set')
                }
            except Exception as e:
                results['settings'] = {
                    'error': str(e)
                }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                'status': 'success',
                'tests': results,
                'summary': {
                    'regular_api_works': results.get('regular_api', {}).get('status') == 'success',
                    'data_api_works': results.get('data_api', {}).get('status') == 'success'
                }
            }
            
            self.wfile.write(json.dumps(response, indent=2).encode('utf-8'))
            
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