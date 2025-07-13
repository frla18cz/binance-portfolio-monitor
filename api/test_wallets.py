"""
Comprehensive wallet test endpoint for Vercel proxy verification
Tests all wallet types and shows actual balance data
"""

import os
import json
import traceback
from http.server import BaseHTTPRequestHandler
from datetime import datetime, UTC

# Import required components
from api.index import create_binance_client, get_comprehensive_nav
from api.logger import get_logger, LogCategory
from config import settings
from utils.database_manager import get_supabase_client

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        logger = get_logger()
        start_time = datetime.now(UTC)
        
        # Initialize response structure
        response = {
            "timestamp": start_time.isoformat(),
            "environment": {
                "is_vercel": bool(os.getenv('VERCEL') or os.getenv('VERCEL_ENV')),
                "vercel_env": os.getenv('VERCEL_ENV', 'Not set'),
                "proxy_configured": bool(os.getenv('OXYLABS_PROXY_URL')),
                "proxy_active": getattr(settings.proxy, 'is_active', False) if hasattr(settings, 'proxy') else False,
                "region": os.getenv('VERCEL_REGION', 'unknown')
            },
            "accounts": {},
            "summary": {
                "total_accounts": 0,
                "successful": 0,
                "failed": 0,
                "total_nav": 0.0
            }
        }
        
        try:
            # Get Binance accounts from database
            supabase = get_supabase_client()
            accounts_result = supabase.table('binance_accounts').select('*').execute()
            accounts = accounts_result.data if accounts_result else []
            
            response["summary"]["total_accounts"] = len(accounts)
            
            # Test each account
            for account in accounts:
                account_id = account['id']
                account_name = account['account_name']
                
                logger.info(LogCategory.SYSTEM, "testing_account", 
                           f"Testing account: {account_name}",
                           account_id=account_id)
                
                account_info = {
                    "name": account_name,
                    "status": "testing",
                    "wallets": {},
                    "nav": 0.0,
                    "errors": []
                }
                
                try:
                    # Create Binance client with credentials
                    client = create_binance_client(
                        api_key=account['binance_api_key'],
                        api_secret=account['binance_api_secret']
                    )
                    
                    # Test 1: Spot Wallet
                    try:
                        spot_account = client.get_account()
                        spot_balances = []
                        spot_total = 0.0
                        
                        for balance in spot_account.get('balances', []):
                            free = float(balance.get('free', 0))
                            locked = float(balance.get('locked', 0))
                            total = free + locked
                            
                            if total > 0.001:  # Only show non-zero balances
                                spot_balances.append({
                                    "asset": balance['asset'],
                                    "total": total,
                                    "free": free,
                                    "locked": locked
                                })
                        
                        account_info["wallets"]["spot"] = {
                            "success": True,
                            "balance_count": len(spot_balances),
                            "balances": spot_balances[:5]  # Show top 5 for brevity
                        }
                    except Exception as e:
                        account_info["wallets"]["spot"] = {
                            "success": False,
                            "error": str(e)
                        }
                        account_info["errors"].append(f"Spot: {str(e)}")
                    
                    # Test 2: Futures Wallet
                    try:
                        futures_account = client.futures_account()
                        futures_balances = []
                        
                        for asset_info in futures_account.get('assets', []):
                            margin_balance = float(asset_info.get('marginBalance', 0))
                            
                            if abs(margin_balance) > 0.001:
                                futures_balances.append({
                                    "asset": asset_info['asset'],
                                    "marginBalance": margin_balance,
                                    "walletBalance": float(asset_info.get('walletBalance', 0)),
                                    "unrealizedProfit": float(asset_info.get('unrealizedProfit', 0))
                                })
                        
                        account_info["wallets"]["futures"] = {
                            "success": True,
                            "balance_count": len(futures_balances),
                            "balances": futures_balances
                        }
                    except Exception as e:
                        account_info["wallets"]["futures"] = {
                            "success": False,
                            "error": str(e)
                        }
                        account_info["errors"].append(f"Futures: {str(e)}")
                    
                    # Test 3: Funding Wallet
                    try:
                        funding_assets = client.funding_wallet()
                        funding_balances = []
                        
                        for asset_info in funding_assets:
                            total = (float(asset_info.get('free', 0)) + 
                                   float(asset_info.get('locked', 0)) + 
                                   float(asset_info.get('freeze', 0)))
                            
                            if total > 0.001:
                                funding_balances.append({
                                    "asset": asset_info.get('asset'),
                                    "total": total,
                                    "free": float(asset_info.get('free', 0)),
                                    "locked": float(asset_info.get('locked', 0))
                                })
                        
                        account_info["wallets"]["funding"] = {
                            "success": True,
                            "balance_count": len(funding_balances),
                            "balances": funding_balances
                        }
                    except Exception as e:
                        account_info["wallets"]["funding"] = {
                            "success": False,
                            "error": str(e)
                        }
                        # Funding wallet errors are often expected
                    
                    # Test 4: Simple Earn
                    try:
                        earn_response = client._request('GET', 'sapi/v1/simple-earn/flexible/position', True, {})
                        earn_positions = []
                        
                        # Handle different response structures
                        positions = []
                        if isinstance(earn_response, dict):
                            if 'rows' in earn_response:
                                positions = earn_response['rows']
                            elif 'data' in earn_response and 'rows' in earn_response['data']:
                                positions = earn_response['data']['rows']
                        
                        for position in positions:
                            total = float(position.get('totalAmount', 0))
                            if total > 0.001:
                                earn_positions.append({
                                    "asset": position.get('asset'),
                                    "totalAmount": total,
                                    "productId": position.get('productId')
                                })
                        
                        account_info["wallets"]["simple_earn"] = {
                            "success": True,
                            "position_count": len(earn_positions),
                            "positions": earn_positions
                        }
                    except Exception as e:
                        account_info["wallets"]["simple_earn"] = {
                            "success": False,
                            "error": str(e)
                        }
                        # Simple Earn errors are often expected
                    
                    # Test 5: Get comprehensive NAV
                    try:
                        # First get prices
                        price_client = create_binance_client(for_prices_only=True)
                        btc_ticker = price_client.get_symbol_ticker(symbol='BTCUSDT')
                        eth_ticker = price_client.get_symbol_ticker(symbol='ETHUSDT')
                        
                        prices = {
                            'BTCUSDT': float(btc_ticker['price']),
                            'ETHUSDT': float(eth_ticker['price'])
                        }
                        
                        # Calculate NAV
                        nav_result = get_comprehensive_nav(
                            client, 
                            logger=logger,
                            account_id=account_id,
                            account_name=account_name,
                            prices=prices
                        )
                        
                        account_info["nav"] = nav_result['total_nav']
                        account_info["nav_breakdown"] = {
                            "spot": nav_result['breakdown'].get('spot_total', 0),
                            "futures": nav_result['breakdown'].get('futures_total', 0),
                            "funding": nav_result['breakdown'].get('funding_total', 0),
                            "earn": nav_result['breakdown'].get('earn_total', 0),
                            "staking": nav_result['breakdown'].get('staking_total', 0)
                        }
                        account_info["status"] = "success"
                        response["summary"]["successful"] += 1
                        response["summary"]["total_nav"] += nav_result['total_nav']
                        
                    except Exception as e:
                        account_info["errors"].append(f"NAV calculation: {str(e)}")
                        account_info["status"] = "partial"
                    
                except Exception as e:
                    # Critical error - couldn't create client or major failure
                    account_info["status"] = "failed"
                    account_info["errors"].append(f"Critical: {str(e)}")
                    response["summary"]["failed"] += 1
                    logger.error(LogCategory.API_ERROR, "account_test_failed",
                               f"Failed to test account {account_name}: {str(e)}",
                               account_id=account_id,
                               traceback=traceback.format_exc())
                
                response["accounts"][account_id] = account_info
            
            # Add execution time
            execution_time = (datetime.now(UTC) - start_time).total_seconds()
            response["execution_time_seconds"] = execution_time
            
            # Log summary
            logger.info(LogCategory.SYSTEM, "wallet_test_complete",
                       f"Wallet test completed: {response['summary']['successful']}/{response['summary']['total_accounts']} successful",
                       data=response["summary"])
            
        except Exception as e:
            response["error"] = str(e)
            response["traceback"] = traceback.format_exc()
            logger.error(LogCategory.API_ERROR, "wallet_test_error",
                        f"Failed to complete wallet test: {str(e)}",
                        traceback=traceback.format_exc())
        
        # Send response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response, indent=2).encode('utf-8'))