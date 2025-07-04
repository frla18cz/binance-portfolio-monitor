"""
Dashboard API for Binance Portfolio Monitor.
Provides real-time data and controls for the web dashboard.
"""

import json
import os
from datetime import datetime, UTC
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from .demo_mode import (
    get_demo_controller, 
    simulate_transaction, 
    simulate_market_scenario,
    get_demo_dashboard_data,
    reset_demo_data
)
from .logger import get_logger, LogCategory
from .index import process_all_accounts


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
            elif path == '/api/dashboard/demo-data':
                self._handle_demo_data()
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
            elif path == '/api/dashboard/simulate-transaction':
                self._handle_simulate_transaction(data)
            elif path == '/api/dashboard/simulate-scenario':
                self._handle_simulate_scenario(data)
            elif path == '/api/dashboard/reset-demo':
                self._handle_reset_demo()
            else:
                self._send_error(404, "Endpoint not found")
                
        except Exception as e:
            logger = get_logger()
            logger.error(LogCategory.SYSTEM, "dashboard_post_error", f"Dashboard POST error: {str(e)}", error=str(e))
            self._send_error(500, f"Internal server error: {str(e)}")
    
    def _handle_status(self):
        """Get system and mode status."""
        logger = get_logger()
        controller = get_demo_controller()
        
        # Get performance metrics
        metrics = logger.get_performance_metrics()
        
        # Get mode status
        mode_status = controller.get_mode_status()
        
        status_data = {
            "mode": mode_status,
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
        controller = get_demo_controller()
        
        # Get logger metrics
        performance_metrics = logger.get_performance_metrics()
        
        # Get demo data if in demo mode
        demo_data = None
        if controller.is_demo_mode():
            demo_data = get_demo_dashboard_data()
        
        # Simulate portfolio data (in real implementation, this would come from database)
        portfolio_data = {
            "account_name": "Demo Trading Account" if controller.is_demo_mode() else "Live Trading Account",
            "current_nav": 13500.00,
            "benchmark_value": 12800.00,
            "initial_balance": 10000.00,
            "total_return": 3500.00,
            "return_percentage": 35.00,
            "vs_benchmark": 700.00,
            "vs_benchmark_pct": 5.47
        }
        
        # Current prices (simulated)
        prices = {
            "btc": 65420.50,
            "eth": 3245.75,
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        metrics_data = {
            "portfolio": portfolio_data,
            "prices": prices,
            "performance": performance_metrics,
            "demo_data": demo_data,
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        logger.debug(LogCategory.SYSTEM, "dashboard_metrics", "Metrics requested")
        self._send_json_response(metrics_data)
    
    def _handle_demo_data(self):
        """Get comprehensive demo mode data."""
        controller = get_demo_controller()
        
        if not controller.is_demo_mode():
            self._send_error(400, "Demo data only available in demo mode")
            return
        
        demo_data = get_demo_dashboard_data()
        self._send_json_response(demo_data)
    
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
    
    def _handle_simulate_transaction(self, data):
        """Handle transaction simulation for demo mode."""
        logger = get_logger()
        
        try:
            transaction_type = data.get('type')
            amount = float(data.get('amount', 0))
            account_id = int(data.get('account_id', 1))
            
            logger.info(LogCategory.DEMO_MODE, "simulate_transaction", 
                       f"Simulating {transaction_type} of ${amount:,.2f}",
                       account_id=account_id, 
                       data={"transaction_type": transaction_type, "amount": amount})
            
            result = simulate_transaction(transaction_type, amount, account_id)
            
            if result.get('success'):
                logger.info(LogCategory.DEMO_MODE, "simulate_transaction_success", 
                           f"Transaction simulation successful: {result.get('transaction_id')}",
                           account_id=account_id, data=result)
            else:
                logger.error(LogCategory.DEMO_MODE, "simulate_transaction_error", 
                            f"Transaction simulation failed: {result.get('error')}",
                            account_id=account_id, error=result.get('error'))
            
            self._send_json_response(result)
            
        except Exception as e:
            logger.error(LogCategory.DEMO_MODE, "simulate_transaction_exception", 
                        f"Transaction simulation exception: {str(e)}", error=str(e))
            self._send_error(500, f"Transaction simulation failed: {str(e)}")
    
    def _handle_simulate_scenario(self, data):
        """Handle market scenario simulation for demo mode."""
        logger = get_logger()
        
        try:
            scenario = data.get('scenario')
            
            logger.info(LogCategory.DEMO_MODE, "simulate_scenario", 
                       f"Simulating market scenario: {scenario}",
                       data={"scenario": scenario})
            
            result = simulate_market_scenario(scenario)
            
            if result.get('success'):
                logger.info(LogCategory.DEMO_MODE, "simulate_scenario_success", 
                           f"Scenario simulation successful: {scenario}",
                           data=result)
            else:
                logger.error(LogCategory.DEMO_MODE, "simulate_scenario_error", 
                            f"Scenario simulation failed: {result.get('error')}",
                            error=result.get('error'))
            
            self._send_json_response(result)
            
        except Exception as e:
            logger.error(LogCategory.DEMO_MODE, "simulate_scenario_exception", 
                        f"Scenario simulation exception: {str(e)}", error=str(e))
            self._send_error(500, f"Scenario simulation failed: {str(e)}")
    
    def _handle_reset_demo(self):
        """Handle demo data reset."""
        logger = get_logger()
        
        try:
            logger.info(LogCategory.DEMO_MODE, "reset_demo", "Resetting demo data from dashboard")
            
            result = reset_demo_data()
            
            if result.get('success'):
                logger.info(LogCategory.DEMO_MODE, "reset_demo_success", "Demo data reset successful")
            else:
                logger.error(LogCategory.DEMO_MODE, "reset_demo_error", 
                            f"Demo data reset failed: {result.get('error')}",
                            error=result.get('error'))
            
            self._send_json_response(result)
            
        except Exception as e:
            logger.error(LogCategory.DEMO_MODE, "reset_demo_exception", 
                        f"Demo reset exception: {str(e)}", error=str(e))
            self._send_error(500, f"Demo reset failed: {str(e)}")
    
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
    import os
    
    # Enable demo mode for testing
    os.environ['DEMO_MODE'] = 'true'
    
    print("🌐 Starting Dashboard Server")
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