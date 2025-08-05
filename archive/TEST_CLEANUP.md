# Test Cleanup Documentation

## Overview
This document describes the test cleanup performed on the Binance Portfolio Monitor project to consolidate and streamline the test suite.

## Changes Made

### Removed Redundant Tests
The following test files were removed from the root directory as they were exploratory/debugging scripts or duplicates:

1. **test_pay_api_direct.py** - Direct Pay API calls (exploratory)
2. **test_pay_api_from_db.py** - Pay API with DB credentials (exploratory)
3. **test_pay_api_structure.py** - Pay API structure verification (exploratory)
4. **test_raw_api_call.py** - Raw API testing (exploratory)
5. **test_mixed_transactions.py** - Duplicate of pay integration tests
6. **test_pay_transactions.py** - Basic version superseded by integration test

### Consolidated Tests
- **test_pay_integration_final.py** → **tests/test_pay_integration.py**
  - This comprehensive test covers all Pay transaction functionality
  - Moved to the tests directory for consistency

## Final Test Structure

```
tests/
├── conftest.py                    # Pytest fixtures and configuration
├── test_api_functions.py          # Unit tests for API functions
├── test_benchmark_functions.py    # Tests for benchmark calculations
├── test_handler.py                # Tests for the main handler function
├── test_integration.py            # Integration tests for the system
├── test_pay_integration.py        # Comprehensive Pay transaction tests
├── test_simulated_transfers.py    # Tests for simulated transfers
├── test_transaction_processing.py # Transaction processing logic tests
└── test_withdrawal_detection.py   # Withdrawal detection tests

scripts/
├── check_historical_transfers.py  # Utility to analyze historical transfers
└── debug_transactions.py          # Debug tool for transaction details
```

### Additional Changes
- Moved utility scripts from `tests/` to `scripts/` directory to keep tests pure

## Test Coverage

### Core Functionality Tests
- **API Functions**: Reading NAV, fetching prices, interacting with Binance
- **Benchmark Logic**: 50/50 BTC/ETH calculation and rebalancing
- **Transaction Processing**: Deposits, withdrawals, and Pay transactions
- **Integration**: End-to-end system behavior

### Special Features
- **Pay Transactions**: Comprehensive testing of Binance Pay detection
- **Simulated Transfers**: Testing transfer simulation logic
- **Withdrawal Detection**: Edge cases for withdrawal processing

## Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_pay_integration.py

# Run with coverage
pytest tests/ --cov=api --cov-report=html

# Run with verbose output
pytest tests/ -v
```

## Maintenance Guidelines

1. **All new tests** should be placed in the `tests/` directory
2. **Use fixtures** from `conftest.py` for common test setup
3. **Follow naming convention**: `test_<functionality>.py`
4. **Group related tests** in the same file
5. **Avoid exploratory scripts** in the main codebase

## Benefits of Cleanup

1. **Reduced Confusion**: No duplicate tests with similar names
2. **Faster Test Runs**: Removed redundant test executions
3. **Clear Structure**: All tests in one location
4. **Better Maintenance**: Easier to find and update tests
5. **Proper Organization**: Following pytest best practices