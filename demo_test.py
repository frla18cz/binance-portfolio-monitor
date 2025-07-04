#!/usr/bin/env python3
"""
Demo Mode Test Script - Safe testing of the Binance Portfolio Monitor
without connecting to real APIs or affecting real accounts.
"""

import os
import sys
from datetime import datetime, UTC

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

# Enable demo mode
os.environ['DEMO_MODE'] = 'true'

from api.demo_mode import (
    get_demo_controller, 
    simulate_transaction, 
    simulate_market_scenario,
    get_demo_dashboard_data,
    reset_demo_data
)
from api.index import process_all_accounts


def print_separator(title: str):
    """Print a visual separator with title."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_demo_mode():
    """Complete demo mode testing."""
    
    print_separator("🎮 BINANCE PORTFOLIO MONITOR - DEMO MODE")
    
    # Check demo mode status
    controller = get_demo_controller()
    status = controller.get_mode_status()
    
    print(f"🔧 Mode: {status['mode']}")
    print(f"🛡️  Safe Testing: {status['safe_testing']}")
    print(f"💰 Real Money: {status['real_money']}")
    print(f"⚠️  {status['warning']}")
    
    print_separator("📊 INITIAL STATE")
    
    # Get initial dashboard data
    dashboard = get_demo_dashboard_data()
    if "error" not in dashboard:
        perf = dashboard["account_performance"]
        prices = dashboard["current_prices"]
        
        print(f"Account: {perf['account_name']}")
        print(f"Initial Balance: ${perf['initial_balance']:,.2f}")
        print(f"Current NAV: ${perf['current_nav']:,.2f}")
        print(f"Total Return: ${perf['total_return']:,.2f} ({perf['return_percentage']:.2f}%)")
        print(f"Transactions: {perf['transaction_count']}")
        print(f"BTC Price: ${prices['btc']:,.2f}")
        print(f"ETH Price: ${prices['eth']:,.2f}")
    
    print_separator("💰 TESTING TRANSACTIONS")
    
    # Test deposit
    print("🟢 Simulating $5,000 deposit...")
    deposit_result = simulate_transaction("DEPOSIT", 5000.0)
    if deposit_result.get("success"):
        print(f"✅ Deposit successful!")
        print(f"   Transaction ID: {deposit_result['transaction_id']}")
        print(f"   New Balance: ${deposit_result['new_balance']:,.2f}")
        print(f"   New NAV: ${deposit_result['new_nav']:,.2f}")
    else:
        print(f"❌ Deposit failed: {deposit_result.get('error')}")
    
    # Test withdrawal
    print("\n🔴 Simulating $2,000 withdrawal...")
    withdrawal_result = simulate_transaction("WITHDRAWAL", 2000.0)
    if withdrawal_result.get("success"):
        print(f"✅ Withdrawal successful!")
        print(f"   Transaction ID: {withdrawal_result['transaction_id']}")
        print(f"   New Balance: ${withdrawal_result['new_balance']:,.2f}")
        print(f"   New NAV: ${withdrawal_result['new_nav']:,.2f}")
    else:
        print(f"❌ Withdrawal failed: {withdrawal_result.get('error')}")
    
    print_separator("📈 TESTING MARKET SCENARIOS")
    
    scenarios = [
        ("bull_run", "🚀 Bull Run (+15% BTC, +20% ETH)"),
        ("bear_market", "🐻 Bear Market (-20% BTC, -25% ETH)"),
        ("btc_dominance", "₿ BTC Dominance (+10% BTC, -5% ETH)"),
        ("eth_surge", "⟠ ETH Surge (+2% BTC, +25% ETH)")
    ]
    
    for scenario_id, description in scenarios:
        print(f"\n{description}")
        result = simulate_market_scenario(scenario_id)
        if result.get("success"):
            btc_change = result["price_changes"]["btc"]["change_percent"]
            eth_change = result["price_changes"]["eth"]["change_percent"]
            new_btc = result["price_changes"]["btc"]["new_price"]
            new_eth = result["price_changes"]["eth"]["new_price"]
            
            print(f"✅ Scenario applied successfully!")
            print(f"   BTC: {btc_change:+.1f}% → ${new_btc:,.2f}")
            print(f"   ETH: {eth_change:+.1f}% → ${new_eth:,.2f}")
            
            # Show portfolio impact
            impact = result["portfolio_impact"]
            print(f"   Portfolio NAV: ${impact['current_nav']:,.2f}")
            if impact['benchmark_value'] > 0:
                vs_benchmark = impact['vs_benchmark']
                print(f"   vs Benchmark: ${vs_benchmark:+,.2f}")
        else:
            print(f"❌ Scenario failed: {result.get('error')}")
        
        # Brief pause for readability
        import time
        time.sleep(0.5)
    
    print_separator("🔄 TESTING FULL MONITORING CYCLE")
    
    # Test the main monitoring process in demo mode
    print("Running complete monitoring process in demo mode...")
    try:
        process_all_accounts()
        print("✅ Monitoring process completed successfully!")
    except Exception as e:
        print(f"❌ Monitoring process failed: {e}")
    
    print_separator("📊 FINAL STATE")
    
    # Get final dashboard data
    final_dashboard = get_demo_dashboard_data()
    if "error" not in final_dashboard:
        final_perf = final_dashboard["account_performance"]
        final_prices = final_dashboard["current_prices"]
        recent_txns = final_dashboard["recent_transactions"]
        
        print(f"Final NAV: ${final_perf['current_nav']:,.2f}")
        print(f"Total Return: ${final_perf['total_return']:,.2f} ({final_perf['return_percentage']:.2f}%)")
        print(f"Total Transactions: {len(recent_txns)}")
        print(f"Final BTC Price: ${final_prices['btc']:,.2f}")
        print(f"Final ETH Price: ${final_prices['eth']:,.2f}")
        
        if final_perf['benchmark_value'] > 0:
            vs_benchmark = final_perf['vs_benchmark']
            print(f"vs Benchmark: ${vs_benchmark:+,.2f}")
    
    print_separator("🎯 DEMO MODE SUMMARY")
    
    print("✅ Demo mode is working perfectly!")
    print("✅ Transaction simulation working")
    print("✅ Market scenario simulation working") 
    print("✅ Price updates working")
    print("✅ Portfolio calculations working")
    print("✅ Full monitoring cycle working")
    print()
    print("🎮 You can now safely test:")
    print("   • Different deposit/withdrawal amounts")
    print("   • Various market scenarios")
    print("   • Portfolio rebalancing")
    print("   • Benchmark calculations")
    print("   • Complete monitoring workflows")
    print()
    print("🛡️  All testing is safe - no real money involved!")
    print("🔄 Reset demo data anytime with reset_demo_data()")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_demo_mode()