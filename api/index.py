import os
import sys
import json
import traceback
from contextlib import nullcontext
from datetime import datetime, timedelta, UTC
from http.server import BaseHTTPRequestHandler
from binance.client import Client as BinanceClient
from api.binance_pay_helper import get_pay_transactions
from api.sub_account_helper import get_sub_account_transfers, normalize_sub_account_transfers

# Debug print removed - was causing issues on Vercel

# Use absolute imports for better Vercel compatibility
from api.logger import get_logger, LogCategory, OperationTimer

# Add project root to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Try to load config, fallback to environment variables for Vercel
try:
    from config import settings
    # Ensure settings has required methods for Vercel
    if not hasattr(settings, 'get_supported_symbols'):
        settings.get_supported_symbols = lambda: getattr(settings.api.binance, 'supported_symbols', ['BTCUSDT', 'ETHUSDT'])
    if not hasattr(settings, 'get_supported_stablecoins'):
        settings.get_supported_stablecoins = lambda: getattr(settings.api.binance, 'supported_stablecoins', ['USDT', 'BUSD', 'USDC', 'BNFCR'])
    if not hasattr(settings, 'financial'):
        class Financial:
            minimum_balance_threshold = 0.00001
            minimum_usd_value_threshold = 0.1
        settings.financial = Financial()
    if not hasattr(settings, 'scheduling'):
        class Scheduling:
            historical_period_days = 30
        settings.scheduling = Scheduling()
except (ValueError, ImportError, ModuleNotFoundError) as e:
    # Create minimal settings for Vercel environment
    class MinimalSettings:
        class Database:
            supabase_url = os.getenv('SUPABASE_URL', '')
            supabase_key = os.getenv('SUPABASE_ANON_KEY', '')
        class Api:
            class Binance:
                data_api_url = 'https://data-api.binance.vision/api'
                tld = 'com'
                supported_symbols = ['BTCUSDT', 'ETHUSDT']
                supported_stablecoins = ['USDT', 'BUSD', 'USDC', 'BNFCR']
        class Financial:
            minimum_balance_threshold = 0.00001
            minimum_usd_value_threshold = 0.1
        class Scheduling:
            historical_period_days = 30
        
        def get_supported_symbols(self):
            """Method to get supported symbols for compatibility"""
            return self.api.binance.supported_symbols
            
        def get_supported_stablecoins(self):
            """Method to get supported stablecoins for compatibility"""
            return self.api.binance.supported_stablecoins
            
    settings = MinimalSettings()
    settings.database = MinimalSettings.Database()
    settings.api = MinimalSettings.Api()
    settings.api.binance = MinimalSettings.Api.Binance()
    settings.financial = MinimalSettings.Financial()
    settings.scheduling = MinimalSettings.Scheduling()
    # Using fallback settings for Vercel
from utils.log_cleanup import run_log_cleanup
from utils.database_manager import get_supabase_client, with_database_retry

# --- Global clients ---
try:
    supabase = get_supabase_client()
except Exception as e:
    # ERROR initializing Supabase client
    # Traceback suppressed for Vercel
    supabase = None

# --- Main handler for Vercel ---
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Health check endpoint
        if self.path == '/api/health':
            health_data = {
                'status': 'checking',
                'supabase_configured': bool(os.getenv('SUPABASE_URL')),
                'supabase_key_configured': bool(os.getenv('SUPABASE_ANON_KEY')),
                'supabase_connected': supabase is not None,
                'environment': os.getenv('VERCEL_ENV', 'unknown'),
                'python_version': sys.version
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            import json
            self.wfile.write(json.dumps(health_data, indent=2).encode('utf-8'))
            return
            
        # Early error check
        if supabase is None:
            self.send_response(500)
            self.send_header('Content-type','text/plain')
            self.end_headers()
            self.wfile.write('Error: Database connection failed during initialization'.encode('utf-8'))
            return
            
        try:
            logger = get_logger()
            logger.info(LogCategory.SYSTEM, "cron_trigger", "Cron job triggered - starting monitoring process")
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type','text/plain')
            self.end_headers()
            self.wfile.write(('Logger initialization error: ' + str(e)).encode('utf-8'))
            return
        
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
            # Traceback suppressed for Vercel
            
            self.send_response(500)
            self.send_header('Content-type','text/plain')
            self.end_headers()
            self.wfile.write(f'Error: {e}'.encode('utf-8'))
        return

# --- Helper functions ---
def ensure_benchmark_configs():
    """Ensure all accounts have benchmark configs, create missing ones."""
    logger = get_logger()
    db_client = get_supabase_client()
    
    try:
        # Get all accounts
        accounts_response = db_client.table('binance_accounts').select('*').execute()
        if not accounts_response.data:
            logger.warning(LogCategory.SYSTEM, "no_accounts_for_config", 
                          "No accounts found for benchmark config check")
            return
        
        # Get existing benchmark configs
        configs_response = db_client.table('benchmark_configs').select('account_id').execute()
        existing_account_ids = {config['account_id'] for config in configs_response.data}
        
        # Find accounts without configs
        accounts_without_config = [
            account for account in accounts_response.data 
            if account['id'] not in existing_account_ids
        ]
        
        if not accounts_without_config:
            logger.info(LogCategory.SYSTEM, "all_configs_exist", 
                       "All accounts have benchmark configs")
            return
        
        # Create missing configs
        logger.info(LogCategory.SYSTEM, "creating_missing_configs", 
                   f"Creating benchmark configs for {len(accounts_without_config)} accounts")
        
        configs_to_create = []
        for account in accounts_without_config:
            config = {
                'account_id': account['id'],
                'btc_units': 0.0,  # Will be initialized on first run
                'eth_units': 0.0   # Will be initialized on first run
            }
            configs_to_create.append(config)
            
            logger.info(LogCategory.SYSTEM, "creating_config_for_account", 
                       f"Creating benchmark config for account: {account['account_name']}",
                       account_id=account['id'], account_name=account['account_name'])
        
        # Insert all configs at once
        response = db_client.table('benchmark_configs').insert(configs_to_create).execute()
        
        if response.data:
            logger.info(LogCategory.SYSTEM, "configs_created", 
                       f"Successfully created {len(response.data)} benchmark configs")
        else:
            logger.error(LogCategory.SYSTEM, "config_creation_failed", 
                        "Failed to create benchmark configs")
            
    except Exception as e:
        logger.error(LogCategory.SYSTEM, "ensure_configs_error", 
                    f"Error ensuring benchmark configs: {str(e)}", error=str(e))
        # Don't re-raise - allow process to continue even if config creation fails

# --- Main logic ---
def process_all_accounts():
    """Get all accounts from DB and run monitoring process for them."""
    logger = get_logger()
    
    # Ensure all accounts have benchmark configs before processing
    ensure_benchmark_configs()
    
    with OperationTimer(logger, LogCategory.SYSTEM, "fetch_all_accounts"):
        # Use real Supabase client
        db_client = supabase
        
        response = db_client.table('binance_accounts').select('*, benchmark_configs(*)').execute()
    
    if not response.data:
        logger.warning(LogCategory.SYSTEM, "no_accounts", "No accounts found in database")
        return

    logger.info(LogCategory.SYSTEM, "accounts_found", f"Found {len(response.data)} accounts to process")
    
    # Fetch prices once for all accounts
    logger.info(LogCategory.PRICE_UPDATE, "fetch_prices_once", "Fetching prices once for all accounts")
    try:
        # Create temporary Binance client just for price fetching
        from binance.client import Client as BinanceClient
        temp_client = BinanceClient('', '')  # Use data API for read-only access
        # ALWAYS force data API URL for price fetching - no fallback needed
        temp_client.API_URL = 'https://data-api.binance.vision/api'
        
        logger.info(LogCategory.PRICE_UPDATE, "temp_client_created", 
                   f"Created temp client with data API URL: {temp_client.API_URL}")
        
        with OperationTimer(logger, LogCategory.PRICE_UPDATE, "fetch_prices_all_accounts"):
            prices = get_prices(temp_client, logger)
        
        if not prices:
            logger.error(LogCategory.PRICE_UPDATE, "price_fetch_failed", "Failed to fetch prices for all accounts")
            return
            
        # Save price history once
        save_price_history(prices, logger)
        
    except Exception as e:
        logger.error(LogCategory.PRICE_UPDATE, "price_fetch_error", 
                    f"Error fetching prices: {str(e)}", error=str(e))
        return
    
    for account in response.data:
        account_name = account.get('account_name', 'Unknown')
        account_id = account.get('id')
        
        logger.info(LogCategory.ACCOUNT_PROCESSING, "start_processing", 
                   f"Starting processing for account: {account_name}", 
                   account_id=account_id, account_name=account_name)
        
        try:
            with OperationTimer(logger, LogCategory.ACCOUNT_PROCESSING, "process_account", 
                              account_id, account_name):
                process_single_account(account, prices)
                
            logger.info(LogCategory.ACCOUNT_PROCESSING, "complete_processing", 
                       f"Successfully processed account: {account_name}",
                       account_id=account_id, account_name=account_name)
                       
        except Exception as e:
            logger.error(LogCategory.ACCOUNT_PROCESSING, "process_error", 
                        f"Failed to process account {account_name}: {str(e)}",
                        account_id=account_id, account_name=account_name, error=str(e))
            # Traceback suppressed for Vercel
    
    # Run log cleanup after processing all accounts
    try:
        run_log_cleanup()
    except Exception as e:
        logger.error(LogCategory.SYSTEM, "log_cleanup_error", 
                    f"Failed to run log cleanup: {str(e)}", error=str(e))


def process_account_transfers(db_client, account, binance_client, prices, logger):
    """
    Process sub-account transfers for any account type.
    Uses master credentials if available for sub-accounts.
    """
    try:
        # Skip if no email
        if not account.get('email'):
            return
            
        account_id = account['id']
        account_name = account.get('account_name', 'Unknown')
        
        # Choose the right client based on account type
        if account.get('is_sub_account') and account.get('master_api_key') and account.get('master_api_secret'):
            # Use master credentials for sub-account
            transfer_client = BinanceClient(account['master_api_key'], account['master_api_secret'])
            logger.info(LogCategory.TRANSACTION, "using_master_credentials",
                       f"Using master credentials for sub-account {account_name}",
                       account_id=account_id)
        else:
            # Use own credentials
            transfer_client = binance_client
            
        # Get last processed transfer time
        last_result = db_client.table('processed_transactions').select('timestamp').eq(
            'account_id', account_id
        ).like('transaction_id', 'SUB_%').order('timestamp', desc=True).limit(1).execute()
        
        start_time = None
        if last_result.data:
            last_timestamp = datetime.fromisoformat(last_result.data[0]['timestamp'].replace('Z', '+00:00'))
            start_time = int((last_timestamp + timedelta(minutes=1)).timestamp() * 1000)
        else:
            # Default to 30 days ago if no previous transfers
            start_time = int((datetime.now(UTC) - timedelta(days=30)).timestamp() * 1000)
            
        # Get transfers using the email
        transfers = get_sub_account_transfers(
            transfer_client.API_KEY,
            transfer_client.API_SECRET,
            email=account['email'],
            start_time=start_time,
            logger=logger,
            account_id=account_id
        )
        
        if not transfers:
            logger.debug(LogCategory.TRANSACTION, "no_sub_transfers",
                        f"No sub-account transfers found for {account_name}",
                        account_id=account_id)
            return
            
        # Normalize and convert to USD
        normalized = normalize_sub_account_transfers(transfers, transfer_client, logger, account_id)
        
        # Convert to processed_transactions format
        transactions_to_insert = []
        for transfer in normalized:
            # Check if already processed
            existing = db_client.table('processed_transactions').select('id').eq(
                'account_id', account_id
            ).eq('transaction_id', transfer['transaction_id']).execute()
            
            if existing.data:
                continue
                
            transactions_to_insert.append({
                'account_id': str(account_id),
                'transaction_id': transfer['transaction_id'],
                'type': transfer['type'],
                'amount': transfer['amount'],
                'timestamp': transfer['timestamp'],
                'status': 'SUCCESS',
                'metadata': transfer.get('metadata')
            })
            
        if transactions_to_insert:
            db_client.table('processed_transactions').insert(transactions_to_insert).execute()
            logger.info(LogCategory.TRANSACTION, "sub_transfers_recorded",
                       f"Recorded {len(transactions_to_insert)} new sub-account transfers for {account_name}",
                       account_id=account_id)
                       
    except Exception as e:
        # Log error but don't fail the whole process
        logger.warning(LogCategory.TRANSACTION, "sub_transfer_detection_failed",
                      f"Failed to detect sub-account transfers: {str(e)}",
                      account_id=account.get('id'), error=str(e))

def process_single_account(account, prices=None):
    """Kompletní logika pro jeden Binance účet."""
    logger = get_logger()
    
    api_key = account.get('api_key')
    api_secret = account.get('api_secret')
    account_id = account.get('id')
    account_name = account.get('account_name', 'Unknown')
    config = account.get('benchmark_configs')

    # Config should always exist now thanks to ensure_benchmark_configs()
    if isinstance(config, list):
        config = config[0]

    if not all([api_key, api_secret, account_id, config]):
        logger.error(LogCategory.ACCOUNT_PROCESSING, "incomplete_data", 
                    "Account data incomplete, skipping",
                    account_id=account_id, account_name=account_name)
        return

    # Use real Binance client for authenticated endpoints
    tld = getattr(settings.api.binance, 'tld', 'com') if hasattr(settings, 'api') else 'com'
    binance_client = BinanceClient(api_key, api_secret, tld=tld)
    # Log which API URL is being used for this client
    logger.info(LogCategory.API_CALL, "binance_client_created", 
               f"Created Binance client for account {account_name}. API URL: {binance_client.API_URL}",
               account_id=account_id, account_name=account_name)
    # Note: We don't set data API URL here as this client is used for private endpoints (NAV, balances)
    # Price fetching uses temp_client with data API URL in process_all_accounts()
    db_client = supabase
    
    # Log price availability for debugging
    logger.info(LogCategory.PRICE_UPDATE, "price_availability_check", 
               f"Prices provided: {bool(prices)}, prices data: {prices if prices else 'None'}",
               account_id=account_id, account_name=account_name)
    
    # If prices not provided, fetch them (for backward compatibility)
    if not prices:
        logger.warning(LogCategory.PRICE_UPDATE, "prices_not_provided", 
                      "Prices not provided to process_single_account, creating data API client",
                      account_id=account_id, account_name=account_name)
        
        # Create a NEW client specifically for price fetching with data API
        price_client = BinanceClient('', '')
        price_client.API_URL = 'https://data-api.binance.vision/api'
        
        with OperationTimer(logger, LogCategory.PRICE_UPDATE, "fetch_prices", account_id, account_name):
            prices = get_prices(price_client, logger, account_id, account_name)
        if not prices:
            return
        # Save price history only if we fetched prices ourselves
        save_price_history(prices, logger)

    with OperationTimer(logger, LogCategory.API_CALL, "fetch_nav", account_id, account_name):
        nav = get_comprehensive_nav(binance_client, logger, account_id, account_name, prices)
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
    
    # Process sub-account transfers
    process_account_transfers(db_client, account, binance_client, prices, logger)

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
            # Use current benchmark value to maintain independence from portfolio NAV
            current_benchmark_value = calculate_benchmark_value(config, prices)
            config = rebalance_benchmark(db_client, config, account_id, current_benchmark_value, prices, logger)

    benchmark_value = calculate_benchmark_value(config, prices)
    save_history(db_client, account_id, nav, benchmark_value, logger, account_name, prices)

# --- Helper functions ---

def get_coin_usd_value(client, coin, amount, btc_usd_price=None, logger=None, account_id=None):
    """
    Get USD value for any cryptocurrency amount.
    Tries multiple approaches: direct USDT pair, then via BTC.
    Returns tuple: (usd_value, coin_price, price_source)
    """
    if amount <= 0:
        return (0.0, None, None)
    
    # Check if it's a stablecoin
    if coin in settings.get_supported_stablecoins():
        return (amount, 1.0, 'stablecoin')
    
    # Try direct USDT pair first
    try:
        ticker = client.get_symbol_ticker(symbol=f"{coin}USDT")
        price = float(ticker['price'])
        usd_value = amount * price
        
        if logger:
            logger.debug(LogCategory.PRICE_UPDATE, "coin_price_direct", 
                        f"Got {coin} price via USDT: ${price:.6f}",
                        account_id=account_id, data={"coin": coin, "price": price, "source": "direct_usdt"})
        
        return (usd_value, price, 'direct_usdt')
    except Exception as e:
        if logger:
            logger.debug(LogCategory.PRICE_UPDATE, "coin_price_direct_failed", 
                        f"Failed to get {coin}USDT price: {str(e)}", account_id=account_id)
    
    # Try via BTC if we have BTC price
    if btc_usd_price and btc_usd_price > 0:
        try:
            btc_ticker = client.get_symbol_ticker(symbol=f"{coin}BTC")
            btc_price = float(btc_ticker['price'])
            coin_usd_price = btc_price * btc_usd_price
            usd_value = amount * coin_usd_price
            
            if logger:
                logger.debug(LogCategory.PRICE_UPDATE, "coin_price_via_btc", 
                            f"Got {coin} price via BTC: ${coin_usd_price:.6f} ({btc_price:.8f} BTC @ ${btc_usd_price:.2f})",
                            account_id=account_id, 
                            data={"coin": coin, "btc_price": btc_price, "usd_price": coin_usd_price, "source": "via_btc"})
            
            return (usd_value, coin_usd_price, 'via_btc')
        except Exception as e:
            if logger:
                logger.debug(LogCategory.PRICE_UPDATE, "coin_price_btc_failed", 
                            f"Failed to get {coin}BTC price: {str(e)}", account_id=account_id)
    
    # All attempts failed
    if logger:
        logger.warning(LogCategory.PRICE_UPDATE, "coin_price_not_found", 
                      f"Could not determine price for {coin}", 
                      account_id=account_id, data={"coin": coin, "amount": amount})
    
    return (None, None, None)

def get_prices(client, logger=None, account_id=None, account_name=None):
    try:
        # ALWAYS force data API for price queries to bypass geographic restrictions
        data_api_url = 'https://data-api.binance.vision/api'
        
        # Store original URL to log the switch
        original_api_url = getattr(client, 'API_URL', None)
        
        # Force data API URL
        client.API_URL = data_api_url
        
        if logger:
            logger.info(LogCategory.PRICE_UPDATE, "data_api_switch", 
                       f"Forcing data API for prices. Original: {original_api_url} -> New: {data_api_url}",
                       account_id=account_id, account_name=account_name,
                       data={"original_url": original_api_url, "new_url": data_api_url})
            
        prices = {}
        # Always use these symbols regardless of settings
        supported_symbols = ['BTCUSDT', 'ETHUSDT']
        
        if logger:
            logger.debug(LogCategory.PRICE_UPDATE, "using_symbols", 
                        f"Fetching prices for symbols: {supported_symbols}")
            
        for symbol in supported_symbols:
            ticker = client.get_symbol_ticker(symbol=symbol)
            prices[symbol] = float(ticker['price'])
        
        # Keep using data API URL - do not restore original
            
        if logger:
            logger.info(LogCategory.PRICE_UPDATE, "prices_fetched", 
                       f"Successfully fetched prices from data API: BTC=${prices['BTCUSDT']:,.2f}, ETH=${prices['ETHUSDT']:,.2f}",
                       account_id=account_id, account_name=account_name, data=prices)
        
        return prices
    except Exception as e:
        if logger:
            logger.error(LogCategory.PRICE_UPDATE, "price_fetch_error", 
                        f"Error fetching prices: {str(e)}",
                        account_id=account_id, account_name=account_name, error=str(e))
        
        # Fallback: use latest prices from database if available
        try:
            price_result = supabase.table('price_history').select('btc_price, eth_price').order('timestamp', desc=True).limit(1).execute()
            if price_result.data:
                latest = price_result.data[0]
                fallback_prices = {
                    'BTCUSDT': float(latest['btc_price']),
                    'ETHUSDT': float(latest['eth_price'])
                }
                if logger:
                    logger.info(LogCategory.PRICE_UPDATE, "prices_fallback", 
                               f"Using fallback prices from DB: BTC=${fallback_prices['BTCUSDT']:,.2f}, ETH=${fallback_prices['ETHUSDT']:,.2f}",
                               account_id=account_id, account_name=account_name)
                return fallback_prices
        except Exception as fallback_error:
            if logger:
                logger.error(LogCategory.PRICE_UPDATE, "price_fallback_error", 
                            f"Fallback price fetch also failed: {str(fallback_error)}",
                            error=str(fallback_error))
        
        # Error getting prices
        return None

def save_price_history(prices, logger=None):
    """Uloží historické ceny BTC a ETH do price_history tabulky."""
    if not prices:
        return
        
    try:
        from datetime import datetime, UTC
        
        # Získat ceny BTC a ETH
        btc_price = None
        eth_price = None
        
        for symbol, price in prices.items():
            if symbol == 'BTCUSDT':
                btc_price = float(price)
            elif symbol == 'ETHUSDT':
                eth_price = float(price)
        
        # Ověřit, že máme obě ceny
        if btc_price is None or eth_price is None:
            if logger:
                logger.warning(LogCategory.PRICE_UPDATE, "price_history_incomplete", 
                             f"Missing price data: BTC={btc_price}, ETH={eth_price}")
            return
        
        # Připravit data pro uložení (jedna řádka s oběma cenami)
        price_record = {
            'timestamp': datetime.now(UTC).isoformat(),
            'btc_price': btc_price,
            'eth_price': eth_price
        }
        
        # Pokusit se uložit do price_history (tabulka možná neexistuje)
        try:
            result = supabase.table('price_history').insert(price_record).execute()
            if logger:
                logger.debug(LogCategory.PRICE_UPDATE, "price_history_saved", 
                           f"Saved price record: BTC=${btc_price:.2f}, ETH=${eth_price:.2f}")
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

def get_comprehensive_nav(client, logger=None, account_id=None, account_name=None, prices=None):
    """
    Vypočítá kompletní NAV zahrnující:
    1. Spot účet - všechny balances převedené na USD
    2. Futures účet - raw asset balances převedené na USD (ne totalWalletBalance!)
    Tento přístup odpovídá tomu, co ukazuje Binance dashboard.
    """
    try:
        total_nav = 0.0
        breakdown = {}
        
        # Use provided prices or fetch BTC price for conversions
        if prices and 'BTCUSDT' in prices:
            btc_usd_price = float(prices['BTCUSDT'])
        else:
            # Fallback to fetching if prices not provided
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
            
            if total_balance > settings.financial.minimum_balance_threshold:  # Ignoruj velmi malé balances
                # Převeď na USD hodnotu
                if asset in settings.get_supported_stablecoins():
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
                
                if usdt_value > settings.financial.minimum_usd_value_threshold:  # Ignoruj hodnoty pod $0.1
                    spot_total += usdt_value
                    spot_details[asset] = {
                        'balance': total_balance,
                        'usdt_value': usdt_value
                    }
        
        breakdown['spot_total'] = spot_total
        breakdown['spot_details'] = spot_details
        
        # 2. FUTURES ACCOUNT - MARGIN BALANCE (wallet + unrealized P&L)
        futures_account = client.futures_account()
        futures_total = 0.0
        futures_details = {}
        
        for asset_info in futures_account.get('assets', []):
            asset = asset_info['asset']
            wallet_balance = float(asset_info['walletBalance'])
            unrealized_pnl = float(asset_info['unrealizedProfit'])
            margin_balance = float(asset_info['marginBalance'])  # wallet + unrealized
            
            if abs(margin_balance) > settings.financial.minimum_balance_threshold:  # Používáme marginBalance místo walletBalance
                # Převeď na USD
                if asset in settings.get_supported_stablecoins():
                    usd_value = margin_balance
                elif asset == 'BTC':
                    usd_value = margin_balance * btc_usd_price
                else:
                    try:
                        ticker = client.get_symbol_ticker(symbol=f"{asset}USDT")
                        price = float(ticker['price'])
                        usd_value = margin_balance * price
                    except:
                        usd_value = 0.0
                
                futures_total += usd_value
                futures_details[asset] = {
                    'wallet_balance': wallet_balance,
                    'unrealized_pnl': unrealized_pnl,
                    'margin_balance': margin_balance,
                    'usd_value': usd_value
                }
        
        breakdown['futures_total'] = futures_total
        breakdown['futures_details'] = futures_details
        
        # 3. FUNDING WALLET (Earn/Savings)
        funding_total = 0.0
        funding_details = {}
        try:
            funding_assets = client.funding_wallet()
            for asset_info in funding_assets:
                asset = asset_info.get('asset', '')
                free = float(asset_info.get('free', '0'))
                locked = float(asset_info.get('locked', '0'))
                freeze = float(asset_info.get('freeze', '0'))
                withdrawing = float(asset_info.get('withdrawing', '0'))
                total_balance = free + locked + freeze + withdrawing
                
                if total_balance > settings.financial.minimum_balance_threshold:
                    # Převeď na USD
                    if asset in settings.get_supported_stablecoins():
                        usd_value = total_balance
                    elif asset == 'BTC':
                        usd_value = total_balance * btc_usd_price
                    else:
                        try:
                            ticker = client.get_symbol_ticker(symbol=f"{asset}USDT")
                            price = float(ticker['price'])
                            usd_value = total_balance * price
                        except:
                            try:
                                btc_ticker_asset = client.get_symbol_ticker(symbol=f"{asset}BTC")
                                btc_price = float(btc_ticker_asset['price'])
                                usd_value = total_balance * btc_price * btc_usd_price
                            except:
                                usd_value = 0.0
                    
                    if usd_value > settings.financial.minimum_usd_value_threshold:
                        funding_total += usd_value
                        funding_details[asset] = {
                            'balance': total_balance,
                            'usd_value': usd_value
                        }
        except Exception as e:
            if logger:
                logger.warning(LogCategory.API_CALL, "funding_wallet_error", 
                             f"Failed to fetch funding wallet: {str(e)}",
                             account_id=account_id, account_name=account_name)
        
        breakdown['funding_total'] = funding_total
        breakdown['funding_details'] = funding_details
        
        # 4. SIMPLE EARN POSITIONS
        earn_total = 0.0
        earn_details = {}
        try:
            # Zkus Simple Earn flexible positions
            response = client._request('GET', 'sapi/v1/simple-earn/flexible/position', True, {})
            
            # Handle different response structures
            positions = []
            if isinstance(response, dict):
                if 'rows' in response:
                    positions = response['rows']
                elif 'data' in response and isinstance(response['data'], dict) and 'rows' in response['data']:
                    positions = response['data']['rows']
            elif isinstance(response, list):
                positions = response
                
            for position in positions:
                    asset = position.get('asset', '')
                    total_amount = float(position.get('totalAmount', '0'))
                    
                    if total_amount > settings.financial.minimum_balance_threshold:
                        # Převeď na USD
                        if asset in settings.get_supported_stablecoins():
                            usd_value = total_amount
                        elif asset == 'BTC':
                            usd_value = total_amount * btc_usd_price
                        else:
                            try:
                                ticker = client.get_symbol_ticker(symbol=f"{asset}USDT")
                                price = float(ticker['price'])
                                usd_value = total_amount * price
                            except:
                                usd_value = 0.0
                        
                        if usd_value > settings.financial.minimum_usd_value_threshold:
                            earn_total += usd_value
                            earn_details[f"{asset}_flexible"] = {
                                'balance': total_amount,
                                'usd_value': usd_value
                            }
        except Exception as e:
            if logger:
                logger.warning(LogCategory.API_CALL, "simple_earn_error", 
                             f"Failed to fetch Simple Earn positions: {str(e)}",
                             account_id=account_id, account_name=account_name)
        
        breakdown['earn_total'] = earn_total
        breakdown['earn_details'] = earn_details
        
        # 5. STAKING POSITIONS
        staking_total = 0.0
        staking_details = {}
        try:
            staking_positions = client.get_staking_position(product='STAKING')
            for position in staking_positions:
                asset = position.get('asset', '')
                amount = float(position.get('amount', '0'))
                
                if amount > settings.financial.minimum_balance_threshold:
                    # Převeď na USD
                    if asset in settings.get_supported_stablecoins():
                        usd_value = amount
                    elif asset == 'BTC':
                        usd_value = amount * btc_usd_price
                    else:
                        try:
                            ticker = client.get_symbol_ticker(symbol=f"{asset}USDT")
                            price = float(ticker['price'])
                            usd_value = amount * price
                        except:
                            usd_value = 0.0
                    
                    if usd_value > settings.financial.minimum_usd_value_threshold:
                        staking_total += usd_value
                        staking_details[asset] = {
                            'balance': amount,
                            'usd_value': usd_value
                        }
        except Exception as e:
            if logger:
                logger.warning(LogCategory.API_CALL, "staking_error", 
                             f"Failed to fetch staking positions: {str(e)}",
                             account_id=account_id, account_name=account_name)
        
        breakdown['staking_total'] = staking_total
        breakdown['staking_details'] = staking_details
        
        # CELKOVÝ NAV = Spot + Futures + Funding + Earn + Staking
        total_nav = spot_total + futures_total + funding_total + earn_total + staking_total
        breakdown['total_nav'] = total_nav
        breakdown['btc_usd_price'] = btc_usd_price
        
        if logger:
            wallet_breakdown = f"Spot: ${spot_total:.2f}, Futures: ${futures_total:.2f}"
            if funding_total > 0:
                wallet_breakdown += f", Funding: ${funding_total:.2f}"
            if earn_total > 0:
                wallet_breakdown += f", Earn: ${earn_total:.2f}"
            if staking_total > 0:
                wallet_breakdown += f", Staking: ${staking_total:.2f}"
                
            logger.info(LogCategory.API_CALL, "comprehensive_nav_fetched", 
                       f"Comprehensive NAV: ${total_nav:.2f} ({wallet_breakdown}) @ BTC ${btc_usd_price:.2f}",
                       account_id=account_id, account_name=account_name, 
                       data=breakdown)
        
        return total_nav
        
    except Exception as e:
        if logger:
            logger.error(LogCategory.API_CALL, "comprehensive_nav_error", 
                        f"Failed to fetch comprehensive NAV: {str(e)}",
                        account_id=account_id, account_name=account_name, error=str(e))
        # Error getting comprehensive NAV
        return None

def get_universal_nav(client, logger=None, account_id=None, account_name=None, prices=None):
    """
    Získá NAV ze všech typů peněženek pomocí univerzálního SAPI endpointu.
    Vyžaduje API klíč s oprávněním 'Permits Universal Transfer'.
    """
    try:
        # Použij univerzální endpoint pro všechny peněženky
        response = client._request('GET', '/sapi/v1/asset/wallet/balance', True, {})
        
        # python-binance může obalit response do struktury s klíčem 'data'
        if isinstance(response, dict) and 'data' in response:
            wallets = response['data']
        else:
            wallets = response
            
        total_nav = 0.0
        breakdown = {
            'wallets': {}
        }
        
        # Zpracuj každou peněženku - response je pole objektů
        for wallet in wallets:
            wallet_name = wallet.get('walletName', 'Unknown')
            balance = float(wallet.get('balance', '0'))  # Už je v USDT ekvivalentu
            activated = wallet.get('activate', False)
            
            if balance > 0:
                if balance > settings.financial.minimum_usd_value_threshold:
                    total_nav += balance
                    breakdown['wallets'][wallet_name] = {
                        'usdt_balance': balance,
                        'activated': activated
                    }
        
        breakdown['total_nav'] = total_nav
        
        if logger:
            wallet_summary = ', '.join([f"{k}: ${v['usdt_balance']:.2f}" for k, v in breakdown['wallets'].items()])
            logger.info(LogCategory.API_CALL, "universal_nav_fetched", 
                       f"Universal NAV: ${total_nav:.2f} ({wallet_summary})",
                       account_id=account_id, account_name=account_name, 
                       data=breakdown)
        
        return total_nav
        
    except Exception as e:
        # Pokud selže (např. chybí oprávnění), použij záložní řešení
        if logger:
            logger.warning(LogCategory.API_CALL, "universal_nav_fallback", 
                          f"Universal NAV failed, falling back to comprehensive NAV: {str(e)}",
                          account_id=account_id, account_name=account_name, error=str(e))
        
        # Použij stávající comprehensive NAV jako fallback
        return get_comprehensive_nav(client, logger, account_id, account_name, prices)

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
        # Error getting NAV
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
    
    # Set initialized_at to current timestamp to prevent duplicate transaction processing
    initialized_at = datetime.now(UTC).isoformat()
    
    with OperationTimer(logger, LogCategory.DATABASE, "update_benchmark_config", account_id) if logger else nullcontext():
        response = db_client.table('benchmark_configs').update({
            'btc_units': btc_units,
            'eth_units': eth_units,
            'next_rebalance_timestamp': next_rebalance.isoformat(),
            'initialized_at': initialized_at
        }).eq('account_id', account_id).execute()
    
    if logger:
        logger.info(LogCategory.BENCHMARK, "initialize_complete", 
                   f"Benchmark initialized successfully. Next rebalance: {next_rebalance}",
                   account_id=account_id,
                   data={"btc_units": btc_units, "eth_units": eth_units, "next_rebalance": next_rebalance.isoformat(),
                        "initialized_at": initialized_at})
    
    # Benchmark initialized
    return response.data[0]

def rebalance_benchmark(db_client, config, account_id, current_value, prices, logger=None):
    investment = current_value / 2
    btc_units = investment / prices['BTCUSDT']
    eth_units = investment / prices['ETHUSDT']

    next_rebalance = calculate_next_rebalance_time(
        datetime.now(UTC), config['rebalance_day'], config['rebalance_hour']
    )

    old_btc_units = float(config.get('btc_units', 0))
    old_eth_units = float(config.get('eth_units', 0))
    rebalance_timestamp = datetime.now(UTC)
    
    # Calculate values before rebalancing
    btc_value_before = old_btc_units * prices['BTCUSDT']
    eth_value_before = old_eth_units * prices['ETHUSDT']
    total_value_before = btc_value_before + eth_value_before
    btc_percentage_before = (btc_value_before / total_value_before * 100) if total_value_before > 0 else 0
    eth_percentage_before = (eth_value_before / total_value_before * 100) if total_value_before > 0 else 0
    
    if logger:
        logger.info(LogCategory.REBALANCING, "rebalance_start", 
                   f"Rebalancing benchmark with current value: ${current_value:.2f}",
                   account_id=account_id,
                   data={
                       "current_value": current_value,
                       "old_btc_units": old_btc_units,
                       "old_eth_units": old_eth_units,
                       "new_btc_units": btc_units,
                       "new_eth_units": eth_units,
                       "btc_investment": investment,
                       "eth_investment": investment
                   })

    # Validation: Check that new benchmark units create a value close to current_value
    calculated_benchmark = (btc_units * prices['BTCUSDT']) + (eth_units * prices['ETHUSDT'])
    validation_error = abs(calculated_benchmark - current_value) / current_value if current_value != 0 else 0
    
    rebalance_status = "success"
    rebalance_error = None
    
    if validation_error > 0.01:  # 1% tolerance
        error_msg = f"Benchmark validation failed: calculated={calculated_benchmark:.2f}, expected={current_value:.2f}, error={validation_error:.2%}"
        rebalance_status = "failed"
        rebalance_error = error_msg
        if logger:
            logger.error(LogCategory.REBALANCING, "validation_failed", error_msg, account_id=account_id)
        raise ValueError(error_msg)
    
    # Get current rebalance count
    current_count = config.get('rebalance_count', 0)
    new_count = current_count + 1
    
    # Calculate values after rebalancing
    btc_value_after = btc_units * prices['BTCUSDT']
    eth_value_after = eth_units * prices['ETHUSDT']
    total_value_after = btc_value_after + eth_value_after
    
    # Save rebalance history
    try:
        rebalance_history_data = {
            'account_id': account_id,
            'rebalance_timestamp': rebalance_timestamp.isoformat(),
            'btc_units_before': old_btc_units,
            'eth_units_before': old_eth_units,
            'btc_price': prices['BTCUSDT'],
            'eth_price': prices['ETHUSDT'],
            'btc_value_before': btc_value_before,
            'eth_value_before': eth_value_before,
            'total_value_before': total_value_before,
            'btc_percentage_before': btc_percentage_before,
            'eth_percentage_before': eth_percentage_before,
            'btc_units_after': btc_units,
            'eth_units_after': eth_units,
            'btc_value_after': btc_value_after,
            'eth_value_after': eth_value_after,
            'total_value_after': total_value_after,
            'rebalance_type': 'scheduled',
            'status': rebalance_status,
            'error_message': rebalance_error,
            'validation_error': validation_error * 100  # Store as percentage
        }
        
        db_client.table('benchmark_rebalance_history').insert(rebalance_history_data).execute()
        
        if logger:
            logger.info(LogCategory.DATABASE, "rebalance_history_saved", 
                       "Saved rebalance history record",
                       account_id=account_id,
                       data={"history_data": rebalance_history_data})
    except Exception as e:
        if logger:
            logger.error(LogCategory.DATABASE, "rebalance_history_error", 
                        f"Failed to save rebalance history: {str(e)}",
                        account_id=account_id, error=str(e))
    
    with OperationTimer(logger, LogCategory.DATABASE, "update_rebalance_config", account_id) if logger else nullcontext():
        response = db_client.table('benchmark_configs').update({
            'btc_units': btc_units,
            'eth_units': eth_units,
            'next_rebalance_timestamp': next_rebalance.isoformat(),
            'last_rebalance_timestamp': rebalance_timestamp.isoformat(),
            'last_rebalance_status': rebalance_status,
            'last_rebalance_error': rebalance_error,
            'rebalance_count': new_count,
            'last_rebalance_btc_units': old_btc_units,
            'last_rebalance_eth_units': old_eth_units
        }).eq('account_id', account_id).execute()
    
    if logger:
        logger.info(LogCategory.REBALANCING, "rebalance_complete", 
                   f"Benchmark rebalanced successfully. Next rebalance: {next_rebalance}",
                   account_id=account_id,
                   data={
                       "btc_units": btc_units,
                       "eth_units": eth_units,
                       "next_rebalance": next_rebalance.isoformat(),
                       "validation_error": validation_error,
                       "rebalance_count": new_count,
                       "old_btc_units": old_btc_units,
                       "old_eth_units": old_eth_units
                   })
    
    # Benchmark rebalanced
    return response.data[0]

def calculate_benchmark_value(config, prices):
    btc_val = (float(config.get('btc_units') or 0)) * prices['BTCUSDT']
    eth_val = (float(config.get('eth_units') or 0)) * prices['ETHUSDT']
    return btc_val + eth_val

def validate_transaction_inputs(account_id, config, prices, logger=None):
    """
    Validuje vstupní parametry pro zpracování transakcí.
    Vrací True pokud jsou všechny požadované parametry validní.
    """
    validation_errors = []
    
    # Validace account_id
    if not account_id or not isinstance(account_id, (int, str)):
        validation_errors.append("Invalid or missing account_id")
    
    # Validace config objektu
    if not config or not isinstance(config, dict):
        validation_errors.append("Invalid or missing config object")
    else:
        # Kontrola požadovaných config klíčů
        required_config_keys = ['btc_units', 'eth_units']
        for key in required_config_keys:
            if key not in config:
                validation_errors.append(f"Missing required config key: {key}")
            elif config[key] is None:
                validation_errors.append(f"Config key {key} is None")
    
    # Validace prices objektu
    if not prices or not isinstance(prices, dict):
        validation_errors.append("Invalid or missing prices object")
    else:
        required_symbols = ['BTCUSDT', 'ETHUSDT']
        for symbol in required_symbols:
            if symbol not in prices:
                validation_errors.append(f"Missing price for {symbol}")
            elif not isinstance(prices[symbol], (int, float)) or prices[symbol] <= 0:
                validation_errors.append(f"Invalid price value for {symbol}: {prices[symbol]}")
    
    # Logování výsledků validace
    if validation_errors:
        error_details = {
            "account_id": account_id,
            "validation_errors": validation_errors,
            "config_keys": list(config.keys()) if isinstance(config, dict) else None,
            "price_symbols": list(prices.keys()) if isinstance(prices, dict) else None
        }
        
        if logger:
            logger.error(LogCategory.TRANSACTION, "validation_failed", 
                        f"Transaction input validation failed: {'; '.join(validation_errors)}",
                        account_id=account_id, error=str(validation_errors), data=error_details)
        
        return False
    
    # Validace prošla úspěšně
    if logger:
        logger.debug(LogCategory.TRANSACTION, "validation_passed", 
                    "Transaction input validation successful",
                    account_id=account_id, 
                    data={"config_keys": list(config.keys()), "price_symbols": list(prices.keys())})
    
    return True

def process_deposits_withdrawals(db_client, binance_client, account_id, config, prices, logger=None):
    """
    Optimalizované zpracování deposits/withdrawals s idempotencí a atomic operations.
    Vrací aktualizovaný config s upravenými BTC/ETH units podle cashflow změn.
    """
    # Enhanced validation before processing
    if not validate_transaction_inputs(account_id, config, prices, logger):
        return config
        
    try:
        with OperationTimer(logger, LogCategory.TRANSACTION, "fetch_last_processed", account_id) if logger else nullcontext():
            last_processed = get_last_processed_time(db_client, account_id)
        
        with OperationTimer(logger, LogCategory.TRANSACTION, "fetch_new_transactions", account_id) if logger else nullcontext():
            new_transactions = fetch_new_transactions(binance_client, last_processed, logger, account_id, prices)
        
        # Filter out transactions that have already been processed
        unprocessed_transactions = filter_unprocessed_transactions(db_client, new_transactions, account_id, logger)
        
        # Filter out transactions that occurred before benchmark initialization (prevents duplicate processing)
        initialized_at = config.get('initialized_at')
        if initialized_at:
            # Convert initialized_at to datetime for comparison
            initialized_dt = datetime.fromisoformat(initialized_at.replace('Z', '+00:00'))
            pre_init_count = len(unprocessed_transactions)
            
            # Filter out transactions before initialization
            unprocessed_transactions = [
                txn for txn in unprocessed_transactions
                if datetime.fromisoformat(txn['timestamp'].replace('Z', '+00:00')) >= initialized_dt
            ]
            
            filtered_count = pre_init_count - len(unprocessed_transactions)
            if filtered_count > 0 and logger:
                logger.info(LogCategory.TRANSACTION, "pre_init_filtered", 
                           f"Filtered out {filtered_count} pre-initialization transactions",
                           account_id=account_id, 
                           data={"filtered_count": filtered_count, "initialized_at": initialized_at})
        
        if not unprocessed_transactions:
            if logger:
                logger.debug(LogCategory.TRANSACTION, "no_new_transactions", 
                           "No new transactions found (after deduplication and pre-init filtering)", account_id=account_id)
            return config
            
        if logger:
            logger.info(LogCategory.TRANSACTION, "processing_transactions", 
                       f"Processing {len(unprocessed_transactions)} new transactions",
                       account_id=account_id, data={"transaction_count": len(unprocessed_transactions)})
        
        # Batch zpracování všech nových transakcí
        total_net_flow = 0  # Kladné = deposit, záporné = withdrawal
        processed_txns = []
        
        for txn in unprocessed_transactions:
            if txn['status'] == 'SUCCESS':  # Pouze úspěšné transakce
                amount = float(txn['amount'])
                
                # Validate transaction type
                valid_types = ['DEPOSIT', 'WITHDRAWAL', 'PAY_DEPOSIT', 'PAY_WITHDRAWAL', 'FEE_WITHDRAWAL', 'SUB_DEPOSIT', 'SUB_WITHDRAWAL']
                if not txn.get('type'):
                    if logger:
                        logger.error(LogCategory.TRANSACTION, "missing_transaction_type", 
                                   f"Transaction missing 'type' field",
                                   account_id=account_id, data={"transaction": txn})
                    continue
                
                if txn['type'] not in valid_types:
                    if logger:
                        logger.error(LogCategory.TRANSACTION, "invalid_transaction_type", 
                                   f"Invalid transaction type: {txn['type']}. Valid types: {valid_types}",
                                   account_id=account_id, data={"transaction": txn})
                    continue
                
                # For deposits, check if we have USD value in metadata
                if txn['type'] in ['DEPOSIT', 'PAY_DEPOSIT', 'SUB_DEPOSIT']:
                    # Try to get USD value from metadata if available
                    if txn['type'] in ['DEPOSIT', 'SUB_DEPOSIT'] and txn.get('metadata') and txn['metadata'].get('usd_value') is not None:
                        usd_amount = float(txn['metadata']['usd_value'])
                        total_net_flow += usd_amount
                        if logger:
                            logger.debug(LogCategory.TRANSACTION, "deposit_usd_value",
                                       f"Using USD value for {txn['type'].lower()}: ${usd_amount:.2f} (from {amount} {txn['metadata'].get('coin', 'UNKNOWN')})",
                                       account_id=account_id)
                    elif txn['type'] in ['DEPOSIT', 'SUB_DEPOSIT'] and txn.get('metadata') and txn['metadata'].get('price_missing'):
                        # Skip deposits without USD value for cashflow calculation
                        if logger:
                            logger.warning(LogCategory.TRANSACTION, "deposit_skipped_no_price",
                                         f"Skipping {txn['type'].lower()} without USD value: {amount} {txn['metadata'].get('coin', 'UNKNOWN')}",
                                         account_id=account_id,
                                         data={'transaction_id': txn['id'], 'amount': amount, 'coin': txn['metadata'].get('coin')})
                    else:
                        # Fallback to raw amount (assumes USD for stablecoins or PAY deposits)
                        total_net_flow += amount
                elif txn['type'] in ['WITHDRAWAL', 'PAY_WITHDRAWAL', 'FEE_WITHDRAWAL', 'SUB_WITHDRAWAL']:
                    total_net_flow -= amount
                    
                processed_txns.append({
                    'account_id': str(account_id),  # Ensure it's a string
                    'transaction_id': str(txn['id']),
                    'type': txn['type'],  # Changed from 'transaction_type' to 'type'
                    'amount': float(amount),  # Ensure it's a proper float
                    'timestamp': txn['timestamp'],
                    'status': txn['status'],
                    'metadata': txn.get('metadata')  # Save transaction metadata if present
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
                    try:
                        db_client.table('processed_transactions').insert(processed_txns).execute()
                        update_last_processed_time(db_client, account_id)
                        
                        if logger:
                            logger.info(LogCategory.TRANSACTION, "transactions_saved", 
                                       f"Saved {len(processed_txns)} transactions with no net cashflow",
                                       account_id=account_id)
                    except Exception as e:
                        # Check if it's a duplicate key error
                        error_msg = str(e)
                        if 'duplicate key' in error_msg.lower() or 'unique constraint' in error_msg.lower():
                            if logger:
                                logger.warning(LogCategory.TRANSACTION, "duplicate_transaction_ignored", 
                                             f"Some transactions already processed, ignoring duplicates",
                                             account_id=account_id)
                        else:
                            # Re-raise other errors
                            raise
            return config
            
    except Exception as e:
        error_context = {
            "account_id": account_id,
            "config_present": config is not None,
            "prices_present": prices is not None,
            "error_type": type(e).__name__,
            "error_details": str(e)
        }
        
        if logger:
            logger.error(LogCategory.TRANSACTION, "process_error", 
                        f"Error processing deposits/withdrawals: {str(e)}",
                        account_id=account_id, error=str(e), data=error_context)
        # Error processing deposits/withdrawals
        # Traceback suppressed for Vercel
        return config  # Failsafe - vrátíme původní config

def get_last_processed_time(db_client, account_id):
    """Get timestamp of last processing for given account."""
    try:
        response = db_client.table('account_processing_status').select('last_processed_timestamp').eq('account_id', account_id).execute()
        if response.data:
            return response.data[0]['last_processed_timestamp']
        else:
            # První spuštění - začneme od před 30 dny
            return (datetime.now(UTC) - timedelta(days=settings.scheduling.historical_period_days)).isoformat()
    except:
        return (datetime.now(UTC) - timedelta(days=settings.scheduling.historical_period_days)).isoformat()

def filter_unprocessed_transactions(db_client, transactions, account_id, logger=None):
    """
    Filtruje transakce, které už byly zpracovány (existují v processed_transactions).
    """
    if not transactions:
        return []
    
    try:
        # Získáme ID všech transakcí, které chceme zkontrolovat
        transaction_ids = [txn['id'] for txn in transactions]
        
        # Zkontrolujeme, které už existují v databázi
        existing_response = db_client.table('processed_transactions').select('transaction_id').eq('account_id', account_id).in_('transaction_id', transaction_ids).execute()
        existing_ids = {row['transaction_id'] for row in existing_response.data}
        
        # Filtrujeme jen ty, které ještě nebyly zpracovány
        unprocessed = [txn for txn in transactions if txn['id'] not in existing_ids]
        
        if logger:
            logger.debug(LogCategory.TRANSACTION, "deduplication_check", 
                       f"Filtered {len(transactions)} transactions: {len(unprocessed)} new, {len(existing_ids)} already processed",
                       account_id=account_id, 
                       data={"total_fetched": len(transactions), "new_count": len(unprocessed), "existing_count": len(existing_ids)})
        
        return unprocessed
        
    except Exception as e:
        if logger:
            logger.error(LogCategory.TRANSACTION, "deduplication_error", 
                       f"Error during deduplication check: {str(e)}",
                       account_id=account_id, error=str(e))
        # V případě chyby vrátíme původní seznam (lepší než ztratit transakce)
        return transactions

def fetch_new_transactions(binance_client, start_time, logger=None, account_id=None, prices=None):
    """
    Optimalizovaně fetchne deposits + withdrawals od start_time.
    Kombinuje oba API calls pro minimální latenci.
    Includes USD conversion for crypto deposits/withdrawals.
    """
    try:
        transactions = []
        
        # Enhanced timestamp validation
        try:
            start_timestamp = int(datetime.fromisoformat(start_time.replace('Z', '+00:00')).timestamp() * 1000)
        except (ValueError, AttributeError) as e:
            error_msg = f"Invalid start_time format: {start_time}"
            if logger:
                logger.error(LogCategory.API_CALL, "fetch_transactions_error", error_msg,
                           account_id=account_id, error=str(e))
            raise ValueError(error_msg)
        
        if logger:
            logger.debug(LogCategory.API_CALL, "fetch_transactions_start", 
                        f"Fetching transactions since {start_time}",
                        account_id=account_id, data={"start_timestamp": start_timestamp})
        
        # Enhanced API calls with individual error handling
        deposits = []
        withdrawals = []
        
        try:
            deposits = binance_client.get_deposit_history(startTime=start_timestamp)
            if logger:
                logger.debug(LogCategory.API_CALL, "deposits_fetched", 
                           f"Fetched {len(deposits)} deposits", account_id=account_id)
        except Exception as e:
            if logger:
                logger.warning(LogCategory.API_CALL, "deposits_fetch_failed", 
                             f"Failed to fetch deposits: {str(e)}", 
                             account_id=account_id, error=str(e))
            # Continue with empty deposits list
        
        try:
            withdrawals = binance_client.get_withdraw_history(startTime=start_timestamp)
            if logger:
                logger.debug(LogCategory.API_CALL, "withdrawals_fetched", 
                           f"Fetched {len(withdrawals)} withdrawals", account_id=account_id)
        except Exception as e:
            if logger:
                logger.warning(LogCategory.API_CALL, "withdrawals_fetch_failed", 
                             f"Failed to fetch withdrawals: {str(e)}", 
                             account_id=account_id, error=str(e))
            # Continue with empty withdrawals list
        
        # Fetch Binance Pay transactions (phone/email transfers)
        pay_transactions = []
        try:
            # Use our helper to work around python-binance bug
            api_key = binance_client.API_KEY
            api_secret = binance_client.API_SECRET
            
            # Get pay transactions using direct API call
            pay_transactions = get_pay_transactions(api_key, api_secret, logger, account_id)
            
            if pay_transactions:
                
                # Filter transactions by time
                filtered_pay_transactions = []
                for pay_txn in pay_transactions:
                    txn_time = int(pay_txn.get('transactionTime', 0))
                    if txn_time >= start_timestamp:
                        filtered_pay_transactions.append(pay_txn)
                
                pay_transactions = filtered_pay_transactions
                
                if logger:
                    logger.debug(LogCategory.API_CALL, "pay_transactions_fetched", 
                               f"Fetched {len(pay_transactions)} pay transactions", account_id=account_id)
        except Exception as e:
            if logger:
                # Log more details about the error
                error_details = {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "has_response": 'pay_response' in locals(),
                    "response_type": type(pay_response).__name__ if 'pay_response' in locals() else None
                }
                
                logger.warning(LogCategory.API_CALL, "pay_transactions_fetch_failed", 
                             f"Failed to fetch pay transactions: {type(e).__name__}: {str(e)}", 
                             account_id=account_id, error=str(e), data=error_details)
            # Continue with empty pay transactions list
        
        # Enhanced transaction normalization with error handling
        for deposit in deposits:
            try:
                if not deposit or 'txId' not in deposit:
                    if logger:
                        logger.warning(LogCategory.API_CALL, "invalid_deposit_data", 
                                     f"Skipping invalid deposit data: {deposit}", account_id=account_id)
                    continue
                
                # Extract deposit details
                coin = deposit.get('coin', '')
                amount = float(deposit.get('amount', 0))
                
                # Calculate USD value for any coin
                usd_value = None
                coin_price = None
                price_source = None
                
                if coin:
                    # Get BTC price from prices dict if available
                    btc_price = prices.get('BTCUSDT') if prices else None
                    
                    # Use our utility function to get USD value
                    usd_value, coin_price, price_source = get_coin_usd_value(
                        binance_client, coin, amount, btc_price, logger, account_id
                    )
                    
                    # If we couldn't get the price, mark it for later processing
                    if usd_value is None:
                        if logger:
                            logger.warning(LogCategory.TRANSACTION, "deposit_price_missing",
                                         f"Could not determine USD value for {amount} {coin}",
                                         account_id=account_id,
                                         data={'coin': coin, 'amount': amount})
                
                transactions.append({
                    'id': f"DEP_{deposit['txId']}",
                    'type': 'DEPOSIT',
                    'amount': float(deposit.get('amount', 0)),
                    'timestamp': deposit.get('insertTime', 0),
                    'status': deposit.get('status', 0),  # 0=pending, 1=success
                    # Metadata for deposits
                    'coin': coin,
                    'network': deposit.get('network', ''),
                    'address': deposit.get('address', ''),
                    'address_tag': deposit.get('addressTag', ''),
                    'tx_id': deposit.get('txId', ''),
                    'usd_value': usd_value,
                    'coin_price': coin_price,
                    'price_source': price_source,
                    'price_missing': usd_value is None
                })
                
                # Log deposit for visibility
                if logger:
                    if usd_value:
                        log_msg = f"Deposit: {amount} {coin} (${usd_value:.2f} @ ${coin_price:.2f} via {price_source})"
                    else:
                        log_msg = f"Deposit: {amount} {coin} (USD value unknown)"
                    
                    logger.info(LogCategory.TRANSACTION, "deposit_detected",
                               log_msg,
                               account_id=account_id,
                               data={
                                   'tx_id': deposit['txId'],
                                   'coin': coin,
                                   'amount': amount,
                                   'usd_value': usd_value,
                                   'coin_price': coin_price,
                                   'price_source': price_source,
                                   'network': deposit.get('network', ''),
                                   'price_missing': usd_value is None
                               })
                               
            except (ValueError, TypeError, KeyError) as e:
                if logger:
                    logger.warning(LogCategory.API_CALL, "deposit_normalization_error", 
                                 f"Error normalizing deposit: {str(e)} | Data: {deposit}", 
                                 account_id=account_id, error=str(e))
                continue
            
        for withdrawal in withdrawals:
            try:
                if not withdrawal or 'id' not in withdrawal:
                    if logger:
                        logger.warning(LogCategory.API_CALL, "invalid_withdrawal_data", 
                                     f"Skipping invalid withdrawal data: {withdrawal}", account_id=account_id)
                    continue
                    
                # Check if this is a fee withdrawal (can be marked in withdrawal info/description)
                withdrawal_type = 'WITHDRAWAL'
                withdrawal_info = withdrawal.get('info', '').lower()
                withdrawal_note = withdrawal.get('withdrawOrderDescription', '').lower()
                
                # Check for fee indicators in withdrawal metadata
                if any(fee_indicator in withdrawal_info + withdrawal_note for fee_indicator in ['fee', 'management', 'performance', 'commission']):
                    withdrawal_type = 'FEE_WITHDRAWAL'
                    if logger:
                        logger.info(LogCategory.TRANSACTION, "fee_withdrawal_detected",
                                   f"Fee withdrawal detected: {withdrawal.get('amount')} {withdrawal.get('coin')}",
                                   account_id=account_id,
                                   data={'withdrawal_id': withdrawal['id'], 'info': withdrawal_info})
                
                transactions.append({
                    'id': f"WD_{withdrawal['id']}",
                    'type': withdrawal_type, 
                    'amount': float(withdrawal.get('amount', 0)),
                    'timestamp': withdrawal.get('applyTime', 0),
                    'status': withdrawal.get('status', 0),  # 0=pending, 1=success, etc.
                    # Metadata for debugging and future analysis
                    'transfer_type': withdrawal.get('transferType', 0),  # 0=external, 1=internal
                    'tx_id': withdrawal.get('txId', ''),  # "Internal transfer" for internal
                    'coin': withdrawal.get('coin', ''),  # Currency
                    'network': withdrawal.get('network', ''),  # Network for external
                    'info': withdrawal.get('info', ''),
                    'note': withdrawal.get('withdrawOrderDescription', '')
                })
                
                # Log internal transfers for debugging
                if withdrawal.get('transferType') == 1 or 'Internal transfer' in str(withdrawal.get('txId', '')):
                    if logger:
                        logger.info(LogCategory.TRANSACTION, "internal_transfer_detected",
                                   f"Internal transfer: {withdrawal.get('amount')} {withdrawal.get('coin')}",
                                   account_id=account_id,
                                   data={'withdrawal_id': withdrawal['id'], 
                                         'transfer_type': withdrawal.get('transferType'),
                                         'tx_id': withdrawal.get('txId')})
            except (ValueError, TypeError, KeyError) as e:
                if logger:
                    logger.warning(LogCategory.API_CALL, "withdrawal_normalization_error", 
                                 f"Error normalizing withdrawal: {str(e)} | Data: {withdrawal}", 
                                 account_id=account_id, error=str(e))
                continue
                
        # Process Binance Pay transactions (phone/email transfers)
        for pay_txn in pay_transactions:
            try:
                if not pay_txn or 'transactionId' not in pay_txn:
                    if logger:
                        logger.warning(LogCategory.API_CALL, "invalid_pay_transaction_data", 
                                     f"Skipping invalid pay transaction: {pay_txn}", account_id=account_id)
                    continue
                
                amount = float(pay_txn.get('amount', 0))
                if amount == 0:
                    continue
                
                # Determine transaction type based on amount sign
                if amount > 0:
                    # Incoming payment (deposit)
                    txn_type = 'PAY_DEPOSIT'
                    payer_info = pay_txn.get('payerInfo', {})
                    contact_info = {
                        'name': payer_info.get('name', ''),
                        'binance_id': payer_info.get('binanceId', ''),
                        'email': payer_info.get('email', ''),
                        'phone': payer_info.get('phone', '')
                    }
                else:
                    # Outgoing payment (withdrawal)
                    txn_type = 'PAY_WITHDRAWAL'
                    amount = abs(amount)  # Convert to positive for processing
                    receiver_info = pay_txn.get('receiverInfo', {})
                    contact_info = {
                        'name': receiver_info.get('name', ''),
                        'email': receiver_info.get('email', ''),
                        'phone': receiver_info.get('phone', ''),
                        'account_id': receiver_info.get('accountId', '')
                    }
                
                transactions.append({
                    'id': f"PAY_{pay_txn['transactionId']}",
                    'type': txn_type,
                    'amount': amount,
                    'timestamp': int(pay_txn.get('transactionTime', 0)),
                    'status': 'SUCCESS',  # Pay transactions are already completed
                    'currency': pay_txn.get('currency', ''),
                    'metadata': {
                        'order_type': pay_txn.get('orderType', ''),
                        'wallet_type': pay_txn.get('walletType', ''),
                        'contact_info': contact_info
                    }
                })
                
                # Log pay transaction for visibility
                if logger:
                    logger.info(LogCategory.TRANSACTION, "pay_transaction_detected",
                               f"Pay {txn_type}: {amount} {pay_txn.get('currency', '')} - {contact_info.get('name', 'Unknown')}",
                               account_id=account_id,
                               data={
                                   'transaction_id': pay_txn['transactionId'],
                                   'type': txn_type,
                                   'amount': amount,
                                   'currency': pay_txn.get('currency', ''),
                                   'contact_info': contact_info
                               })
                               
            except (ValueError, TypeError, KeyError) as e:
                if logger:
                    logger.warning(LogCategory.API_CALL, "pay_transaction_normalization_error", 
                                 f"Error normalizing pay transaction: {str(e)} | Data: {pay_txn}", 
                                 account_id=account_id, error=str(e))
                continue
            
        # Fetch sub-account transfers if we have account email
        # This needs to be done from the perspective of the master account
        # We'll handle this separately in process_single_account
            
        # Filtrujeme jen SUCCESS transakce a sortujeme podle času
        successful_txns = []
        for txn in transactions:
            # Different status codes for deposits (1) and withdrawals (6=completed)
            if (txn['status'] == 1 or txn['status'] == 6 or txn['status'] == 'SUCCESS'):  # Binance používá různé formáty
                txn['status'] = 'SUCCESS'
                txn['timestamp'] = datetime.fromtimestamp(txn['timestamp']/1000, UTC).isoformat()
                
                # Preserve metadata for deposits
                if txn['type'] == 'DEPOSIT' and any(key in txn for key in ['coin', 'network', 'address', 'address_tag', 'tx_id', 'usd_value', 'coin_price', 'price_source', 'price_missing']):
                    txn['metadata'] = {
                        'coin': txn.pop('coin', ''),
                        'network': txn.pop('network', ''),
                        'address': txn.pop('address', ''),
                        'address_tag': txn.pop('address_tag', ''),
                        'tx_id': txn.pop('tx_id', ''),
                        'usd_value': txn.pop('usd_value', None),
                        'coin_price': txn.pop('coin_price', None),
                        'price_source': txn.pop('price_source', None),
                        'price_missing': txn.pop('price_missing', False)
                    }
                
                # Preserve metadata for withdrawals
                if txn['type'] in ['WITHDRAWAL', 'FEE_WITHDRAWAL'] and any(key in txn for key in ['transfer_type', 'tx_id', 'coin', 'network', 'info', 'note']):
                    txn['metadata'] = {
                        'transfer_type': txn.pop('transfer_type', 0),
                        'tx_id': txn.pop('tx_id', ''),
                        'coin': txn.pop('coin', ''),
                        'network': txn.pop('network', ''),
                        'info': txn.pop('info', ''),
                        'note': txn.pop('note', '')
                    }
                
                # Preserve metadata for PAY transactions (already has metadata dict)
                # PAY transactions already have metadata from processing above
                    
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
        # Error fetching transaction history
        return []

def adjust_benchmark_for_cashflow(db_client, config, account_id, net_flow, prices, processed_txns, logger=None):
    """
    Atomic adjustment benchmarku podle net cashflow.
    Při depositu: zvýší BTC/ETH units proporcionálně
    Při withdrawal: sníží BTC/ETH units proporcionálně
    """
    # Enhanced input validation and error context
    validation_context = {
        "account_id": account_id,
        "net_flow": net_flow,
        "config_present": config is not None,
        "prices_present": prices is not None,
        "processed_txns_count": len(processed_txns) if processed_txns else 0,
        "config_keys": list(config.keys()) if isinstance(config, dict) else None,
        "price_symbols": list(prices.keys()) if isinstance(prices, dict) else None,
        "config_has_initialized_at": bool(config.get('initialized_at')) if config else False
    }
    
    # Validation: Check if benchmark is properly initialized
    if not config.get('initialized_at'):
        error_msg = "Cannot adjust benchmark for uninitialized config (missing initialized_at)"
        if logger:
            logger.error(LogCategory.TRANSACTION, "adjust_benchmark_error", 
                        error_msg, account_id=account_id, error=error_msg, data=validation_context)
        raise ValueError(error_msg)
    
    if logger:
        logger.debug(LogCategory.TRANSACTION, "benchmark_adjustment_start",
                    f"Starting benchmark adjustment for net flow: ${net_flow:.2f}",
                    account_id=account_id, data=validation_context)
    
    # Validate critical inputs
    if not isinstance(net_flow, (int, float)) or abs(net_flow) < 0.01:
        error_msg = f"Invalid net_flow value: {net_flow}"
        if logger:
            logger.error(LogCategory.TRANSACTION, "adjust_benchmark_error", 
                        error_msg, account_id=account_id, error=error_msg, data=validation_context)
        raise ValueError(error_msg)
    
    if not config or not isinstance(config, dict):
        error_msg = "Invalid config object provided"
        if logger:
            logger.error(LogCategory.TRANSACTION, "adjust_benchmark_error", 
                        error_msg, account_id=account_id, error=error_msg, data=validation_context)
        raise ValueError(error_msg)
    
    if not prices or 'BTCUSDT' not in prices or 'ETHUSDT' not in prices:
        error_msg = "Invalid or missing price data"
        if logger:
            logger.error(LogCategory.TRANSACTION, "adjust_benchmark_error", 
                        error_msg, account_id=account_id, error=error_msg, data=validation_context)
        raise ValueError(error_msg)
    
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
        
        # Determine modification type from processed transactions
        modification_type = 'deposit' if net_flow > 0 else 'withdrawal'
        
        # Check if it's a fee withdrawal
        if processed_txns and any(txn['type'] == 'FEE_WITHDRAWAL' for txn in processed_txns):
            modification_type = 'fee_withdrawal'
        
        # Get transaction details for reference
        transaction_id = None
        transaction_type = None
        if processed_txns:
            # Use the first transaction as primary reference
            transaction_id = processed_txns[0].get('transaction_id')
            transaction_type = processed_txns[0].get('type')
        
        # Prepare modification history data
        modification_timestamp = datetime.now(UTC)
        modification_data = {
            'account_id': account_id,
            'modification_timestamp': modification_timestamp.isoformat(),
            'modification_type': modification_type,
            'btc_units_before': current_btc_units,
            'eth_units_before': current_eth_units,
            'cashflow_amount': net_flow,
            'btc_price': prices['BTCUSDT'],
            'eth_price': prices['ETHUSDT'],
            'btc_allocation': btc_investment if net_flow > 0 else None,
            'eth_allocation': eth_investment if net_flow > 0 else None,
            'btc_units_bought': (btc_investment / prices['BTCUSDT']) if net_flow > 0 else -(current_btc_units - new_btc_units),
            'eth_units_bought': (eth_investment / prices['ETHUSDT']) if net_flow > 0 else -(current_eth_units - new_eth_units),
            'btc_units_after': new_btc_units,
            'eth_units_after': new_eth_units,
            'transaction_id': transaction_id,
            'transaction_type': transaction_type
        }
        
        # Enhanced atomic database update with transaction safety
        # Convert to Decimal for proper JSON serialization
        from decimal import Decimal
        update_data = {
            'btc_units': float(Decimal(str(new_btc_units)).quantize(Decimal('0.000000000001'))),
            'eth_units': float(Decimal(str(new_eth_units)).quantize(Decimal('0.000000000001')))
        }
        
        atomic_context = {
            "account_id": account_id,
            "update_data": update_data,
            "processed_txns_count": len(processed_txns) if processed_txns else 0,
            "operation_type": "atomic_cashflow_update"
        }
        
        with OperationTimer(logger, LogCategory.DATABASE, "atomic_cashflow_update", account_id) if logger else nullcontext():
            try:
                # 1. Update benchmark config first
                config_result = db_client.table('benchmark_configs').update(update_data).eq('account_id', account_id).execute()
                
                if not config_result.data:
                    error_msg = f"Failed to update benchmark_configs for account_id {account_id} - no rows affected"
                    if logger:
                        logger.error(LogCategory.DATABASE, "atomic_cashflow_update", error_msg,
                                   account_id=account_id, error=error_msg, data=atomic_context)
                    raise Exception(error_msg)
                
                # 2. Insert processed transactions if any
                if processed_txns:
                    try:
                        txn_result = db_client.table('processed_transactions').insert(processed_txns).execute()
                        if not txn_result.data:
                            error_msg = f"Failed to insert processed_transactions for account_id {account_id}"
                            if logger:
                                logger.error(LogCategory.DATABASE, "atomic_cashflow_update", error_msg,
                                           account_id=account_id, error=error_msg, data=atomic_context)
                            raise Exception(error_msg)
                    except Exception as txn_error:
                        # Check if it's a duplicate key error
                        error_msg = str(txn_error)
                        if 'duplicate key' in error_msg.lower() or 'unique constraint' in error_msg.lower():
                            if logger:
                                logger.warning(LogCategory.DATABASE, "duplicate_in_atomic_update", 
                                             f"Duplicate transactions in atomic update, rolling back",
                                             account_id=account_id, data=atomic_context)
                        raise  # Always re-raise to trigger rollback
                
                # 3. Save modification history
                try:
                    # Get the modification_id if we need to reference it
                    mod_result = db_client.table('benchmark_modifications').insert(modification_data).execute()
                    if mod_result.data and len(mod_result.data) > 0:
                        modification_id = mod_result.data[0].get('id')
                        
                        # Update benchmark_configs with last modification info
                        db_client.table('benchmark_configs').update({
                            'last_modification_type': modification_type,
                            'last_modification_timestamp': modification_timestamp.isoformat(),
                            'last_modification_amount': net_flow,
                            'last_modification_id': modification_id
                        }).eq('account_id', account_id).execute()
                        
                        if logger:
                            logger.info(LogCategory.DATABASE, "modification_history_saved", 
                                       "Saved benchmark modification history",
                                       account_id=account_id,
                                       data={"modification_id": modification_id, "modification_data": modification_data})
                except Exception as mod_error:
                    if logger:
                        logger.error(LogCategory.DATABASE, "modification_history_error", 
                                   f"Failed to save modification history: {str(mod_error)}",
                                   account_id=account_id, error=str(mod_error))
                    # Don't fail the whole transaction if history save fails
                
                # 4. Update last processed timestamp
                update_last_processed_time(db_client, account_id)
                
                if logger:
                    logger.debug(LogCategory.DATABASE, "atomic_update_success", 
                               "Atomic cashflow update completed successfully",
                               account_id=account_id, data=atomic_context)
                               
            except Exception as db_error:
                error_context = {**atomic_context, "db_error_type": type(db_error).__name__, "db_error_details": str(db_error)}
                if logger:
                    logger.error(LogCategory.DATABASE, "atomic_cashflow_update", 
                               f"Database atomic operation failed: {str(db_error)}",
                               account_id=account_id, error=str(db_error), data=error_context)
                raise  # Re-raise to trigger rollback in calling function
        
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
        
        # Benchmark adjusted
        return updated_config
        
    except Exception as e:
        # Enhanced error context for debugging
        error_context = {
            **validation_context,
            "error_type": type(e).__name__,
            "error_details": str(e),
            "current_btc_units": current_btc_units if 'current_btc_units' in locals() else None,
            "current_eth_units": current_eth_units if 'current_eth_units' in locals() else None,
            "new_btc_units": new_btc_units if 'new_btc_units' in locals() else None,
            "new_eth_units": new_eth_units if 'new_eth_units' in locals() else None,
            "stage": "benchmark_calculation" if 'new_btc_units' not in locals() else "database_update"
        }
        
        if logger:
            logger.error(LogCategory.TRANSACTION, "adjust_benchmark_error", 
                        f"Error adjusting benchmark: {str(e)}",
                        account_id=account_id, error=str(e), data=error_context)
        # Error adjusting benchmark
        raise  # Re-raise aby se celá operace rollbackla

def update_last_processed_time(db_client, account_id):
    """Aktualizuje timestamp posledního zpracování."""
    try:
        current_time = datetime.now(UTC).isoformat()
        db_client.table('account_processing_status').upsert({
            'account_id': str(account_id),  # Ensure it's a string
            'last_processed_timestamp': current_time
        }).execute()
    except Exception as e:
        # Error updating last processed time
        pass

def save_history(db_client, account_id, nav, benchmark_value, logger=None, account_name=None, prices=None):
    timestamp = datetime.now(UTC).isoformat()
    
    # Ceny jsou nyní povinné - bez nich nemůžeme pokračovat
    if not prices or 'BTCUSDT' not in prices or 'ETHUSDT' not in prices:
        error_msg = "BTC/ETH prices are required for saving history"
        if logger:
            logger.error(LogCategory.DATABASE, "missing_prices", error_msg, account_id=account_id)
        raise ValueError(error_msg)
    
    history_data = {
        'account_id': str(account_id),  # Ensure it's a string
        'timestamp': timestamp,
        'nav': float(nav),  # Store as numeric, not string
        'benchmark_value': float(benchmark_value),
        'btc_price': float(prices['BTCUSDT']),
        'eth_price': float(prices['ETHUSDT'])
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
    
    # NAV and Benchmark values saved

# Handler is already defined above at line 80

# Tento blok je pro lokální testování, Vercel ho ignoruje
if __name__ == "__main__":
    # MODULE MODE: When run as 'python -m api.index' or 'python api/index.py'
    # This is how run_forever.py calls this script
    # It runs the monitoring process once and exits
    process_all_accounts()