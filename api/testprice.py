from http.server import BaseHTTPRequestHandler
import json
from binance.client import Client

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Test price fetching with forced data API."""
        results = {}
        
        try:
            # Create client with data API
            client = Client('', '')
            client.API_URL = 'https://data-api.binance.vision/api'
            
            # Try to fetch BTC price
            ticker = client.get_symbol_ticker(symbol='BTCUSDT')
            
            results = {
                'status': 'success',
                'api_url': client.API_URL,
                'btc_price': ticker['price'],
                'message': 'Successfully fetched price using data API'
            }
            
        except Exception as e:
            results = {
                'status': 'error',
                'error': str(e),
                'error_type': type(e).__name__,
                'message': 'Failed to fetch price'
            }
            
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        self.wfile.write(json.dumps(results, indent=2).encode('utf-8'))