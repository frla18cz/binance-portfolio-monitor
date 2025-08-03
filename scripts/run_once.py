#!/usr/bin/env python3
"""
Binance Portfolio Monitor - Run Once
Spustí monitoring jednou a skončí.
Vhodné pro testování nebo manuální spuštění.
"""

import os
import sys
import subprocess
import logging
from datetime import datetime

# Přidání projektového adresáře do PYTHONPATH
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Nastavení loggeru
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('RunOnce')

def main():
    """Spustí monitoring jednou"""
    logger.info("="*60)
    logger.info("🚀 Binance Portfolio Monitor - Jednorázové spuštění")
    logger.info(f"📅 Čas: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)
    
    try:
        # Spustit monitoring jako subprocess
        logger.info("📊 Spouštím monitoring proces...")
        
        result = subprocess.run(
            [sys.executable, '-m', 'api.index'],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        
        # Zobrazit výstup real-time (pokud je)
        if result.stdout:
            print("\n--- VÝSTUP MONITORINGU ---")
            print(result.stdout)
            print("--- KONEC VÝSTUPU ---\n")
            
        if result.stderr:
            print("\n--- CHYBOVÝ VÝSTUP ---")
            print(result.stderr)
            print("--- KONEC CHYBOVÉHO VÝSTUPU ---\n")
        
        if result.returncode == 0:
            logger.info("✅ Monitoring dokončen úspěšně")
            logger.info("💡 Tip: Pro zobrazení dashboardu spusťte: python -m api.dashboard")
        else:
            logger.error(f"❌ Monitoring selhal s kódem: {result.returncode}")
            return 1
            
    except KeyboardInterrupt:
        logger.info("⚠️  Přerušeno uživatelem (Ctrl+C)")
        return 130
    except Exception as e:
        logger.error(f"❌ Chyba při spouštění: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    logger.info("="*60)
    logger.info("✨ Jednorázové spuštění dokončeno")
    logger.info("="*60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())