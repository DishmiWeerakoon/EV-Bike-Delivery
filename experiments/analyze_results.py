# experiments/analyze_results.py
from __future__ import annotations
import os
import csv
from collections import defaultdict

# import matplotlib.pyplot as plt  # optional plots

def load_metrics(csv_path: str):
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            # convert numeric fields where possible
            for k, v in list(row.items()):
                if v is None:
                    continue
                try:
                    if "." in v:
                        row[k] = float(v)
                    else:
                        row[k] = int(v)
                except Exception:
                    pass
            rows.append(row)
    return rows

def summarize(rows):
    # group by (scenario, policy)
    groups = defaultdict(list)
    for row in rows:
        groups[(row["scenario"], row["policy"])].append(row)

    summary = []
    for (scenario, policy), items in groups.items():
        def avg(key):
            vals = [x[key] for x in items if x.get(key) is not None]
            return sum(vals) / len(vals) if vals else None

        summary.append({
            "scenario": scenario,
            "policy": policy,
            "orders_delivered_avg": avg("orders_delivered"),
            "late_deliveries_avg": avg("late_deliveries"),
            "avg_completion_time_min_avg": avg("avg_completion_time_min"),
            "avg_bike_downtime_min_avg": avg("avg_bike_downtime_min"),
            "avg_soc_avg": avg("avg_soc"),
        })
    return summary

def save_summary(summary, out_csv):
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)

def plot_metric(summary, metric_key, out_path):
    # one plot per metric; no manual colors (default)
    scenarios = sorted(set(s["scenario"] for s in summary))
    policies = sorted(set(s["policy"] for s in summary))

    x = list(range(len(scenarios)))
    width = 0.35 if len(policies) == 2 else 0.25

    plt.figure()
    for i, pol in enumerate(policies):
        y = []
        for sc in scenarios:
            row = next((r for r in summary if r["scenario"] == sc and r["policy"] == pol), None)
            y.append(row[metric_key] if row else 0)
        offset = [(xi + (i - (len(policies)-1)/2) * width) for xi in x]
        plt.bar(offset, y, width=width, label=pol)

    plt.xticks(x, scenarios)
    plt.ylabel(metric_key)
    plt.legend()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
