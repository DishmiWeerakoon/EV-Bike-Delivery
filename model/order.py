# model/order.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class Order:
    id: int
    x: float
    y: float
    release_time: int
    deadline: int
    service_time: int = 2

    delivered: bool = False
    completion_time: Optional[int] = None
    assigned_to: Optional[int] = None
    delivered_by: Optional[int] = None
