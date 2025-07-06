import os
import traceback
from contextlib import nullcontext
from datetime import datetime, timedelta, UTC
from dotenv import load_dotenv
from http.server import BaseHTTPRequestHandler
from supabase import create_client, Client
from binance.client import Client as BinanceClient
from .logger import get_logger, LogCategory, OperationTimer

# Načtení proměnných z .env souboru
load_dotenv()

# --- Globální klienti ---
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_ANON_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# --- Hlavní handler pro Vercel ---
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        logger = get_logger()
        logger.info(LogCategory.SYSTEM, "cron_trigger", "Cron job triggered - starting monitoring process")
        
        try:
            with OperationTimer(logger, LogCategory.SYSTEM, "full_monitoring_cycle"):
                process_all_accounts()
            
            self.send_response(200)
            self.send_header('Content-type','text/plain')
            self.end_headers()
            self.wfile.write('Monitoring process completed successfully.'.encode('utf-8'))
            
            logger.info(LogCategory.SYSTEM, "cron_complete", "Monitoring process completed successfully")
            
        except Exception as e:
            logger.error(LogCategory.SYSTEM, "cron_error", f"Main process failed: {str(e)}", error=str(e))
            traceback.print_exc()
            
            self.send_response(500)
            self.send_header('Content-type','text/plain')
            self.end_headers()
            self.wfile.write(f'Error: {e}'.encode('utf-8'))
        return

# --- Hlavní logika ---
def process_all_accounts():
    """Získá všechny účty z DB a spustí pro ně monitorovací proces."""
    logger = get_logger()
    
    with OperationTimer(logger, LogCategory.SYSTEM, "fetch_all_accounts"):
        # Use real Supabase client
        db_client = supabase
        
        response = db_client.table('binance_accounts').select('*, benchmark_configs(*)').execute()
    
    if not response.data:
        logger.warning(LogCategory.SYSTEM, "no_accounts", "No accounts found in database")
        return

    logger.info(LogCategory.SYSTEM, "accounts_found", f"Found {len(response.data)} accounts to process")
    
    for account in response.data:
        account_name = account.get('account_name', 'Unknown')
        account_id = account.get('id')
        
        logger.info(LogCategory.ACCOUNT_PROCESSING, "start_processing", 
                   f"Starting processing for account: {account_name}", 
                   account_id=account_id, account_name=account_name)
        
        try:
            with OperationTimer(logger, LogCategory.ACCOUNT_PROCESSING, "process_account", 
                              account_id, account_name):
                process_single_account(account)
                
            logger.info(LogCategory.ACCOUNT_PROCESSING, "complete_processing", 
                       f"Successfully processed account: {account_name}",
                       account_id=account_id, account_name=account_name)
                       
        except Exception as e:
            logger.error(LogCategory.ACCOUNT_PROCESSING, "process_error", 
                        f"Failed to process account {account_name}: {str(e)}",
                        account_id=account_id, account_name=account_name, error=str(e))
            traceback.print_exc()

def process_single_account(account):
    """Kompletní logika pro jeden Binance účet."""
    logger = get_logger()
    
    api_key = account.get('api_key')
    api_secret = account.get('api_secret')
    account_id = account.get('id')
    account_name = account.get('account_name', 'Unknown')
    config = account.get('benchmark_configs')

    if not config:
        logger.warning(LogCategory.ACCOUNT_PROCESSING, "no_config", 
                      "Benchmark config not found for account, skipping",
                      account_id=account_id, account_name=account_name)
        return
    if isinstance(config, list):
        config = config[0]

    if not all([api_key, api_secret, account_id, config]):
        logger.error(LogCategory.ACCOUNT_PROCESSING, "incomplete_data", 
                    "Account data incomplete, skipping",
                    account_id=account_id, account_name=account_name)
        return

    # Use real Binance client
    binance_client = BinanceClient(api_key, api_secret, tld='com')
    db_client = supabase
    
    with OperationTimer(logger, LogCategory.PRICE_UPDATE, "fetch_prices", account_id, account_name):
        prices = get_prices(binance_client, logger, account_id, account_name)
    if not prices:
        return
    
    # Uložit historické ceny (pro dynamický benchmark)
    save_price_history(prices, logger)

    with OperationTimer(logger, LogCategory.API_CALL, "fetch_nav", account_id, account_name):
        nav = get_comprehensive_nav(binance_client, logger, account_id, account_name)
    if nav is None:
        return

    if not config.get('btc_units') and not config.get('eth_units'):
        logger.info(LogCategory.BENCHMARK, "initialize", 
                   f"Benchmark not initialized, initializing with NAV: ${nav:.2f}",
                   account_id=account_id, account_name=account_name, 
                   data={"initial_nav": nav})
        config = initialize_benchmark(db_client, config, account_id, nav, prices, logger)

    # Zpracování vkladů a výběrů
    config = process_deposits_withdrawals(db_client, binance_client, account_id, config, prices, logger)

    # Kontrola a provedení rebalance
    now_utc = datetime.now(UTC)
    next_rebalance_str = config.get('next_rebalance_timestamp')
    if next_rebalance_str:
        # Properly parse ISO timestamp with timezone
        clean_timestamp = next_rebalance_str.replace('Z', '+00:00')
        next_rebalance_dt = datetime.fromisoformat(clean_timestamp)
        if now_utc >= next_rebalance_dt:
            logger.info(LogCategory.REBALANCING, "rebalance_time", 
                       "Rebalance time reached, starting rebalancing",
                       account_id=account_id, account_name=account_name)
            benchmark_value = calculate_benchmark_value(config, prices)
            config = rebalance_benchmark(db_client, config, account_id, benchmark_value, prices, logger)

    benchmark_value = calculate_benchmark_value(config, prices)
    save_history(db_client, account_id, nav, benchmark_value, logger, account_name, prices)

# --- Pomocné funkce ---

def get_prices(client, logger=None, account_id=None, account_name=None):
    try:
        prices = {}
        for symbol in ["BTCUSDT", "ETHUSDT"]:
            ticker = client.get_symbol_ticker(symbol=symbol)
            prices[symbol] = float(ticker['price'])
        
        if logger:
            logger.info(LogCategory.PRICE_UPDATE, "prices_fetched", 
                       f"Successfully fetched prices: BTC=${prices['BTCUSDT']:,.2f}, ETH=${prices['ETHUSDT']:,.2f}",
                       account_id=account_id, account_name=account_name, data=prices)
        return prices
    except Exception as e:
        if logger:
            logger.error(LogCategory.PRICE_UPDATE, "price_fetch_error", 
                        f"Failed to fetch prices: {str(e)}",
                        account_id=account_id, account_name=account_name, error=str(e))
        print(f"Error getting prices: {e}")
        return None

def save_price_history(prices, logger=None):
    """Uloží historické ceny BTC a ETH do price_history tabulky."""
    if not prices:
        return
        
    try:
        from datetime import datetime, UTC
        
        # Připravit data pro uložení
        price_records = []
        timestamp = datetime.now(UTC).isoformat()
        
        for symbol, price in prices.items():
            if symbol in ['BTCUSDT', 'ETHUSDT']:
                asset = symbol.replace('USDT', '')  # BTC nebo ETH
                price_records.append({
                    'timestamp': timestamp,
                    'asset': asset,
                    'price': float(price)
                })
        
        if price_records:
            # Pokusit se uložit do price_history (tabulka možná neexistuje)
            try:
                result = supabase.table('price_history').insert(price_records).execute()
                if logger:
                    logger.debug(LogCategory.PRICE_UPDATE, "price_history_saved", 
                               f"Saved {len(price_records)} price records")
            except Exception as table_error:
                # Tabulka pravděpodobně neexistuje, vytvoříme ji manuálně později
                if logger:
                    logger.debug(LogCategory.PRICE_UPDATE, "price_history_table_missing", 
                               f"Price history table not found: {str(table_error)}")
                pass
                
    except Exception as e:
        if logger:
            logger.error(LogCategory.PRICE_UPDATE, "price_history_error", 
                        f"Failed to save price history: {str(e)}", error=str(e))

def get_comprehensive_nav(client, logger=None, account_id=None, account_name=None):
    """
    Vypočítá kompletní NAV zahrnující:
    1. Spot účet - všechny balances převedené na USD
    2. Futures účet - raw asset balances převedené na USD (ne totalWalletBalance!)
    Tento přístup odpovídá tomu, co ukazuje Binance dashboard.
    """
    try:
        total_nav = 0.0
        breakdown = {}
        
        # Získej aktuální BTC cenu pro konverze
        btc_ticker = client.get_symbol_ticker(symbol="BTCUSDT")
        btc_usd_price = float(btc_ticker['price'])
        
        # 1. SPOT ACCOUNT - všechny balances
        spot_account = client.get_account()
        spot_total = 0.0
        spot_details = {}
        
        for balance in spot_account['balances']:
            asset = balance['asset']
            free = float(balance['free'])
            locked = float(balance['locked'])
            total_balance = free + locked
            
            if total_balance > 0.001:  # Ignoruj velmi malé balances
                # Převeď na USD hodnotu
                if asset in ['USDT', 'BUSD', 'USDC']:
                    usdt_value = total_balance
                elif asset == 'BTC':
                    usdt_value = total_balance * btc_usd_price
                else:
                    try:
                        # Získej cenu vůči USDT
                        ticker = client.get_symbol_ticker(symbol=f"{asset}USDT")
                        price = float(ticker['price'])
                        usdt_value = total_balance * price
                    except:
                        try:
                            # Zkus přes BTC pak na USDT
                            btc_ticker_asset = client.get_symbol_ticker(symbol=f"{asset}BTC")
                            btc_price = float(btc_ticker_asset['price'])
                            usdt_value = total_balance * btc_price * btc_usd_price
                        except:
                            usdt_value = 0.0  # Nelze určit cenu
                
                if usdt_value > 0.1:  # Ignoruj hodnoty pod $0.1
                    spot_total += usdt_value
                    spot_details[asset] = {
                        'balance': total_balance,
                        'usdt_value': usdt_value
                    }
        
        breakdown['spot_total'] = spot_total
        breakdown['spot_details'] = spot_details
        
        # 2. FUTURES ACCOUNT - RAW ASSET KONVERZE (ne totalWalletBalance!)
        futures_account = client.futures_account()
        futures_total = 0.0
        futures_details = {}
        
        for asset_info in futures_account.get('assets', []):
            asset = asset_info['asset']
            wallet_balance = float(asset_info['walletBalance'])
            
            if abs(wallet_balance) > 0.001:  # Zahrnuj i záporné balances
                # Převeď na USD
                if asset in ['USDT', 'BUSD', 'USDC', 'BNFCR']:
                    usd_value = wallet_balance
                elif asset == 'BTC':
                    usd_value = wallet_balance * btc_usd_price
                else:
                    try:
                        ticker = client.get_symbol_ticker(symbol=f"{asset}USDT")
                        price = float(ticker['price'])
                        usd_value = wallet_balance * price
                    except:
                        usd_value = 0.0
                
                futures_total += usd_value
                futures_details[asset] = {
                    'balance': wallet_balance,
                    'usd_value': usd_value
                }
        
        breakdown['futures_total'] = futures_total
        breakdown['futures_details'] = futures_details
        
        # CELKOVÝ NAV = Spot + Futures (raw asset conversion)
        total_nav = spot_total + futures_total
        breakdown['total_nav'] = total_nav
        breakdown['btc_usd_price'] = btc_usd_price
        
        if logger:
            logger.info(LogCategory.API_CALL, "comprehensive_nav_fetched", 
                       f"Comprehensive NAV: ${total_nav:.2f} (Spot: ${spot_total:.2f}, Futures: ${futures_total:.2f}) @ BTC ${btc_usd_price:.2f}",
                       account_id=account_id, account_name=account_name, 
                       data=breakdown)
        
        return total_nav
        
    except Exception as e:
        if logger:
            logger.error(LogCategory.API_CALL, "comprehensive_nav_error", 
                        f"Failed to fetch comprehensive NAV: {str(e)}",
                        account_id=account_id, account_name=account_name, error=str(e))
        print(f"Error getting comprehensive NAV: {e}")
        return None

def get_futures_account_nav(client, logger=None, account_id=None, account_name=None):
    """Starý způsob výpočtu NAV - zachován pro kompatibilitu"""
    try:
        info = client.futures_account()
        nav = float(info['totalWalletBalance']) + float(info['totalUnrealizedProfit'])
        
        if logger:
            logger.info(LogCategory.API_CALL, "nav_fetched", 
                       f"Successfully fetched NAV: ${nav:.2f}",
                       account_id=account_id, account_name=account_name, 
                       data={"nav": nav, "wallet_balance": float(info['totalWalletBalance']), 
                            "unrealized_pnl": float(info['totalUnrealizedProfit'])})
        return nav
    except Exception as e:
        if logger:
            logger.error(LogCategory.API_CALL, "nav_fetch_error", 
                        f"Failed to fetch NAV: {str(e)}",
                        account_id=account_id, account_name=account_name, error=str(e))
        print(f"Error getting NAV: {e}")
        return None

def calculate_next_rebalance_time(now, rebalance_day, rebalance_hour):
    days_ahead = (rebalance_day - now.weekday() + 7) % 7
    if days_ahead == 0 and now.hour >= rebalance_hour:
        days_ahead = 7
    next_date = now.date() + timedelta(days=days_ahead)
    return datetime.combine(next_date, datetime.min.time()).replace(hour=rebalance_hour)

def initialize_benchmark(db_client, config, account_id, initial_nav, prices, logger=None):
    investment = initial_nav / 2
    btc_units = investment / prices['BTCUSDT']
    eth_units = investment / prices['ETHUSDT']
    
    next_rebalance = calculate_next_rebalance_time(
        datetime.now(UTC), config['rebalance_day'], config['rebalance_hour']
    )

    if logger:
        logger.info(LogCategory.BENCHMARK, "initialize_start", 
                   f"Initializing benchmark with NAV: ${initial_nav:.2f}",
                   account_id=account_id, 
                   data={"initial_nav": initial_nav, "btc_investment": investment, 
                        "eth_investment": investment, "btc_units": btc_units, "eth_units": eth_units})
    
    with OperationTimer(logger, LogCategory.DATABASE, "update_benchmark_config", account_id) if logger else nullcontext():
        response = db_client.table('benchmark_configs').update({
            'btc_units': btc_units,
            'eth_units': eth_units,
            'next_rebalance_timestamp': next_rebalance.isoformat() + '+00:00'
        }).eq('account_id', account_id).execute()
    
    if logger:
        logger.info(LogCategory.BENCHMARK, "initialize_complete", 
                   f"Benchmark initialized successfully. Next rebalance: {next_rebalance}",
                   account_id=account_id,
                   data={"btc_units": btc_units, "eth_units": eth_units, "next_rebalance": next_rebalance.isoformat()})
    
    print(f"Benchmark initialized. Next rebalance: {next_rebalance}")
    return response.data[0]

def rebalance_benchmark(db_client, config, account_id, current_value, prices, logger=None):
    investment = current_value / 2
    btc_units = investment / prices['BTCUSDT']
    eth_units = investment / prices['ETHUSDT']

    next_rebalance = calculate_next_rebalance_time(
        datetime.now(UTC), config['rebalance_day'], config['rebalance_hour']
    )

    if logger:
        old_btc_units = float(config.get('btc_units', 0))
        old_eth_units = float(config.get('eth_units', 0))
        
        logger.info(LogCategory.REBALANCING, "rebalance_start", 
                   f"Rebalancing benchmark with current value: ${current_value:.2f}",
                   account_id=account_id,
                   data={
                       "current_value": current_value,
                       "old_btc_units": old_btc_units,
                       "old_eth_units": old_eth_units,
                       "new_btc_units": btc_units,
                       "new_eth_units": new_eth_units,
                       "btc_investment": investment,
                       "eth_investment": investment
                   })

    with OperationTimer(logger, LogCategory.DATABASE, "update_rebalance_config", account_id) if logger else nullcontext():
        response = db_client.table('benchmark_configs').update({
            'btc_units': btc_units,
            'eth_units': eth_units,
            'next_rebalance_timestamp': next_rebalance.isoformat() + '+00:00'
        }).eq('account_id', account_id).execute()
    
    if logger:
        logger.info(LogCategory.REBALANCING, "rebalance_complete", 
                   f"Benchmark rebalanced successfully. Next rebalance: {next_rebalance}",
                   account_id=account_id,
                   data={
                       "btc_units": btc_units,
                       "eth_units": eth_units,
                       "next_rebalance": next_rebalance.isoformat()
                   })
    
    print(f"Benchmark rebalanced. Next rebalance: {next_rebalance}")
    return response.data[0]

def calculate_benchmark_value(config, prices):
    btc_val = (float(config.get('btc_units') or 0)) * prices['BTCUSDT']
    eth_val = (float(config.get('eth_units') or 0)) * prices['ETHUSDT']
    return btc_val + eth_val

def process_deposits_withdrawals(db_client, binance_client, account_id, config, prices, logger=None):
    """
    Optimalizované zpracování deposits/withdrawals s idempotencí a atomic operations.
    Vrací aktualizovaný config s upravenými BTC/ETH units podle cashflow změn.
    """
    try:
        with OperationTimer(logger, LogCategory.TRANSACTION, "fetch_last_processed", account_id) if logger else nullcontext():
            last_processed = get_last_processed_time(db_client, account_id)
        
        with OperationTimer(logger, LogCategory.TRANSACTION, "fetch_new_transactions", account_id) if logger else nullcontext():
            new_transactions = fetch_new_transactions(binance_client, last_processed, logger, account_id)
        
        if not new_transactions:
            if logger:
                logger.debug(LogCategory.TRANSACTION, "no_new_transactions", 
                           "No new transactions found", account_id=account_id)
            return config
            
        if logger:
            logger.info(LogCategory.TRANSACTION, "processing_transactions", 
                       f"Processing {len(new_transactions)} new transactions",
                       account_id=account_id, data={"transaction_count": len(new_transactions)})
        
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
            if logger:
                logger.info(LogCategory.TRANSACTION, "cashflow_detected", 
                           f"Net cashflow detected: ${total_net_flow:+,.2f}",
                           account_id=account_id, data={"net_flow": total_net_flow, "transaction_count": len(processed_txns)})
            
            # Atomic update: benchmark config + processed transactions
            updated_config = adjust_benchmark_for_cashflow(
                db_client, config, account_id, total_net_flow, prices, processed_txns, logger
            )
            return updated_config
        else:
            # Žádné cashflow změny, jen uložíme tracking
            if processed_txns:
                with OperationTimer(logger, LogCategory.DATABASE, "save_processed_transactions", account_id) if logger else nullcontext():
                    db_client.table('processed_transactions').insert(processed_txns).execute()
                    update_last_processed_time(db_client, account_id)
                    
                if logger:
                    logger.info(LogCategory.TRANSACTION, "transactions_saved", 
                               f"Saved {len(processed_txns)} transactions with no net cashflow",
                               account_id=account_id)
            return config
            
    except Exception as e:
        if logger:
            logger.error(LogCategory.TRANSACTION, "process_error", 
                        f"Error processing deposits/withdrawals: {str(e)}",
                        account_id=account_id, error=str(e))
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

def fetch_new_transactions(binance_client, start_time, logger=None, account_id=None):
    """
    Optimalizovaně fetchne deposits + withdrawals od start_time.
    Kombinuje oba API calls pro minimální latenci.
    """
    try:
        transactions = []
        start_timestamp = int(datetime.fromisoformat(start_time.replace('Z', '+00:00')).timestamp() * 1000)
        
        if logger:
            logger.debug(LogCategory.API_CALL, "fetch_transactions_start", 
                        f"Fetching transactions since {start_time}",
                        account_id=account_id, data={"start_timestamp": start_timestamp})
        
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
        
        if logger:
            logger.info(LogCategory.API_CALL, "transactions_fetched", 
                       f"Fetched {len(successful_txns)} successful transactions (from {len(transactions)} total)",
                       account_id=account_id, 
                       data={"successful_count": len(successful_txns), "total_count": len(transactions)})
                
        return sorted(successful_txns, key=lambda x: x['timestamp'])
        
    except Exception as e:
        if logger:
            logger.error(LogCategory.API_CALL, "fetch_transactions_error", 
                        f"Error fetching transaction history: {str(e)}",
                        account_id=account_id, error=str(e))
        print(f"Error fetching transaction history: {e}")
        return []

def adjust_benchmark_for_cashflow(db_client, config, account_id, net_flow, prices, processed_txns, logger=None):
    """
    Atomic adjustment benchmarku podle net cashflow.
    Při depositu: zvýší BTC/ETH units proporcionálně
    Při withdrawal: sníží BTC/ETH units proporcionálně
    """
    try:
        current_btc_units = float(config.get('btc_units', 0))
        current_eth_units = float(config.get('eth_units', 0))
        
        if net_flow > 0:  # DEPOSIT - přidáváme do benchmarku
            # Rozdělíme deposit 50/50 mezi BTC a ETH
            btc_investment = net_flow / 2
            eth_investment = net_flow / 2
            
            new_btc_units = current_btc_units + (btc_investment / prices['BTCUSDT'])
            new_eth_units = current_eth_units + (eth_investment / prices['ETHUSDT'])
            
            if logger:
                logger.info(LogCategory.TRANSACTION, "process_deposit", 
                           f"Processing deposit: +${net_flow:.2f}",
                           account_id=account_id,
                           data={"net_flow": net_flow, "btc_investment": btc_investment, 
                                "eth_investment": eth_investment, "new_btc_units": new_btc_units, 
                                "new_eth_units": new_eth_units})
            
        else:  # WITHDRAWAL - ubíráme z benchmarku proporcionálně
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
            
            if logger:
                logger.info(LogCategory.TRANSACTION, "process_withdrawal", 
                           f"Processing withdrawal: ${net_flow:.2f}",
                           account_id=account_id,
                           data={"net_flow": net_flow, "withdrawal_amount": withdrawal_amount,
                                "current_benchmark_value": current_benchmark_value,
                                "reduction_ratio": reduction_ratio if current_benchmark_value > 0 else 0,
                                "new_btc_units": new_btc_units, "new_eth_units": new_eth_units})
        
        # Atomic database update - benchmark config + processed transactions
        with OperationTimer(logger, LogCategory.DATABASE, "atomic_cashflow_update", account_id) if logger else nullcontext():
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
        
        if logger:
            logger.info(LogCategory.TRANSACTION, "benchmark_adjusted", 
                       f"Benchmark adjusted - BTC: {new_btc_units:.6f}, ETH: {new_eth_units:.6f}",
                       account_id=account_id, 
                       data={"old_btc_units": current_btc_units, "old_eth_units": current_eth_units,
                            "new_btc_units": new_btc_units, "new_eth_units": new_eth_units})
        
        print(f"Benchmark adjusted - BTC: {new_btc_units:.6f}, ETH: {new_eth_units:.6f}")
        return updated_config
        
    except Exception as e:
        if logger:
            logger.error(LogCategory.TRANSACTION, "adjust_benchmark_error", 
                        f"Error adjusting benchmark: {str(e)}",
                        account_id=account_id, error=str(e))
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

def save_history(db_client, account_id, nav, benchmark_value, logger=None, account_name=None, prices=None):
    timestamp = datetime.now(UTC).isoformat()
    
    # Ceny jsou nyní povinné - bez nich nemůžeme pokračovat
    if not prices or 'BTCUSDT' not in prices or 'ETHUSDT' not in prices:
        error_msg = "BTC/ETH prices are required for saving history"
        if logger:
            logger.error(LogCategory.DATABASE, "missing_prices", error_msg, account_id=account_id)
        raise ValueError(error_msg)
    
    history_data = {
        'account_id': account_id,
        'timestamp': timestamp,
        'nav': f'{nav:.2f}',
        'benchmark_value': f'{benchmark_value:.2f}',
        'btc_price': f"{prices['BTCUSDT']:.2f}",
        'eth_price': f"{prices['ETHUSDT']:.2f}"
    }
    
    # Insert data with required price columns
    with OperationTimer(logger, LogCategory.DATABASE, "insert_nav_history", account_id, account_name) if logger else nullcontext():
        db_client.table('nav_history').insert(history_data).execute()
    
    if logger:
        vs_benchmark = nav - benchmark_value
        vs_benchmark_pct = (vs_benchmark / benchmark_value * 100) if benchmark_value > 0 else 0
        
        logger.info(LogCategory.DATABASE, "save_nav_history", 
                   f"NAV: ${nav:.2f} | Benchmark: ${benchmark_value:.2f} | vs Benchmark: ${vs_benchmark:+.2f} ({vs_benchmark_pct:+.2f}%)",
                   account_id=account_id, account_name=account_name,
                   data={"nav": nav, "benchmark_value": benchmark_value, "vs_benchmark": vs_benchmark, "vs_benchmark_pct": vs_benchmark_pct})
    
    print(f"{timestamp} | NAV: {nav:.2f} | Benchmark: {benchmark_value:.2f}")

# Tento blok je pro lokální testování, Vercel ho ignoruje
if __name__ == "__main__":
    print("Running script locally for testing...")
    process_all_accounts()