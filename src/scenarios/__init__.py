"""Reproducible synthetic traces. Physical randomness is independent of transport."""
from __future__ import annotations
import math
import random
from src.domain import Assets, Scenario, Task, Fault

SCENARIOS = {
    "normal": "Routine day and night",
    "cloudy_evening": "Cloud cover and evening feeder constraint",
    "extended_outage": "Islanded upstream outage, 17:00–23:00",
    "coordinator_failure": "Coordinator stops during evening dispatch",
    "partition": "Controller communication partition",
    "flex_arrival": "Large flexible load near feeder limit",
    "resource_exhaustion": "Low SOC and prolonged upstream outage",
}


def profile(hour: float, pv_capacity: float) -> tuple[float, float, float]:
    hour %= 24
    critical = 9 + (3 if 18 <= hour < 23 else 0)
    normal = 22 + 28*math.exp(-((hour-19)/2.4)**2) + 10*math.exp(-((hour-8)/2)**2)
    pv = pv_capacity*max(0, math.sin(math.pi*(hour-6)/12)) if 6 < hour < 18 else 0
    return critical, normal, pv


def build(scenario_id: str = "cloudy_evening", seed: int = 7, assets: Assets | None = None,
          participation: float = 1, outage_hours: float | None = None) -> Scenario:
    if scenario_id not in SCENARIOS:
        raise ValueError("unknown scenario")
    if not 0 <= participation <= 1:
        raise ValueError("participation must be between 0 and 1")
    if outage_hours is not None and not 0 <= outage_hours <= 24:
        raise ValueError("outage duration must be between 0 and 24 hours")
    a = assets or Assets(initial_soc=.2 if scenario_id == "resource_exhaustion" else .65)
    rng = random.Random(seed)
    critical, normal, solar, wind, grid = [], [], [], [], []
    for i in range(288):
        hour = i/12
        c, n, p = profile(hour, a.pv_kw)
        critical.append(c)
        normal.append(n*rng.uniform(.94, 1.06))
        cloud = rng.uniform(.72, 1)
        if scenario_id != "normal" and 14 <= hour < 18:
            cloud *= .3
        solar.append(p*cloud)
        wind.append(0.)  # No wind asset in the illustrative pilot.
        limit = a.grid_limit_kw
        if scenario_id != "normal" and 17 <= hour < 22:
            limit = min(limit, 24)
        if scenario_id in {"extended_outage", "resource_exhaustion"}:
            begin = 17 if scenario_id == "extended_outage" else 12
            end = min(24, begin + (outage_hours if outage_hours is not None else (6 if begin == 17 else 12)))
            if begin <= hour < end:
                limit = 0
        grid.append(limit)
    tasks = tuple(Task(id=f"ev-{j+1}", required_kwh=20 if scenario_id != "flex_arrival" else 55,
                       release_step=12*10 if scenario_id != "flex_arrival" else 12*17,
                       deadline_step=12*23, max_kw=7.2, consent=j < round(4*participation)) for j in range(4))
    # Pump models replenishing a tank before its next service deadline; it is not essential real-time pumping.
    tasks += (Task(id="tank-refill", required_kwh=18, release_step=12*9, deadline_step=12*16, max_kw=6),)
    faults = ()
    if scenario_id in {"coordinator_failure", "partition"}:
        faults = (Fault(kind="controller_failure" if scenario_id == "coordinator_failure" else "partition",
                        start_step=12*18, end_step=12*20),)
    return Scenario(id=scenario_id, seed=seed, assets=a, critical_kw=tuple(critical), normal_kw=tuple(normal),
                    pv_kw=tuple(solar), wind_kw=tuple(wind), grid_kw=tuple(grid), tasks=tasks, faults=faults)
