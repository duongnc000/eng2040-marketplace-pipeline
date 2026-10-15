"""Shared paths and fixed dataset definitions."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RAW_SQL = ROOT / "data" / "raw.sql"
DATABASE = ROOT / "marketplace.sqlite"

OUTPUTS = ROOT / "outputs"
LOADING_OUTPUTS = OUTPUTS / "01_loading"
CLEANING_OUTPUTS = OUTPUTS / "02_cleaning"
ANALYSIS_OUTPUTS = OUTPUTS / "03_analysis"
CHART_OUTPUTS = ANALYSIS_OUTPUTS / "charts"
FEATURE_OUTPUTS = OUTPUTS / "04_features"
DOCUMENTATION_OUTPUTS = OUTPUTS / "05_documentation"

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

BRAZIL_STATES = (
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT",
    "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO",
    "RR", "SC", "SP", "SE", "TO",
)

TABLE_MEANINGS = {
    "category_translation": ("one row per product category", "product_category_name"),
    "customers": ("one customer record used by an order", "customer_id"),
    "order_items": ("one purchased item/sequence within an order", "order_id + order_item_id"),
    "order_payments": ("one payment record/sequence within an order", "order_id + payment_sequential"),
    "order_reviews": ("one review identifier attached to an order", "review_id + order_id"),
    "orders": ("one marketplace order", "order_id"),
    "products": ("one catalogue product", "product_id"),
    "sellers": ("one seller", "seller_id"),
}


def prepare_output_directories() -> None:
    """Create stage folders and remove only files from the former flat layout."""
    for directory in (
        LOADING_OUTPUTS, CLEANING_OUTPUTS, CHART_OUTPUTS, FEATURE_OUTPUTS,
        DOCUMENTATION_OUTPUTS,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    legacy_files = (
        "01_table_inventory.csv", "01_column_profile.csv", "01_relationship_checks.csv",
        "01_monetary_totals.csv", "02_cleaned_orders.csv", "02_delivery_labels.csv",
        "02_order_audit.csv", "02_quality_summary.csv", "03_lateness_summary.csv",
        "03_delay_distribution.csv", "03_approval_window_lateness.csv",
        "03_state_lateness.csv", "03_sensitivity.csv", "04_features.csv",
        "04_feature_order_ids.csv", "04_feature_labels.csv", "04_feature_dictionary.csv",
        "05_checks.csv", "05_resources.csv", "05_executed_queries.sql",
        "05_environment.txt",
    )
    for name in legacy_files:
        (OUTPUTS / name).unlink(missing_ok=True)

    old_charts = OUTPUTS / "charts"
    for name in (
        "question_1_lateness.svg", "question_2_approval_window.svg",
        "question_3_customer_state.svg",
    ):
        (old_charts / name).unlink(missing_ok=True)
    if old_charts.exists() and not any(old_charts.iterdir()):
        old_charts.rmdir()

    for name in (
        "question_1_lateness.svg", "question_2_approval_window.svg",
        "question_3_customer_state.svg",
    ):
        (CHART_OUTPUTS / name).unlink(missing_ok=True)
