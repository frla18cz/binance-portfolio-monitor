from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Simple test to check if handler works."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {"status": "ok", "message": "Handler is working"}
        self.wfile.write(json.dumps(response).encode('utf-8'))