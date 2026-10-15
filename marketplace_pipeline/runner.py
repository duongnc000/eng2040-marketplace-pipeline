"""Pipeline orchestration: one call runs every assignment stage in order."""

import sqlite3

from .analysis import analyse
from .cleaning import clean_and_label
from .common import timed_step, write_csv
from .config import (
    ANALYSIS_OUTPUTS, CHART_OUTPUTS, CLEANING_OUTPUTS, DATABASE,
    DOCUMENTATION_OUTPUTS, FEATURE_OUTPUTS, LOADING_OUTPUTS, RAW_SQL,
    OUTPUTS, ROOT, prepare_output_directories,
)
from .documentation import SQLInventory, write_supporting_files
from .features import build_features
from .loading import load_and_profile, setup_database
from .validation import run_checks


def run_pipeline() -> int:
    """Run all stages, returning a process-style success/failure code."""
    prepare_output_directories()
    resources = []
    sql_inventory = SQLInventory()

    setup = timed_step(
        resources, "0_database_setup", str(RAW_SQL.relative_to(ROOT)), [DATABASE],
        (2.0, 30_000_000, 0, 20_000_000), lambda: setup_database(sql_inventory),
    )
    resources[-1].update(setup)
    connection = sqlite3.connect(DATABASE)
    connection.set_trace_callback(sql_inventory)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA temp_store=MEMORY")

    loading_paths = [
        LOADING_OUTPUTS / "table_inventory.csv",
        LOADING_OUTPUTS / "column_profile.csv",
        LOADING_OUTPUTS / "relationship_checks.csv",
        LOADING_OUTPUTS / "monetary_totals.csv",
    ]
    profile = timed_step(
        resources, "1_load_and_profile", "data/raw.sql; marketplace.sqlite", loading_paths,
        (1.0, 8_000_000, 0, 20_000), lambda: load_and_profile(connection),
    )

    cleaning_paths = [
        CLEANING_OUTPUTS / "cleaned_orders.csv",
        CLEANING_OUTPUTS / "delivery_labels.csv",
        CLEANING_OUTPUTS / "order_audit.csv",
        CLEANING_OUTPUTS / "quality_summary.csv",
    ]
    context = timed_step(
        resources, "2_clean_and_label", "marketplace.sqlite", cleaning_paths,
        (2.0, 80_000_000, 0, 18_000_000), lambda: clean_and_label(connection),
        retained={"profile": profile},
    )

    analysis_paths = [
        ANALYSIS_OUTPUTS / "lateness_summary.csv",
        ANALYSIS_OUTPUTS / "delay_distribution.csv",
        ANALYSIS_OUTPUTS / "approval_window_lateness.csv",
        ANALYSIS_OUTPUTS / "state_lateness.csv",
        ANALYSIS_OUTPUTS / "sensitivity.csv",
        CHART_OUTPUTS / "question_1_lateness.png",
        CHART_OUTPUTS / "question_2_approval_window.png",
        CHART_OUTPUTS / "question_3_customer_state.png",
    ]
    analysis = timed_step(
        resources, "3_exploratory_analysis",
        "outputs/02_cleaning/cleaned_orders.csv; outputs/02_cleaning/delivery_labels.csv",
        analysis_paths, (1.0, 12_000_000, 0, 150_000), lambda: analyse(context),
        retained={"profile": profile, "context": context},
    )

    feature_paths = [
        FEATURE_OUTPUTS / "features.csv", FEATURE_OUTPUTS / "order_ids.csv",
        FEATURE_OUTPUTS / "labels.csv", FEATURE_OUTPUTS / "feature_dictionary.csv",
        FEATURE_OUTPUTS / "all_features.csv", FEATURE_OUTPUTS / "all_order_ids.csv",
        FEATURE_OUTPUTS / "all_labels.csv",
    ]
    feature_data = timed_step(
        resources, "4_feature_engineering",
        "outputs/02_cleaning/cleaned_orders.csv; outputs/02_cleaning/delivery_labels.csv",
        feature_paths, (2.0, 70_000_000, 0, 20_000_000), lambda: build_features(context["orders"]),
        retained={"profile": profile, "context": context, "analysis": analysis},
    )

    checks = timed_step(
        resources, "5_validation", "outputs from stages 1-4",
        [DOCUMENTATION_OUTPUTS / "checks.csv"], (0.5, 5_000_000, 0, 5_000),
        lambda: run_checks(connection, context, feature_data),
        retained={"profile": profile, "context": context, "analysis": analysis, "features": feature_data},
    )
    connection.close()

    documentation_paths = [
        DOCUMENTATION_OUTPUTS / "environment.txt",
        DOCUMENTATION_OUTPUTS / "executed_queries.sql",
    ]
    timed_step(
        resources, "6_documentation", "source code and outputs from stages 1-5",
        documentation_paths, (0.1, 1_000_000, 0, 10_000), lambda: write_supporting_files(sql_inventory),
        retained={"profile": profile, "context": context, "analysis": analysis, "features": feature_data},
    )
    # Report evidence is part of the same command; PDF compilation stays separate.
    from .report_evidence import main as build_report_evidence, write_resource_table

    report_paths = [ROOT / "report" / "figures" / f"question_{number}.png" for number in (1, 2, 3)]
    report_paths += [ROOT / "report" / "evidence" / name for name in (
        "window_sensitivity.csv", "state_sensitivity.csv", "priority_threshold_sensitivity.csv",
        "window_table.tex", "state_table.tex",
    )]
    timed_step(
        resources, "7_report_evidence", "outputs/02_cleaning; outputs/03_analysis", report_paths,
        (3.0, 20_000_000, 0, 250_000), lambda: build_report_evidence(include_resource_table=False),
        retained={"profile": profile, "context": context, "analysis": analysis, "features": feature_data},
    )
    write_csv(DOCUMENTATION_OUTPUTS / "resources.csv", resources)
    write_resource_table()

    failed = [row for row in checks if row["status"] != "PASS"]
    print(f"Built {len(context['orders']):,} cleaned orders and {len(feature_data['features']):,} model-ready rows.")
    print(f"All {len(checks)} validation checks passed." if not failed else f"FAILED checks: {len(failed)}")
    print(f"Outputs: {OUTPUTS}")
    return 1 if failed else 0
