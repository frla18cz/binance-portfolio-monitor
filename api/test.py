from http.server import BaseHTTPRequestHandler
import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Try importing settings to check configuration
try:
    from config import settings
except:
    # Fallback for Vercel
    class settings:
        api = type('api', (), {
            'binance': type('binance', (), {
                'data_api_url': 'https://data-api.binance.vision/api'
            })()
        })()

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            "status": "ok",
            "message": "Vercel Python function is working",
            "timestamp": "2025-07-13",
            "version": "v2-with-minimal-settings-api-config",
            "has_data_api": hasattr(settings, 'api') and hasattr(settings.api, 'binance') and hasattr(settings.api.binance, 'data_api_url')
        }
        
        self.wfile.write(json.dumps(response, indent=2).encode('utf-8'))
        return