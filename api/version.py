from http.server import BaseHTTPRequestHandler
import json
import datetime

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            "status": "ok",
            "version": "v3-fixed-cron-2025-07-13",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "message": "This is the latest version with MinimalSettings API config fix"
        }
        
        self.wfile.write(json.dumps(response, indent=2).encode('utf-8'))
        return