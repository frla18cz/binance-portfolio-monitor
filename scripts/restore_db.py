#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path when running as a script
THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.db_backup import restore_from_dump, BackupError


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore a Postgres dump to a target DB URL or local DB name.")
    parser.add_argument("dump_file", help="Path to .dump or .sql file (e.g., backups/2025-08-11_150000.dump)")
    parser.add_argument("target", nargs="?", help="Target DB URL or local DB name. If omitted, uses $TARGET_DB_URL or 'postgres:///branch_db'.")
    args = parser.parse_args()

    target = args.target or os.environ.get("TARGET_DB_URL") or "postgres:///branch_db"

    try:
        restore_from_dump(args.dump_file, target)
        print(f"Restore completed into: {target}")
        return 0
    except BackupError as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

