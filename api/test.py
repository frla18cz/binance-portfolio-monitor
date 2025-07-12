"""Simple test endpoint for Vercel deployment debugging."""
import os
import json
import sys
from http.server import BaseHTTPRequestHandler

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Test endpoint including data API test."""
        response = {
            'status': 'ok',
            'message': 'Test endpoint working',
            'environment': {
                'VERCEL_ENV': os.getenv('VERCEL_ENV', 'not_set'),
                'SUPABASE_URL': 'configured' if os.getenv('SUPABASE_URL') else 'missing',
                'SUPABASE_ANON_KEY': 'configured' if os.getenv('SUPABASE_ANON_KEY') else 'missing',
                'PYTHONPATH': os.getenv('PYTHONPATH', 'not_set'),
                'PWD': os.getenv('PWD', 'not_set'),
                'NODE_ENV': os.getenv('NODE_ENV', 'not_set')
            }
        }
        
        # Test data API directly
        try:
            from binance.client import Client as BinanceClient
            client = BinanceClient('', '')
            client.API_URL = 'https://data-api.binance.vision/api'
            ticker = client.get_symbol_ticker(symbol='BTCUSDT')
            response["data_api_test"] = f"SUCCESS: BTC=${float(ticker['price']):,.2f}"
        except Exception as e:
            response["data_api_test"] = f"FAILED: {str(e)}"
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response, indent=2).encode('utf-8'))