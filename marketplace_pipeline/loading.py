"""Stage 1: create/open the database and profile its tables and relationships."""

import sqlite3

from setup_db import populate

from .common import write_csv
from .config import DATABASE, LOADING_OUTPUTS, RAW_SQL, TABLE_MEANINGS
from .queries import RELATIONSHIP_SQL


def setup_database(trace_callback=None) -> dict:
    """Create the faithful SQLite copy only when it does not already exist."""
    reused = DATABASE.exists()
    if not reused:
        populate(RAW_SQL, DATABASE, trace_callback=trace_callback)
    return {"database_setup_mode": "reused" if reused else "fresh_import"}


def load_and_profile(connection: sqlite3.Connection) -> dict:
    """Profile all source tables and save loading-stage evidence."""
    table_rows = []
    column_rows = []
    tables = [row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]
    for table in tables:
        count = connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        meaning, key = TABLE_MEANINGS[table]
        table_rows.append({"table": table, "row_meaning": meaning, "primary_key": key, "row_count": count})
        for column in connection.execute(f'PRAGMA table_info("{table}")'):
            name = column[1]
            quoted = name.replace('"', '""')
            nulls, distinct = connection.execute(
                f'SELECT SUM("{quoted}" IS NULL), COUNT(DISTINCT "{quoted}") FROM "{table}"'
            ).fetchone()
            minimum, maximum = connection.execute(
                f'SELECT MIN("{quoted}"), MAX("{quoted}") FROM "{table}"'
            ).fetchone()
            column_rows.append({
                "table": table, "column": name, "declared_type": column[2],
                "primary_key_position": column[5], "null_count": nulls or 0,
                "distinct_non_null_count": distinct, "minimum_observed": minimum,
                "maximum_observed": maximum,
            })

    relationships = [dict(row) for row in connection.execute(RELATIONSHIP_SQL)]
    price_total, freight_total = connection.execute(
        "SELECT SUM(price), SUM(freight_value) FROM order_items"
    ).fetchone()
    payment_total, payment_rows, zero_installments = connection.execute(
        "SELECT SUM(payment_value), COUNT(*), SUM(payment_installments=0) FROM order_payments"
    ).fetchone()
    monetary_rows = [
        {"measure": "item_price", "source_unit": "BRL", "source_total": round(price_total, 2),
         "comparable_brl_total": round(price_total, 2), "rule": "sum each item price once"},
        {"measure": "item_freight", "source_unit": "BRL", "source_total": round(freight_total, 2),
         "comparable_brl_total": round(freight_total, 2), "rule": "sum each item freight once"},
        {"measure": "payment_value", "source_unit": "centavos", "source_total": payment_total,
         "comparable_brl_total": round(payment_total / 100, 2),
         "rule": f"divide by 100 once; {payment_rows} payment records; do not multiply by installments"},
        {"measure": "zero_installment_payments", "source_unit": "records", "source_total": zero_installments,
         "comparable_brl_total": "", "rule": "preserved as valid; not changed or rejected"},
    ]

    write_csv(LOADING_OUTPUTS / "table_inventory.csv", table_rows)
    write_csv(LOADING_OUTPUTS / "column_profile.csv", column_rows)
    write_csv(LOADING_OUTPUTS / "relationship_checks.csv", relationships)
    write_csv(LOADING_OUTPUTS / "monetary_totals.csv", monetary_rows)
    return {"table_rows": table_rows, "relationships": relationships, "monetary": monetary_rows}
