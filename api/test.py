"""Simple test endpoint for Vercel deployment debugging."""
import os
import json
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Simple test endpoint that doesn't require any dependencies."""
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
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response, indent=2).encode('utf-8'))