"""Stage 5a: validate accounting, label behavior and feature safety."""

import csv
import math
import sqlite3

from .common import write_csv
from .config import BRAZIL_STATES, CLEANING_OUTPUTS, DOCUMENTATION_OUTPUTS, FEATURE_OUTPUTS
from .features import FEATURE_SOURCES


def run_checks(connection: sqlite3.Connection, context: dict, feature_data: dict) -> list[dict]:
    """Run submission invariants, save them, and return every check result."""
    orders = context["orders"]
    cleaned = context["cleaned"]
    checks = []

    def add(name: str, passed: bool, observed, expected) -> None:
        checks.append({
            "check": name, "status": "PASS" if passed else "FAIL",
            "observed": observed, "expected": expected,
        })

    raw_orders = connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    raw_items = connection.execute("SELECT COUNT(*) FROM order_items").fetchone()[0]
    add("one cleaned row per raw order",
        len(cleaned) == raw_orders == len({row["order_id"] for row in cleaned}),
        len(cleaned), raw_orders)
    add("all item rows accounted for", sum(row["item_count"] for row in cleaned) == raw_items,
        sum(row["item_count"] for row in cleaned), raw_items)

    raw_valid_price = connection.execute(
        "SELECT SUM(CASE WHEN price>=0 THEN price ELSE 0 END) FROM order_items"
    ).fetchone()[0]
    assembled_valid_price = sum(row["basket_price_valid_brl"] for row in cleaned)
    add("valid item price total preserved", abs(raw_valid_price - assembled_valid_price) < .01,
        round(assembled_valid_price, 2), round(raw_valid_price, 2))

    raw_valid_freight = connection.execute(
        "SELECT SUM(CASE WHEN freight_value>=0 THEN freight_value ELSE 0 END) FROM order_items"
    ).fetchone()[0]
    assembled_valid_freight = sum(row["basket_freight_valid_brl"] for row in cleaned)
    add("valid freight total preserved", abs(raw_valid_freight - assembled_valid_freight) < .01,
        round(assembled_valid_freight, 2), round(raw_valid_freight, 2))

    raw_price = connection.execute("SELECT SUM(price) FROM order_items").fetchone()[0]
    assembled_raw_price = sum(row["basket_price_raw_brl"] for row in cleaned)
    add("raw item price total preserved", abs(raw_price - assembled_raw_price) < .01,
        round(assembled_raw_price, 2), round(raw_price, 2))

    raw_freight = connection.execute("SELECT SUM(freight_value) FROM order_items").fetchone()[0]
    assembled_raw_freight = sum(row["basket_freight_raw_brl"] for row in cleaned)
    add("raw freight total preserved", abs(raw_freight - assembled_raw_freight) < .01,
        round(assembled_raw_freight, 2), round(raw_freight, 2))

    reliable = sum(row["_label"] is not None for row in orders)
    feature_count = len(feature_data["features"])
    id_count = len(feature_data["ids"])
    label_count = len(feature_data["labels"])
    add("feature, ID and label row counts align",
        feature_count == id_count == label_count == reliable,
        f"{feature_count}/{id_count}/{label_count}", reliable)
    add("feature IDs are unique",
        id_count == len({row["order_id"] for row in feature_data["ids"]}),
        len({row["order_id"] for row in feature_data["ids"]}), id_count)

    feature_names = set(feature_data["all_features"][0]) if feature_data["all_features"] else set()
    prohibited = {"payment", "status", "delivered", "carrier", "review", "shipping_limit"}
    leaks = sorted(name for name in feature_names if any(term in name for term in prohibited))
    add("no prohibited field names in predictors", not leaks, ";".join(leaks) or "none", "none")

    non_numeric = sum(
        not isinstance(value, (int, float))
        for row in feature_data["all_features"] for value in row.values()
    )
    add("all predictor cells are numeric", non_numeric == 0, non_numeric, 0)
    null_features = sum(
        value is None or (isinstance(value, float) and not math.isfinite(value))
        for row in feature_data["all_features"] for value in row.values()
    )
    add("no null/NaN/infinite predictor cells", null_features == 0, null_features, 0)

    same_day_bad = sum(
        row["_label"] != 0 for row in orders
        if row["_label"] is not None and row["_delay_days"] == 0
    )
    add("same-calendar-date deliveries are on time", same_day_bad == 0, same_day_bad, 0)
    null_as_zero = sum(
        row["_label"] == 0 for row in orders
        if row["_label_reason"] != "reliable_completed_delivery"
    )
    add("unreliable outcomes are never filled as zero", null_as_zero == 0, null_as_zero, 0)
    def read(path):
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    source_ids = [row["order_id"] for row in orders]
    audit = read(CLEANING_OUTPUTS / "order_audit.csv")
    audit_ids = [row["order_id"] for row in audit]
    add("every order has exactly one saved audit row",
        len(audit_ids) == raw_orders and set(audit_ids) == set(source_ids),
        len(set(audit_ids)), raw_orders)

    all_ids = [row["order_id"] for row in feature_data["all_ids"]]
    add("all retained orders have feature rows",
        all_ids == source_ids and len(feature_data["all_features"]) == raw_orders,
        len(feature_data["all_features"]), raw_orders)

    # Check the actual saved files, including positions and null-label handling.
    for prefix, population in (("", [row for row in orders if row["_label"] is not None]),
                               ("all_", orders)):
        saved_features = read(FEATURE_OUTPUTS / f"{prefix}features.csv")
        saved_ids = read(FEATURE_OUTPUTS / f"{prefix}order_ids.csv")
        saved_labels = read(FEATURE_OUTPUTS / f"{prefix}labels.csv")
        expected_features = feature_data["all_features" if prefix else "features"]
        aligned = len(saved_features) == len(saved_ids) == len(saved_labels) == len(population)
        if aligned:
            for x, identity, target, source, expected in zip(
                    saved_features, saved_ids, saved_labels, population, expected_features):
                expected_label = "" if source["_label"] is None else str(source["_label"])
                if (identity != {"order_id": source["order_id"]}
                        or target != {"delivered_after_estimate": expected_label}
                        or x != {key: str(value) for key, value in expected.items()}):
                    aligned = False
                    break
        add(f"{prefix or 'supervised_'}saved feature/ID/label positions match source orders",
            aligned, "aligned" if aligned else "mismatch", "aligned")

    expected_names = set(FEATURE_SOURCES) | {f"customer_state_{state}" for state in (*BRAZIL_STATES, "UNKNOWN")}
    dictionary = feature_data["dictionary"]
    add("predictor schema matches explicit approval-time feature manifest",
        feature_names == expected_names == {row["feature"] for row in dictionary},
        len(feature_names), len(expected_names))
    allowed_sources = {
        "order_items.order_id", "order_items.product_id", "order_items.seller_id",
        "order_items.price", "order_items.freight_value", "products.product_category_name",
        "products.product_weight_g", "products.product_length_cm", "products.product_height_cm",
        "products.product_width_cm", "sellers.seller_state", "customers.customer_state",
        "customers.customer_zip_code_prefix", "orders.order_purchase_timestamp",
        "orders.order_approved_at", "orders.order_estimated_delivery_date",
    }
    sources = {source for row in dictionary for source in row["source"].split("; ")}
    add("documented feature sources are explicitly allowed at approval",
        sources <= allowed_sources and all(row["available_at_approval"] == "yes" for row in dictionary),
        "; ".join(sorted(sources - allowed_sources)) or "allowed", "allowed")
    add("all checks pass", all(row["status"] == "PASS" for row in checks),
        sum(row["status"] == "PASS" for row in checks), len(checks))

    write_csv(DOCUMENTATION_OUTPUTS / "checks.csv", checks)
    return checks
