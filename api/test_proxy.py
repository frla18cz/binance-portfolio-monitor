"""
Enhanced test endpoint for proxy configuration and wallet access on Vercel
"""

import os
import json
import traceback
from http.server import BaseHTTPRequestHandler
from api.index import create_binance_client
from api.logger import get_logger, LogCategory
from config import settings
from utils.database_manager import get_supabase_client

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        logger = get_logger()
        
        # Collect test information
        test_info = {
            "environment": {
                "VERCEL": os.getenv('VERCEL', 'Not set'),
                "VERCEL_ENV": os.getenv('VERCEL_ENV', 'Not set'),
                "VERCEL_REGION": os.getenv('VERCEL_REGION', 'unknown'),
                "OXYLABS_PROXY_URL": "Set" if os.getenv('OXYLABS_PROXY_URL') else "Not set",
            },
            "proxy_config": {
                "enabled_on_vercel": getattr(settings.proxy, 'enabled_on_vercel', 'N/A'),
                "is_active": getattr(settings.proxy, 'is_active', False) if hasattr(settings, 'proxy') else False,
                "has_url": bool(settings.proxy.url) if hasattr(settings, 'proxy') else False,
                "verify_ssl": getattr(settings.proxy, 'verify_ssl', True) if hasattr(settings, 'proxy') else True
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
        
        # Test 3: Try fetching BTC and ETH prices
        try:
            price_client = create_binance_client(for_prices_only=True)
            btc_ticker = price_client.get_symbol_ticker(symbol='BTCUSDT')
            eth_ticker = price_client.get_symbol_ticker(symbol='ETHUSDT')
            test_info["tests"]["price_fetch"] = {
                "success": True,
                "btc_price": float(btc_ticker['price']),
                "eth_price": float(eth_ticker['price'])
            }
        except Exception as e:
            test_info["tests"]["price_fetch"] = {
                "success": False,
                "error": str(e)
            }
        
        # Test 4: Test wallet access with real account (if available)
        try:
            supabase = get_supabase_client()
            accounts_result = supabase.table('binance_accounts').select('*').limit(1).execute()
            
            if accounts_result.data and len(accounts_result.data) > 0:
                account = accounts_result.data[0]
                account_name = account['account_name']
                
                # Create client with real credentials
                client = create_binance_client(
                    api_key=account['binance_api_key'],
                    api_secret=account['binance_api_secret']
                )
                
                # Test spot wallet access
                try:
                    spot_account = client.get_account()
                    test_info["tests"]["wallet_access"] = {
                        "success": True,
                        "account_name": account_name,
                        "spot_permissions": spot_account.get('permissions', []),
                        "can_trade": spot_account.get('canTrade', False),
                        "can_withdraw": spot_account.get('canWithdraw', False),
                        "balance_count": len([b for b in spot_account.get('balances', []) if float(b['free']) + float(b['locked']) > 0])
                    }
                except Exception as e:
                    test_info["tests"]["wallet_access"] = {
                        "success": False,
                        "account_name": account_name,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                    
                    # If it's a restricted location error, it confirms proxy is needed but not working
                    if "restricted location" in str(e).lower():
                        test_info["tests"]["wallet_access"]["needs_proxy"] = True
                        test_info["tests"]["wallet_access"]["proxy_working"] = False
                        
            else:
                test_info["tests"]["wallet_access"] = {
                    "success": False,
                    "error": "No accounts found in database"
                }
                
        except Exception as e:
            test_info["tests"]["wallet_access"] = {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        
        # Test 5: Data API test (should work without proxy)
        try:
            # Test data API endpoints
            data_api_client = create_binance_client(for_prices_only=True)
            
            # Test multiple endpoints
            server_time = data_api_client.get_server_time()
            exchange_info = data_api_client.get_exchange_info(symbol='BTCUSDT')
            
            test_info["tests"]["data_api"] = {
                "success": True,
                "server_time": server_time.get('serverTime'),
                "exchange_info_received": bool(exchange_info),
                "symbol": exchange_info.get('symbols', [{}])[0].get('symbol') if exchange_info.get('symbols') else None
            }
        except Exception as e:
            test_info["tests"]["data_api"] = {
                "success": False,
                "error": str(e)
            }
        
        # Summary
        test_info["summary"] = {
            "proxy_should_be_active": test_info["proxy_config"]["is_active"],
            "price_api_working": test_info["tests"].get("price_fetch", {}).get("success", False),
            "wallet_api_working": test_info["tests"].get("wallet_access", {}).get("success", False),
            "recommendation": self._get_recommendation(test_info)
        }
        
        # Send response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(test_info, indent=2).encode('utf-8'))
    
    def _get_recommendation(self, test_info):
        """Generate recommendation based on test results"""
        if not test_info["proxy_config"]["is_active"]:
            if test_info["environment"]["VERCEL"] != "Not set":
                return "Proxy not active on Vercel. Check OXYLABS_PROXY_URL environment variable."
            else:
                return "Running locally. Proxy not needed."
        
        wallet_test = test_info["tests"].get("wallet_access", {})
        if wallet_test.get("success"):
            return "Everything working correctly! Proxy is active and wallet access successful."
        elif wallet_test.get("needs_proxy") and not wallet_test.get("proxy_working"):
            return "Proxy is configured but not working. Verify proxy credentials and connection."
        elif not wallet_test.get("success") and "No accounts found" in str(wallet_test.get("error", "")):
            return "No accounts to test. Add accounts to database first."
        else:
            return "Wallet access failed. Check error details above."