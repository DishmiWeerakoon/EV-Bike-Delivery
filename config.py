# config.py
from dataclasses import dataclass

# Reproducibility
RANDOM_SEED = 42

# City
CITY_SIZE_KM = 5.0  # 5 km x 5 km square

# Simulation
DT_MIN = 1
SIM_DURATION_MIN = 600  # 3 hours

# Charging / battery
SOC_MIN_BASELINE = 0.20
CHARGE_TARGET_SOC = 0.80

# Candidate limits for heuristic search (speed-up)
CANDIDATE_ORDERS_K = 20
CANDIDATE_STATIONS_K = 5

@dataclass
class Weights:
    w_travel: float = 1.0
    w_late: float = 10.0
    w_queue: float = 2.0
    w_downtime: float = 2.0
    w_battery_risk: float = 10.0
