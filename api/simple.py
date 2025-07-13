from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Simple endpoint that just imports and runs monitoring."""
        try:
            # Import monitoring function
            from api.index import process_all_accounts
            
            # Run monitoring
            process_all_accounts()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                "status": "success",
                "message": "Monitoring completed"
            }
            
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            error_response = {
                "status": "error",
                "message": str(e),
                "type": type(e).__name__
            }
            
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
        
        return