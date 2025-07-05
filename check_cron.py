#!/usr/bin/env python3
"""
Quick Cron Checker - Rychlá kontrola stavu cron jobů
"""

import subprocess
import os
from pathlib import Path

def check_cron_status():
    """Zkontroluje stav cron jobů."""
    project_dir = Path(__file__).parent.absolute()
    script_path = str(project_dir / 'scrape_data.py')
    
    print("🔍 Kontrola cron jobů...")
    print("=" * 50)
    
    try:
        # Získej aktuální crontab
        current_crontab = subprocess.check_output(['crontab', '-l'], stderr=subprocess.DEVNULL).decode('utf-8')
        
        print("📋 Aktuální crontab:")
        print(current_crontab)
        
        # Spočítej naše joby
        lines = current_crontab.strip().split('\n')
        our_jobs = [line for line in lines if script_path in line]
        
        print(f"🎯 Binance monitor jobů: {len(our_jobs)}")
        
        if len(our_jobs) == 0:
            print("❌ Žádný Binance monitor cron job není nastaven")
        elif len(our_jobs) == 1:
            print("✅ Jeden cron job (správně)")
            print(f"   {our_jobs[0]}")
        else:
            print("⚠️  VÍCE NEŽ JEDEN JOB! Doporučuji vyčistit:")
            for i, job in enumerate(our_jobs, 1):
                print(f"   {i}. {job}")
            print("\n💡 Spusťte: python setup_cron.py → možnost 4 (odebrat) → možnost 1 (přidat)")
        
        # Zkontroluj log soubor
        log_path = project_dir / 'logs' / 'cron.log'
        if log_path.exists():
            print(f"\n📝 Log soubor existuje: {log_path}")
            print(f"📏 Velikost: {log_path.stat().st_size} bytů")
            
            # Ukáž posledních pár řádků
            try:
                with open(log_path, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        print("📄 Posledních 5 řádků logu:")
                        for line in lines[-5:]:
                            print(f"   {line.rstrip()}")
                    else:
                        print("📄 Log soubor je prázdný")
            except Exception as e:
                print(f"📄 Chyba při čtení logu: {e}")
        else:
            print(f"\n📝 Log soubor neexistuje: {log_path}")
            print("💡 Možná cron job ještě neběžel nebo má jinou cestu")
        
    except subprocess.CalledProcessError:
        print("❌ Žádný crontab nenalezen")
    
    print("\n" + "=" * 50)

def check_running_processes():
    """Zkontroluje běžící procesy."""
    print("🔄 Kontrola běžících procesů...")
    
    try:
        # Hledej běžící Python procesy s naším scriptem
        result = subprocess.run(['pgrep', '-f', 'scrape_data.py'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"🏃 Běžící scrape_data.py procesy: {len(pids)}")
            for pid in pids:
                print(f"   PID: {pid}")
        else:
            print("✅ Žádné běžící scrape_data.py procesy")
            
    except FileNotFoundError:
        # pgrep není dostupný na všech systémech
        print("⚠️  pgrep není dostupný, nelze zkontrolovat procesy")

if __name__ == "__main__":
    check_cron_status()
    check_running_processes()
    
    print("\n💡 Tip: Pro správu cron jobů použijte 'python setup_cron.py'")