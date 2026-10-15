"""Build report figures and sensitivity evidence from saved pipeline CSVs.

Called by runner.py; the separate report folder need not exist beforehand.
Generated evidence is written beneath report/; the written report is separate.
"""

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "report"
EVIDENCE = REPORT / "evidence"
FIGURES = REPORT / "figures"


def read(relative):
    with (ROOT / relative).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def save(name, rows):
    with (EVIDENCE / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def parse(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def wilson(k, n):
    if not n:
        return 0, 0
    z = 1.96
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * (p * (1 - p) / n + z * z / (4 * n * n)) ** .5 / den
    return mid - half, mid + half


def style(axis):
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="y", alpha=.2)
    axis.set_axisbelow(True)


def finish(fig, name):
    fig.tight_layout()
    fig.savefig(FIGURES / name, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main(include_resource_table=True):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.titlesize": 12})
    cleaned = read("outputs/02_cleaning/cleaned_orders.csv")
    labels = {r["order_id"]: r for r in read("outputs/02_cleaning/delivery_labels.csv")}
    windows = [("0--13", 0, 13), ("14--20", 14, 20), ("21--27", 21, 27),
               ("28--34", 28, 34), ("35+", 35, 10000)]
    populations = {"strict": [], "lenient": []}
    for row in cleaned:
        actual = parse(row["actual_delivery_timestamp_clean"])
        estimate = parse(row["estimated_delivery_timestamp_clean"])
        if row["order_status_clean"] != "delivered" or not actual or not estimate:
            continue
        approval = parse(row["approval_timestamp_clean"])
        record = {
            "state": row["customer_state_clean"],
            "late": int(actual.date() > estimate.date()),
            "window": ((estimate.date() - approval.date()).days
                       if approval and estimate >= approval else None),
        }
        populations["lenient"].append(record)
        if labels[row["order_id"]]["label_eligible"] == "1":
            populations["strict"].append(record)

    window_rows = []
    state_rows = []
    threshold_rows = []
    for rule, records in populations.items():
        for group, start, end in windows:
            selected = [r for r in records if r["window"] is not None and start <= r["window"] <= end]
            n, k = len(selected), sum(r["late"] for r in selected)
            low, high = wilson(k, n)
            window_rows.append({"rule": rule, "window_days": group, "orders": n,
                                "late": k, "rate": k / n, "wilson_low": low, "wilson_high": high})
        by_state = defaultdict(list)
        for record in records:
            by_state[record["state"]].append(record)
        current = []
        for state, selected in sorted(by_state.items()):
            n, k = len(selected), sum(r["late"] for r in selected)
            current.append({"rule": rule, "state": state, "orders": n,
                            "late": k, "rate": k / n})
        state_rows.extend(current)
        for threshold in (50, 100, 200):
            ranked = sorted([r for r in current if r["state"] != "UNKNOWN" and r["orders"] >= threshold],
                            key=lambda r: (-r["late"], -r["rate"], r["state"]))
            threshold_rows.append({"rule": rule, "minimum_labels": threshold,
                                   "first": ranked[0]["state"], "second": ranked[1]["state"],
                                   "third": ranked[2]["state"]})
    save("window_sensitivity.csv", window_rows)
    save("state_sensitivity.csv", state_rows)
    save("priority_threshold_sensitivity.csv", threshold_rows)

    summary = {r["metric"]: float(r["value"]) for r in read("outputs/03_analysis/lateness_summary.csv")}
    distribution = read("outputs/03_analysis/delay_distribution.csv")[3:]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4))
    bars = axes[0].bar(["On time", "Late"], [summary["on_time_orders"], summary["late_orders"]], color=["#2F6B9A", "#D46A5C"])
    axes[0].bar_label(bars, fmt="%.0f", padding=3)
    axes[0].set_title("Reliable delivery outcomes")
    axes[0].set_ylabel("Orders (n = 16,481)")
    axes[0].set_ylim(0, 17500)
    bars = axes[1].bar(["1--3", "4--7", "8--14", "15+"], [int(r["orders"]) for r in distribution], color="#D46A5C")
    axes[1].bar_label(bars, padding=3)
    axes[1].set_title("Delay severity among late orders")
    axes[1].set_xlabel("Calendar days late")
    axes[1].set_ylabel("Late orders (n = 1,107)")
    axes[1].set_ylim(0, 380)
    for axis in axes:
        style(axis)
    finish(fig, "question_1.png")

    strict = window_rows[:5]
    fig, axis = plt.subplots(figsize=(9.5, 3.3))
    rates = [r["rate"] for r in strict]
    errors = [[r["rate"] - r["wilson_low"] for r in strict],
              [r["wilson_high"] - r["rate"] for r in strict]]
    bars = axis.bar([r["window_days"] for r in strict], rates, color="#2F6B9A", yerr=errors, capsize=4)
    axis.bar_label(bars, labels=[f"n={r['orders']:,}" for r in strict], padding=23, fontsize=9)
    axis.yaxis.set_major_formatter(PercentFormatter(1))
    axis.set_ylim(0, .115)
    axis.set_ylabel("Late rate; 95% Wilson intervals")
    axis.set_xlabel("Approval-to-estimate interval (local calendar days)")
    style(axis)
    finish(fig, "question_2.png")
    (EVIDENCE / "window_table.tex").write_text("\n".join(
        f"{r['window_days']} & {r['orders']:,} & {r['late']:,} & {100*r['rate']:.2f}\\% & "
        f"{100*r['wilson_low']:.2f}--{100*r['wilson_high']:.2f}\\% \\\\"
        for r in strict) + "\n", encoding="utf-8")

    states = {r["customer_state"]: r for r in read("outputs/03_analysis/state_lateness.csv")}
    names = ["SP", "RJ", "MG", "CE", "MA", "PE", "UNKNOWN"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4))
    selected = [states[name] for name in names]
    rates = [float(r["late_rate"]) for r in selected]
    errors = [[float(r["late_rate"]) - float(r["wilson_95_low"]) for r in selected],
              [float(r["wilson_95_high"]) - float(r["late_rate"]) for r in selected]]
    axes[0].bar(names, rates, color="#2F6B9A", yerr=errors, capsize=3)
    axes[0].axhline(summary["late_rate"], color="#52606D", linestyle="--", label="Overall 6.7%")
    axes[0].legend(frameon=False, fontsize=8)
    axes[0].set_title("Selected customer-state late rates")
    axes[0].yaxis.set_major_formatter(PercentFormatter(1))
    axes[0].set_ylabel("Rate; 95% Wilson intervals")
    axes[1].bar(names, [int(r["late_orders"]) for r in selected], color="#D46A5C")
    axes[1].set_title("Late-order volume in the same groups")
    axes[1].set_ylabel("Late orders")
    for axis in axes:
        style(axis)
        axis.tick_params(axis="x", rotation=30)
    finish(fig, "question_3.png")
    (EVIDENCE / "state_table.tex").write_text("\n".join(
        f"{r['customer_state']} & {int(r['labelled_orders']):,} & {int(r['late_orders']):,} & "
        f"{100*float(r['late_rate']):.1f}\\% & {100*float(r['wilson_95_low']):.1f}--"
        f"{100*float(r['wilson_95_high']):.1f}\\% \\\\"
        for r in selected) + "\n", encoding="utf-8")

    if include_resource_table:
        write_resource_table()
    for r in window_rows:
        print(f"{r['rule']:7} {r['window_days']:6} n={r['orders']:5} late={r['late']:4} rate={r['rate']:.4%}")
    print("State-volume top three:", threshold_rows)
    print("Built three report figures, three sensitivity CSVs and three LaTeX tables.")


def write_resource_table():
    """Render all recorded stages; called after the runner finalizes its log."""
    resources = read("outputs/05_documentation/resources.csv")
    names = {"0_database_setup": "Database", "1_load_and_profile": "Load/profile",
             "2_clean_and_label": "Clean/label", "3_exploratory_analysis": "Analysis/charts",
             "4_feature_engineering": "Features", "5_validation": "Validation",
             "6_documentation": "Documentation", "7_report_evidence": "Report evidence"}
    (EVIDENCE / "resource_table.tex").write_text("\n".join(
        f"{names[r['step']]} & {float(r['estimated_runtime_seconds']):.2f} / {float(r['measured_runtime_seconds']):.4f} & "
        f"{float(r['estimated_peak_memory_bytes'])/1e6:.2f} / {float(r['measured_peak_memory_bytes'])/1e6:.3f} & "
        f"{float(r['estimated_saved_storage_bytes'])/1e6:.3f} / {float(r['measured_saved_storage_bytes'])/1e6:.3f} \\\\"
        for r in resources) + "\n", encoding="utf-8")
    rss = max(float(r.get("sampled_process_peak_rss_bytes") or 0) for r in resources) / 1e6
    intermediate = max(float(r.get("measured_intermediate_python_bytes") or 0) for r in resources) / 1e6
    temporary = max(int(r["measured_temporary_storage_bytes"]) for r in resources)
    runtime = sum(float(r["measured_runtime_seconds"]) for r in resources)
    mode = resources[0].get("database_setup_mode", "unrecorded").replace("_", "\\_")
    (EVIDENCE / "resource_summary.tex").write_text(
        f"Recorded stage runtimes sum to {runtime:.2f} s. Setup mode: {mode}. "
        f"Maximum sampled process RSS was {rss:.2f} MB; maximum reachable input/result "
        f"Python size was {intermediate:.2f} MB; maximum observed temporary files occupied "
        f"{temporary:,} bytes within the monitored scope.\n", encoding="utf-8")


if __name__ == "__main__":
    main()
