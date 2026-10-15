"""Stage 3: answer the three delivery-delay business questions."""

from collections import Counter, defaultdict

from .common import make_bar_chart, percentile, wilson, write_csv
from .config import ANALYSIS_OUTPUTS, CHART_OUTPUTS


def analyse(context: dict) -> dict:
    """Create summary/chart data and return results used by later stages."""
    orders = context["orders"]
    eligible = [row for row in orders if row["_label"] is not None]
    late = [row for row in eligible if row["_label"] == 1]
    on_time = len(eligible) - len(late)
    rate = len(late) / len(eligible)
    low, high = wilson(len(late), len(eligible))
    signed_delays = [row["_delay_days"] for row in eligible]
    positive_delays = [row["_delay_days"] for row in late]

    lateness_summary = [
        {"metric": "all_orders", "value": len(orders), "unit": "orders"},
        {"metric": "reliably_labelled_orders", "value": len(eligible), "unit": "orders"},
        {"metric": "unlabelled_orders", "value": len(orders) - len(eligible), "unit": "orders"},
        {"metric": "late_orders", "value": len(late), "unit": "orders"},
        {"metric": "on_time_orders", "value": on_time, "unit": "orders"},
        {"metric": "late_rate", "value": round(rate, 6), "unit": "proportion"},
        {"metric": "late_rate_wilson_95_low", "value": round(low, 6), "unit": "proportion"},
        {"metric": "late_rate_wilson_95_high", "value": round(high, 6), "unit": "proportion"},
        {"metric": "median_signed_delay", "value": percentile(signed_delays, .5), "unit": "calendar_days"},
        {"metric": "median_late_delay", "value": percentile(positive_delays, .5), "unit": "calendar_days"},
        {"metric": "late_delay_q1", "value": percentile(positive_delays, .25), "unit": "calendar_days"},
        {"metric": "late_delay_q3", "value": percentile(positive_delays, .75), "unit": "calendar_days"},
        {"metric": "maximum_late_delay", "value": max(positive_delays), "unit": "calendar_days"},
    ]
    write_csv(ANALYSIS_OUTPUTS / "lateness_summary.csv", lateness_summary)

    delay_bins = [
        ("8+ days early", lambda x: x <= -8),
        ("1-7 days early", lambda x: -7 <= x <= -1),
        ("estimated date", lambda x: x == 0),
        ("1-3 days late", lambda x: 1 <= x <= 3),
        ("4-7 days late", lambda x: 4 <= x <= 7),
        ("8-14 days late", lambda x: 8 <= x <= 14),
        ("15+ days late", lambda x: x >= 15),
    ]
    delay_distribution = []
    for label, predicate in delay_bins:
        count = sum(predicate(value) for value in signed_delays)
        delay_distribution.append({
            "delay_group": label, "orders": count, "share": round(count / len(eligible), 6),
        })
    write_csv(ANALYSIS_OUTPUTS / "delay_distribution.csv", delay_distribution)

    approval_groups = [
        ("0-13 days", 0, 13), ("14-20 days", 14, 20), ("21-27 days", 21, 27),
        ("28-34 days", 28, 34), ("35+ days", 35, 10_000),
    ]
    approval_rows = []
    for label, start, end in approval_groups:
        group = [
            row for row in eligible if row["_approval_to_estimate_days"] is not None
            and start <= row["_approval_to_estimate_days"] <= end
        ]
        group_late = sum(row["_label"] for row in group)
        group_low, group_high = wilson(group_late, len(group))
        approval_rows.append({
            "approval_to_estimate_group": label, "labelled_orders": len(group),
            "late_orders": group_late,
            "late_rate": round(group_late / len(group), 6) if group else "",
            "wilson_95_low": round(group_low, 6) if group_low is not None else "",
            "wilson_95_high": round(group_high, 6) if group_high is not None else "",
        })
    write_csv(ANALYSIS_OUTPUTS / "approval_window_lateness.csv", approval_rows)

    by_state = defaultdict(list)
    all_by_state = Counter(row["_state_clean"] for row in orders)
    for row in eligible:
        by_state[row["_state_clean"]].append(row)
    state_rows = []
    for state in sorted(all_by_state):
        group = by_state[state]
        state_late = sum(row["_label"] for row in group)
        state_low, state_high = wilson(state_late, len(group))
        state_rows.append({
            "customer_state": state, "all_orders": all_by_state[state],
            "labelled_orders": len(group), "unlabelled_orders": all_by_state[state] - len(group),
            "late_orders": state_late,
            "late_rate": round(state_late / len(group), 6) if group else "",
            "wilson_95_low": round(state_low, 6) if state_low is not None else "",
            "wilson_95_high": round(state_high, 6) if state_high is not None else "",
            "share_of_all_late_orders": round(state_late / len(late), 6) if late else "",
            "priority_rank": "",
        })
    priority = sorted(
        [row for row in state_rows if row["customer_state"] != "UNKNOWN" and row["labelled_orders"] >= 100],
        key=lambda row: (-row["late_orders"], -float(row["late_rate"]), row["customer_state"]),
    )
    for rank, row in enumerate(priority, 1):
        row["priority_rank"] = rank
    write_csv(ANALYSIS_OUTPUTS / "state_lateness.csv", state_rows)

    sensitivity = [
        {"rule": "strict: normalized delivered status, valid target dates, no detected impossible chronology",
         "labelled_orders": len(eligible), "late_orders": len(late), "late_rate": round(rate, 6)},
        {"rule": "lenient: normalized delivered status and valid actual/estimate dates only",
         "labelled_orders": context["lenient_total"], "late_orders": context["lenient_late"],
         "late_rate": round(context["lenient_late"] / context["lenient_total"], 6)},
    ]
    write_csv(ANALYSIS_OUTPUTS / "sensitivity.csv", sensitivity)

    make_bar_chart(
        CHART_OUTPUTS / "question_1_lateness.png", "Reliable delivery outcomes",
        f"Population: {len(eligible):,} reliably labelled orders; {len(orders)-len(eligible):,} unlabelled",
        [{"outcome": "On time", "count": on_time}, {"outcome": "Late", "count": len(late)}],
        "outcome", "count", "Orders",
    )
    make_bar_chart(
        CHART_OUTPUTS / "question_2_approval_window.png", "Lateness by approval-to-estimate window",
        "Interval uses local calendar dates; bars show the late rate among reliably labelled orders",
        approval_rows, "approval_to_estimate_group", "late_rate", "Late rate", percent=True,
    )
    make_bar_chart(
        CHART_OUTPUTS / "question_3_customer_state.png",
        "State investigation priorities by late-order volume",
        "Named states with at least 100 reliable labels; rates and intervals are saved in the source table",
        priority[:12], "customer_state", "late_orders", "Late orders",
    )

    return {
        "eligible": eligible, "late": late, "late_rate": rate, "late_low": low, "late_high": high,
        "lateness_summary": lateness_summary, "approval_rows": approval_rows,
        "state_rows": state_rows, "priority": priority, "sensitivity": sensitivity,
        "positive_delays": positive_delays,
    }
