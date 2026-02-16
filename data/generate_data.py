# data/generate_data.py
from __future__ import annotations
import random
from typing import List
from config import CITY_SIZE_KM, RANDOM_SEED
from model.bike import Bike
from model.order import Order
from model.station import Station

import csv
import os

def save_generated_data(bikes, orders, stations, folder="data/saved"):
    os.makedirs(folder, exist_ok=True)

    with open(os.path.join(folder, "bikes.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id","x","y","soc","battery_wh","wh_per_km","speed_kmph"])
        for b in bikes:
            w.writerow([b.id,b.x,b.y,b.soc,b.battery_wh,b.wh_per_km,b.speed_kmph])

    with open(os.path.join(folder, "orders.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id","x","y","release_time","deadline","service_time"])
        for o in orders:
            w.writerow([o.id,o.x,o.y,o.release_time,o.deadline,o.service_time])

    with open(os.path.join(folder, "stations.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id","x","y","ports","charge_rate_w"])
        for s in stations:
            w.writerow([s.id,s.x,s.y,s.ports,s.charge_rate_w])


def set_seed(seed: int = RANDOM_SEED) -> None:
    random.seed(seed)

def generate_bikes(n: int) -> List[Bike]:
    bikes: List[Bike] = []

    # depot in the center of the city
    depot_x = CITY_SIZE_KM / 2.0
    depot_y = CITY_SIZE_KM / 2.0

    for i in range(n):
        bikes.append(
            Bike(
                id=i,
                x=depot_x,
                y=depot_y,
                soc=1.0,
                battery_wh=450.0,
                wh_per_km=18.0,
                speed_kmph=18.0,
            )
        )
    return bikes
'''

def generate_orders(n: int, horizon_min: int = 120) -> List[Order]:
    orders: List[Order] = []
    for i in range(n):
        release = random.randint(0, horizon_min)
        deadline = release + random.randint(20, 60)
        orders.append(
            Order(
                id=i,
                x=random.uniform(0, CITY_SIZE_KM),
                y=random.uniform(0, CITY_SIZE_KM),
                release_time=release,
                deadline=deadline,
                service_time=2,
            )
        )
    return orders
'''
def generate_orders(n: int, horizon_min: int = 120) -> List[Order]:
    orders: List[Order] = []

    depot_x = CITY_SIZE_KM / 2.0
    depot_y = CITY_SIZE_KM / 2.0
    proxy_speed_kmph = 18.0  # matches bike speed in generate_bikes

    for i in range(n):
        x = random.uniform(0, CITY_SIZE_KM)
        y = random.uniform(0, CITY_SIZE_KM)

        release = random.randint(0, horizon_min)

        # distance-aware travel-time proxy from depot
        d = ((x - depot_x) ** 2 + (y - depot_y) ** 2) ** 0.5
        t_proxy = max(1, int((d / proxy_speed_kmph) * 60.0 + 0.9999))  # ceil without math

        # Slack tiers create meaningful urgency variety
        r = random.random()
        if r < 0.35:
            slack = random.randint(5, 12)     # tight
        elif r < 0.80:
            slack = random.randint(13, 25)    # medium
        else:
            slack = random.randint(26, 45)    # loose

        deadline = release + t_proxy + slack

        orders.append(
            Order(
                id=i,
                x=x,
                y=y,
                release_time=release,
                deadline=deadline,
                service_time=2,
            )
        )
    return orders


def generate_stations(n: int) -> List[Station]:
    # place stations spread out
    base_points = [
        (1.0, 4.0),
        (4.0, 1.0),
        (2.5, 2.5),
        (0.5, 0.5),
        (4.5, 4.5),
    ]
    stations: List[Station] = []
    for i in range(n):
        x, y = base_points[i % len(base_points)]
        stations.append(
            Station(
                id=i,
                x=x,
                y=y,
                ports=1 if n <= 2 else 2,
                charge_rate_w=250.0,
            )
        )
    return stations
