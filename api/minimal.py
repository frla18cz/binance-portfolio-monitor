from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime, UTC

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Minimal test endpoint."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            "status": "ok",
            "message": "Minimal handler works",
            "timestamp": datetime.now(UTC).isoformat(),
            "path": self.path
        }
        
        self.wfile.write(json.dumps(response).encode('utf-8'))