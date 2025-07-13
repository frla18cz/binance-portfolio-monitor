"""
Test endpoint for proxy configuration on Vercel
"""

import os
import json
from http.server import BaseHTTPRequestHandler
from api.index import create_binance_client
from api.logger import get_logger, LogCategory
from config import settings

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        logger = get_logger()
        
        # Collect test information
        test_info = {
            "environment": {
                "VERCEL": os.getenv('VERCEL', 'Not set'),
                "VERCEL_ENV": os.getenv('VERCEL_ENV', 'Not set'),
                "OXYLABS_PROXY_URL": "Set" if os.getenv('OXYLABS_PROXY_URL') else "Not set",
            },
            "proxy_config": {
                "enabled_on_vercel": getattr(settings.proxy, 'enabled_on_vercel', 'N/A'),
                "is_active": getattr(settings.proxy, 'is_active', False) if hasattr(settings, 'proxy') else False,
                "has_url": bool(settings.proxy.url) if hasattr(settings, 'proxy') else False
            },
            "tests": {}
        }
        
        # Test 1: Price client (should use data API)
        try:
            price_client = create_binance_client(for_prices_only=True)
            test_info["tests"]["price_client"] = {
                "success": True,
                "api_url": price_client.API_URL,
                "expected": "https://data-api.binance.vision/api",
                "correct": price_client.API_URL == "https://data-api.binance.vision/api"
            }
        except Exception as e:
            test_info["tests"]["price_client"] = {
                "success": False,
                "error": str(e)
            }
        
        # Test 2: Regular client (should use proxy on Vercel)
        try:
            regular_client = create_binance_client('test', 'test')
            test_info["tests"]["regular_client"] = {
                "success": True,
                "api_url": regular_client.API_URL,
                "has_session": hasattr(regular_client, 'session') and regular_client.session is not None,
                "proxy_applied": hasattr(regular_client.session, 'proxies') if hasattr(regular_client, 'session') else False
            }
            
            # Log proxy status
            if test_info["proxy_config"]["is_active"]:
                logger.info(LogCategory.SYSTEM, "proxy_test", 
                           "Proxy test: Proxy is ACTIVE on Vercel", 
                           data=test_info)
            else:
                logger.info(LogCategory.SYSTEM, "proxy_test", 
                           "Proxy test: Proxy is NOT active", 
                           data=test_info)
                
        except Exception as e:
            test_info["tests"]["regular_client"] = {
                "success": False,
                "error": str(e)
            }
        
        # Test 3: Try fetching BTC price
        try:
            price_client = create_binance_client(for_prices_only=True)
            ticker = price_client.get_symbol_ticker(symbol='BTCUSDT')
            test_info["tests"]["price_fetch"] = {
                "success": True,
                "btc_price": float(ticker['price'])
            }
        except Exception as e:
            test_info["tests"]["price_fetch"] = {
                "success": False,
                "error": str(e)
            }
        
        # Send response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(test_info, indent=2).encode('utf-8'))