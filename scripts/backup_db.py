#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path when running as a script
THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.db_backup import backup, BackupError


def main() -> int:
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("Error: SUPABASE_DB_URL environment variable is not set.", file=sys.stderr)
        print("Set it to your Postgres connection string.", file=sys.stderr)
        return 2

    backups_dir = os.environ.get("BACKUPS_DIR", "backups")

    try:
        out = backup(db_url, backups_dir=backups_dir)
        print(f"Backup created: {out}")
        # Also print latest symlink if exists
        latest = Path(backups_dir) / "latest.dump"
        if latest.exists() or latest.is_symlink():
            print(f"Latest: {latest} -> {latest.resolve() if latest.is_symlink() else latest}")
        return 0
    except BackupError as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

