
"""
Dashboard API for Binance Portfolio Monitor.
Provides real-time data and controls for the web dashboard.
"""

import json
import os
import sys
from datetime import datetime, UTC, timedelta
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import traceback

# Add project root to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import settings

try:
    from .logger import get_logger, LogCategory
    from .index import process_all_accounts, supabase, get_prices
except ImportError:
    from api.logger import get_logger, LogCategory
    from api.index import process_all_accounts, supabase, get_prices


# Note: Dynamic benchmark calculation removed - now using stored DB values for consistency


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP handler for dashboard API endpoints."""
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        logger = get_logger()
        logger.info(LogCategory.SYSTEM, "request_received", f"GET request for {path} with params {query_params}")
        
        try:
            if path == '/api/dashboard' or path == '/api/dashboard/':
                self._serve_dashboard()
            elif path == '/api/dashboard/status':
                self._handle_status()
            elif path == '/api/dashboard/logs':
                self._handle_logs(query_params)
            elif path == '/api/dashboard/system-status':
                self._handle_system_status(query_params)
            elif path == '/api/dashboard/metrics':
                self._handle_metrics(query_params)
            elif path == '/api/dashboard/chart-data':
                self._handle_chart_data(query_params)
            elif path == '/dashboard':
                self._serve_dashboard()
            else:
                self._send_error(404, "Endpoint not found")
                
        except Exception as e:
            logger.error(LogCategory.SYSTEM, "dashboard_error", f"Dashboard API error on path {path}: {str(e)}", error=str(e))
            traceback.print_exc()
            self._send_error(500, f"Internal server error: {str(e)}")
    
    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        logger = get_logger()
        logger.info(LogCategory.SYSTEM, "request_received", f"POST request for {path}")
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(post_data) if post_data else {}
            
            if path == '/api/dashboard/run-monitoring':
                self._handle_run_monitoring()
            else:
                self._send_error(404, "Endpoint not found")
                
        except Exception as e:
            logger.error(LogCategory.SYSTEM, "dashboard_post_error", f"Dashboard POST error on path {path}: {str(e)}", error=str(e))
            traceback.print_exc()
            self._send_error(500, f"Internal server error: {str(e)}")

    def _handle_status(self):
        self._send_json_response({"status": "ok"})

    def _handle_logs(self, query_params):
        logger = get_logger()
        try:
            # Get recent logs from database (correct table name is 'system_logs')
            logs_query = supabase.table('system_logs').select('*').order('timestamp', desc=True).limit(100)
            logs_result = logs_query.execute()
            
            logs = []
            if logs_result.data:
                for log_entry in logs_result.data:
                    logs.append({
                        "timestamp": log_entry.get('timestamp'),
                        "level": log_entry.get('level', 'INFO'),
                        "category": log_entry.get('category', 'SYSTEM'),
                        "event": log_entry.get('operation', ''),  # Map 'operation' to 'event'
                        "message": log_entry.get('message', ''),
                        "account_id": log_entry.get('account_id'),
                        "account_name": log_entry.get('account_name', '')
                    })
            
            self._send_json_response({"logs": logs})
        except Exception as e:
            logger.error(LogCategory.SYSTEM, "logs_fetch_error", f"Failed to fetch logs: {str(e)}", error=str(e))
            # Return empty logs with error info instead of failing completely
            self._send_json_response({"logs": [], "error": str(e)})

    def _handle_metrics(self, query_params):
        logger = get_logger()
        account_id = query_params.get('account_id', [None])[0]
        logger.debug(LogCategory.SYSTEM, "metrics_start", f"Handling metrics for account_id: {account_id}")

        portfolio_data = {}
        prices = {}
        all_accounts = []

        try:
            accounts_response = supabase.table('binance_accounts').select('id, account_name').execute()
            if accounts_response.data:
                all_accounts = accounts_response.data
            else:
                logger.warning(LogCategory.SYSTEM, "no_accounts_found", "No accounts in DB for metrics.")

            if not account_id and all_accounts:
                account_id = all_accounts[0]['id']
                logger.debug(LogCategory.SYSTEM, "metrics_first_account", f"No account_id provided, using first found: {account_id}")

            if account_id:
                nav_query = supabase.table('nav_history').select('*').eq('account_id', account_id).order('timestamp', desc=False)
                nav_history = nav_query.execute()

                if nav_history.data:
                    nav_data = nav_history.data
                    latest_data = nav_data[-1]
                    # Use stored benchmark_value from database instead of dynamic calculation
                    latest_benchmark_value = float(latest_data.get("benchmark_value", 0))
                    
                    account_name = next((acc['account_name'] for acc in all_accounts if acc['id'] == account_id), "Unknown")

                    portfolio_data = {
                        "account_id": account_id,
                        "account_name": account_name,
                        "current_nav": float(latest_data.get("nav", 0)),
                        "benchmark_value": float(latest_benchmark_value),
                        "vs_benchmark": float(latest_data.get("nav", 0)) - float(latest_benchmark_value),
                        "vs_benchmark_pct": (float(latest_data.get("nav", 0)) - float(latest_benchmark_value)) / float(latest_benchmark_value) * 100 if latest_benchmark_value != 0 else 0,
                        "last_updated": latest_data.get("timestamp")
                    }
                else:
                    logger.warning(LogCategory.SYSTEM, "metrics_no_nav", f"No NAV history for account_id: {account_id}")

            # Get latest BTC/ETH prices from database with timestamp
            try:
                price_result = supabase.table('price_history').select('btc_price, eth_price, timestamp').order('timestamp', desc=True).limit(1).execute()
                if price_result.data:
                    latest_prices = price_result.data[0]
                    prices = {
                        "btc": float(latest_prices.get("btc_price", 0.0)), 
                        "eth": float(latest_prices.get("eth_price", 0.0)),
                        "timestamp": latest_prices.get("timestamp"),
                        "source": "database"
                    }
                else:
                    prices = {
                        "btc": 0.0, 
                        "eth": 0.0, 
                        "timestamp": None,
                        "source": "none"
                    }
            except Exception as price_error:
                logger.warning(LogCategory.SYSTEM, "dashboard_price_fallback", f"Could not fetch prices from DB: {str(price_error)}")
                prices = {
                    "btc": 0.0, 
                    "eth": 0.0, 
                    "timestamp": None,
                    "source": "error"
                }

        except Exception as e:
            logger.error(LogCategory.SYSTEM, "dashboard_live_data_error", f"Error fetching metrics: {str(e)}", error=str(e))
            traceback.print_exc()
            portfolio_data = {"account_id": account_id, "account_name": "Error Loading Data"}

        metrics_data = {
            "portfolio": portfolio_data,
            "prices": prices,
            "accounts": all_accounts,
            "timestamp": datetime.now(UTC).isoformat()
        }
        logger.debug(LogCategory.SYSTEM, "dashboard_metrics_success", f"Prepared metrics for account_id: {account_id}")
        self._send_json_response(metrics_data)

    def _handle_chart_data(self, query_params):
        logger = get_logger()
        period = query_params.get('period', ['inception'])[0]
        account_id = query_params.get('account_id', [None])[0]
        logger.debug(LogCategory.SYSTEM, "chart_data_start", f"Chart data for account {account_id}, period {period}")

        try:
            if not account_id:
                first_account = supabase.table('binance_accounts').select('id').limit(1).single().execute()
                if first_account.data:
                    account_id = first_account.data['id']
                else:
                    self._send_json_response({"chart_data": {"labels": [], "datasets": []}, "stats": {}})
                    return

            now = datetime.now(UTC)
            start_time = None
            if period == '1w': start_time = now - timedelta(weeks=1)
            elif period == '1m': start_time = now - timedelta(days=30)
            elif period == '1y': start_time = now - timedelta(days=365)
            elif period == 'ytd': start_time = datetime(now.year, 1, 1, tzinfo=UTC)

            query = supabase.table('nav_history').select('*').eq('account_id', account_id).order('timestamp', desc=False)
            if start_time:
                query = query.gte('timestamp', start_time.isoformat())
            
            result = query.execute()
            nav_data = result.data or []
            
            # Use stored benchmark_value from database instead of dynamic calculation
            stored_benchmark_values = [float(item['benchmark_value']) for item in nav_data]
            
            chart_data = {
                "labels": [item['timestamp'] for item in nav_data],
                "datasets": [
                    {"label": "Portfolio NAV", "data": [float(item['nav']) for item in nav_data]},
                    {"label": "Benchmark", "data": stored_benchmark_values}
                ]
            }
            
            stats = {}
            if nav_data and stored_benchmark_values:
                first_nav = float(nav_data[0]['nav'])
                last_nav = float(nav_data[-1]['nav'])
                first_benchmark = stored_benchmark_values[0]
                last_benchmark = stored_benchmark_values[-1]
                nav_return = ((last_nav - first_nav) / first_nav * 100) if first_nav != 0 else 0
                benchmark_return = ((last_benchmark - first_benchmark) / first_benchmark * 100) if first_benchmark != 0 else 0
                stats = {"nav_return_pct": nav_return, "benchmark_return_pct": benchmark_return}

            self._send_json_response({"chart_data": chart_data, "stats": stats})
        except Exception as e:
            logger.error(LogCategory.SYSTEM, "chart_data_error", f"Failed to fetch chart data: {str(e)}", error=str(e))
            traceback.print_exc()
            self._send_error(500, f"Failed to fetch chart data: {str(e)}")

    def _handle_system_status(self, query_params):
        logger = get_logger()
        try:
            # Check database connection
            db_status = "connected"
            try:
                supabase.table('binance_accounts').select('id').limit(1).execute()
            except Exception:
                db_status = "disconnected"
            
            # Check API status (simplified)
            api_status = "active"
            try:
                from binance.client import Client as BinanceClient
                temp_client = BinanceClient('', '')
                temp_client.API_URL = 'https://data-api.binance.vision/api'
                # Simple ping to check if we can reach Binance
                temp_client.ping()
            except Exception:
                api_status = "inactive"
            
            # Get system stats
            system_stats = {
                "database_status": db_status,
                "api_status": api_status,
                "last_update": datetime.now(UTC).isoformat(),
                "uptime": "Available",
                "version": "1.0.0"
            }
            
            self._send_json_response(system_stats)
        except Exception as e:
            logger.error(LogCategory.SYSTEM, "system_status_error", f"Failed to get system status: {str(e)}", error=str(e))
            self._send_json_response({"error": str(e)})

    def _handle_run_monitoring(self):
        self._send_json_response({"status": "ok"})

    def _serve_dashboard(self):
        try:
            dashboard_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dashboard.html')
            with open(dashboard_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        except Exception as e:
            self._send_error(500, f"Error serving dashboard: {str(e)}")

    def _send_json_response(self, data):
        json_data = json.dumps(data, indent=2)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json_data.encode('utf-8'))

    def _send_error(self, code, message):
        error_data = {"error": True, "code": code, "message": message}
        json_data = json.dumps(error_data, indent=2)
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json_data.encode('utf-8'))

# Export handler for Vercel
handler = DashboardHandler

if __name__ == "__main__":
    from http.server import HTTPServer
    print(f"🟢 Starting Dashboard on http://{settings.dashboard.host}:{settings.dashboard.port}/dashboard")
    server = HTTPServer((settings.dashboard.host, settings.dashboard.port), DashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Dashboard server stopped")
        server.shutdown()
