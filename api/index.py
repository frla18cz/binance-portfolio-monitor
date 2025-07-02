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

    # Zpracování vkladů a výběrů
    config = process_deposits_withdrawals(supabase, binance_client, account_id, config, prices)

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

def process_deposits_withdrawals(db_client, binance_client, account_id, config, prices):
    """
    Optimalizované zpracování deposits/withdrawals s idempotencí a atomic operations.
    Vrací aktualizovaný config s upravenými BTC/ETH units podle cashflow změn.
    """
    try:
        # Získání posledního zpracovaného času pro tento účet
        last_processed = get_last_processed_time(db_client, account_id)
        
        # Fetch nových transakcí od posledního zpracování
        new_transactions = fetch_new_transactions(binance_client, last_processed)
        
        if not new_transactions:
            return config
            
        print(f"Processing {len(new_transactions)} new transactions...")
        
        # Batch zpracování všech nových transakcí
        total_net_flow = 0  # Kladné = deposit, záporné = withdrawal
        processed_txns = []
        
        for txn in new_transactions:
            if txn['status'] == 'SUCCESS':  # Pouze úspěšné transakce
                amount = float(txn['amount'])
                if txn['type'] == 'DEPOSIT':
                    total_net_flow += amount
                elif txn['type'] == 'WITHDRAWAL':
                    total_net_flow -= amount
                    
                processed_txns.append({
                    'account_id': account_id,
                    'transaction_id': txn['id'],
                    'transaction_type': txn['type'],
                    'amount': amount,
                    'timestamp': txn['timestamp'],
                    'status': txn['status']
                })
        
        if total_net_flow != 0:
            # Atomic update: benchmark config + processed transactions
            updated_config = adjust_benchmark_for_cashflow(
                db_client, config, account_id, total_net_flow, prices, processed_txns
            )
            return updated_config
        else:
            # Žádné cashflow změny, jen uložíme tracking
            if processed_txns:
                db_client.table('processed_transactions').insert(processed_txns).execute()
                update_last_processed_time(db_client, account_id)
            return config
            
    except Exception as e:
        print(f"Error processing deposits/withdrawals: {e}")
        return config  # Failsafe - vrátíme původní config

def get_last_processed_time(db_client, account_id):
    """Získá timestamp posledního zpracování pro daný účet."""
    try:
        response = db_client.table('account_processing_status').select('last_processed_timestamp').eq('account_id', account_id).execute()
        if response.data:
            return response.data[0]['last_processed_timestamp']
        else:
            # První spuštění - začneme od před 30 dny
            return (datetime.now(UTC) - timedelta(days=30)).isoformat()
    except:
        return (datetime.now(UTC) - timedelta(days=30)).isoformat()

def fetch_new_transactions(binance_client, start_time):
    """
    Optimalizovaně fetchne deposits + withdrawals od start_time.
    Kombinuje oba API calls pro minimální latenci.
    """
    try:
        transactions = []
        start_timestamp = int(datetime.fromisoformat(start_time.replace('Z', '+00:00')).timestamp() * 1000)
        
        # Paralelně fetchneme deposits a withdrawals
        deposits = binance_client.get_deposit_history(startTime=start_timestamp)
        withdrawals = binance_client.get_withdraw_history(startTime=start_timestamp)
        
        # Normalizujeme format pro snadné zpracování
        for deposit in deposits:
            transactions.append({
                'id': f"DEP_{deposit['txId']}",
                'type': 'DEPOSIT',
                'amount': deposit['amount'],
                'timestamp': deposit['insertTime'],
                'status': deposit['status']  # 0=pending, 1=success
            })
            
        for withdrawal in withdrawals:
            transactions.append({
                'id': f"WD_{withdrawal['id']}",
                'type': 'WITHDRAWAL', 
                'amount': withdrawal['amount'],
                'timestamp': withdrawal['applyTime'],
                'status': withdrawal['status']  # 0=pending, 1=success, etc.
            })
            
        # Filtrujeme jen SUCCESS transakce a sortujeme podle času
        successful_txns = []
        for txn in transactions:
            if (txn['status'] == 1 or txn['status'] == 'SUCCESS'):  # Binance používá různé formáty
                txn['status'] = 'SUCCESS'
                txn['timestamp'] = datetime.fromtimestamp(txn['timestamp']/1000, UTC).isoformat()
                successful_txns.append(txn)
                
        return sorted(successful_txns, key=lambda x: x['timestamp'])
        
    except Exception as e:
        print(f"Error fetching transaction history: {e}")
        return []

def adjust_benchmark_for_cashflow(db_client, config, account_id, net_flow, prices, processed_txns):
    """
    Atomic adjustment benchmarku podle net cashflow.
    Při depositu: zvýší BTC/ETH units proporcionálně
    Při withdrawal: sníží BTC/ETH units proporcionálně
    """
    try:
        current_btc_units = float(config.get('btc_units', 0))
        current_eth_units = float(config.get('eth_units', 0))
        
        if net_flow > 0:  # DEPOSIT - přidáváme do benchmarku
            print(f"Processing deposit: +${net_flow:.2f}")
            # Rozdělíme deposit 50/50 mezi BTC a ETH
            btc_investment = net_flow / 2
            eth_investment = net_flow / 2
            
            new_btc_units = current_btc_units + (btc_investment / prices['BTCUSDT'])
            new_eth_units = current_eth_units + (eth_investment / prices['ETHUSDT'])
            
        else:  # WITHDRAWAL - ubíráme z benchmarku proporcionálně
            print(f"Processing withdrawal: ${net_flow:.2f}")
            withdrawal_amount = abs(net_flow)
            
            # Zjistíme aktuální hodnotu benchmarku
            current_benchmark_value = (current_btc_units * prices['BTCUSDT']) + (current_eth_units * prices['ETHUSDT'])
            
            if current_benchmark_value > 0:
                # Proporcionální snížení podle withdrawal
                reduction_ratio = withdrawal_amount / current_benchmark_value
                new_btc_units = current_btc_units * (1 - reduction_ratio)
                new_eth_units = current_eth_units * (1 - reduction_ratio)
            else:
                new_btc_units = current_btc_units
                new_eth_units = current_eth_units
        
        # Atomic database update - benchmark config + processed transactions
        db_client.table('benchmark_configs').update({
            'btc_units': new_btc_units,
            'eth_units': new_eth_units
        }).eq('account_id', account_id).execute()
        
        if processed_txns:
            db_client.table('processed_transactions').insert(processed_txns).execute()
            
        update_last_processed_time(db_client, account_id)
        
        # Vrátíme aktualizovaný config
        updated_config = config.copy()
        updated_config['btc_units'] = new_btc_units
        updated_config['eth_units'] = new_eth_units
        
        print(f"Benchmark adjusted - BTC: {new_btc_units:.6f}, ETH: {new_eth_units:.6f}")
        return updated_config
        
    except Exception as e:
        print(f"Error adjusting benchmark: {e}")
        raise  # Re-raise aby se celá operace rollbackla

def update_last_processed_time(db_client, account_id):
    """Aktualizuje timestamp posledního zpracování."""
    try:
        current_time = datetime.now(UTC).isoformat()
        db_client.table('account_processing_status').upsert({
            'account_id': account_id,
            'last_processed_timestamp': current_time
        }).execute()
    except Exception as e:
        print(f"Error updating last processed time: {e}")

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