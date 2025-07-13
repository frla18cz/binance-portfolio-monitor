from http.server import BaseHTTPRequestHandler
import json
import os

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Test database connection."""
        results = {
            'env_vars': {
                'SUPABASE_URL': bool(os.getenv('SUPABASE_URL')),
                'SUPABASE_ANON_KEY': bool(os.getenv('SUPABASE_ANON_KEY'))
            },
            'database_test': {}
        }
        
        try:
            # Test database connection
            from utils.database_manager import get_supabase_client
            supabase = get_supabase_client()
            
            # Try a simple query
            result = supabase.table('binance_accounts').select('count', count='exact').execute()
            
            results['database_test'] = {
                'connected': True,
                'account_count': result.count
            }
            
        except Exception as e:
            results['database_test'] = {
                'connected': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
            
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        self.wfile.write(json.dumps(results, indent=2).encode('utf-8'))