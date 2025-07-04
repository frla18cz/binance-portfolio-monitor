"""
Demo Mode Integration for the main monitoring system.
Switches between real Binance API and mock data based on configuration.
"""

import os
from typing import Optional, Dict, Any
from datetime import datetime, UTC

# Import both real and mock implementations
from .mock_mode import MockBinanceClient, MockDataManager, get_mock_manager
from .mock_supabase import get_mock_supabase_client
from binance.client import Client as RealBinanceClient


class DemoModeController:
    """Controls switching between demo and live modes."""
    
    def __init__(self):
        self.demo_mode = self._is_demo_mode_enabled()
        self.mock_manager = get_mock_manager() if self.demo_mode else None
        
    def _is_demo_mode_enabled(self) -> bool:
        """Check if demo mode is enabled via environment variable."""
        return os.getenv('DEMO_MODE', 'false').lower() in ('true', '1', 'yes', 'on')
    
    def get_binance_client(self, api_key: str, api_secret: str, **kwargs):
        """Get appropriate Binance client based on mode."""
        if self.demo_mode:
            print("🎮 DEMO MODE: Using mock Binance client")
            return MockBinanceClient(api_key, api_secret, **kwargs)
        else:
            print("🔴 LIVE MODE: Using real Binance client")
            return RealBinanceClient(api_key, api_secret, **kwargs)
    
    def get_supabase_client(self, real_supabase_client=None):
        """Get appropriate Supabase client based on mode."""
        if self.demo_mode:
            print("🎮 DEMO MODE: Using mock Supabase client")
            return get_mock_supabase_client()
        else:
            print("🔴 LIVE MODE: Using real Supabase client")
            return real_supabase_client
    
    def is_demo_mode(self) -> bool:
        """Check if currently in demo mode."""
        return self.demo_mode
    
    def get_mode_status(self) -> Dict[str, Any]:
        """Get current mode status and information."""
        if self.demo_mode:
            summary = self.mock_manager.get_performance_summary(1)
            return {
                "mode": "DEMO",
                "safe_testing": True,
                "real_money": False,
                "account_data": summary,
                "warning": "All data is simulated - no real trading"
            }
        else:
            return {
                "mode": "LIVE",
                "safe_testing": False,
                "real_money": True,
                "account_data": None,
                "warning": "⚠️ REAL TRADING MODE - Real money at risk"
            }


# Global demo controller instance
_demo_controller = None

def get_demo_controller() -> DemoModeController:
    """Get the global demo controller instance."""
    global _demo_controller
    if _demo_controller is None:
        _demo_controller = DemoModeController()
    return _demo_controller


def simulate_transaction(transaction_type: str, amount: float, account_id: int = 1) -> Dict[str, Any]:
    """
    Simulate a transaction in demo mode.
    Returns transaction details and updated account state.
    """
    controller = get_demo_controller()
    
    if not controller.is_demo_mode():
        return {
            "error": "Transaction simulation only available in demo mode",
            "current_mode": "LIVE"
        }
    
    mock_manager = controller.mock_manager
    
    try:
        # Add the transaction
        txn_id = mock_manager.add_transaction(account_id, transaction_type, amount)
        
        # Get updated account state
        account = mock_manager.get_account(account_id)
        summary = mock_manager.get_performance_summary(account_id)
        
        return {
            "success": True,
            "transaction_id": txn_id,
            "transaction_type": transaction_type,
            "amount": amount,
            "timestamp": datetime.now(UTC).isoformat(),
            "new_balance": account.current_balance if account else 0,
            "new_nav": summary.get("current_nav", 0),
            "performance_summary": summary
        }
        
    except Exception as e:
        return {
            "error": f"Transaction simulation failed: {str(e)}",
            "transaction_type": transaction_type,
            "amount": amount
        }


def simulate_market_scenario(scenario: str) -> Dict[str, Any]:
    """
    Simulate a market scenario in demo mode.
    Returns new prices and market impact.
    """
    controller = get_demo_controller()
    
    if not controller.is_demo_mode():
        return {
            "error": "Market simulation only available in demo mode",
            "current_mode": "LIVE"
        }
    
    mock_manager = controller.mock_manager
    
    try:
        # Store old prices
        old_prices = mock_manager.get_current_prices()
        
        # Apply scenario
        new_prices = mock_manager.simulate_market_scenario(scenario)
        
        # Calculate changes
        btc_change = ((new_prices.btc_price - old_prices.btc_price) / old_prices.btc_price) * 100
        eth_change = ((new_prices.eth_price - old_prices.eth_price) / old_prices.eth_price) * 100
        
        # Get updated performance
        summary = mock_manager.get_performance_summary(1)
        
        return {
            "success": True,
            "scenario": scenario,
            "timestamp": new_prices.timestamp,
            "price_changes": {
                "btc": {
                    "old_price": old_prices.btc_price,
                    "new_price": new_prices.btc_price,
                    "change_percent": round(btc_change, 2)
                },
                "eth": {
                    "old_price": old_prices.eth_price,
                    "new_price": new_prices.eth_price,
                    "change_percent": round(eth_change, 2)
                }
            },
            "portfolio_impact": summary
        }
        
    except Exception as e:
        return {
            "error": f"Market scenario simulation failed: {str(e)}",
            "scenario": scenario
        }


def get_demo_dashboard_data() -> Dict[str, Any]:
    """
    Get comprehensive data for demo mode dashboard.
    Includes account state, recent transactions, price history, etc.
    """
    controller = get_demo_controller()
    
    if not controller.is_demo_mode():
        return {
            "error": "Demo dashboard only available in demo mode",
            "current_mode": "LIVE"
        }
    
    mock_manager = controller.mock_manager
    
    try:
        # Get account performance
        summary = mock_manager.get_performance_summary(1)
        
        # Get current prices
        current_prices = mock_manager.get_current_prices()
        
        # Get recent transactions
        recent_txns = mock_manager.data["transactions"][-10:]  # Last 10 transactions
        
        # Get price history for charts
        price_history = mock_manager.data["price_history"][-50:]  # Last 50 price points
        
        # Get benchmark config
        benchmark_config = None
        for config in mock_manager.data["benchmark_configs"]:
            if config["account_id"] == 1:
                benchmark_config = config
                break
        
        return {
            "mode_status": controller.get_mode_status(),
            "account_performance": summary,
            "current_prices": {
                "btc": current_prices.btc_price,
                "eth": current_prices.eth_price,
                "timestamp": current_prices.timestamp
            },
            "recent_transactions": recent_txns,
            "price_history": price_history,
            "benchmark_config": benchmark_config,
            "available_scenarios": [
                "bull_run", "bear_market", "btc_dominance", 
                "eth_surge", "crash", "sideways"
            ],
            "nav_history": mock_manager.data.get("nav_history", [])
        }
        
    except Exception as e:
        return {
            "error": f"Failed to get demo dashboard data: {str(e)}"
        }


def reset_demo_data() -> Dict[str, Any]:
    """Reset all demo data to initial state."""
    controller = get_demo_controller()
    
    if not controller.is_demo_mode():
        return {
            "error": "Demo reset only available in demo mode",
            "current_mode": "LIVE"
        }
    
    try:
        controller.mock_manager.reset_to_defaults()
        return {
            "success": True,
            "message": "Demo data reset to initial state",
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        return {
            "error": f"Failed to reset demo data: {str(e)}"
        }


if __name__ == "__main__":
    # Demo mode testing
    import os
    
    # Enable demo mode for testing
    os.environ['DEMO_MODE'] = 'true'
    
    print("🎮 Demo Mode Testing")
    print("=" * 50)
    
    # Test mode detection
    controller = get_demo_controller()
    status = controller.get_mode_status()
    print(f"Mode: {status['mode']}")
    print(f"Safe Testing: {status['safe_testing']}")
    
    # Test transaction simulation
    print("\n💰 Testing transaction simulation...")
    deposit_result = simulate_transaction("DEPOSIT", 5000.0)
    if deposit_result.get("success"):
        print(f"✅ Deposit successful: ${deposit_result['amount']:,.2f}")
        print(f"New NAV: ${deposit_result['new_nav']:,.2f}")
    
    # Test market scenario
    print("\n📈 Testing market scenario...")
    scenario_result = simulate_market_scenario("bull_run")
    if scenario_result.get("success"):
        btc_change = scenario_result["price_changes"]["btc"]["change_percent"]
        eth_change = scenario_result["price_changes"]["eth"]["change_percent"]
        print(f"✅ Bull run applied: BTC {btc_change:+.1f}%, ETH {eth_change:+.1f}%")
    
    # Test dashboard data
    print("\n📊 Testing dashboard data...")
    dashboard_data = get_demo_dashboard_data()
    if "error" not in dashboard_data:
        print(f"✅ Dashboard data loaded: {len(dashboard_data['recent_transactions'])} transactions")
        print(f"Current BTC: ${dashboard_data['current_prices']['btc']:,.2f}")
        print(f"Current ETH: ${dashboard_data['current_prices']['eth']:,.2f}")
    
    print("\n🎯 Demo mode is ready for integration!")