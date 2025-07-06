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
    
    # Get detailed futures account info
    try:
        info = client.futures_account()
        
        total_wallet_balance = float(info['totalWalletBalance'])
        total_unrealized_pnl = float(info['totalUnrealizedProfit'])
        total_margin_balance = float(info['totalMarginBalance'])
        available_balance = float(info['availableBalance'])
        
        calculated_nav = total_wallet_balance + total_unrealized_pnl
        
        print(f"💰 Total Wallet Balance: ${total_wallet_balance:,.2f}")
        print(f"📈 Total Unrealized PnL: ${total_unrealized_pnl:+,.2f}")
        print(f"💼 Total Margin Balance: ${total_margin_balance:,.2f}")
        print(f"💵 Available Balance: ${available_balance:,.2f}")
        print("-" * 30)
        print(f"🎯 Calculated NAV: ${calculated_nav:,.2f}")
        print(f"   (totalWalletBalance + totalUnrealizedProfit)")
        
        # Get positions for detailed breakdown
        positions = client.futures_position_information()
        active_positions = [p for p in positions if float(p['positionAmt']) != 0]
        
        if active_positions:
            print(f"\n📊 Active Positions ({len(active_positions)}):")
            print("-" * 30)
            total_unrealized_from_positions = 0
            
            for pos in active_positions:
                symbol = pos['symbol']
                position_amt = float(pos['positionAmt'])
                entry_price = float(pos['entryPrice'])
                mark_price = float(pos['markPrice'])
                unrealized_pnl = float(pos['unRealizedProfit'])
                total_unrealized_from_positions += unrealized_pnl
                
                print(f"🏷️  {symbol}")
                print(f"   Size: {position_amt:+,.4f}")
                print(f"   Entry: ${entry_price:,.4f}")
                print(f"   Mark: ${mark_price:,.4f}")
                print(f"   PnL: ${unrealized_pnl:+,.2f}")
                print()
            
            print(f"💹 Total PnL from positions: ${total_unrealized_from_positions:+,.2f}")
            
            if abs(total_unrealized_from_positions - total_unrealized_pnl) > 0.01:
                print(f"⚠️  PnL mismatch: {total_unrealized_from_positions:.2f} vs {total_unrealized_pnl:.2f}")
        
        # Show what you might see in Binance UI
        print(f"\n🖥️  Binance UI Comparison:")
        print("-" * 30)
        print(f"Balance Tab 'Wallet Balance': ${total_wallet_balance:,.2f}")
        print(f"+ Unrealized PnL: ${total_unrealized_pnl:+,.2f}")
        print(f"= Our calculated NAV: ${calculated_nav:,.2f}")
        print(f"\nBinance může zobrazovat:")
        print(f"- 'Total Balance' (možná margin balance): ${total_margin_balance:,.2f}")
        print(f"- 'Available' (pro trading): ${available_balance:,.2f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()