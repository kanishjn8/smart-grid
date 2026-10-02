"""Typed contracts and a constrained, aggregate AC-bus plant (kW, kWh, hours)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class Assets(Contract):
    battery_kwh: float = Field(default=160, ge=0, le=10000)
    initial_soc: float = Field(default=.65, ge=0, le=1)
    reserve_soc: float = Field(default=.1, ge=0, le=1)
    charge_kw: float = Field(default=50, ge=0, le=10000)
    discharge_kw: float = Field(default=50, ge=0, le=10000)
    eta_charge: float = Field(default=.95, gt=0, le=1)
    eta_discharge: float = Field(default=.95, gt=0, le=1)
    pv_kw: float = Field(default=100, ge=0, le=10000)
    grid_limit_kw: float = Field(default=65, ge=0, le=10000)
    export_limit_kw: float = Field(default=0, ge=0, le=10000)
    households: int = Field(default=100, ge=1, le=10000)
    island_capable: bool = True

    @model_validator(mode="after")
    def check_soc(self):
        if self.initial_soc < self.reserve_soc:
            raise ValueError("initial SOC must be at least reserve SOC")
        return self


class Task(Contract):
    id: str
    required_kwh: float = Field(gt=0, le=10000)
    release_step: int = Field(ge=0)
    deadline_step: int = Field(gt=0)
    max_kw: float = Field(gt=0, le=10000)
    consent: bool = True
    interruptible: Literal[True] = True

    @model_validator(mode="after")
    def check_window(self):
        if self.deadline_step <= self.release_step:
            raise ValueError("task deadline must follow release")
        return self


class Fault(Contract):
    kind: Literal["controller_failure", "partition", "battery_unavailable", "generator_loss"]
    start_step: int = Field(ge=0)
    end_step: int = Field(gt=0)

    @model_validator(mode="after")
    def window(self):
        if self.end_step <= self.start_step:
            raise ValueError("fault end must follow start")
        return self


class Scenario(Contract):
    id: str
    timezone: Literal["Asia/Kolkata"] = "Asia/Kolkata"
    start: datetime = datetime.fromisoformat("2026-01-01T00:00:00+05:30")
    interval_minutes: int = Field(default=5, ge=1, le=60)
    seed: int = Field(default=7, ge=0, le=2**31-1)
    assets: Assets = Assets()
    critical_kw: tuple[float, ...]
    normal_kw: tuple[float, ...]
    pv_kw: tuple[float, ...]
    wind_kw: tuple[float, ...]
    grid_kw: tuple[float, ...]
    tasks: tuple[Task, ...] = ()
    faults: tuple[Fault, ...] = ()
    provenance: str = "Synthetic design assumptions, not a measured community"

    @model_validator(mode="after")
    def validate_series(self):
        import math
        from zoneinfo import ZoneInfo
        n = len(self.critical_kw)
        if not 1 <= n <= 2016:
            raise ValueError("scenario must contain 1–2016 intervals")
        if self.start.tzinfo is None or self.start.utcoffset() != self.start.astimezone(ZoneInfo(self.timezone)).utcoffset():
            raise ValueError("start must include the Asia/Kolkata UTC offset")
        for name in ("critical_kw", "normal_kw", "pv_kw", "wind_kw", "grid_kw"):
            values = getattr(self, name)
            if len(values) != n or any(not math.isfinite(v) or v < 0 for v in values):
                raise ValueError(f"{name}: equal-length, finite nonnegative kW required")
        if any(v > self.assets.pv_kw + 1e-8 for v in self.pv_kw):
            raise ValueError("PV exceeds installed capacity")
        if any(v > self.assets.grid_limit_kw + 1e-8 for v in self.grid_kw):
            raise ValueError("grid profile exceeds connection limit")
        if len({t.id for t in self.tasks}) != len(self.tasks):
            raise ValueError("task IDs must be unique")
        if any(t.deadline_step > n for t in self.tasks):
            raise ValueError("evaluate through every task deadline")
        if any(f.end_step > n for f in self.faults):
            raise ValueError("fault exceeds horizon")
        return self


class Observation(Contract):
    step: int
    timestamp: datetime
    energy_kwh: float
    critical_kw: float
    normal_kw: float
    renewable_kw: float
    grid_limit_kw: float
    telemetry_age_rounds: int = 0
    battery_available: bool = True


class ForecastBundle(Contract):
    issue_step: int
    demand_kw: tuple[float, ...]
    pv_kw: tuple[float, ...]
    lower_pv_kw: tuple[float, ...]
    upper_pv_kw: tuple[float, ...]
    model_version: str
    provenance: str = "Current observation and public synthetic time-of-day template; no future trace"


class DispatchPlan(Contract):
    issued_round: int
    expires_round: int
    epoch: int
    sequence: int
    battery_kw: float  # positive discharge, negative charge
    task_kw: dict[str, float]
    reason: str
    controller: str


class ActuationResult(Contract):
    accepted: bool
    requested_kw: float
    actual_kw: float
    reason: str
    epoch: int
    acknowledged: bool = True


class Battery:
    def __init__(self, assets: Assets):
        self.assets = assets
        self.energy = assets.battery_kwh * assets.initial_soc
        self.throughput = 0.0

    def apply(self, power: float, dt: float, available: bool = True) -> float:
        import math
        if not math.isfinite(power) or dt <= 0 or not math.isfinite(dt):
            raise ValueError("finite power and positive dt required")
        a = self.assets
        if not available:
            return 0.0
        if power >= 0:
            actual = min(power, a.discharge_kw, max(0, self.energy-a.battery_kwh*a.reserve_soc)*a.eta_discharge/dt)
            self.energy -= actual*dt/a.eta_discharge
        else:
            actual = -min(-power, a.charge_kw, max(0, a.battery_kwh-self.energy)/a.eta_charge/dt)
            self.energy -= actual*dt*a.eta_charge
        self.throughput += abs(actual)*dt
        return actual
