#!/usr/bin/env python3
"""
Cron Setup Script - Nastaví automatické spouštění data scrapingu
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

# Add project root to path for config import
sys.path.insert(0, os.path.dirname(__file__))
from config import settings

def get_project_info():
    """Získá informace o projektu a prostředí."""
    project_dir = Path(__file__).parent.absolute()
    venv_python = sys.executable
    
    return {
        'project_dir': str(project_dir),
        'venv_python': venv_python,
        'script_path': str(project_dir / 'scrape_data.py'),
        'log_path': str(project_dir / settings.get_log_file_path('cron_log'))
    }

def create_cron_entry(info, interval_minutes=None):
    """Vytvoří cron entry pro automatické spouštění."""
    if interval_minutes is None:
        interval_minutes = settings.scheduling.cron_interval_minutes
    return f"*/{interval_minutes} * * * * {info['venv_python']} {info['script_path']} >> {info['log_path']} 2>&1"

def setup_cron_local(interval_minutes=None):
    """Nastaví cron job pro lokální spuštění."""
    print("🔧 Nastavuji lokální cron job...")
    
    info = get_project_info()
    
    # Vytvoř logs složku pokud neexistuje
    os.makedirs(os.path.dirname(info['log_path']), exist_ok=True)
    
    # Získej současný crontab
    try:
        current_crontab = subprocess.check_output(['crontab', '-l'], stderr=subprocess.DEVNULL).decode('utf-8')
    except subprocess.CalledProcessError:
        current_crontab = ""
    
    # Zkontroluj jestli už není náš job přidaný
    cron_entry = create_cron_entry(info, interval_minutes)
    
    if info['script_path'] in current_crontab:
        print("⚠️  Cron job už existuje!")
        print("Současný crontab:")
        print(current_crontab)
        
        response = input("Chcete ho přepsat? (y/N): ")
        if response.lower() != 'y':
            print("❌ Instalace zrušena")
            return False
        
        # Odeber staré záznamy s naším scriptem
        lines = current_crontab.split('\n')
        filtered_lines = [line for line in lines if info['script_path'] not in line]
        current_crontab = '\n'.join(filtered_lines)
    
    # Přidej nový cron job
    new_crontab = current_crontab.rstrip() + '\n' + cron_entry + '\n'
    
    # Zapíš nový crontab
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
        temp_file.write(new_crontab)
        temp_file.flush()
        
        try:
            subprocess.run(['crontab', temp_file.name], check=True)
            os.unlink(temp_file.name)
            
            print("✅ Cron job úspěšně nastaven!")
            print(f"📊 Data se budou stahovat každé {interval_minutes or settings.scheduling.cron_interval_minutes} minuty")
            print(f"📝 Logy: {info['log_path']}")
            print(f"🔧 Cron entry: {cron_entry}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            os.unlink(temp_file.name)
            print(f"❌ Chyba při nastavování crontab: {e}")
            return False

def remove_cron_local():
    """Odebere cron job."""
    print("🗑️  Odebírám cron job...")
    
    info = get_project_info()
    
    try:
        current_crontab = subprocess.check_output(['crontab', '-l'], stderr=subprocess.DEVNULL).decode('utf-8')
    except subprocess.CalledProcessError:
        print("❌ Žádný crontab nenalezen")
        return False
    
    # Odeber naše záznamy
    lines = current_crontab.split('\n')
    filtered_lines = [line for line in lines if info['script_path'] not in line]
    new_crontab = '\n'.join(filtered_lines)
    
    # Zapíš nový crontab
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
        temp_file.write(new_crontab)
        temp_file.flush()
        
        try:
            subprocess.run(['crontab', temp_file.name], check=True)
            os.unlink(temp_file.name)
            
            print("✅ Cron job úspěšně odebrán!")
            return True
            
        except subprocess.CalledProcessError as e:
            os.unlink(temp_file.name)
            print(f"❌ Chyba při odebírání crontab: {e}")
            return False

def show_cron_status():
    """Zobrazí aktuální stav cron jobů."""
    info = get_project_info()
    
    try:
        current_crontab = subprocess.check_output(['crontab', '-l'], stderr=subprocess.DEVNULL).decode('utf-8')
        
        print("📋 Současný crontab:")
        print("-" * 50)
        print(current_crontab)
        
        # Zkontroluj náš job
        if info['script_path'] in current_crontab:
            print("✅ Binance monitor cron job je aktivní")
        else:
            print("❌ Binance monitor cron job NENÍ nastaven")
            
    except subprocess.CalledProcessError:
        print("❌ Žádný crontab nenalezen")

def create_vercel_json():
    """Vytvoří vercel.json pro automatické spouštění na Vercelu."""
    vercel_config = {
        "functions": {
            "api/index.py": {
                "runtime": settings.raw_config.get('runtime', {}).get('python_version', 'python3.9')
            },
            "api/dashboard.py": {
                "runtime": settings.raw_config.get('runtime', {}).get('python_version', 'python3.9')
            }
        },
        "crons": [
            {
                "path": "/api/index",
                "schedule": settings.scheduling.vercel_schedule
            }
        ]
    }
    
    import json
    with open('vercel.json', 'w') as f:
        json.dump(vercel_config, f, indent=2)
    
    print("✅ vercel.json vytvořen pro automatické spouštění na Vercelu!")
    print(f"📊 Data se budou stahovat podle schedule: {settings.scheduling.vercel_schedule}")

def main():
    """Hlavní menu pro nastavení."""
    print("🎯 Binance Portfolio Monitor - Cron Setup")
    print("=" * 50)
    
    while True:
        print("\nVyberte možnost:")
        print(f"1. 🔧 Nastavit lokální cron job (každé {settings.scheduling.cron_interval_minutes} minuty)")
        print("2. ⚙️  Nastavit lokální cron job (vlastní interval)")
        print("3. 📋 Zobrazit stav cron jobů")
        print("4. 🗑️  Odebrat cron job")
        print("5. ☁️  Vytvořit vercel.json pro Vercel deployment")
        print("6. 🚪 Ukončit")
        
        choice = input("\nVaše volba (1-6): ").strip()
        
        if choice == '1':
            setup_cron_local()
        elif choice == '2':
            try:
                interval = int(input("Zadejte interval v minutách: "))
                setup_cron_local(interval)
            except ValueError:
                print("❌ Neplatný interval!")
        elif choice == '3':
            show_cron_status()
        elif choice == '4':
            remove_cron_local()
        elif choice == '5':
            create_vercel_json()
        elif choice == '6':
            print("👋 Ukončuji...")
            break
        else:
            print("❌ Neplatná volba!")

if __name__ == "__main__":
    main()