# model/station.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

@dataclass
class Station:
    id: int
    x: float
    y: float
    ports: int
    charge_rate_w: float

    charging_bikes: List[int] = field(default_factory=list)
    queue: List[int] = field(default_factory=list)
