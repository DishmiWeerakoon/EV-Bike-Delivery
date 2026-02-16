# main.py
import os

from data.scenarios import SCENARIOS
from experiments.run_baseline import run_baseline, save_metrics as save_baseline
from experiments.run_heuristic import run_heuristic, save_metrics as save_heuristic
from experiments.analyze_results import load_metrics, summarize, save_summary, plot_metric

RESULTS_CSV = os.path.join("results", "tables", "runs.csv")
SUMMARY_CSV = os.path.join("results", "tables", "summary.csv")

def main():
    # Run each scenario once for baseline + heuristic.
    # Later you can loop 10 times with different seeds for stronger statistics.
    for sc in SCENARIOS.keys():
        m1 = run_baseline(sc)
        save_baseline(m1, RESULTS_CSV)

        m2 = run_heuristic(sc)
        save_heuristic(m2, RESULTS_CSV)

    rows = load_metrics(RESULTS_CSV)
    summ = summarize(rows)
    save_summary(summ, SUMMARY_CSV)

    # plots
    #plot_metric(summ, "orders_delivered_avg", os.path.join("results", "plots", "orders_delivered.png"))
    #plot_metric(summ, "late_deliveries_avg", os.path.join("results", "plots", "late_deliveries.png"))
    #plot_metric(summ, "avg_bike_downtime_min_avg", os.path.join("results", "plots", "downtime.png"))

    print("Done.")
    print("Saved:", RESULTS_CSV)
    print("Saved:", SUMMARY_CSV)

if __name__ == "__main__":
    main()
