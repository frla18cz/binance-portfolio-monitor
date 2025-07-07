#!/usr/bin/env python3
"""
Monitor Daemon - Kontinuální běh data scrapingu v pozadí
Alternativa k cron jobu pro development a testování
"""

import os
import sys
import time
import signal
import threading
from datetime import datetime, UTC
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))
from config import settings

class MonitorDaemon:
    def __init__(self, interval_seconds=None):  # Default from config
        if interval_seconds is None:
            interval_seconds = settings.scheduling.daemon_interval_seconds
        self.interval_seconds = interval_seconds
        self.running = False
        self.thread = None
        
    def start(self):
        """Spustí daemon v pozadí."""
        if self.running:
            print("⚠️  Daemon už běží!")
            return
            
        print(f"🚀 Spouštím monitor daemon (interval: {self.interval_seconds}s)")
        print(f"🕐 Spuštěno: {datetime.now(UTC).isoformat()}")
        print("📊 Pro ukončení stiskněte Ctrl+C")
        print("-" * 50)
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        # Nastavení signál handlerů pro graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            # Hlavní thread čeká
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Zastaví daemon."""
        print("\n🛑 Zastavuji monitor daemon...")
        self.running = False
        if self.thread:
            self.thread.join(timeout=settings.scheduling.thread_join_timeout_seconds)
        print("✅ Daemon zastaven")
    
    def _signal_handler(self, signum, frame):
        """Zpracuje signály pro ukončení."""
        self.stop()
    
    def _run_loop(self):
        """Hlavní smyčka daemonu."""
        while self.running:
            try:
                print(f"\n⏰ {datetime.now(UTC).strftime('%H:%M:%S')} - Spouštím data scraping...")
                
                # Import a spuštění scraping funkce
                from api.index import process_all_accounts
                process_all_accounts()
                
                print(f"✅ {datetime.now(UTC).strftime('%H:%M:%S')} - Data scraping dokončen")
                
            except Exception as e:
                print(f"❌ {datetime.now(UTC).strftime('%H:%M:%S')} - Chyba: {e}")
                import traceback
                traceback.print_exc()
            
            # Čekání do dalšího spuštění
            if self.running:
                print(f"😴 Čekám {self.interval_seconds} sekund do dalšího spuštění...")
                for i in range(self.interval_seconds):
                    if not self.running:
                        break
                    time.sleep(1)

def main():
    """Hlavní funkce."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor Daemon pro kontinuální data scraping")
    parser.add_argument('--interval', type=int, default=settings.scheduling.daemon_interval_seconds, 
                       help=f'Interval mezi spuštěními v sekundách (default: {settings.scheduling.daemon_interval_seconds})')
    parser.add_argument('--minutes', type=int, 
                       help='Interval v minutách (alternativa k --interval)')
    
    args = parser.parse_args()
    
    # Převod minut na sekundy pokud zadáno
    if args.minutes:
        interval = args.minutes * 60
    else:
        interval = args.interval
    
    daemon = MonitorDaemon(interval)
    
    try:
        daemon.start()
    except KeyboardInterrupt:
        daemon.stop()

if __name__ == "__main__":
    main()