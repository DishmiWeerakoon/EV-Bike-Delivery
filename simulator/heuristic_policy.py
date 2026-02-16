# simulator/heuristic_policy.py
from __future__ import annotations
import math

from config import CANDIDATE_ORDERS_K, CANDIDATE_STATIONS_K
from simulator.environment import (
    Environment, dist_km, travel_time_min, energy_fraction,
    battery_risk_penalty, lateness
)
from model.bike import Bike

def required_soc_for_order(env: Environment, b: Bike, o) -> float:
    # SOC needed to reach order
    d1 = dist_km((b.x, b.y), (o.x, o.y))
    soc_need_1 = energy_fraction(d1, b)

    # SOC needed to reach nearest station after delivery (safety)
    nearest_s = min(env.stations.values(), key=lambda s: dist_km((o.x, o.y), (s.x, s.y)))
    d2 = dist_km((o.x, o.y), (nearest_s.x, nearest_s.y))
    soc_need_2 = energy_fraction(d2, b)

    safety_margin = 0.05  # 5% buffer
    return min(1.0, soc_need_1 + soc_need_2 + safety_margin)


def heuristic_decide(env: Environment, b: Bike) -> None:
    active = env.active_orders()
    if not active:
        # optionally top-up when idle and low-ish
        if b.soc < 0.6:
            s = env.nearest_station(b)
            env.start_travel_to_station(b, s)
        return

    orders = env.order_candidates(b, CANDIDATE_ORDERS_K)
    stations = env.station_candidates(b, CANDIDATE_STATIONS_K)

    best = None
    best_score = float("inf")

    # Deliver options
    for o in orders:
        d = dist_km((b.x, b.y), (o.x, o.y))
        t_travel = travel_time_min(d, b.speed_kmph)
        soc_after = b.soc - energy_fraction(d, b)

        arrival = env.t + t_travel
        late = lateness(arrival, o.deadline)

        req_soc = required_soc_for_order(env, b, o)
        if b.soc < req_soc:
            continue


        score = (
            env.w.w_travel * t_travel +
            env.w.w_late * late +
            env.w.w_battery_risk * battery_risk_penalty(soc_after)
        )
        if score < best_score:
            best_score = score
            best = ("deliver", o.id)

    # Charge options
    min_required = None
    for o in orders:
        r = required_soc_for_order(env, b, o)
        if min_required is None or r < min_required:
            min_required = r

    # fallback if no orders (shouldn’t happen here)
    if min_required is None:
        min_required = 0.6


    for s in stations:
        d = dist_km((b.x, b.y), (s.x, s.y))
        t_travel = travel_time_min(d, b.speed_kmph)
        soc_after = b.soc - energy_fraction(d, b)

        # simple queue wait estimate
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
        b.charge_target_soc = min_required
        env.start_travel_to_station(b, env.stations[best[1]])
