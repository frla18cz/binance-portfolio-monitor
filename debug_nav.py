#!/usr/bin/env python3
"""
Debug script to check detailed NAV breakdown from Binance Futures API
"""

import os
import json
from dotenv import load_dotenv
from supabase import create_client
from binance.client import Client as BinanceClient

load_dotenv()

def main():
    print("🔍 Debug NAV Calculation")
    print("=" * 50)
    
    # Get account from database
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_ANON_KEY")
    supabase = create_client(supabase_url, supabase_key)
    
    accounts = supabase.table('binance_accounts').select('*').execute()
    if not accounts.data:
        print("❌ No accounts found")
        return
    
    account = accounts.data[0]
    api_key = account['api_key']
    api_secret = account['api_secret']
    account_name = account['account_name']
    
    print(f"👤 Account: {account_name}")
    print("-" * 30)
    
    # Create Binance client
    client = BinanceClient(api_key, api_secret, tld='com')
    
    # Get BTC price first
    btc_ticker = client.get_symbol_ticker(symbol="BTCUSDT")
    btc_usdt_price = float(btc_ticker['price'])
    
    # TEST NEW WALLET ENDPOINTS
    try:
        print("🔍 TESTING NEW WALLET ENDPOINTS")
        print("=" * 50)
        
        # Test funding wallet
        print("\n💰 FUNDING WALLET:")
        print("-" * 30)
        try:
            funding_assets = client.funding_wallet()
            funding_total = 0.0
            for asset_info in funding_assets:
                asset = asset_info.get('asset', '')
                free = float(asset_info.get('free', '0'))
                locked = float(asset_info.get('locked', '0'))
                freeze = float(asset_info.get('freeze', '0'))
                withdrawing = float(asset_info.get('withdrawing', '0'))
                total = free + locked + freeze + withdrawing
                if total > 0:
                    print(f"{asset}: {total:.8f} (free: {free}, locked: {locked}, freeze: {freeze}, withdrawing: {withdrawing})")
                    # Convert to USD for major assets
                    if asset == 'BTC':
                        funding_total += total * btc_usdt_price
                    elif asset in ['USDT', 'BUSD', 'USDC']:
                        funding_total += total
            print(f"Funding wallet total (est): ${funding_total:,.2f}")
        except Exception as e:
            print(f"❌ Funding wallet error: {e}")
        
        # Test Simple Earn
        print("\n📈 SIMPLE EARN POSITIONS:")
        print("-" * 30)
        try:
            response = client._request('GET', 'sapi/v1/simple-earn/flexible/position', True, {})
            # Debug response structure
            print(f"Response type: {type(response)}")
            if isinstance(response, dict):
                print(f"Response keys: {list(response.keys())}")
                
            # Handle different response structures
            positions = []
            if isinstance(response, dict):
                if 'rows' in response:
                    positions = response['rows']
                elif 'data' in response:
                    data = response['data']
                    if isinstance(data, dict) and 'rows' in data:
                        positions = data['rows']
                    elif isinstance(data, list):
                        positions = data
            elif isinstance(response, list):
                positions = response
                
            if positions:
                earn_total = 0.0
                for position in positions:
                    asset = position.get('asset', '')
                    total_amount = float(position.get('totalAmount', '0'))
                    if total_amount > 0:
                        print(f"{asset}: {total_amount:.8f}")
                        # Convert to USD
                        if asset == 'BTC':
                            earn_total += total_amount * btc_usdt_price
                        elif asset in ['USDT', 'BUSD', 'USDC']:
                            earn_total += total_amount
                print(f"Simple Earn total (est): ${earn_total:,.2f}")
            else:
                print("No Simple Earn positions found")
        except Exception as e:
            print(f"❌ Simple Earn error: {e}")
            if hasattr(e, 'code'):
                print(f"API Error Code: {e.code}")
            if hasattr(e, 'message'):
                print(f"API Error Message: {e.message}")
        
        # Test Staking
        print("\n🥇 STAKING POSITIONS:")
        print("-" * 30)
        try:
            staking_positions = client.get_staking_position(product='STAKING')
            staking_total = 0.0
            for position in staking_positions:
                asset = position.get('asset', '')
                amount = float(position.get('amount', '0'))
                if amount > 0:
                    print(f"{asset}: {amount:.8f}")
                    # Convert to USD
                    if asset == 'BTC':
                        staking_total += amount * btc_usdt_price
                    elif asset in ['USDT', 'BUSD', 'USDC']:
                        staking_total += amount
            print(f"Staking total (est): ${staking_total:,.2f}")
        except Exception as e:
            print(f"❌ Staking error: {e}")
            
    except Exception as e:
        print(f"Error in wallet endpoint tests: {e}")
    
    # COMPREHENSIVE NAV ANALYSIS
    try:
        print("\n💰 COMPREHENSIVE NAV BREAKDOWN (OLD METHOD)")
        print("=" * 50)
        
        total_nav = 0.0
        
        # 1. SPOT ACCOUNT ANALYSIS
        print("\n🔵 SPOT ACCOUNT BREAKDOWN:")
        print("-" * 30)
        spot_account = client.get_account()
        spot_total = 0.0
        
        for balance in spot_account['balances']:
            asset = balance['asset']
            free = float(balance['free'])
            locked = float(balance['locked'])
            total_balance = free + locked
            
            if total_balance > 0.001:
                # Convert to USDT value
                if asset in ['USDT', 'BUSD', 'USDC']:
                    usdt_value = total_balance
                else:
                    try:
                        ticker = client.get_symbol_ticker(symbol=f"{asset}USDT")
                        price = float(ticker['price'])
                        usdt_value = total_balance * price
                    except:
                        try:
                            btc_ticker = client.get_symbol_ticker(symbol=f"{asset}BTC")
                            btc_price = float(btc_ticker['price'])
                            btc_usdt_ticker = client.get_symbol_ticker(symbol="BTCUSDT")
                            btc_usdt_price = float(btc_usdt_ticker['price'])
                            usdt_value = total_balance * btc_price * btc_usdt_price
                        except:
                            usdt_value = 0.0
                
                if usdt_value > 0.1:
                    spot_total += usdt_value
                    print(f"   - {asset}: {total_balance:,.6f} = ${usdt_value:,.2f}")
        
        print("-" * 30)
        print(f"Σ Spot Total: ${spot_total:,.2f}")
        total_nav += spot_total
        
        # ZKONTROLUJ MARGIN ÚČET
        print("\n🟠 MARGIN ACCOUNT CHECK:")
        print("-" * 30)
        try:
            margin_account = client.get_margin_account()
            margin_nav = float(margin_account['totalNetAssetOfBtc'])
            
            # Převedeme BTC na USD
            btc_price = client.get_symbol_ticker(symbol="BTCUSDT")
            btc_usdt_price = float(btc_price['price'])
            margin_usd = margin_nav * btc_usdt_price
            
            print(f"Margin NAV (BTC): {margin_nav:.8f}")
            print(f"BTC Price: ${btc_usdt_price:,.2f}")
            print(f"Margin NAV (USD): ${margin_usd:,.2f}")
            
            if margin_usd > 1:
                total_nav += margin_usd
                print("✅ Added to total NAV")
            else:
                print("❌ Too small, not added")
                
        except Exception as e:
            print(f"❌ Margin account error: {e}")
        
        # ZKONTROLUJ ISOLATED MARGIN
        print("\n🔸 ISOLATED MARGIN CHECK:")
        print("-" * 30)
        try:
            isolated_margin = client.get_isolated_margin_account()
            isolated_total = 0
            
            if 'assets' in isolated_margin:
                for asset in isolated_margin['assets']:
                    if 'totalNetAsset' in asset:
                        net_asset = float(asset['totalNetAsset'])
                        if net_asset > 0.001:
                            symbol = asset['symbol']
                            print(f"Isolated {symbol}: {net_asset:.6f}")
                            isolated_total += net_asset
            
            print(f"Isolated margin total: ${isolated_total:,.2f}")
            if isolated_total > 1:
                total_nav += isolated_total
                print("✅ Added to total NAV")
            else:
                print("❌ Too small, not added")
                
        except Exception as e:
            print(f"❌ Isolated margin error: {e}")
        
        # ZKONTROLUJ SAVINGS/LENDING
        print("\n💰 SAVINGS/LENDING CHECK:")
        print("-" * 30)
        try:
            # Flexible savings
            flexible_products = client.get_all_coins_info()
            flexible_total = 0
            for coin in flexible_products:
                if float(coin['free']) > 0 or float(coin['locked']) > 0:
                    total_balance = float(coin['free']) + float(coin['locked'])
                    print(f"Savings {coin['coin']}: {total_balance:.6f}")
                    flexible_total += total_balance
            
            print(f"Flexible savings total: {flexible_total}")
                
        except Exception as e:
            print(f"❌ Savings check error: {e}")
        
        # ZKONTROLUJ STAKING
        print("\n🥇 STAKING CHECK:")
        print("-" * 30)
        try:
            staking_products = client.get_staking_product_list(product='STAKING')
            print(f"Found {len(staking_products)} staking products")
            
            # Zkus získat staking positions
            staking_positions = client.get_staking_position(product='STAKING')
            staking_total = 0
            for position in staking_positions:
                amount = float(position.get('amount', 0))
                asset = position.get('asset', 'UNKNOWN')
                if amount > 0:
                    print(f"Staking {asset}: {amount:.6f}")
                    staking_total += amount
            
            print(f"Staking total value: {staking_total}")
                
        except Exception as e:
            print(f"❌ Staking check error: {e}")
        
        # ZKONTROLUJ PORTFOLIO MARGIN (možná je to tam!)
        print("\n🏦 PORTFOLIO MARGIN CHECK:")
        print("-" * 30) 
        try:
            # Někdy je portfolio margin jiný endpoint
            portfolio_account = client.get_portfolio_account()
            print("Portfolio account data:")
            for key, value in portfolio_account.items():
                print(f"   {key}: {value}")
                
        except Exception as e:
            print(f"❌ Portfolio margin error: {e}")
            
        # ZKONTROLUJ ACCOUNT SNAPSHOT - možná tam uvidíme všechno
        print("\n📸 ACCOUNT SNAPSHOT CHECK:")
        print("-" * 30)
        snapshot_total_usd = 0
        try:
            # Zkus všechny typy
            for account_type in ['SPOT', 'MARGIN', 'FUTURES']:
                try:
                    snapshot = client.get_account_snapshot(type=account_type)
                    print(f"{account_type} snapshot:")
                    if 'snapshotVos' in snapshot:
                        latest = snapshot['snapshotVos'][0] if snapshot['snapshotVos'] else {}
                        if 'data' in latest:
                            data = latest['data']
                            if 'totalAssetOfBtc' in data:
                                btc_value = float(data['totalAssetOfBtc'])
                                usd_value = btc_value * btc_usdt_price
                                print(f"   Total Asset (BTC): {btc_value:.8f}")
                                print(f"   Total Asset (USD): ${usd_value:,.2f}")
                                snapshot_total_usd += usd_value
                except Exception as se:
                    print(f"   {account_type} snapshot error: {se}")
                    
            print("-" * 30)
            print(f"📸 SNAPSHOT TOTAL NAV: ${snapshot_total_usd:,.2f}")
            
        except Exception as e:
            print(f"❌ Snapshot check error: {e}")
        
        # MANUAL CALCULATION - použijeme futures API znovu 
        print("\n🔥 MANUAL BTC CALCULATION:")
        print("-" * 30)
        manual_total = 0
        
        # Spot BTC (raw check)
        spot_btc_total = 0
        for balance in spot_account['balances']:
            if balance['asset'] == 'BTC':
                btc_amount = float(balance['free']) + float(balance['locked'])
                btc_usd = btc_amount * btc_usdt_price
                spot_btc_total += btc_usd
                print(f"Spot BTC: {btc_amount:.8f} = ${btc_usd:,.2f}")
        
        # Futures BTC (raw check) - get fresh data
        futures_account_fresh = client.futures_account()
        futures_btc_total = 0
        for asset in futures_account_fresh.get('assets', []):
            if asset['asset'] == 'BTC':
                btc_amount = float(asset['walletBalance'])
                btc_usd = btc_amount * btc_usdt_price
                futures_btc_total += btc_usd
                print(f"Futures BTC: {btc_amount:.8f} = ${btc_usd:,.2f}")
        
        manual_total = spot_btc_total + futures_btc_total
        print(f"Manual BTC Total: ${manual_total:,.2f}")
        
        # Plus non-BTC assets
        print(f"Plus BNFCR: ${18.22:,.2f}")
        manual_total += 18.22
        
        print("-" * 30)
        print(f"🔥 MANUAL TOTAL: ${manual_total:,.2f}")
        
        # POROVNEJ S BINANCE DASHBOARD
        print(f"🎯 BINANCE DASHBOARD: ~$421,000")
        difference_from_dashboard = manual_total - 421000
        print(f"📊 DIFFERENCE: ${difference_from_dashboard:+,.2f}")
        
        if abs(difference_from_dashboard) < 5000:
            print("✅ VERY CLOSE to Binance dashboard!")
        elif abs(difference_from_dashboard) < 10000:
            print("🟡 Close to Binance dashboard")
        else:
            print("🚨 Still significant difference")
        
        # 2. FUTURES ACCOUNT ANALYSIS
        print("\n🟡 FUTURES ACCOUNT BREAKDOWN:")
        print("-" * 30)
        futures_info = client.futures_account()
        
        print("DEBUG: Futures account structure:")
        print(f"totalWalletBalance: ${float(futures_info['totalWalletBalance']):,.2f}")
        print(f"totalUnrealizedProfit: ${float(futures_info['totalUnrealizedProfit']):,.2f}")
        print(f"totalMarginBalance: ${float(futures_info['totalMarginBalance']):,.2f}")
        print(f"totalPositionInitialMargin: ${float(futures_info['totalPositionInitialMargin']):,.2f}")
        print(f"availableBalance: ${float(futures_info['availableBalance']):,.2f}")
        print(f"totalOpenOrderInitialMargin: ${float(futures_info.get('totalOpenOrderInitialMargin', 0)):,.2f}")
        print(f"totalCrossWalletBalance: ${float(futures_info.get('totalCrossWalletBalance', 0)):,.2f}")
        print(f"totalCrossUnPnl: ${float(futures_info.get('totalCrossUnPnl', 0)):,.2f}")
        
        # Zkusme všechny možné hodnoty
        print("\n🔍 TRYING DIFFERENT FUTURES VALUES:")
        print(f"Binance Dashboard:      ~$421,000")
        print(f"totalWalletBalance:     ${float(futures_info['totalWalletBalance']):,.2f}")
        print(f"totalMarginBalance:     ${float(futures_info['totalMarginBalance']):,.2f}")
        if 'totalCrossWalletBalance' in futures_info:
            print(f"totalCrossWalletBalance: ${float(futures_info['totalCrossWalletBalance']):,.2f}")
        
        # Zkontroluj všechny klíče
        print(f"\n📋 All futures account keys:")
        for key, value in futures_info.items():
            if key not in ['assets', 'positions']:
                try:
                    print(f"   {key}: ${float(value):,.2f}")
                except:
                    print(f"   {key}: {value}")
        
        futures_collateral = 0
        print("\nAssets breakdown (RAW VALUES):")
        for asset in futures_info.get('assets', []):
            asset_name = asset.get('asset')
            wallet_balance = float(asset.get('walletBalance', 0))
            unrealized_profit = float(asset.get('unrealizedProfit', 0))
            margin_balance = float(asset.get('marginBalance', 0))
            if wallet_balance > 0.0001 or unrealized_profit != 0 or margin_balance > 0.0001:
                print(f"   - {asset_name}:")
                print(f"     walletBalance: {wallet_balance:,.8f} {asset_name}")
                print(f"     unrealizedProfit: {unrealized_profit:,.8f}")
                print(f"     marginBalance: {margin_balance:,.8f}")
                
                # Convert to USD if it's BTC
                if asset_name == 'BTC':
                    btc_price = float(client.get_symbol_ticker(symbol="BTCUSDT")['price'])
                    wallet_usd = wallet_balance * btc_price
                    unrealized_usd = unrealized_profit * btc_price
                    margin_usd = margin_balance * btc_price
                    print(f"     → walletBalance USD: ${wallet_usd:,.2f}")
                    print(f"     → unrealizedProfit USD: ${unrealized_usd:,.2f}")
                    print(f"     → marginBalance USD: ${margin_usd:,.2f}")
                    futures_collateral += wallet_usd
                elif asset_name in ['USDT', 'BUSD', 'USDC', 'BNFCR']:
                    futures_collateral += wallet_balance
                    print(f"     → USD value: ${wallet_balance:,.2f}")
                else:
                    # Try to convert other assets
                    try:
                        ticker = client.get_symbol_ticker(symbol=f"{asset_name}USDT")
                        price = float(ticker['price'])
                        wallet_usd = wallet_balance * price
                        futures_collateral += wallet_usd
                        print(f"     → USD value: ${wallet_usd:,.2f}")
                    except:
                        print(f"     → Cannot convert {asset_name} to USD")
        
        print("-" * 30)
        print(f"Σ Futures Collateral (walletBalance): ${futures_collateral:,.2f}")
        print(f"  Total Wallet Balance: ${float(futures_info['totalWalletBalance']):,.2f}")
        
        # Použijeme totalWalletBalance místo součtu walletBalance
        futures_total_balance = float(futures_info['totalWalletBalance'])
        total_nav += futures_total_balance

        # 3. FUTURES POSITIONS P/L ANALYSIS (pro informaci, ale nepřičítáme k NAV)
        print("\n🟢 FUTURES POSITIONS P/L (informativní - už zahrnut v totalWalletBalance):")
        print("-" * 30)
        positions = client.futures_position_information()
        total_pnl = 0
        
        for pos in positions:
            position_amt = float(pos['positionAmt'])
            if position_amt != 0:
                symbol = pos['symbol']
                unrealized_pnl = float(pos['unRealizedProfit'])  # Správný klíč
                mark_price = float(pos['markPrice'])
                total_pnl += unrealized_pnl
                print(f"   - {symbol}: {position_amt:+,.4f} @ ${mark_price:,.4f} = P/L: ${unrealized_pnl:+,.2f}")
            
        print("-" * 30)
        print(f"Σ Total Positions P/L: ${total_pnl:+,.2f}")
        print("(POZNÁMKA: už zahrnut v totalWalletBalance, nepřičítáme znovu)")
        
        # 4. FINAL COMPREHENSIVE NAV
        print("\n" + "=" * 50)
        print("🎯 COMPREHENSIVE NAV CALCULATION:")
        print("=" * 50)
        print(f"   Spot Account:        ${spot_total:>12,.2f}")
        print(f"   Futures Total:       ${futures_total_balance:>12,.2f}")
        print("-" * 50)
        print(f"   TOTAL NAV:           ${total_nav:>12,.2f}")
        print("=" * 50)
        
        # 5. COMPARE WITH OLD METHOD
        print("\n📊 COMPARISON WITH OLD METHOD:")
        print("-" * 30)
        old_nav = float(futures_info['totalWalletBalance']) + float(futures_info['totalUnrealizedProfit'])
        difference = total_nav - old_nav
        print(f"Old Method NAV:      ${old_nav:,.2f}")
        print(f"New Method NAV:      ${total_nav:,.2f}")
        print(f"Difference:          ${difference:+,.2f}")
        
        if abs(difference) > 1000:
            print(f"🚨 SIGNIFICANT DIFFERENCE: ${difference:+,.2f}")
        else:
            print("✅ NAV values are similar")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()