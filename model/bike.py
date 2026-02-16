# model/bike.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class Bike:
    id: int
    x: float
    y: float
    soc: float                 # 0..1
    battery_wh: float
    wh_per_km: float
    speed_kmph: float
    charge_target_soc: float = 0.0


    # dynamic state
    status: str = "idle"       # idle, traveling_to_order, delivering, traveling_to_station, charging, waiting_charge
    target_order_id: Optional[int] = None
    target_station_id: Optional[int] = None

    remaining_travel_min: int = 0
    remaining_service_min: int = 0
    remaining_charge_min: int = 0

    # stats
    downtime_min: int = 0
    delivered_count: int = 0
