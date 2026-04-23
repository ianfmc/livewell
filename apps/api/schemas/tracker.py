from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class TrackedSignal(BaseModel):
    date: str
    market: str
    strike: str
    expiry: str
    recommendation: Literal['Take', 'Watch', 'Pass']
    actionTaken: Literal['Taken', 'Skipped'] | None
    outcome: Literal['Win', 'Loss', 'Pending']
    edge: float
    modelProbability: float
