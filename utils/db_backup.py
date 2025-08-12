import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


class BackupError(Exception):
    pass


def _ensure_tool_exists(tool: str) -> None:
    """Ensure a CLI tool is available in PATH, raise with helpful hint on macOS."""
    if shutil.which(tool) is None:
        hint = ""
        if sys.platform == "darwin":
            if tool in {"pg_dump", "pg_restore", "psql"}:
                hint = (
                    " Tip: brew install libpq && add /opt/homebrew/opt/libpq/bin to PATH."
                )
        raise BackupError(f"Required tool '{tool}' not found in PATH.{hint}")


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def _run(cmd: list[str], env: Optional[dict] = None) -> None:
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        raise BackupError(
            f"Command failed: {' '.join(cmd)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )


def _is_sql_file(path: Path) -> bool:
    return path.suffix.lower() == ".sql"


def backup(
    database_url: str,
    backups_dir: str = "backups",
    compression_level: int = 9,
    create_latest_symlink: bool = True,
) -> Path:
    """
    Create a compressed logical backup (.dump) using pg_dump (custom format).

    Returns the backup file path.
    """
    _ensure_tool_exists("pg_dump")

    out_dir = Path(backups_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = _timestamp()
    dump_path = out_dir / f"{ts}.dump"

    cmd = [
        "pg_dump",
        "-d",
        database_url,
        "-Fc",  # custom format
        f"-Z{compression_level}",  # compression level
        "-f",
        str(dump_path),
    ]

    _run(cmd)

    if create_latest_symlink:
        latest = out_dir / "latest.dump"
        try:
            if latest.exists() or latest.is_symlink():
                latest.unlink()
            # Use a symlink if possible; fallback to copying if not supported
            try:
                latest.symlink_to(dump_path.name)
            except OSError:
                # On filesystems without symlink support
                shutil.copy2(dump_path, latest)
        except Exception as e:
            # Don't fail the whole backup if symlink creation fails
            print(f"Warning: could not update latest symlink: {e}", file=sys.stderr)

    return dump_path


def restore_from_dump(
    dump_file: str,
    target: str,
) -> None:
    """
    Restore a dump file to target.
    - If dump is .dump: use pg_restore --clean --if-exists
    - If dump is .sql: use psql -f

    target may be a full DB URL or a local database name. If it does not contain
    '://', it is treated as a local database name and converted to 'postgres:///<name>'.
    """
    path = Path(dump_file)
    if not path.exists():
        raise BackupError(f"Dump file not found: {dump_file}")

    # Normalize target to URL if a bare DB name is given
    if "://" not in target:
        db_url = f"postgres:///{target}"
    else:
        db_url = target

    if _is_sql_file(path):
        _ensure_tool_exists("psql")
        cmd = [
            "psql",
            "-d",
            db_url,
            "-f",
            str(path),
        ]
        _run(cmd)
    else:
        _ensure_tool_exists("pg_restore")
        cmd = [
            "pg_restore",
            "--clean",
            "--if-exists",
            "-d",
            db_url,
            str(path),
        ]
        _run(cmd)


def list_backups(backups_dir: str = "backups") -> list[Tuple[Path, int]]:
    """
    Returns list of (path, size_bytes) for *.dump and *.sql sorted by mtime desc.
    """
    out_dir = Path(backups_dir)
    if not out_dir.exists():
        return []
    files = [
        p for p in out_dir.iterdir() if p.is_file() and p.suffix.lower() in {".dump", ".sql"}
    ]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [(p, p.stat().st_size) for p in files]

