# simulator/global_policy.py
from __future__ import annotations
from typing import List

from model.bike import Bike
from model.order import Order
from model.station import Station
from simulator.environment import (
    Environment, dist_km, travel_time_min, energy_fraction,
    battery_risk_penalty
)

SAFETY_MARGIN = 0.05
BIG = 1e9


def est_completion_time(env: Environment, b: Bike, o: Order) -> int:
    d = dist_km((b.x, b.y), (o.x, o.y))
    t_travel = travel_time_min(d, b.speed_kmph)
    return env.t + t_travel + o.service_time


def nearest_station_to_point(env: Environment, x: float, y: float) -> Station:
    return min(env.stations.values(), key=lambda s: dist_km((x, y), (s.x, s.y)))


def required_soc_for_order(env: Environment, b: Bike, o: Order) -> float:
    d1 = dist_km((b.x, b.y), (o.x, o.y))
    soc1 = energy_fraction(d1, b)

    s2 = nearest_station_to_point(env, o.x, o.y)
    d2 = dist_km((o.x, o.y), (s2.x, s2.y))
    soc2 = energy_fraction(d2, b)

    return min(1.0, soc1 + soc2 + SAFETY_MARGIN)


def hungarian(cost: List[List[float]]) -> List[int]:
    n = len(cost)
    u = [0.0] * (n + 1)
    v = [0.0] * (n + 1)
    p = [0] * (n + 1)
    way = [0] * (n + 1)

    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [float("inf")] * (n + 1)
        used = [False] * (n + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = float("inf")
            j1 = 0
            for j in range(1, n + 1):
                if not used[j]:
                    cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur
                        way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]
                        j1 = j
            for j in range(0, n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break

    assignment = [-1] * n
    for j in range(1, n + 1):
        assignment[p[j] - 1] = j - 1
    return assignment


def global_decide(env: Environment) -> None:
    idle_bikes = [b for b in env.bikes.values() if b.status == "idle"]
    if not idle_bikes:
        return

    orders = env.active_orders()

    # --- No orders: only small subset top-up (optional) ---
    if not orders:
        idle_sorted = sorted(idle_bikes, key=lambda x: x.soc)
        k = max(1, int(0.30 * len(idle_sorted)))
        for b in idle_sorted[:k]:
            if b.soc < 0.60:
                s = env.best_station_for_bike(b)
                b.charge_target_soc = min(1.0, b.soc + 0.20)
                env.start_travel_to_station(b, s)
        return

    B = len(idle_bikes)
    O = len(orders)
    N = max(B, O)

    cost = [[BIG for _ in range(N)] for __ in range(N)]

    for i, b in enumerate(idle_bikes):
        for j, o in enumerate(orders):
            req = required_soc_for_order(env, b, o)
            if b.soc < req:
                continue

            d = dist_km((b.x, b.y), (o.x, o.y))
            t_travel = travel_time_min(d, b.speed_kmph)
            soc_after = b.soc - energy_fraction(d, b)

            completion = est_completion_time(env, b, o)
            late = max(0, completion - o.deadline)

            cost[i][j] = (
                env.w.w_travel * t_travel +
                env.w.w_late * late +
                env.w.w_battery_risk * battery_risk_penalty(soc_after)
            )

    assign = hungarian(cost)

    assigned_any = False
    assigned_bikes = set()

    for i in range(B):
        j = assign[i]
        if 0 <= j < O and cost[i][j] < BIG / 2:
            b = idle_bikes[i]
            o = orders[j]
            env.start_travel_to_order(b, o)
            assigned_any = True
            assigned_bikes.add(b.id)

    # --- If nobody could be assigned: charge only bottom 30% SOC ---
    if not assigned_any:
        idle_sorted = sorted(idle_bikes, key=lambda x: x.soc)
        k = max(1, int(0.30 * len(idle_sorted)))
        for b in idle_sorted[:k]:
            s = env.best_station_for_bike(b)
            b.charge_target_soc = min(1.0, b.soc + 0.20)
            env.start_travel_to_station(b, s)
        return

    # --- Some bikes unassigned: only charge those who need it ---
    for b in idle_bikes:
        if b.id in assigned_bikes:
            continue
        if b.status != "idle":
            continue

        min_req = min(required_soc_for_order(env, b, o) for o in orders)
        if b.soc < min_req:
            s = env.best_station_for_bike(b)
            b.charge_target_soc = min(1.0, min_req)
            env.start_travel_to_station(b, s)
