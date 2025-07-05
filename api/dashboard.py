"""
Dashboard API for Binance Portfolio Monitor.
Provides real-time data and controls for the web dashboard.
"""

import json
import os
from datetime import datetime, UTC
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from .logger import get_logger, LogCategory
from .index import process_all_accounts, supabase, get_prices


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP handler for dashboard API endpoints."""
    
    def do_GET(self):
        """Handle GET requests for dashboard data."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        try:
            if path == '/api/dashboard/status':
                self._handle_status()
            elif path == '/api/dashboard/logs':
                self._handle_logs(query_params)
            elif path == '/api/dashboard/metrics':
                self._handle_metrics()
            elif path == '/dashboard':
                self._serve_dashboard()
            else:
                self._send_error(404, "Endpoint not found")
                
        except Exception as e:
            logger = get_logger()
            logger.error(LogCategory.SYSTEM, "dashboard_error", f"Dashboard API error: {str(e)}", error=str(e))
            self._send_error(500, f"Internal server error: {str(e)}")
    
    def do_POST(self):
        """Handle POST requests for dashboard actions."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(post_data) if post_data else {}
            
            if path == '/api/dashboard/run-monitoring':
                self._handle_run_monitoring()
            else:
                self._send_error(404, "Endpoint not found")
                
        except Exception as e:
            logger = get_logger()
            logger.error(LogCategory.SYSTEM, "dashboard_post_error", f"Dashboard POST error: {str(e)}", error=str(e))
            self._send_error(500, f"Internal server error: {str(e)}")
    
    def _handle_status(self):
        """Get system and mode status."""
        logger = get_logger()
        
        # Get performance metrics
        metrics = logger.get_performance_metrics()
        
        status_data = {
            "mode": "LIVE",
            "system": {
                "monitoring_active": True,
                "last_run": datetime.now(UTC).isoformat(),
                "database_connected": True,
                "api_connected": True
            },
            "performance": metrics,
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        logger.debug(LogCategory.SYSTEM, "dashboard_status", "Dashboard status requested")
        self._send_json_response(status_data)
    
    def _handle_logs(self, query_params):
        """Get recent logs with optional filtering."""
        logger = get_logger()
        
        # Parse query parameters
        limit = int(query_params.get('limit', [100])[0])
        category = query_params.get('category', [None])[0]
        account_id = query_params.get('account_id', [None])[0]
        level = query_params.get('level', [None])[0]
        
        if account_id:
            account_id = int(account_id)
        
        # Get logs
        if level == 'ERROR':
            logs = logger.get_error_logs(24)  # Last 24 hours of errors
        else:
            logs = logger.get_recent_logs(limit, category, account_id)
        
        # Filter by level if specified
        if level and level != 'ERROR':
            logs = [log for log in logs if log.get('level') == level]
        
        logger.debug(LogCategory.SYSTEM, "dashboard_logs", 
                    f"Logs requested: {len(logs)} entries", 
                    data={"limit": limit, "category": category, "account_id": account_id, "level": level})
        
        self._send_json_response({
            "logs": logs,
            "total_count": len(logs),
            "filters": {
                "limit": limit,
                "category": category,
                "account_id": account_id,
                "level": level
            },
            "timestamp": datetime.now(UTC).isoformat()
        })
    
    def _handle_metrics(self):
        """Get comprehensive metrics and performance data."""
        logger = get_logger()
        
        # Get logger metrics
        performance_metrics = logger.get_performance_metrics()
        
        # Get portfolio data and prices
        portfolio_data = {}
        prices = {}

        # Fetch real data
        try:
            # Fetch latest NAV history for the first account
            latest_nav_history = supabase.table('nav_history').select('*').order('timestamp', desc=True).limit(1).execute()
            if latest_nav_history.data:
                latest_data = latest_nav_history.data[0]
                portfolio_data = {
                    "account_name": "Live Trading Account",
                    "current_nav": float(latest_data.get("nav", 0)),
                    "benchmark_value": float(latest_data.get("benchmark_value", 0)),
                    "initial_balance": 0.0, 
                    "total_return": 0.0,
                    "return_percentage": 0.0,
                    "vs_benchmark": float(latest_data.get("nav", 0)) - float(latest_data.get("benchmark_value", 0)),
                    "vs_benchmark_pct": (float(latest_data.get("nav", 0)) - float(latest_data.get("benchmark_value", 0))) / float(latest_data.get("benchmark_value", 0)) * 100 if float(latest_data.get("benchmark_value", 0)) != 0 else 0
                }
                # Fetch account name from binance_accounts
                account_info = supabase.table('binance_accounts').select('account_name').eq('id', latest_data.get('account_id')).limit(1).execute()
                if account_info.data:
                    portfolio_data["account_name"] = account_info.data[0]["account_name"]

            # Fetch real-time prices from a dummy client (we just need the get_prices function)
            from binance.client import Client as BinanceClient
            # Create a temporary client just for price fetching (public API)
            temp_client = BinanceClient('', '')  # Empty keys for public endpoints
            real_prices = get_prices(temp_client, logger)
            if real_prices:
                prices = {
                    "btc": real_prices.get("BTCUSDT", 0.0),
                    "eth": real_prices.get("ETHUSDT", 0.0),
                    "timestamp": datetime.now(UTC).isoformat()
                }
        except Exception as e:
            logger.error(LogCategory.SYSTEM, "dashboard_live_data_error", f"Failed to fetch live data for dashboard: {str(e)}", error=str(e))
            # Fallback to default or empty data if fetching fails
            portfolio_data = {
                "account_name": "Live Trading Account (Error)",
                "current_nav": 0.0, "benchmark_value": 0.0, "initial_balance": 0.0,
                "total_return": 0.0, "return_percentage": 0.0, "vs_benchmark": 0.0, "vs_benchmark_pct": 0.0
            }
            prices = {"btc": 0.0, "eth": 0.0, "timestamp": datetime.now(UTC).isoformat()}
        
        metrics_data = {
            "portfolio": portfolio_data,
            "prices": prices,
            "performance": performance_metrics,
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        logger.debug(LogCategory.SYSTEM, "dashboard_metrics", "Metrics requested")
        self._send_json_response(metrics_data)
    
    
    def _handle_run_monitoring(self):
        """Trigger the monitoring process."""
        logger = get_logger()
        
        try:
            logger.info(LogCategory.SYSTEM, "manual_trigger", "Manual monitoring trigger from dashboard")
            
            # Run the monitoring process
            process_all_accounts()
            
            response_data = {
                "success": True,
                "message": "Monitoring process completed successfully",
                "timestamp": datetime.now(UTC).isoformat()
            }
            
            logger.info(LogCategory.SYSTEM, "manual_complete", "Manual monitoring completed successfully")
            self._send_json_response(response_data)
            
        except Exception as e:
            logger.error(LogCategory.SYSTEM, "manual_error", f"Manual monitoring failed: {str(e)}", error=str(e))
            self._send_error(500, f"Monitoring failed: {str(e)}")
    
    
    
    
    def _serve_dashboard(self):
        """Serve the dashboard HTML file."""
        try:
            dashboard_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dashboard.html')
            
            with open(dashboard_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Content-length', str(len(content.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
            
        except FileNotFoundError:
            self._send_error(404, "Dashboard file not found")
        except Exception as e:
            self._send_error(500, f"Error serving dashboard: {str(e)}")
    
    def _send_json_response(self, data):
        """Send JSON response."""
        json_data = json.dumps(data, indent=2)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-length', str(len(json_data.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(json_data.encode('utf-8'))
    
    def _send_error(self, code, message):
        """Send error response."""
        error_data = {
            "error": True,
            "code": code,
            "message": message,
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        json_data = json.dumps(error_data, indent=2)
        
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-length', str(len(json_data.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(json_data.encode('utf-8'))


# For Vercel deployment
def handler(request):
    """Vercel serverless function handler."""
    # This would need to be adapted for Vercel's request/response format
    # For now, this is a placeholder
    pass


if __name__ == "__main__":
    # Test the dashboard API locally
    from http.server import HTTPServer
    
    print("🟢 Starting Dashboard in LIVE MODE")
    print("=" * 50)
    print("Dashboard URL: http://localhost:8000/dashboard")
    print("API Status: http://localhost:8000/api/dashboard/status")
    print("API Logs: http://localhost:8000/api/dashboard/logs")
    print("API Metrics: http://localhost:8000/api/dashboard/metrics")
    print("=" * 50)

    server = HTTPServer(('localhost', 8000), DashboardHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Dashboard server stopped")
        server.shutdown()