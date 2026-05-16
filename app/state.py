from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class CurveType(str, Enum):
    linear = "linear"
    logarithmic = "logarithmic"
    exponential = "exponential"


@dataclass
class AlarmState:
    wake_time: Optional[datetime] = None
    curve: CurveType = CurveType.linear
    is_running: bool = False
    current_volume: float = 0.0
    job_id: Optional[str] = None


# Single shared instance — imported by all modules
state = AlarmState()