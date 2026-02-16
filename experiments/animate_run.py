# experiments/animate_run.py
from __future__ import annotations
import numpy as np  # add at top of file

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from config import SIM_DURATION_MIN, CITY_SIZE_KM, Weights, RANDOM_SEED
from data.generate_data import set_seed, generate_bikes, generate_orders, generate_stations
from data.scenarios import SCENARIOS
from simulator.environment import Environment

# Choose ONE policy
from simulator.baseline_policy import baseline_decide
# from simulator.heuristic_policy import heuristic_decide
# from simulator.global_policy import global_decide


def run_and_animate(scenario_name: str = "high"):
    set_seed(RANDOM_SEED)
    sc = SCENARIOS[scenario_name]

    bikes = generate_bikes(sc["bikes"])
    orders = generate_orders(sc["orders"])
    stations = generate_stations(sc["stations"])

    env = Environment(bikes=bikes, orders=orders, stations=stations, weights=Weights())

    # Run simulation (collects env.trace)
    env.run(SIM_DURATION_MIN, decide_fn=baseline_decide)
    # env.run(SIM_DURATION_MIN, decide_fn=heuristic_decide)
    # env.run(SIM_DURATION_MIN, decide_fn=global_decide)

    trace = env.trace

    fig, ax = plt.subplots()
    ax.set_xlim(0, CITY_SIZE_KM)
    ax.set_ylim(0, CITY_SIZE_KM)
    ax.set_title(f"Scenario: {scenario_name}")
    ax.set_xlabel("x (km)")
    ax.set_ylabel("y (km)")

    # scatter artists (initialized empty)
    bikes_sc = ax.scatter([], [])
    stations_sc = ax.scatter([], [])
    active_orders_sc = ax.scatter([], [])
    delivered_orders_sc = ax.scatter([], [])

    time_text = ax.text(0.02, 0.98, "", transform=ax.transAxes, va="top")

    def init():
        empty = np.empty((0, 2))
        bikes_sc.set_offsets(empty)
        stations_sc.set_offsets(empty)
        active_orders_sc.set_offsets(empty)
        delivered_orders_sc.set_offsets(empty)
        time_text.set_text("")
        return bikes_sc, stations_sc, active_orders_sc, delivered_orders_sc, time_text
    
    def update(frame):
        snap = trace[frame]

        # stations
        sx = [s[1] for s in snap["stations"]]
        sy = [s[2] for s in snap["stations"]]
        stations_sc.set_offsets(list(zip(sx, sy)))

        # bikes
        bx = [b[1] for b in snap["bikes"]]
        by = [b[2] for b in snap["bikes"]]
        bikes_sc.set_offsets(list(zip(bx, by)))

        # orders split active vs delivered
        active = [(o[1], o[2]) for o in snap["orders"] if not o[3] and o[0] is not None]
        delivered = [(o[1], o[2]) for o in snap["orders"] if o[3]]

        empty = np.empty((0, 2))
        active_orders_sc.set_offsets(active if active else empty)
        delivered_orders_sc.set_offsets(delivered if delivered else empty)


        time_text.set_text(f"t = {snap['t']} min")

        return bikes_sc, stations_sc, active_orders_sc, delivered_orders_sc, time_text

    ani = FuncAnimation(fig, update, frames=len(trace), init_func=init, interval=50, blit=True)
    plt.show()


if __name__ == "__main__":
    run_and_animate("high")
