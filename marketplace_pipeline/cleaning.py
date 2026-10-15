"""Stage 2: assemble, clean, audit and label one row per order."""

import sqlite3
from collections import Counter

from .common import clean_state, parse_date, write_csv
from .config import CLEANING_OUTPUTS, DATE_FORMAT
from .queries import BASE_SQL, ITEM_SQL


def clean_and_label(connection: sqlite3.Connection) -> dict:
    """Return the cleaned in-memory context and save all cleaning artifacts."""
    item_by_order = {row["order_id"]: dict(row) for row in connection.execute(ITEM_SQL)}
    cleaned, labels, audit = [], [], []
    quality = Counter()
    lenient_late = lenient_total = 0

    for raw in connection.execute(BASE_SQL):
        row = dict(raw)
        order_id = row["order_id"]
        item = item_by_order.get(order_id, {})
        status_raw = row["order_status"]
        status = (status_raw or "").strip().lower() or "unknown"
        state_raw = row["customer_state"]
        state = clean_state(state_raw)
        parsed, date_states = {}, {}
        for name in (
            "order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
            "order_delivered_customer_date", "order_estimated_delivery_date",
        ):
            parsed[name], date_states[name] = parse_date(row[name])

        purchase = parsed["order_purchase_timestamp"]
        approval = parsed["order_approved_at"]
        carrier = parsed["order_delivered_carrier_date"]
        actual = parsed["order_delivered_customer_date"]
        estimate = parsed["order_estimated_delivery_date"]

        chronology = []
        if actual and purchase and actual < purchase:
            chronology.append("delivery_before_purchase")
        if actual and approval and actual < approval:
            chronology.append("delivery_before_approval")
        if actual and carrier and actual < carrier:
            chronology.append("delivery_before_carrier")
        if estimate and approval and estimate < approval:
            chronology.append("estimate_before_approval")

        if status != "delivered":
            label, reason = None, "status_not_delivered"
        elif date_states["order_delivered_customer_date"] != "valid":
            label, reason = None, "actual_delivery_" + date_states["order_delivered_customer_date"]
        elif date_states["order_estimated_delivery_date"] != "valid":
            label, reason = None, "estimated_delivery_" + date_states["order_estimated_delivery_date"]
        elif chronology:
            label, reason = None, "impossible_chronology"
        else:
            label = int(actual.date() > estimate.date())
            reason = "reliable_completed_delivery"

        if status == "delivered" and actual and estimate:
            lenient_total += 1
            lenient_late += int(actual.date() > estimate.date())

        issues = []
        if status_raw != status:
            issues.append("status_normalized")
        if state == "UNKNOWN":
            issues.append("customer_state_unknown")
        elif state_raw != state:
            issues.append("customer_state_normalized")
        if row["customer_not_found"]:
            issues.append("customer_record_not_found")
        for name, date_state in date_states.items():
            if date_state != "valid":
                issues.append(f"{name}_{date_state}")
        issues.extend(chronology)
        if not item:
            issues.append("no_item_rows")
        for field, issue in (
            ("bad_price_count", "missing_or_negative_price"),
            ("bad_freight_count", "missing_or_negative_freight"),
            ("unmatched_product_count", "product_record_not_found"),
            ("unmatched_seller_count", "seller_record_not_found"),
            ("optional_product_issue_count", "optional_product_data_issue"),
        ):
            if item.get(field, 0):
                issues.append(issue)
        if label is None:
            issues.append("unlabelled:" + reason)
        quality.update(set(issues))

        approval_to_estimate = None
        if approval and estimate and estimate >= approval:
            approval_to_estimate = (estimate.date() - approval.date()).days
        purchase_to_approval = None
        if purchase and approval and approval >= purchase:
            purchase_to_approval = (approval - purchase).total_seconds() / 3600
        delay_days = (actual.date() - estimate.date()).days if label is not None else None

        cleaned.append({
            "order_id": order_id, "customer_id": row["customer_id"],
            "customer_unique_id": row["customer_unique_id"] or "",
            "order_status_raw": status_raw, "order_status_clean": status,
            "customer_state_raw": state_raw or "", "customer_state_clean": state,
            "customer_zip_code_prefix": row["customer_zip_code_prefix"] or "",
            "purchase_timestamp_clean": purchase.strftime(DATE_FORMAT) if purchase else "",
            "approval_timestamp_clean": approval.strftime(DATE_FORMAT) if approval else "",
            "actual_delivery_timestamp_clean": actual.strftime(DATE_FORMAT) if actual else "",
            "estimated_delivery_timestamp_clean": estimate.strftime(DATE_FORMAT) if estimate else "",
            "item_count": item.get("item_count", 0),
            "distinct_product_count": item.get("distinct_product_count", 0),
            "distinct_seller_count": item.get("distinct_seller_count", 0),
            "basket_price_raw_brl": round(item.get("raw_price_total", 0) or 0, 2),
            "basket_freight_raw_brl": round(item.get("raw_freight_total", 0) or 0, 2),
            "basket_price_valid_brl": round(item.get("valid_price_total", 0) or 0, 2),
            "basket_freight_valid_brl": round(item.get("valid_freight_total", 0) or 0, 2),
            "bad_price_count": item.get("bad_price_count", 0),
            "bad_freight_count": item.get("bad_freight_count", 0),
            "unmatched_product_count": item.get("unmatched_product_count", 0),
            "unmatched_seller_count": item.get("unmatched_seller_count", 0),
            "optional_product_issue_count": item.get("optional_product_issue_count", 0),
            "approval_to_estimate_days": "" if approval_to_estimate is None else approval_to_estimate,
            "purchase_to_approval_hours": "" if purchase_to_approval is None else round(purchase_to_approval, 4),
            "retained_in_cleaned_orders": 1, "quality_issue_count": len(set(issues)),
        })
        labels.append({
            "order_id": order_id, "delivered_after_estimate": "" if label is None else label,
            "label_eligible": int(label is not None), "label_reason": reason,
            "delay_calendar_days": "" if delay_days is None else delay_days,
        })
        audit.append({
            "order_id": order_id, "action": "retained",
            "label_action": "labelled" if label is not None else "left_unlabelled",
            "issue_count": len(set(issues)), "issues": ";".join(sorted(set(issues))) or "none",
        })

        row.update({
            "_status_clean": status, "_state_clean": state, "_parsed": parsed,
            "_item": item, "_label": label, "_label_reason": reason,
            "_delay_days": delay_days, "_approval_to_estimate_days": approval_to_estimate,
            "_purchase_to_approval_hours": purchase_to_approval,
            "_issues": issues, "_chronology": chronology,
        })
        item_by_order[order_id] = row

    quality_rows = [
        {"rule_or_issue": key, "affected_orders": count, "treatment": quality_treatment(key)}
        for key, count in sorted(quality.items())
    ]
    write_csv(CLEANING_OUTPUTS / "cleaned_orders.csv", cleaned)
    write_csv(CLEANING_OUTPUTS / "delivery_labels.csv", labels)
    write_csv(CLEANING_OUTPUTS / "order_audit.csv", audit)
    write_csv(CLEANING_OUTPUTS / "quality_summary.csv", quality_rows)
    return {
        "orders": [item_by_order[row["order_id"]] for row in cleaned],
        "cleaned": cleaned, "labels": labels, "quality": quality,
        "lenient_total": lenient_total, "lenient_late": lenient_late,
    }


def quality_treatment(issue: str) -> str:
    if issue.endswith("_normalized"):
        return "trimmed and case-normalized; raw value preserved"
    if issue.startswith("unlabelled"):
        return "order retained; delivery target left null"
    if "optional_product" in issue:
        return "order retained; invalid/missing value represented by zero plus indicator in features"
    if "price" in issue or "freight" in issue:
        return "negative/missing component omitted from valid sum and counted; order retained"
    if "not_found" in issue or "no_item" in issue:
        return "order retained and missing relationship flagged"
    if "before" in issue or "timestamp" in issue:
        return "raw value preserved; parsed value blank or label left null where reliability is affected"
    return "order retained and uncertainty flagged"
