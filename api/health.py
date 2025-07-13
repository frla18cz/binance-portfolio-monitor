"""Health check endpoint for API monitoring."""
from http.server import BaseHTTPRequestHandler
import json
import os
from datetime import datetime, UTC

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Simple health check that always returns 200 OK."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "region": os.getenv('VERCEL_REGION', 'unknown'),
            "version": "1.0.1",
            "message": "API handler fixes deployed"
        }
        
        self.wfile.write(json.dumps(response).encode('utf-8'))