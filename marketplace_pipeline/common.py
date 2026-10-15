"""Small shared helpers for CSVs, statistics, charts and measurements."""

import csv
import gc
import math
import time
import tracemalloc
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

from .config import BRAZIL_STATES, DATE_FORMAT, ROOT
from .monitoring import ResourceMonitor, python_size


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_date(value: str | None) -> tuple[datetime | None, str]:
    if value is None or not value.strip():
        return None, "missing"
    try:
        return datetime.strptime(value, DATE_FORMAT), "valid"
    except ValueError:
        return None, "invalid"


def percentile(values: list[float], proportion: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * proportion
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def wilson(successes: int, total: int) -> tuple[float | None, float | None]:
    if total == 0:
        return None, None
    z = 1.96
    rate = successes / total
    denominator = 1 + z * z / total
    centre = (rate + z * z / (2 * total)) / denominator
    half = z * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total * total)) / denominator
    return centre - half, centre + half


def clean_state(value: str | None) -> str:
    state = (value or "").strip().upper()
    return state if state in BRAZIL_STATES else "UNKNOWN"


def value_or_zero(value) -> float:
    return round(float(value), 6) if value is not None else 0.0


def timed_step(resources: list[dict], step: str, inputs: str, outputs: list[Path],
               estimate: tuple[float, int, int, int], function, retained=None):
    gc.collect()
    with ResourceMonitor() as monitor:
        tracemalloc.start()
        started = time.perf_counter()
        try:
            result = function()
            elapsed = time.perf_counter() - started
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
    intermediate_bytes = python_size({"retained": retained, "result": result})
    saved = sum(path.stat().st_size for path in outputs if path.exists())
    artifact_sizes = "; ".join(
        f"{path.relative_to(ROOT)}={path.stat().st_size} bytes" for path in outputs if path.exists()
    )
    resources.append({
        "step": step,
        "input_artifacts": inputs,
        "output_artifacts": "; ".join(str(path.relative_to(ROOT)) for path in outputs),
        "estimated_runtime_seconds": estimate[0],
        "measured_runtime_seconds": round(elapsed, 4),
        "estimated_peak_memory_bytes": estimate[1],
        "measured_peak_memory_bytes": peak,
        "estimated_temporary_storage_bytes": estimate[2],
        "measured_temporary_storage_bytes": monitor.peak_temporary,
        "estimated_saved_storage_bytes": estimate[3],
        "measured_saved_storage_bytes": saved,
        "intermediate_artifacts_and_sizes": artifact_sizes,
        "measured_intermediate_python_bytes": intermediate_bytes,
        "initial_process_rss_bytes": monitor.initial_rss,
        "estimated_process_peak_rss_bytes": (monitor.initial_rss + estimate[1]) if monitor.initial_rss is not None else "",
        "sampled_process_peak_rss_bytes": monitor.peak_rss,
        "measurement_method": "tracemalloc; 20ms RSS/temp-file sampling; recursive sys.getsizeof; saved file sizes",
        "measurement_scope": "Python peak=new allocations in step; RSS=whole process including native/retained memory; intermediates=retained inputs+result Python containers, shared objects once; temp=redirected run directory+SQLite sidecars; short peaks may be missed",
    })
    return result


def make_bar_chart(path: Path, title: str, subtitle: str, rows: list[dict],
                   label_key: str, value_key: str, value_label: str,
                   percent: bool = False) -> None:
    """Create a presentation-ready PNG bar chart with matplotlib."""
    labels = [str(row[label_key]) for row in rows]
    values = [float(row[value_key]) for row in rows]
    colours = ["#2F6B9A" if index % 2 == 0 else "#D46A5C" for index in range(len(rows))]

    figure, axis = plt.subplots(figsize=(9.2, 5.2))
    bars = axis.bar(labels, values, color=colours, width=0.7)
    axis.set_ylabel(value_label)
    axis.grid(axis="y", color="#D7DEE7", linewidth=0.8)
    axis.set_axisbelow(True)
    axis.spines[["top", "right"]].set_visible(False)
    axis.tick_params(axis="x", rotation=28 if len(labels) > 5 else 0)

    if percent:
        axis.yaxis.set_major_formatter(PercentFormatter(1.0))
        bar_labels = [f"{value:.1%}" for value in values]
    else:
        bar_labels = [f"{value:,.0f}" for value in values]

    axis.bar_label(bars, labels=bar_labels, padding=3, fontsize=8.5)
    axis.set_ylim(0, max(values or [1]) * 1.16)
    figure.suptitle(title, x=0.08, ha="left", fontsize=15, fontweight="bold")
    axis.set_title(subtitle, loc="left", fontsize=9.5, color="#52606D", pad=10)
    figure.tight_layout(rect=(0, 0, 1, 0.93))

    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)
