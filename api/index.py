import os
import traceback
from datetime import datetime, timedelta, UTC
from dotenv import load_dotenv
from http.server import BaseHTTPRequestHandler
from supabase import create_client, Client
from binance.client import Client as BinanceClient

# Načtení proměnných z .env souboru
load_dotenv()

# --- Globální klienti ---
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_ANON_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# --- Hlavní handler pro Vercel ---
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        print("Cron job triggered. Starting the monitoring process...")
        try:
            process_all_accounts()
            self.send_response(200)
            self.send_header('Content-type','text/plain')
            self.end_headers()
            self.wfile.write('Monitoring process completed successfully.'.encode('utf-8'))
        except Exception as e:
            print(f"An error occurred during the main process: {e}")
            traceback.print_exc()
            self.send_response(500)
            self.send_header('Content-type','text/plain')
            self.end_headers()
            self.wfile.write(f'Error: {e}'.encode('utf-8'))
        return

# --- Hlavní logika ---
def process_all_accounts():
    """Získá všechny účty z DB a spustí pro ně monitorovací proces."""
    response = supabase.table('binance_accounts').select('*, benchmark_configs(*)').execute()
    if not response.data:
        print("No accounts found in the database.")
        return

    print(f"Found {len(response.data)} accounts to process.")
    for account in response.data:
        print(f"--- Processing account: {account.get('account_name')} ---")
        try:
            process_single_account(account)
        except Exception as e:
            print(f"Failed to process account {account.get('account_name')}. Error: {e}")
            traceback.print_exc()

def process_single_account(account):
    """Kompletní logika pro jeden Binance účet."""
    api_key = account.get('api_key')
    api_secret = account.get('api_secret')
    account_id = account.get('id')
    config = account.get('benchmark_configs')

    if not config:
        print("Benchmark config not found for this account. Skipping.")
        return
    if isinstance(config, list):
        config = config[0]

    if not all([api_key, api_secret, account_id, config]):
        print("Account data is incomplete. Skipping.")
        return

    binance_client = BinanceClient(api_key, api_secret, tld='com')
    
    prices = get_prices(binance_client)
    if not prices:
        return

    nav = get_futures_account_nav(binance_client)
    if nav is None:
        return

    if not config.get('btc_units') and not config.get('eth_units'):
        print("Benchmark not initialized. Initializing now...")
        config = initialize_benchmark(supabase, config, account_id, nav, prices)

    # Zpracování vkladů a výběrů (bude implementováno)

    # Kontrola a provedení rebalance
    now_utc = datetime.now(UTC)
    next_rebalance_str = config.get('next_rebalance_timestamp')
    if next_rebalance_str:
        next_rebalance_dt = datetime.fromisoformat(next_rebalance_str.replace('Z', '+00:00').replace('+00:00', ''))
        if now_utc >= next_rebalance_dt:
            print("Rebalance time reached. Rebalancing benchmark...")
            benchmark_value = calculate_benchmark_value(config, prices)
            config = rebalance_benchmark(supabase, config, account_id, benchmark_value, prices)

    benchmark_value = calculate_benchmark_value(config, prices)
    save_history(supabase, account_id, nav, benchmark_value)

# --- Pomocné funkce ---

def get_prices(client):
    try:
        prices = {}
        for symbol in ["BTCUSDT", "ETHUSDT"]:
            ticker = client.get_symbol_ticker(symbol=symbol)
            prices[symbol] = float(ticker['price'])
        return prices
    except Exception as e:
        print(f"Error getting prices: {e}")
        return None

def get_futures_account_nav(client):
    try:
        info = client.futures_account()
        nav = float(info['totalWalletBalance']) + float(info['totalUnrealizedProfit'])
        return nav
    except Exception as e:
        print(f"Error getting NAV: {e}")
        return None

def calculate_next_rebalance_time(now, rebalance_day, rebalance_hour):
    days_ahead = (rebalance_day - now.weekday() + 7) % 7
    if days_ahead == 0 and now.hour >= rebalance_hour:
        days_ahead = 7
    next_date = now.date() + timedelta(days=days_ahead)
    return datetime.combine(next_date, datetime.min.time()).replace(hour=rebalance_hour)

def initialize_benchmark(db_client, config, account_id, initial_nav, prices):
    print(f"Initializing benchmark with NAV: {initial_nav:.2f}")
    investment = initial_nav / 2
    btc_units = investment / prices['BTCUSDT']
    eth_units = investment / prices['ETHUSDT']
    
    next_rebalance = calculate_next_rebalance_time(
        datetime.now(UTC), config['rebalance_day'], config['rebalance_hour']
    )

    response = db_client.table('benchmark_configs').update({
        'btc_units': btc_units,
        'eth_units': eth_units,
        'next_rebalance_timestamp': next_rebalance.isoformat() + '+00:00'
    }).eq('account_id', account_id).execute()
    print(f"Benchmark initialized. Next rebalance: {next_rebalance}")
    return response.data[0]

def rebalance_benchmark(db_client, config, account_id, current_value, prices):
    print(f"Rebalancing benchmark with current value: {current_value:.2f}")
    investment = current_value / 2
    btc_units = investment / prices['BTCUSDT']
    eth_units = investment / prices['ETHUSDT']

    next_rebalance = calculate_next_rebalance_time(
        datetime.now(UTC), config['rebalance_day'], config['rebalance_hour']
    )

    response = db_client.table('benchmark_configs').update({
        'btc_units': btc_units,
        'eth_units': eth_units,
        'next_rebalance_timestamp': next_rebalance.isoformat() + '+00:00'
    }).eq('account_id', account_id).execute()
    print(f"Benchmark rebalanced. Next rebalance: {next_rebalance}")
    return response.data[0]

def calculate_benchmark_value(config, prices):
    btc_val = (float(config.get('btc_units') or 0)) * prices['BTCUSDT']
    eth_val = (float(config.get('eth_units') or 0)) * prices['ETHUSDT']
    return btc_val + eth_val

def save_history(db_client, account_id, nav, benchmark_value):
    timestamp = datetime.now(UTC).isoformat()
    print(f"{timestamp} | NAV: {nav:.2f} | Benchmark: {benchmark_value:.2f}")
    db_client.table('nav_history').insert({
        'account_id': account_id,
        'timestamp': timestamp,
        'nav': f'{nav:.2f}',
        'benchmark_value': f'{benchmark_value:.2f}'
    }).execute()

# Tento blok je pro lokální testování, Vercel ho ignoruje
if __name__ == "__main__":
    print("Running script locally for testing...")
    process_all_accounts()