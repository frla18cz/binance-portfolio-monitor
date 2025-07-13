#!/usr/bin/env python3
"""
Local monitoring runner - runs the monitoring process at regular intervals
"""
import time
import subprocess
import sys
from datetime import datetime
from config import settings

def run_monitoring():
    """Run the monitoring process"""
    print(f"[{datetime.now()}] Running monitoring...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "api.index"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"[{datetime.now()}] Monitoring completed successfully")
        else:
            print(f"[{datetime.now()}] Monitoring failed: {result.stderr}")
    except Exception as e:
        print(f"[{datetime.now()}] Error running monitoring: {e}")

def main():
    # Get interval from settings (in minutes)
    interval_minutes = settings.scheduling.cron_interval_minutes
    interval_seconds = interval_minutes * 60
    
    print(f"Starting local monitoring with {interval_minutes} minute interval")
    print("Press Ctrl+C to stop")
    
    while True:
        run_monitoring()
        print(f"[{datetime.now()}] Waiting {interval_minutes} minutes until next run...")
        time.sleep(interval_seconds)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
        sys.exit(0)