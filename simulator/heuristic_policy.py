# simulator/heuristic_policy.py
from __future__ import annotations
import math
from typing import Optional, Tuple

from config import CANDIDATE_ORDERS_K, CANDIDATE_STATIONS_K, CHARGE_TARGET_SOC
from simulator.environment import (
    Environment, dist_km, travel_time_min, energy_fraction,
    battery_risk_penalty
)
from model.bike import Bike
from model.order import Order
from model.station import Station

SAFETY_MARGIN = 0.05  # 5% buffer


def required_soc_for_order(env: Environment, b: Bike, o: Order) -> float:
    # bike -> order
    d1 = dist_km((b.x, b.y), (o.x, o.y))
    soc1 = energy_fraction(d1, b)

    # order -> nearest station after delivery (safety)
    nearest_s = min(env.stations.values(), key=lambda s: dist_km((o.x, o.y), (s.x, s.y)))
    d2 = dist_km((o.x, o.y), (nearest_s.x, nearest_s.y))
    soc2 = energy_fraction(d2, b)

    return min(1.0, soc1 + soc2 + SAFETY_MARGIN)


def est_completion_time(env: Environment, b: Bike, o: Order) -> int:
    d = dist_km((b.x, b.y), (o.x, o.y))
    t_travel = travel_time_min(d, b.speed_kmph)
    return env.t + t_travel + o.service_time


def heuristic_decide(env: Environment, b: Bike) -> None:
    if b.status != "idle":
        return

    active = env.active_orders()
    if not active:
        # No orders: only top-up if low SOC
        if b.soc < 0.60:
            s = env.best_station_for_bike(b)
            b.charge_target_soc = min(1.0, max(b.soc, CHARGE_TARGET_SOC))
            env.start_travel_to_station(b, s)
        return

    orders = env.order_candidates(b, CANDIDATE_ORDERS_K)
    stations = env.station_candidates(b, CANDIDATE_STATIONS_K)

    best: Optional[Tuple[str, int]] = None
    best_score = float("inf")

    # ---------------- Deliver options ----------------
    for o in orders:
        req_soc = required_soc_for_order(env, b, o)
        if b.soc < req_soc:
            continue

        d = dist_km((b.x, b.y), (o.x, o.y))
        t_travel = travel_time_min(d, b.speed_kmph)
        soc_after = b.soc - energy_fraction(d, b)

        completion = est_completion_time(env, b, o)
        late = max(0, completion - o.deadline)

        score = (
            env.w.w_travel * t_travel +
            env.w.w_late * late +
            env.w.w_battery_risk * battery_risk_penalty(soc_after)
        )
        if score < best_score:
            best_score = score
            best = ("deliver", o.id)

    # minimum SOC needed among candidate orders
    min_required = None
    for o in orders:
        r = required_soc_for_order(env, b, o)
        min_required = r if min_required is None else min(min_required, r)
    if min_required is None:
        min_required = 0.60

    # ---------------- Charge options ----------------
    for s in stations:
        d = dist_km((b.x, b.y), (s.x, s.y))
        t_travel = travel_time_min(d, b.speed_kmph)
        soc_after = b.soc - energy_fraction(d, b)

        # queue wait estimate: bikes ahead / ports * avg charge time
        ahead = len(s.queue)
        avg_charge = 15  # minutes (rough)
        queue_wait = int(math.ceil((ahead / max(1, s.ports)) * avg_charge))
        downtime = t_travel + queue_wait

        score = (
            env.w.w_travel * t_travel +
            env.w.w_queue * queue_wait +
            env.w.w_downtime * downtime +
            env.w.w_battery_risk * battery_risk_penalty(soc_after)
        )
        if score < best_score:
            best_score = score
            best = ("charge", s.id)

    if best is None:
        return

    if best[0] == "deliver":
        env.start_travel_to_order(b, env.orders[best[1]])
    else:
        b.charge_target_soc = min(1.0, max(b.soc, min_required))
        env.start_travel_to_station(b, env.stations[best[1]])
