# experiments/run_heuristic.py
from __future__ import annotations
import os
import csv

from config import SIM_DURATION_MIN, Weights, RANDOM_SEED
from data.generate_data import set_seed, generate_bikes, generate_orders, generate_stations, save_generated_data
from data.scenarios import SCENARIOS
from simulator.environment import Environment
from simulator.heuristic_policy import heuristic_decide

def run_heuristic(scenario_name: str) -> dict:
    if scenario_name not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_name}")

    set_seed(RANDOM_SEED)
    sc = SCENARIOS[scenario_name]

    bikes = generate_bikes(sc["bikes"])
    orders = generate_orders(sc["orders"])
    stations = generate_stations(sc["stations"])

    save_generated_data(bikes, orders, stations)


    env = Environment(bikes=bikes, orders=orders, stations=stations, weights=Weights())
    env.run(SIM_DURATION_MIN, decide_fn=heuristic_decide)
    env.export_order_bike_table(os.path.join("results", "tables", f"orders_heuristic_{scenario_name}.csv"))
    metrics = env.metrics()
    metrics["scenario"] = scenario_name
    metrics["policy"] = "heuristic"
    return metrics

def save_metrics(metrics: dict, out_csv: str) -> None:
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    write_header = not os.path.exists(out_csv)
    with open(out_csv, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(metrics.keys()))
        if write_header:
            w.writeheader()
        w.writerow(metrics)
