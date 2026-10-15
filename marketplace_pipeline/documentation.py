"""Stage 6: save the SQL and environment needed for reproducibility."""

import importlib.metadata
import hashlib
import platform
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from .config import DATABASE, DOCUMENTATION_OUTPUTS, RAW_SQL


class SQLInventory:
    """Record distinct executed statements; source INSERTs remain in raw.sql."""

    def __init__(self):
        self.statements = {}

    def __call__(self, statement: str) -> None:
        statement = statement.strip()
        if statement and not statement.upper().startswith("INSERT"):
            self.statements.setdefault(statement, None)

    def write(self) -> None:
        text = (
            "-- Distinct SQL statements actually executed during this run.\n"
            "-- On fresh setup, source INSERT statements are supplied in data/raw.sql;\n"
            "-- they are not duplicated here. On reused setup the import is skipped.\n\n"
            + "\n\n".join(statement.rstrip(";") + ";" for statement in self.statements)
            + "\n"
        )
        (DOCUMENTATION_OUTPUTS / "executed_queries.sql").write_text(text, encoding="utf-8")


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_supporting_files(sql_inventory: SQLInventory) -> None:
    """Save the executed SQL and execution environment."""
    sql_inventory.write()

    environment = [
        f"Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"Command: {Path(sys.executable).name} pipeline.py",
        f"Python: {platform.python_version()}",
        f"SQLite: {sqlite3.sqlite_version}",
        f"Operating system: {platform.platform()}",
        f"Python dependency: matplotlib {importlib.metadata.version('matplotlib')}",
        "Recorded timestamps: treated as supplied local clock; no timezone conversion",
        "Resource memory: tracemalloc new Python allocations + sampled whole-process RSS (20ms)",
        "Intermediates: recursive Python container size of retained stage inputs and result; shared objects once",
        "Temporary storage: sampled redirected run directory and SQLite journal/WAL/SHM sizes; short-lived files may be missed",
        f"Source SQL SHA256: {file_hash(RAW_SQL)}",
        f"Database SHA256: {file_hash(DATABASE)}",
    ]
    (DOCUMENTATION_OUTPUTS / "environment.txt").write_text(
        "\n".join(environment) + "\n", encoding="utf-8"
    )
