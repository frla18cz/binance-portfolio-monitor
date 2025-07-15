#!/usr/bin/env python3
"""
Test script for Binance API access from AWS
Tests both public (price) and private (account) API endpoints
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from binance.client import Client as BinanceClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_server_info():
    """Get information about the server/instance"""
    info = {
        "timestamp": datetime.now().isoformat(),
        "python_version": sys.version,
        "platform": sys.platform
    }
    
    # Try to get AWS metadata
    try:
        # AWS EC2 instance metadata
        token_response = requests.put(
            "http://169.254.169.254/latest/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
            timeout=1
        )
        token = token_response.text
        
        metadata_response = requests.get(
            "http://169.254.169.254/latest/meta-data/placement/region",
            headers={"X-aws-ec2-metadata-token": token},
            timeout=1
        )
        info["aws_region"] = metadata_response.text
        
        instance_response = requests.get(
            "http://169.254.169.254/latest/meta-data/instance-id",
            headers={"X-aws-ec2-metadata-token": token},
            timeout=1
        )
        info["aws_instance_id"] = instance_response.text
        
        # Get public IP
        ip_response = requests.get(
            "http://169.254.169.254/latest/meta-data/public-ipv4",
            headers={"X-aws-ec2-metadata-token": token},
            timeout=1
        )
        info["aws_public_ip"] = ip_response.text
    except:
        info["aws_info"] = "Not running on AWS EC2"
    
    # Get external IP as seen by the internet
    try:
        ip_check = requests.get("https://api.ipify.org?format=json", timeout=5)
        info["external_ip"] = ip_check.json().get("ip")
    except:
        info["external_ip"] = "Unable to determine"
    
    return info

def test_public_api():
    """Test public API endpoints (prices)"""
    print("\n=== Testing Public API (Prices) ===")
    results = {}
    
    # Test regular Binance API
    print("\n1. Testing regular Binance API...")
    try:
        client = BinanceClient('', '')
        ticker = client.get_symbol_ticker(symbol='BTCUSDT')
        results["regular_api"] = {
            "status": "SUCCESS",
            "btc_price": float(ticker['price']),
            "api_url": client.API_URL
        }
        print(f"✅ Regular API works! BTC Price: ${ticker['price']}")
    except Exception as e:
        results["regular_api"] = {
            "status": "FAILED",
            "error": str(e),
            "error_type": type(e).__name__
        }
        print(f"❌ Regular API failed: {e}")
    
    # Test data API
    print("\n2. Testing data-api.binance.vision...")
    try:
        client = BinanceClient('', '')
        client.API_URL = 'https://data-api.binance.vision/api'
        ticker = client.get_symbol_ticker(symbol='BTCUSDT')
        results["data_api"] = {
            "status": "SUCCESS",
            "btc_price": float(ticker['price']),
            "api_url": client.API_URL
        }
        print(f"✅ Data API works! BTC Price: ${ticker['price']}")
    except Exception as e:
        results["data_api"] = {
            "status": "FAILED",
            "error": str(e),
            "error_type": type(e).__name__
        }
        print(f"❌ Data API failed: {e}")
    
    return results

def test_private_api():
    """Test private API endpoints (account data)"""
    print("\n=== Testing Private API (Account Data) ===")
    results = {}
    
    # Get API credentials
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        print("⚠️  No API credentials found in environment variables")
        print("   Set BINANCE_API_KEY and BINANCE_API_SECRET to test private endpoints")
        return {"status": "SKIPPED", "reason": "No API credentials"}
    
    print("\n1. Testing account status...")
    try:
        client = BinanceClient(api_key, api_secret)
        account = client.get_account_status()
        results["account_status"] = {
            "status": "SUCCESS",
            "data": account
        }
        print(f"✅ Account status retrieved: {account}")
    except Exception as e:
        results["account_status"] = {
            "status": "FAILED",
            "error": str(e),
            "error_type": type(e).__name__
        }
        print(f"❌ Account status failed: {e}")
    
    print("\n2. Testing account balance...")
    try:
        client = BinanceClient(api_key, api_secret)
        account = client.get_account()
        
        # Get non-zero balances
        balances = [b for b in account['balances'] if float(b['free']) > 0 or float(b['locked']) > 0]
        
        results["account_balance"] = {
            "status": "SUCCESS",
            "balances_count": len(balances),
            "sample_balances": balances[:3] if balances else []
        }
        print(f"✅ Account balance retrieved: {len(balances)} non-zero balances")
        if balances:
            for b in balances[:3]:
                print(f"   {b['asset']}: {b['free']} (free) + {b['locked']} (locked)")
    except Exception as e:
        results["account_balance"] = {
            "status": "FAILED",
            "error": str(e),
            "error_type": type(e).__name__
        }
        print(f"❌ Account balance failed: {e}")
    
    print("\n3. Testing different wallet types...")
    wallet_tests = [
        ("funding_wallet", lambda c: c.funding_wallet()),
        ("get_asset_balance", lambda c: c.get_asset_balance(asset='USDT'))
    ]
    
    for wallet_name, wallet_func in wallet_tests:
        try:
            result = wallet_func(client)
            results[wallet_name] = {
                "status": "SUCCESS",
                "data": result
            }
            print(f"✅ {wallet_name}: {result}")
        except Exception as e:
            results[wallet_name] = {
                "status": "FAILED",
                "error": str(e),
                "error_type": type(e).__name__
            }
            print(f"❌ {wallet_name} failed: {e}")
    
    return results

def test_connectivity():
    """Test basic connectivity to various endpoints"""
    print("\n=== Testing Basic Connectivity ===")
    endpoints = [
        ("Binance.com", "https://api.binance.com/api/v3/ping"),
        ("Binance.vision", "https://data-api.binance.vision/api/v3/ping"),
        ("Binance EU", "https://api1.binance.com/api/v3/ping"),
        ("Binance US", "https://api.binance.us/api/v3/ping"),
    ]
    
    results = {}
    for name, url in endpoints:
        try:
            start = time.time()
            response = requests.get(url, timeout=5)
            elapsed = time.time() - start
            results[name] = {
                "status": "SUCCESS",
                "status_code": response.status_code,
                "response_time_ms": round(elapsed * 1000, 2)
            }
            print(f"✅ {name}: {response.status_code} ({elapsed*1000:.0f}ms)")
        except Exception as e:
            results[name] = {
                "status": "FAILED",
                "error": str(e)
            }
            print(f"❌ {name}: {e}")
    
    return results

def save_results(all_results):
    """Save test results to file"""
    filename = f"binance_api_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n📄 Results saved to: {filename}")
    return filename

def main():
    """Run all tests"""
    print("🚀 Binance API Test Script for AWS")
    print("=" * 50)
    
    # Get server information
    server_info = get_server_info()
    print("\n📍 Server Information:")
    for key, value in server_info.items():
        print(f"   {key}: {value}")
    
    # Run tests
    all_results = {
        "server_info": server_info,
        "connectivity": test_connectivity(),
        "public_api": test_public_api(),
        "private_api": test_private_api()
    }
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    
    # Check if we can access prices
    if all_results["public_api"].get("data_api", {}).get("status") == "SUCCESS":
        print("✅ Price data accessible via data-api.binance.vision")
    else:
        print("❌ Cannot access price data")
    
    # Check if we can access account data
    private_results = all_results.get("private_api", {})
    if isinstance(private_results, dict) and private_results.get("status") != "SKIPPED":
        success_count = sum(1 for k, v in private_results.items() 
                          if isinstance(v, dict) and v.get("status") == "SUCCESS")
        total_count = len([k for k, v in private_results.items() if isinstance(v, dict)])
        if success_count > 0:
            print(f"✅ Private API partially working ({success_count}/{total_count} endpoints)")
        else:
            print("❌ Private API not accessible")
    
    # Save results
    save_results(all_results)
    
    # Recommendations
    print("\n💡 Recommendations:")
    if all_results["public_api"].get("regular_api", {}).get("status") == "FAILED":
        print("- Use data-api.binance.vision for public endpoints (already implemented)")
    
    if private_results.get("account_balance", {}).get("status") == "FAILED":
        error = private_results.get("account_balance", {}).get("error", "")
        if "restricted location" in error.lower():
            print("- Private API blocked from this location")
            print("- Consider: AWS region change, VPN gateway, or proxy solution")
            print("- Try EU regions: eu-central-1 (Frankfurt), eu-west-1 (Ireland)")

if __name__ == "__main__":
    main()