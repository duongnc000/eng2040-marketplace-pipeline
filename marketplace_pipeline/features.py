"""Stage 4: create the numerical approval-time feature matrix."""

from .common import value_or_zero, write_csv
from .config import BRAZIL_STATES, FEATURE_OUTPUTS


FEATURE_SOURCES = {
    "item_count": "order_items.order_id",
    "distinct_product_count": "order_items.product_id",
    "distinct_seller_count": "order_items.seller_id",
    "basket_price_valid_brl": "order_items.price",
    "basket_freight_valid_brl": "order_items.freight_value",
    "bad_price_count": "order_items.price",
    "bad_freight_count": "order_items.freight_value",
    "category_count": "products.product_category_name",
    "avg_product_weight_g": "products.product_weight_g",
    "avg_product_volume_cm3": "products.product_length_cm; products.product_height_cm; products.product_width_cm",
    "product_attributes_missing": "products.product_weight_g; products.product_length_cm; products.product_height_cm; products.product_width_cm",
    "seller_state_count": "sellers.seller_state",
    "same_state_seller_item_fraction": "sellers.seller_state; customers.customer_state; order_items.order_id",
    "seller_location_missing": "sellers.seller_state; customers.customer_state; order_items.order_id",
    "customer_zip_prefix": "customers.customer_zip_code_prefix",
    "customer_zip_missing": "customers.customer_zip_code_prefix",
    "approval_year": "orders.order_approved_at",
    "approval_month": "orders.order_approved_at",
    "approval_weekday": "orders.order_approved_at",
    "approval_hour": "orders.order_approved_at",
    "approval_time_missing": "orders.order_approved_at",
    "approval_to_estimate_days": "orders.order_approved_at; orders.order_estimated_delivery_date",
    "approval_to_estimate_missing": "orders.order_approved_at; orders.order_estimated_delivery_date",
    "purchase_to_approval_hours": "orders.order_purchase_timestamp; orders.order_approved_at",
    "purchase_to_approval_missing": "orders.order_purchase_timestamp; orders.order_approved_at",
}


def build_features(orders: list[dict]) -> dict:
    """Export every retained order and preserve the reliable supervised subset."""
    features, ids, labels = [], [], []
    all_features, all_ids, all_labels = [], [], []
    dictionary = []

    base_dictionary = [
        ("item_count", "number of item rows", "count", "0 if no item row"),
        ("distinct_product_count", "distinct products in basket", "count", "0 if no item row"),
        ("distinct_seller_count", "distinct sellers in basket", "count", "0 if no item row"),
        ("basket_price_valid_brl", "sum of non-negative item prices", "BRL", "0 plus bad-price count"),
        ("basket_freight_valid_brl", "sum of non-negative item freight", "BRL", "0 plus bad-freight count"),
        ("bad_price_count", "missing or negative item prices", "count", "not applicable"),
        ("bad_freight_count", "missing or negative item freight values", "count", "not applicable"),
        ("category_count", "distinct non-missing product categories", "count", "0 if unavailable"),
        ("avg_product_weight_g", "mean positive catalogue weight", "grams", "0 plus missing indicator"),
        ("avg_product_volume_cm3", "mean positive L x H x W", "cubic centimetres", "0 plus missing indicator"),
        ("product_attributes_missing", "one if product weight/volume unavailable", "binary", "explicit indicator"),
        ("seller_state_count", "distinct normalized seller states", "count", "0 if unavailable"),
        ("same_state_seller_item_fraction", "fraction of item sellers in customer state", "proportion", "0 plus missing indicator"),
        ("seller_location_missing", "one if seller/customer state comparison unavailable", "binary", "explicit indicator"),
        ("customer_zip_prefix", "numeric customer postcode prefix", "code", "0 plus missing indicator"),
        ("customer_zip_missing", "one if postcode prefix is unavailable/non-numeric", "binary", "explicit indicator"),
        ("approval_year", "local approval year", "year", "0 plus approval-missing indicator"),
        ("approval_month", "local approval month", "1-12", "0 plus approval-missing indicator"),
        ("approval_weekday", "local approval weekday; Monday=0", "0-6", "0 plus approval-missing indicator"),
        ("approval_hour", "local approval clock hour", "0-23", "0 plus approval-missing indicator"),
        ("approval_time_missing", "one if approval timestamp is missing/invalid", "binary", "explicit indicator"),
        ("approval_to_estimate_days", "calendar days from approval to estimate", "calendar days", "0 plus missing indicator"),
        ("approval_to_estimate_missing", "one if interval cannot be computed reliably", "binary", "explicit indicator"),
        ("purchase_to_approval_hours", "elapsed local-clock hours from purchase to approval", "hours", "0 plus missing indicator"),
        ("purchase_to_approval_missing", "one if interval cannot be computed reliably", "binary", "explicit indicator"),
    ]
    for name, meaning, unit, missing in base_dictionary:
        dictionary.append({
            "feature": name, "meaning": meaning,
            "source": FEATURE_SOURCES[name],
            "representation": "numeric", "unit": unit, "missing_value_policy": missing,
            "available_at_approval": "yes",
        })
    for state in (*BRAZIL_STATES, "UNKNOWN"):
        dictionary.append({
            "feature": f"customer_state_{state}", "meaning": f"customer state is {state}",
            "source": "customers.customer_state", "representation": "one-hot binary", "unit": "binary",
            "missing_value_policy": "missing/invalid state maps to UNKNOWN", "available_at_approval": "yes",
        })

    for row in orders:
        item = row["_item"]
        approval = row["_parsed"]["order_approved_at"]
        interval = row["_approval_to_estimate_days"]
        purchase_interval = row["_purchase_to_approval_hours"]
        weight = item.get("avg_weight_g")
        volume = item.get("avg_volume_cm3")
        item_count = int(item.get("item_count", 0) or 0)
        same_state_known = (
            item_count > 0 and row["_state_clean"] != "UNKNOWN"
            and int(item.get("seller_state_count", 0) or 0) > 0
        )
        zip_text = str(row["customer_zip_code_prefix"] or "").strip()
        zip_known = zip_text.isdigit()
        feature = {
            "item_count": item_count,
            "distinct_product_count": int(item.get("distinct_product_count", 0) or 0),
            "distinct_seller_count": int(item.get("distinct_seller_count", 0) or 0),
            "basket_price_valid_brl": round(item.get("valid_price_total", 0) or 0, 2),
            "basket_freight_valid_brl": round(item.get("valid_freight_total", 0) or 0, 2),
            "bad_price_count": int(item.get("bad_price_count", 0) or 0),
            "bad_freight_count": int(item.get("bad_freight_count", 0) or 0),
            "category_count": int(item.get("category_count", 0) or 0),
            "avg_product_weight_g": value_or_zero(weight),
            "avg_product_volume_cm3": value_or_zero(volume),
            "product_attributes_missing": int(weight is None or volume is None),
            "seller_state_count": int(item.get("seller_state_count", 0) or 0),
            "same_state_seller_item_fraction": round((item.get("same_state_item_count", 0) or 0) / item_count, 6) if same_state_known else 0,
            "seller_location_missing": int(not same_state_known),
            "customer_zip_prefix": int(zip_text) if zip_known else 0,
            "customer_zip_missing": int(not zip_known),
            "approval_year": approval.year if approval else 0,
            "approval_month": approval.month if approval else 0,
            "approval_weekday": approval.weekday() if approval else 0,
            "approval_hour": approval.hour if approval else 0,
            "approval_time_missing": int(approval is None),
            "approval_to_estimate_days": interval if interval is not None else 0,
            "approval_to_estimate_missing": int(interval is None),
            "purchase_to_approval_hours": round(purchase_interval, 6) if purchase_interval is not None else 0,
            "purchase_to_approval_missing": int(purchase_interval is None),
        }
        for state in (*BRAZIL_STATES, "UNKNOWN"):
            feature[f"customer_state_{state}"] = int(row["_state_clean"] == state)
        identity = {"order_id": row["order_id"]}
        label = {"delivered_after_estimate": row["_label"]}
        all_features.append(feature)
        all_ids.append(identity)
        all_labels.append(label)
        if row["_label"] is not None:
            features.append(feature)
            ids.append(identity)
            labels.append(label)

    write_csv(FEATURE_OUTPUTS / "features.csv", features)
    write_csv(FEATURE_OUTPUTS / "order_ids.csv", ids)
    write_csv(FEATURE_OUTPUTS / "labels.csv", labels)
    write_csv(FEATURE_OUTPUTS / "all_features.csv", all_features)
    write_csv(FEATURE_OUTPUTS / "all_order_ids.csv", all_ids)
    write_csv(FEATURE_OUTPUTS / "all_labels.csv", all_labels)
    write_csv(FEATURE_OUTPUTS / "feature_dictionary.csv", dictionary)
    return {"features": features, "ids": ids, "labels": labels, "dictionary": dictionary,
            "all_features": all_features, "all_ids": all_ids, "all_labels": all_labels}
