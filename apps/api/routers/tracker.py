from __future__ import annotations
from fastapi import APIRouter
from schemas.tracker import TrackedSignal

router = APIRouter()

_SIGNALS: list[TrackedSignal] = [
    TrackedSignal(date="2026-04-23", market="EUR/USD", strike="1.0880", expiry="14:00", recommendation="Take",  actionTaken="Taken",   outcome="Pending", edge=0.18,  modelProbability=0.70),
    TrackedSignal(date="2026-04-22", market="GBP/USD", strike="1.2680", expiry="11:00", recommendation="Watch", actionTaken="Skipped", outcome="Win",     edge=0.11,  modelProbability=0.58),
    TrackedSignal(date="2026-04-22", market="USD/JPY", strike="154.50", expiry="16:00", recommendation="Pass",  actionTaken=None,      outcome="Loss",    edge=-0.04, modelProbability=0.44),
    TrackedSignal(date="2026-04-21", market="EUR/USD", strike="1.0860", expiry="12:00", recommendation="Take",  actionTaken="Taken",   outcome="Win",     edge=0.22,  modelProbability=0.72),
    TrackedSignal(date="2026-04-21", market="GBP/USD", strike="1.2650", expiry="14:00", recommendation="Take",  actionTaken="Taken",   outcome="Loss",    edge=0.15,  modelProbability=0.65),
    TrackedSignal(date="2026-04-19", market="USD/JPY", strike="154.00", expiry="10:00", recommendation="Watch", actionTaken="Skipped", outcome="Win",     edge=0.09,  modelProbability=0.55),
    TrackedSignal(date="2026-04-18", market="EUR/USD", strike="1.0840", expiry="11:00", recommendation="Take",  actionTaken="Taken",   outcome="Win",     edge=0.20,  modelProbability=0.69),
    TrackedSignal(date="2026-04-18", market="GBP/USD", strike="1.2700", expiry="16:00", recommendation="Pass",  actionTaken=None,      outcome="Win",     edge=-0.02, modelProbability=0.45),
    TrackedSignal(date="2026-04-17", market="EUR/USD", strike="1.0870", expiry="14:00", recommendation="Take",  actionTaken="Taken",   outcome="Loss",    edge=0.13,  modelProbability=0.61),
    TrackedSignal(date="2026-04-16", market="USD/JPY", strike="153.50", expiry="12:00", recommendation="Watch", actionTaken="Taken",   outcome="Win",     edge=0.10,  modelProbability=0.57),
    TrackedSignal(date="2026-04-15", market="EUR/USD", strike="1.0855", expiry="10:00", recommendation="Take",  actionTaken="Taken",   outcome="Win",     edge=0.19,  modelProbability=0.68),
    TrackedSignal(date="2026-04-14", market="GBP/USD", strike="1.2660", expiry="11:00", recommendation="Pass",  actionTaken=None,      outcome="Loss",    edge=-0.06, modelProbability=0.42),
    TrackedSignal(date="2026-04-12", market="USD/JPY", strike="153.00", expiry="14:00", recommendation="Take",  actionTaken="Skipped", outcome="Win",     edge=0.16,  modelProbability=0.64),
    TrackedSignal(date="2026-04-11", market="EUR/USD", strike="1.0830", expiry="16:00", recommendation="Watch", actionTaken="Skipped", outcome="Loss",    edge=0.07,  modelProbability=0.53),
    TrackedSignal(date="2026-04-10", market="GBP/USD", strike="1.2640", expiry="12:00", recommendation="Take",  actionTaken="Taken",   outcome="Win",     edge=0.21,  modelProbability=0.71),
]


@router.get("/signals/tracker", response_model=list[TrackedSignal])
def get_signal_tracker() -> list[TrackedSignal]:
    return _SIGNALS
