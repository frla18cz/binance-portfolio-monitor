from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            "status": "ok",
            "message": "Vercel Python function is working",
            "timestamp": "2025-07-13"
        }
        
        self.wfile.write(json.dumps(response, indent=2).encode('utf-8'))
        return