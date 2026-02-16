# simulator/environment.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import math

from config import DT_MIN, CHARGE_TARGET_SOC
from config import Weights
from model.bike import Bike
from model.order import Order
from model.station import Station

Point = Tuple[float, float]

def dist_km(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])

def travel_time_min(distance_km: float, speed_kmph: float) -> int:
    if speed_kmph <= 0:
        return 10**9
    return max(1, int(math.ceil((distance_km / speed_kmph) * 60.0)))

def energy_fraction(distance_km: float, bike: Bike) -> float:
    wh = distance_km * bike.wh_per_km
    return wh / max(1e-9, bike.battery_wh)

def battery_risk_penalty(soc_after: float, critical: float = 0.15) -> float:
    if soc_after >= critical:
        return 0.0
    return (critical - soc_after) ** 2 * 100.0

def lateness(arrival_time: int, deadline: int) -> int:
    return max(0, arrival_time - deadline)

@dataclass
class StepInfo:
    time_min: int
    delivered_now: int

class Environment:
    def __init__(self, bikes: List[Bike], orders: List[Order], stations: List[Station], weights: Weights):
        self.bikes: Dict[int, Bike] = {b.id: b for b in bikes}
        self.orders: Dict[int, Order] = {o.id: o for o in orders}
        self.stations: Dict[int, Station] = {s.id: s for s in stations}
        self.w = weights
        self.t = 0
        self.trace = []  # list of snapshots per minute


    def active_orders(self) -> List[Order]:
        #return [o for o in self.orders.values() if (not o.delivered) and (o.release_time <= self.t)]
        return [o for o in self.orders.values()
            if (not o.delivered) and (o.assigned_to is None) and (o.release_time <= self.t)]


    def step(self, decide_fn) -> StepInfo:
        delivered_now = 0

        # 1) update bikes state
        for b in self.bikes.values():
            delivered_now += self._update_bike(b)

        # 2) stations queue → ports
        for s in self.stations.values():
            self._process_station(s)
        '''
        # 3) decision for idle bikes
        for b in self.bikes.values():
            if b.status == "idle":
                decide_fn(self, b)
        '''
        # 3) decision
        try:
            # global policy: decide_fn(env)
            decide_fn(self)
        except TypeError:
            # per-bike policy: decide_fn(env, bike)
            for b in self.bikes.values():
                if b.status == "idle":
                    decide_fn(self, b)


        self.t += DT_MIN

        # record snapshot for visualization
        self.trace.append({
            "t": self.t,
            "bikes": [
                (b.id, b.x, b.y, b.soc, b.status, b.target_order_id, b.target_station_id)
                for b in self.bikes.values()
            ],
            "orders": [
                (o.id, o.x, o.y, o.delivered, o.assigned_to, o.deadline)
                for o in self.orders.values()
            ],
            "stations": [
                (s.id, s.x, s.y, len(s.queue), len(s.charging_bikes), s.ports)
                for s in self.stations.values()
            ]
        })


        return StepInfo(time_min=self.t, delivered_now=delivered_now)

    def run(self, duration_min: int, decide_fn) -> None:
        while self.t < duration_min:
            self.step(decide_fn)

    # ----------------- mechanics -----------------
    def _update_bike(self, b: Bike) -> int:
        delivered_now = 0

        if b.status.startswith("traveling"):
            b.remaining_travel_min -= DT_MIN
            if b.remaining_travel_min <= 0:
                if b.status == "traveling_to_order":
                    o = self.orders[b.target_order_id]  # type: ignore
                    b.x, b.y = o.x, o.y
                    b.status = "delivering"
                    b.remaining_service_min = o.service_time
                elif b.status == "traveling_to_station":
                    s = self.stations[b.target_station_id]  # type: ignore
                    b.x, b.y = s.x, s.y
                    self._arrive_station(b, s)

        elif b.status == "delivering":
            b.remaining_service_min -= DT_MIN
            if b.remaining_service_min <= 0:
                o = self.orders[b.target_order_id]  # type: ignore
                o.delivered = True
                o.completion_time = self.t
                b.delivered_count += 1
                o.delivered_by = b.id

                b.target_order_id = None
                b.status = "idle"
                delivered_now = 1

        elif b.status in ("charging", "waiting_charge"):
            b.downtime_min += DT_MIN

            if b.status == "charging":
                s = self.stations[b.target_station_id]  # type: ignore

                # how much SOC can we add per minute?
                soc_per_min = (s.charge_rate_w / max(1e-9, b.battery_wh)) / 60.0

                # increase SOC for this time step
                b.soc = min(1.0, b.soc + soc_per_min * DT_MIN)

                b.remaining_charge_min -= DT_MIN

                # stop charging once target SOC reached (or timer done)
                if b.soc >= b.charge_target_soc or b.remaining_charge_min <= 0:
                    if b.id in s.charging_bikes:
                        s.charging_bikes.remove(b.id)
                    b.target_station_id = None
                    b.status = "idle"
                    b.charge_target_soc = 0.0


        return delivered_now

    def _process_station(self, s: Station) -> None:
        while len(s.charging_bikes) < s.ports and s.queue:
            bike_id = s.queue.pop(0)
            b = self.bikes[bike_id]
            s.charging_bikes.append(bike_id)
            b.status = "charging"
            self._start_charging(b, s)

    def _arrive_station(self, b: Bike, s: Station) -> None:
        if len(s.charging_bikes) < s.ports:
            s.charging_bikes.append(b.id)
            b.status = "charging"
            self._start_charging(b, s)
        else:
            s.queue.append(b.id)
            b.status = "waiting_charge"
    
    '''

    def _start_charging(self, b: Bike, s: Station) -> None:
        target_soc = max(b.soc, min(1.0, CHARGE_TARGET_SOC))
        needed_wh = (target_soc - b.soc) * b.battery_wh
        minutes = (needed_wh / max(1e-9, s.charge_rate_w)) * 60.0
        b.remaining_charge_min = max(1, int(math.ceil(minutes)))
        # simple model: set SOC to target immediately (you can refine later)
        b.soc = target_soc
        b.target_station_id = s.id
    '''
    '''
    def _start_charging(self, b: Bike, s: Station) -> None:
        # Clamp target between current SOC and 100%
        target_soc = max(b.soc, min(1.0, b.charge_target_soc if b.charge_target_soc > 0 else CHARGE_TARGET_SOC))

        needed_wh = (target_soc - b.soc) * b.battery_wh
        minutes = (needed_wh / max(1e-9, s.charge_rate_w)) * 60.0

        b.remaining_charge_min = max(1, int(math.ceil(minutes)))
        b.charge_target_soc = target_soc
        b.target_station_id = s.id
    '''

    def _start_charging(self, b: Bike, s: Station) -> None:
        # If policy didn't set a target, use default
        target = b.charge_target_soc if b.charge_target_soc > 0 else CHARGE_TARGET_SOC
        target_soc = max(b.soc, min(1.0, target))

        needed_wh = (target_soc - b.soc) * b.battery_wh
        minutes = (needed_wh / max(1e-9, s.charge_rate_w)) * 60.0

        b.remaining_charge_min = max(1, int(math.ceil(minutes)))
        b.charge_target_soc = target_soc
        b.target_station_id = s.id
       
    


    def start_travel_to_order(self, b: Bike, o: Order) -> None:
        d = dist_km((b.x, b.y), (o.x, o.y))
        b.remaining_travel_min = travel_time_min(d, b.speed_kmph)
        b.soc = max(0.0, b.soc - energy_fraction(d, b))
        b.status = "traveling_to_order"
        b.target_order_id = o.id
        o.assigned_to = b.id


    def start_travel_to_station(self, b: Bike, s: Station) -> None:
        d = dist_km((b.x, b.y), (s.x, s.y))
        b.remaining_travel_min = travel_time_min(d, b.speed_kmph)
        b.soc = max(0.0, b.soc - energy_fraction(d, b))
        b.status = "traveling_to_station"
        b.target_station_id = s.id

    # ----------------- evaluation -----------------
    def metrics(self) -> dict:
        orders = list(self.orders.values())
        delivered = [o for o in orders if o.delivered]
        late = [o for o in delivered if (o.completion_time is not None and o.completion_time > o.deadline)]

        avg_completion = None
        if delivered:
            avg_completion = sum(o.completion_time for o in delivered if o.completion_time is not None) / len(delivered)

        return {
            "time_min": self.t,
            "orders_total": len(orders),
            "orders_delivered": len(delivered),
            "late_deliveries": len(late),
            "avg_completion_time_min": avg_completion,
            "avg_bike_downtime_min": sum(b.downtime_min for b in self.bikes.values()) / max(1, len(self.bikes)),
            "avg_soc": sum(b.soc for b in self.bikes.values()) / max(1, len(self.bikes)),
        }

    # helpers for policies
    def nearest_station(self, b: Bike) -> Station:
        return min(self.stations.values(), key=lambda s: dist_km((b.x, b.y), (s.x, s.y)))

    def station_candidates(self, b: Bike, k: int) -> List[Station]:
        return sorted(self.stations.values(), key=lambda s: dist_km((b.x, b.y), (s.x, s.y)))[:k]

    def order_candidates(self, b: Bike, k: int) -> List[Order]:
        active = self.active_orders()
        return sorted(active, key=lambda o: dist_km((b.x, b.y), (o.x, o.y)))[:k]

    def export_order_bike_table(self, out_csv: str) -> None:
        import os, csv
        os.makedirs(os.path.dirname(out_csv), exist_ok=True)

        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "order_id", "delivered", "delivered_by",
                "release_time", "deadline", "completion_time",
                "is_late", "x", "y"
            ])
            for o in sorted(self.orders.values(), key=lambda x: x.id):
                is_late = int(o.delivered and o.completion_time is not None and o.completion_time > o.deadline)
                w.writerow([
                    o.id, int(o.delivered), o.delivered_by,
                    o.release_time, o.deadline, o.completion_time,
                    is_late, o.x, o.y
                ])


    def best_station_for_bike(self, b: Bike, alpha: float = 3.0) -> Station:
        """
        Choose station that minimizes: travel_time + alpha * expected_queue_wait.
        alpha controls how strongly you avoid queues.
        """
        best_s = None
        best_score = float("inf")

        for s in self.stations.values():
            # travel time to station
            d = dist_km((b.x, b.y), (s.x, s.y))
            t_travel = travel_time_min(d, b.speed_kmph)

            # rough queue wait estimate
            ports = max(1, s.ports)
            bikes_ahead = max(0, len(s.queue) - ports)
            expected_wait = int((bikes_ahead / ports) * 10)  # 10-min chunks (simple model)

            score = t_travel + alpha * expected_wait
            if score < best_score:
                best_score = score
                best_s = s

        # best_s will never be None if you have at least 1 station
        return best_s
