"""
Mock Supabase client for demo mode testing.
Simulates database operations without connecting to real Supabase.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, UTC, timedelta
import json
import os


class MockSupabaseResponse:
    """Mock response from Supabase operations."""
    
    def __init__(self, data: List[Dict] = None, error: Any = None):
        self.data = data or []
        self.error = error
    
    def execute(self):
        """Mock execute method."""
        return self


class MockSupabaseTable:
    """Mock Supabase table operations."""
    
    def __init__(self, table_name: str, mock_client):
        self.table_name = table_name
        self.mock_client = mock_client
        self._query_filters = {}
        self._query_select = "*"
        self._query_data = None
        self._query_operation = None
    
    def select(self, columns: str = "*"):
        """Mock select operation."""
        self._query_select = columns
        self._query_operation = "select"
        return self
    
    def insert(self, data: Dict or List[Dict]):
        """Mock insert operation."""
        self._query_data = data
        self._query_operation = "insert"
        return self
    
    def update(self, data: Dict):
        """Mock update operation."""
        self._query_data = data
        self._query_operation = "update"
        return self
    
    def upsert(self, data: Dict or List[Dict]):
        """Mock upsert operation."""
        self._query_data = data
        self._query_operation = "upsert"
        return self
    
    def eq(self, column: str, value: Any):
        """Mock equality filter."""
        self._query_filters[column] = value
        return self
    
    def execute(self):
        """Execute the mock query."""
        return self.mock_client._execute_query(
            self.table_name,
            self._query_operation,
            self._query_data,
            self._query_filters,
            self._query_select
        )


class MockSupabaseClient:
    """Mock Supabase client for demo mode."""
    
    def __init__(self, data_file: str = "mock_supabase_data.json"):
        self.data_file = data_file
        self.data = self._load_data()
    
    def _load_data(self) -> Dict:
        """Load mock database data."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return self._create_default_data()
    
    def _save_data(self):
        """Save mock database data."""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Error saving mock database: {e}")
    
    def _create_default_data(self) -> Dict:
        """Create default mock database."""
        now = datetime.now(UTC).isoformat()
        
        return {
            "binance_accounts": [
                {
                    "id": 1,
                    "account_name": "Demo Trading Account",
                    "api_key": "demo_api_key",
                    "api_secret": "demo_api_secret",
                    "created_at": now,
                    "benchmark_configs": {
                        "id": 1,
                        "account_id": 1,
                        "btc_units": 0.0769230769,  # Will be initialized
                        "eth_units": 1.4285714286,  # Will be initialized  
                        "rebalance_day": 0,
                        "rebalance_hour": 12,
                        "next_rebalance_timestamp": f"2025-07-07T12:00:00+00:00",
                        "created_at": now
                    }
                }
            ],
            "benchmark_configs": [
                {
                    "id": 1,
                    "account_id": 1,
                    "btc_units": 0.0769230769,
                    "eth_units": 1.4285714286,
                    "rebalance_day": 0,
                    "rebalance_hour": 12,
                    "next_rebalance_timestamp": f"2025-07-07T12:00:00+00:00",
                    "created_at": now
                }
            ],
            "nav_history": [],
            "processed_transactions": [],
            "account_processing_status": [
                {
                    "account_id": 1,
                    "last_processed_timestamp": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
                    "updated_at": now
                }
            ]
        }
    
    def table(self, table_name: str) -> MockSupabaseTable:
        """Get mock table interface."""
        return MockSupabaseTable(table_name, self)
    
    def _execute_query(self, table_name: str, operation: str, data: Any, filters: Dict, select_cols: str) -> MockSupabaseResponse:
        """Execute mock database query."""
        try:
            if table_name not in self.data:
                self.data[table_name] = []
            
            table_data = self.data[table_name]
            
            if operation == "select":
                # Apply filters
                result = table_data.copy()
                for column, value in filters.items():
                    result = [row for row in result if row.get(column) == value]
                
                return MockSupabaseResponse(data=result)
            
            elif operation == "insert":
                # Insert new records
                if isinstance(data, list):
                    for item in data:
                        if 'id' not in item and table_name != 'nav_history':
                            item['id'] = len(table_data) + 1
                        table_data.append(item)
                else:
                    if 'id' not in data and table_name != 'nav_history':
                        data['id'] = len(table_data) + 1
                    table_data.append(data)
                
                self._save_data()
                return MockSupabaseResponse(data=[data] if not isinstance(data, list) else data)
            
            elif operation == "update":
                # Update records matching filters
                updated_records = []
                for row in table_data:
                    matches = all(row.get(col) == val for col, val in filters.items())
                    if matches:
                        row.update(data)
                        updated_records.append(row)
                
                self._save_data()
                return MockSupabaseResponse(data=updated_records)
            
            elif operation == "upsert":
                # Upsert records
                if isinstance(data, list):
                    for item in data:
                        self._upsert_single_record(table_data, item, filters)
                else:
                    self._upsert_single_record(table_data, data, filters)
                
                self._save_data()
                return MockSupabaseResponse(data=[data] if not isinstance(data, list) else data)
            
            else:
                return MockSupabaseResponse(error=f"Unknown operation: {operation}")
        
        except Exception as e:
            print(f"Mock database error: {e}")
            return MockSupabaseResponse(error=str(e))
    
    def _upsert_single_record(self, table_data: List[Dict], record: Dict, filters: Dict):
        """Upsert a single record."""
        # Try to find existing record
        for i, row in enumerate(table_data):
            matches = all(row.get(col) == val for col, val in filters.items())
            if matches:
                table_data[i].update(record)
                return
        
        # If not found, insert new
        if 'id' not in record:
            record['id'] = len(table_data) + 1
        table_data.append(record)


# Global mock Supabase client
_mock_supabase_client = None

def get_mock_supabase_client() -> MockSupabaseClient:
    """Get global mock Supabase client."""
    global _mock_supabase_client
    if _mock_supabase_client is None:
        _mock_supabase_client = MockSupabaseClient()
    return _mock_supabase_client


if __name__ == "__main__":
    # Test mock Supabase
    client = get_mock_supabase_client()
    
    print("🧪 Testing Mock Supabase Client")
    print("=" * 40)
    
    # Test select
    accounts = client.table('binance_accounts').select('*').execute()
    print(f"Accounts found: {len(accounts.data)}")
    
    # Test insert
    result = client.table('nav_history').insert({
        'account_id': 1,
        'timestamp': datetime.now(UTC).isoformat(),
        'nav': '10500.00',
        'benchmark_value': '10000.00'
    }).execute()
    print(f"NAV history inserted: {len(result.data)} records")
    
    # Test update
    update_result = client.table('benchmark_configs').update({
        'btc_units': 0.15,
        'eth_units': 2.0
    }).eq('account_id', 1).execute()
    print(f"Benchmark config updated: {len(update_result.data)} records")
    
    print("✅ Mock Supabase client working!")