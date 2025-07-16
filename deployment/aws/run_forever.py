#!/usr/bin/env python3
"""
Binance Portfolio Monitor - Continuous Runner
Spouští monitoring v nekonečné smyčce každou hodinu
"""

import os
import sys
import time
import signal
import logging
from datetime import datetime, timedelta
import subprocess
import traceback

# Přidání projektového adresáře do PYTHONPATH
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Vytvoření adresáře pro logy pokud neexistuje
os.makedirs('logs', exist_ok=True)

# Nastavení loggeru
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/continuous_runner.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('ContinuousRunner')

# Globální proměnná pro graceful shutdown
should_stop = False

def signal_handler(signum, frame):
    """Handler pro SIGINT (Ctrl+C) a SIGTERM"""
    global should_stop
    logger.info(f"Přijat signál {signum}, ukončuji aplikaci...")
    should_stop = True

# Registrace signal handlerů
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def run_monitoring():
    """Spustí monitoring proces"""
    try:
        logger.info("🚀 Spouštím monitoring proces...")
        
        # Spuštění monitoring scriptu
        result = subprocess.run(
            [sys.executable, '-m', 'api.index'],
            capture_output=True,
            text=True,
            timeout=300  # 5 minut timeout
        )
        
        if result.returncode == 0:
            logger.info("✅ Monitoring úspěšně dokončen")
            if result.stdout:
                logger.debug(f"Výstup: {result.stdout}")
        else:
            logger.error(f"❌ Monitoring selhal s kódem {result.returncode}")
            if result.stderr:
                logger.error(f"Chyba: {result.stderr}")
            if result.stdout:
                logger.error(f"Výstup: {result.stdout}")
                
    except subprocess.TimeoutExpired:
        logger.error("⏱️ Monitoring překročil časový limit 5 minut")
    except Exception as e:
        logger.error(f"❌ Neočekávaná chyba při spuštění monitoringu: {str(e)}")
        logger.error(traceback.format_exc())

def run_dashboard():
    """Spustí dashboard v samostatném procesu"""
    try:
        logger.info("🌐 Spouštím dashboard...")
        
        # Spuštění dashboard jako samostatný proces (nezávislý na tomto scriptu)
        subprocess.Popen(
            [sys.executable, '-m', 'api.dashboard'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True  # Odpojí proces od tohoto scriptu
        )
        
        logger.info("✅ Dashboard spuštěn na pozadí (port 8000)")
        
    except Exception as e:
        logger.error(f"❌ Nepodařilo se spustit dashboard: {str(e)}")
        # Dashboard není kritický, pokračujeme dál

def calculate_next_run():
    """Vypočítá čas do další hodiny"""
    now = datetime.now()
    next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    seconds_until_next_hour = (next_hour - now).total_seconds()
    return seconds_until_next_hour, next_hour

def main():
    """Hlavní smyčka aplikace"""
    logger.info("=" * 60)
    logger.info("🚀 Binance Portfolio Monitor - Continuous Runner")
    logger.info("=" * 60)
    logger.info(f"Python: {sys.version}")
    logger.info(f"Pracovní adresář: {os.getcwd()}")
    logger.info(f"Project root: {project_root}")
    
    # Kontrola prostředí
    env_vars = ['SUPABASE_URL', 'SUPABASE_ANON_KEY', 'BINANCE_API_KEY', 'BINANCE_API_SECRET']
    missing_vars = [var for var in env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.warning(f"⚠️ Chybějící environment proměnné: {', '.join(missing_vars)}")
        logger.warning("Ujistěte se, že máte správně nastaven .env soubor")
    
    # Spuštění dashboard
    run_dashboard()
    time.sleep(2)  # Počkáme 2 sekundy na start dashboardu
    
    # První spuštění monitoringu ihned
    logger.info("🏁 První spuštění monitoringu...")
    run_monitoring()
    
    # Hlavní smyčka
    run_count = 1
    while not should_stop:
        try:
            # Výpočet času do další hodiny
            seconds_to_wait, next_run_time = calculate_next_run()
            
            logger.info(f"⏰ Další běh naplánován na: {next_run_time.strftime('%H:%M:%S')}")
            logger.info(f"💤 Čekám {int(seconds_to_wait)} sekund...")
            
            # Čekání s možností přerušení
            wait_start = time.time()
            while time.time() - wait_start < seconds_to_wait and not should_stop:
                time.sleep(1)  # Kontrola každou sekundu
            
            if should_stop:
                break
                
            # Spuštění monitoringu
            run_count += 1
            logger.info(f"🔄 Běh #{run_count}")
            run_monitoring()
            
        except Exception as e:
            logger.error(f"❌ Chyba v hlavní smyčce: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Počkáme 60 sekund před dalším pokusem
            logger.info("⏳ Čekám 60 sekund před dalším pokusem...")
            for _ in range(60):
                if should_stop:
                    break
                time.sleep(1)
    
    logger.info("👋 Aplikace ukončena")
    sys.exit(0)

if __name__ == "__main__":
    # Spuštění hlavní smyčky
    main()