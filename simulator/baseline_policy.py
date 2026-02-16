# simulator/baseline_policy.py
from __future__ import annotations
from config import SOC_MIN_BASELINE
from simulator.environment import Environment
from model.bike import Bike

def baseline_decide(env: Environment, b: Bike) -> None:
    active = env.active_orders()
    if not active:
        return

    if b.soc < SOC_MIN_BASELINE:
        s = env.nearest_station(b)
        env.start_travel_to_station(b, s)
        return

    # nearest order
    o = min(active, key=lambda o: (o.x - b.x) ** 2 + (o.y - b.y) ** 2)
    env.start_travel_to_order(b, o)
