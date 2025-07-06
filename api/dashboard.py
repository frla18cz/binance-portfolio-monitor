"""
Dashboard API for Binance Portfolio Monitor.
Provides real-time data and controls for the web dashboard.
"""

import json
import os
from datetime import datetime, UTC, timedelta
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from .logger import get_logger, LogCategory
from .index import process_all_accounts, supabase, get_prices


def get_historical_prices(start_time, end_time):
    """Získá historické ceny BTC a ETH z price_history tabulky nebo z Binance API."""
    try:
        # Pokusit se získat z price_history tabulky
        result = supabase.table('price_history').select('*').gte('timestamp', start_time).lte('timestamp', end_time).order('timestamp').execute()
        
        if result.data:
            # Uspořádat ceny podle času
            prices_by_time = {}
            for record in result.data:
                timestamp = record['timestamp']
                if timestamp not in prices_by_time:
                    prices_by_time[timestamp] = {}
                prices_by_time[timestamp][record['asset']] = record['price']
            return prices_by_time
        else:
            # Fallback: použít current prices pro všechny timestamp (jednoduchá implementace)
            return None
            
    except Exception as e:
        print(f"Error getting historical prices: {e}")
        return None


def calculate_dynamic_benchmark(nav_data, allocation={'BTC': 0.5, 'ETH': 0.5}, rebalance_frequency='weekly'):
    """
    Vypočítá dynamický benchmark na základě NAV historie.
    
    Args:
        nav_data: List of nav_history records
        allocation: Dict s alokačními váhami {'BTC': 0.5, 'ETH': 0.5}
        rebalance_frequency: 'weekly', 'monthly', 'never'
    
    Returns:
        List of benchmark values corresponding to nav_data timestamps
    """
    if not nav_data:
        return []
    
    try:
        # Získat historické ceny pro celé období
        start_time = nav_data[0]['timestamp']
        end_time = nav_data[-1]['timestamp']
        
        # Všechny záznamy musí mít historické ceny (clean start approach)
        if not nav_data:
            return []
            
        # Ověřit že všechny záznamy mají ceny
        missing_prices = [item for item in nav_data if 'btc_price' not in item or 'eth_price' not in item]
        if missing_prices:
            print(f"Warning: {len(missing_prices)} records missing price data, using old benchmark values")
            return [float(item['benchmark_value']) for item in nav_data]
        
        # Začínáme s NAV z prvního záznamu
        initial_nav = float(nav_data[0]['nav'])
        
        # Virtuální nákup podle alokace s cenami z prvního záznamu
        btc_allocation = allocation.get('BTC', 0.5)
        eth_allocation = allocation.get('ETH', 0.5)
        
        initial_btc_value = initial_nav * btc_allocation
        initial_eth_value = initial_nav * eth_allocation
        
        # Ceny z prvního záznamu období
        first_btc_price = float(nav_data[0]['btc_price'])
        first_eth_price = float(nav_data[0]['eth_price'])
        
        btc_units = initial_btc_value / first_btc_price if first_btc_price > 0 else 0
        eth_units = initial_eth_value / first_eth_price if first_eth_price > 0 else 0
        
        benchmark_values = []
        last_rebalance_week = None
        
        for i, record in enumerate(nav_data):
            # Ceny z aktuálního záznamu (skutečné historické ceny)
            current_btc_price = float(record['btc_price'])
            current_eth_price = float(record['eth_price'])
            
            current_benchmark_value = (btc_units * current_btc_price) + (eth_units * current_eth_price)
            
            # Rebalancing logika (jednou týdně v pondělí)
            if rebalance_frequency == 'weekly':
                record_time = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
                week_number = record_time.isocalendar()[1]  # ISO week number
                
                if last_rebalance_week is None or week_number != last_rebalance_week:
                    # Rebalancovat pokud je pondělí nebo první záznam
                    if record_time.weekday() == 0 or i == 0:  # 0 = pondělí
                        total_value = current_benchmark_value
                        btc_units = (total_value * btc_allocation) / current_btc_price if current_btc_price > 0 else 0
                        eth_units = (total_value * eth_allocation) / current_eth_price if current_eth_price > 0 else 0
                        last_rebalance_week = week_number
                        
                        current_benchmark_value = (btc_units * current_btc_price) + (eth_units * current_eth_price)
            
            benchmark_values.append(current_benchmark_value)
        
        return benchmark_values
        
    except Exception as e:
        print(f"Error calculating dynamic benchmark: {e}")
        # Fallback na původní benchmark hodnoty
        return [float(item['benchmark_value']) for item in nav_data]


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
            elif path == '/api/dashboard/chart-data':
                self._handle_chart_data(query_params)
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
    
    def _handle_chart_data(self, query_params):
        """Get NAV history data for chart with period filtering."""
        logger = get_logger()
        
        # Parse query parameters
        period = query_params.get('period', ['inception'])[0]
        account_id = query_params.get('account_id', [None])[0]
        start_date = query_params.get('start_date', [None])[0]
        end_date = query_params.get('end_date', [None])[0]
        
        try:
            # Calculate date range based on period
            now = datetime.now(UTC)
            
            if period == 'inception':
                # Get all data from the beginning
                query = supabase.table('nav_history').select('*').order('timestamp', desc=False)
            elif period == '1w':
                start_time = now - timedelta(weeks=1)
                query = supabase.table('nav_history').select('*').gte('timestamp', start_time.isoformat()).order('timestamp', desc=False)
            elif period == '1m':
                start_time = now - timedelta(days=30)
                query = supabase.table('nav_history').select('*').gte('timestamp', start_time.isoformat()).order('timestamp', desc=False)
            elif period == '1y':
                start_time = now - timedelta(days=365)
                query = supabase.table('nav_history').select('*').gte('timestamp', start_time.isoformat()).order('timestamp', desc=False)
            elif period == 'ytd':
                start_time = datetime(now.year, 1, 1, tzinfo=UTC)
                query = supabase.table('nav_history').select('*').gte('timestamp', start_time.isoformat()).order('timestamp', desc=False)
            elif period == 'custom' and start_date and end_date:
                query = supabase.table('nav_history').select('*').gte('timestamp', start_date).lte('timestamp', end_date).order('timestamp', desc=False)
            else:
                # Default to last 30 days
                start_time = now - timedelta(days=30)
                query = supabase.table('nav_history').select('*').gte('timestamp', start_time.isoformat()).order('timestamp', desc=False)
            
            # Add account filter if specified
            if account_id:
                query = query.eq('account_id', account_id)
            
            # Execute query
            result = query.execute()
            nav_data = result.data
            
            # Vypočítat dynamický benchmark
            dynamic_benchmark_values = calculate_dynamic_benchmark(
                nav_data, 
                allocation={'BTC': 0.5, 'ETH': 0.5}, 
                rebalance_frequency='weekly'
            )
            
            # Format data for Chart.js
            chart_data = {
                "labels": [datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M') for item in nav_data],
                "datasets": [
                    {
                        "label": "Portfolio NAV",
                        "data": [float(item['nav']) for item in nav_data],
                        "borderColor": "#667eea",
                        "backgroundColor": "rgba(102, 126, 234, 0.1)",
                        "tension": 0.4,
                        "pointRadius": 2,
                        "pointHoverRadius": 5,
                        "fill": False
                    },
                    {
                        "label": "50/50 BTC/ETH Benchmark",
                        "data": dynamic_benchmark_values,
                        "borderColor": "#764ba2",
                        "backgroundColor": "rgba(118, 75, 162, 0.1)",
                        "tension": 0.4,
                        "pointRadius": 2,
                        "pointHoverRadius": 5,
                        "fill": False
                    }
                ]
            }
            
            # Calculate performance stats using dynamic benchmark
            stats = {}
            if nav_data and dynamic_benchmark_values:
                first_nav = float(nav_data[0]['nav'])
                last_nav = float(nav_data[-1]['nav'])
                first_benchmark = dynamic_benchmark_values[0] if dynamic_benchmark_values else first_nav
                last_benchmark = dynamic_benchmark_values[-1] if dynamic_benchmark_values else first_nav
                
                nav_return = ((last_nav - first_nav) / first_nav * 100) if first_nav != 0 else 0
                benchmark_return = ((last_benchmark - first_benchmark) / first_benchmark * 100) if first_benchmark != 0 else 0
                
                stats = {
                    "period": period,
                    "data_points": len(nav_data),
                    "nav_return_pct": round(nav_return, 2),
                    "benchmark_return_pct": round(benchmark_return, 2),
                    "outperformance_pct": round(nav_return - benchmark_return, 2),
                    "start_date": nav_data[0]['timestamp'] if nav_data else None,
                    "end_date": nav_data[-1]['timestamp'] if nav_data else None,
                    "start_nav": round(first_nav, 2),
                    "end_nav": round(last_nav, 2),
                    "start_benchmark": round(first_benchmark, 2),
                    "end_benchmark": round(last_benchmark, 2)
                }
            
            response_data = {
                "chart_data": chart_data,
                "stats": stats,
                "period": period,
                "timestamp": datetime.now(UTC).isoformat()
            }
            
            logger.debug(LogCategory.SYSTEM, "dashboard_chart_data", 
                        f"Chart data requested for period: {period}, data points: {len(nav_data)}")
            
            self._send_json_response(response_data)
            
        except Exception as e:
            logger.error(LogCategory.SYSTEM, "chart_data_error", f"Failed to fetch chart data: {str(e)}", error=str(e))
            self._send_error(500, f"Failed to fetch chart data: {str(e)}")
    
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
    # Fix relative imports when running standalone
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    
    # Re-import with fixed paths
    from api.logger import get_logger, LogCategory
    from api.index import process_all_accounts, supabase, get_prices
    
    # Test the dashboard API locally
    from http.server import HTTPServer
    
    print("🟢 Starting Dashboard in LIVE MODE")
    print("=" * 50)
    print("Dashboard URL: http://localhost:8001/dashboard")
    print("API Status: http://localhost:8001/api/dashboard/status")
    print("API Logs: http://localhost:8001/api/dashboard/logs")
    print("API Metrics: http://localhost:8001/api/dashboard/metrics")
    print("API Chart Data: http://localhost:8001/api/dashboard/chart-data")
    print("=" * 50)

    server = HTTPServer(('localhost', 8001), DashboardHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Dashboard server stopped")
        server.shutdown()