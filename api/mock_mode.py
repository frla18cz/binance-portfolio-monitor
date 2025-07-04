"""
Mock/Demo Mode for safe testing of the Binance Portfolio Monitor.
Allows simulation of deposits, withdrawals, price changes, and market scenarios
without connecting to real Binance API or affecting real accounts.
"""

import json
import os
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import random


@dataclass
class MockAccount:
    """Mock account data for testing."""
    id: int
    account_name: str
    initial_balance: float
    current_balance: float
    unrealized_pnl: float
    created_at: str

@dataclass
class MockTransaction:
    """Mock transaction for testing."""
    id: str
    account_id: int
    type: str  # 'DEPOSIT' or 'WITHDRAWAL'
    amount: float
    timestamp: str
    status: str = 'SUCCESS'

@dataclass
class MockPrices:
    """Mock price data for testing."""
    btc_price: float
    eth_price: float
    timestamp: str
    volatility: float = 0.05  # 5% volatility by default

class MockDataManager:
    """Manages mock data for testing and simulation."""
    
    def __init__(self, data_file: str = "mock_data.json"):
        self.data_file = data_file
        self.data = self._load_data()
        
    def _load_data(self) -> Dict:
        """Load mock data from file or create default."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading mock data: {e}")
                
        return self._create_default_data()
    
    def _create_default_data(self) -> Dict:
        """Create default mock data for testing."""
        now = datetime.now(UTC).isoformat()
        
        return {
            "accounts": [
                {
                    "id": 1,
                    "account_name": "Demo Trading Account",
                    "initial_balance": 10000.0,
                    "current_balance": 10000.0,
                    "unrealized_pnl": 0.0,
                    "created_at": now
                }
            ],
            "transactions": [],
            "price_history": [
                {
                    "btc_price": 65000.0,
                    "eth_price": 3500.0,
                    "timestamp": now,
                    "volatility": 0.05
                }
            ],
            "benchmark_configs": [
                {
                    "id": 1,
                    "account_id": 1,
                    "btc_units": 0.0,
                    "eth_units": 0.0,
                    "rebalance_day": 0,
                    "rebalance_hour": 12,
                    "next_rebalance_timestamp": None
                }
            ],
            "nav_history": [],
            "settings": {
                "demo_mode": True,
                "auto_price_updates": True,
                "price_volatility": 0.05,
                "simulation_speed": 1.0
            }
        }
    
    def save_data(self):
        """Save current mock data to file."""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Error saving mock data: {e}")
    
    def get_account(self, account_id: int) -> Optional[MockAccount]:
        """Get mock account by ID."""
        for account_data in self.data["accounts"]:
            if account_data["id"] == account_id:
                return MockAccount(**account_data)
        return None
    
    def update_account_balance(self, account_id: int, new_balance: float, unrealized_pnl: float = 0.0):
        """Update account balance for simulation."""
        for account in self.data["accounts"]:
            if account["id"] == account_id:
                account["current_balance"] = new_balance
                account["unrealized_pnl"] = unrealized_pnl
                break
        self.save_data()
    
    def add_transaction(self, account_id: int, transaction_type: str, amount: float) -> str:
        """Add a mock transaction for testing."""
        transaction_id = f"MOCK_{transaction_type}_{len(self.data['transactions']) + 1}"
        transaction = {
            "id": transaction_id,
            "account_id": account_id,
            "type": transaction_type,
            "amount": amount,
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "SUCCESS"
        }
        
        self.data["transactions"].append(transaction)
        
        # Update account balance
        account = self.get_account(account_id)
        if account:
            if transaction_type == "DEPOSIT":
                new_balance = account.current_balance + amount
            else:  # WITHDRAWAL
                new_balance = account.current_balance - amount
            
            self.update_account_balance(account_id, new_balance, account.unrealized_pnl)
        
        self.save_data()
        return transaction_id
    
    def get_current_prices(self) -> MockPrices:
        """Get current mock prices."""
        if not self.data["price_history"]:
            return MockPrices(65000.0, 3500.0, datetime.now(UTC).isoformat())
        
        latest = self.data["price_history"][-1]
        return MockPrices(**latest)
    
    def update_prices(self, btc_price: Optional[float] = None, eth_price: Optional[float] = None, 
                     simulate_volatility: bool = True):
        """Update mock prices with optional volatility simulation."""
        current = self.get_current_prices()
        
        if simulate_volatility and (btc_price is None or eth_price is None):
            # Simulate price movement with volatility
            volatility = current.volatility
            btc_change = random.uniform(-volatility, volatility)
            eth_change = random.uniform(-volatility, volatility)
            
            new_btc = current.btc_price * (1 + btc_change) if btc_price is None else btc_price
            new_eth = current.eth_price * (1 + eth_change) if eth_price is None else eth_price
        else:
            new_btc = btc_price or current.btc_price
            new_eth = eth_price or current.eth_price
        
        new_prices = {
            "btc_price": round(new_btc, 2),
            "eth_price": round(new_eth, 2),
            "timestamp": datetime.now(UTC).isoformat(),
            "volatility": current.volatility
        }
        
        self.data["price_history"].append(new_prices)
        
        # Keep only last 1000 price points
        if len(self.data["price_history"]) > 1000:
            self.data["price_history"] = self.data["price_history"][-1000:]
        
        self.save_data()
        return MockPrices(**new_prices)
    
    def get_transactions_since(self, account_id: int, since_timestamp: str) -> List[MockTransaction]:
        """Get transactions since specific timestamp."""
        since_dt = datetime.fromisoformat(since_timestamp.replace('Z', '+00:00'))
        
        transactions = []
        for txn_data in self.data["transactions"]:
            if txn_data["account_id"] != account_id:
                continue
                
            txn_dt = datetime.fromisoformat(txn_data["timestamp"].replace('Z', '+00:00'))
            if txn_dt >= since_dt:
                transactions.append(MockTransaction(**txn_data))
        
        return sorted(transactions, key=lambda x: x.timestamp)
    
    def simulate_market_scenario(self, scenario: str):
        """Simulate predefined market scenarios."""
        current = self.get_current_prices()
        
        scenarios = {
            "bull_run": {"btc_mult": 1.15, "eth_mult": 1.20},  # +15% BTC, +20% ETH
            "bear_market": {"btc_mult": 0.80, "eth_mult": 0.75},  # -20% BTC, -25% ETH
            "btc_dominance": {"btc_mult": 1.10, "eth_mult": 0.95},  # BTC up, ETH down
            "eth_surge": {"btc_mult": 1.02, "eth_mult": 1.25},  # ETH outperforms
            "crash": {"btc_mult": 0.70, "eth_mult": 0.65},  # Major crash
            "sideways": {"btc_mult": 1.0, "eth_mult": 1.0}  # No movement
        }
        
        if scenario not in scenarios:
            raise ValueError(f"Unknown scenario: {scenario}")
        
        scenario_data = scenarios[scenario]
        new_btc = current.btc_price * scenario_data["btc_mult"]
        new_eth = current.eth_price * scenario_data["eth_mult"]
        
        return self.update_prices(new_btc, new_eth, simulate_volatility=False)
    
    def reset_to_defaults(self):
        """Reset all mock data to defaults."""
        self.data = self._create_default_data()
        self.save_data()
    
    def get_performance_summary(self, account_id: int) -> Dict:
        """Get performance summary for account."""
        account = self.get_account(account_id)
        if not account:
            return {}
        
        current_nav = account.current_balance + account.unrealized_pnl
        total_return = current_nav - account.initial_balance
        return_pct = (total_return / account.initial_balance) * 100 if account.initial_balance > 0 else 0
        
        # Calculate benchmark performance (if initialized)
        benchmark_config = None
        for config in self.data["benchmark_configs"]:
            if config["account_id"] == account_id:
                benchmark_config = config
                break
        
        benchmark_value = 0
        if benchmark_config and (benchmark_config["btc_units"] > 0 or benchmark_config["eth_units"] > 0):
            current_prices = self.get_current_prices()
            benchmark_value = (
                benchmark_config["btc_units"] * current_prices.btc_price +
                benchmark_config["eth_units"] * current_prices.eth_price
            )
        
        return {
            "account_name": account.account_name,
            "initial_balance": account.initial_balance,
            "current_nav": current_nav,
            "total_return": total_return,
            "return_percentage": return_pct,
            "benchmark_value": benchmark_value,
            "vs_benchmark": current_nav - benchmark_value if benchmark_value > 0 else 0,
            "transaction_count": len([t for t in self.data["transactions"] if t["account_id"] == account_id])
        }


# Global mock data manager instance
mock_manager = MockDataManager()


def get_mock_manager() -> MockDataManager:
    """Get the global mock data manager instance."""
    return mock_manager


# Mock implementations for main API functions
class MockBinanceClient:
    """Mock Binance client for testing."""
    
    def __init__(self, api_key: str, api_secret: str, **kwargs):
        self.api_key = api_key
        self.api_secret = api_secret
        self.mock_manager = get_mock_manager()
    
    def futures_account(self) -> Dict:
        """Mock futures account data."""
        account = self.mock_manager.get_account(1)  # Default to account 1
        if not account:
            raise Exception("Mock account not found")
        
        return {
            'totalWalletBalance': str(account.current_balance),
            'totalUnrealizedProfit': str(account.unrealized_pnl)
        }
    
    def get_symbol_ticker(self, symbol: str) -> Dict:
        """Mock price ticker data."""
        prices = self.mock_manager.get_current_prices()
        
        price_map = {
            'BTCUSDT': str(prices.btc_price),
            'ETHUSDT': str(prices.eth_price)
        }
        
        if symbol not in price_map:
            raise Exception(f"Unknown symbol: {symbol}")
        
        return {'price': price_map[symbol]}
    
    def get_deposit_history(self, **kwargs) -> List[Dict]:
        """Mock deposit history."""
        start_time = kwargs.get('startTime', 0)
        start_timestamp = datetime.fromtimestamp(start_time / 1000, UTC).isoformat()
        
        transactions = self.mock_manager.get_transactions_since(1, start_timestamp)
        deposits = [t for t in transactions if t.type == 'DEPOSIT']
        
        return [
            {
                'txId': t.id.replace('MOCK_DEPOSIT_', ''),
                'amount': str(t.amount),
                'insertTime': int(datetime.fromisoformat(t.timestamp.replace('Z', '+00:00')).timestamp() * 1000),
                'status': 1 if t.status == 'SUCCESS' else 0
            }
            for t in deposits
        ]
    
    def get_withdraw_history(self, **kwargs) -> List[Dict]:
        """Mock withdrawal history."""
        start_time = kwargs.get('startTime', 0)
        start_timestamp = datetime.fromtimestamp(start_time / 1000, UTC).isoformat()
        
        transactions = self.mock_manager.get_transactions_since(1, start_timestamp)
        withdrawals = [t for t in transactions if t.type == 'WITHDRAWAL']
        
        return [
            {
                'id': t.id.replace('MOCK_WITHDRAWAL_', ''),
                'amount': str(t.amount),
                'applyTime': int(datetime.fromisoformat(t.timestamp.replace('Z', '+00:00')).timestamp() * 1000),
                'status': 1 if t.status == 'SUCCESS' else 0
            }
            for t in withdrawals
        ]


if __name__ == "__main__":
    # Demo usage
    manager = get_mock_manager()
    
    print("🎮 Mock Mode Demo")
    print("=" * 50)
    
    # Show initial state
    summary = manager.get_performance_summary(1)
    print(f"Initial NAV: ${summary['current_nav']:,.2f}")
    
    # Simulate some transactions
    print("\n📈 Adding $5000 deposit...")
    manager.add_transaction(1, "DEPOSIT", 5000.0)
    
    print("📉 Adding $2000 withdrawal...")
    manager.add_transaction(1, "WITHDRAWAL", 2000.0)
    
    # Simulate market movement
    print("\n🎯 Simulating bull run...")
    manager.simulate_market_scenario("bull_run")
    
    # Show final state
    summary = manager.get_performance_summary(1)
    print(f"\nFinal NAV: ${summary['current_nav']:,.2f}")
    print(f"Total Return: ${summary['total_return']:,.2f} ({summary['return_percentage']:.2f}%)")
    
    current_prices = manager.get_current_prices()
    print(f"BTC: ${current_prices.btc_price:,.2f} | ETH: ${current_prices.eth_price:,.2f}")