from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import platform
import subprocess
from datetime import timedelta
from pathlib import Path
from importlib.metadata import version
from src.domain import Scenario, Observation, ActuationResult
from src.domain.plant import Plant
from src.forecasting import forecast
from src.control import dispatch
from src.coordination import AuthorityGate, Transport
from src.evaluation.metrics import metrics

VERSION = "gridsathi-v1"


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def code_provenance():
    root = Path(__file__).resolve().parents[2]
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = "unavailable"
    paths = sorted((root/"src").rglob("*.py")) + [root/"dashboard.py", root/"evaluate.py", root/"uv.lock"]
    hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.exists()}
    return revision, hashes


class Runner:
    def __init__(self, scenario: Scenario, controller: str = "P", forecast_model: str = "profile",
                 forecast_error: float = 1, loss: float = 0, delay_rounds: int = 0, duplicate: float = 0,
                 timeout_rounds: int = 3):
        if controller not in {"B0", "B1", "P"} or forecast_model not in {"profile", "persistence"}:
            raise ValueError("unknown controller or forecast")
        if not 0 <= forecast_error <= 3:
            raise ValueError("forecast error multiplier outside 0–3")
        self.scenario, self.controller, self.forecast_model = scenario, controller, forecast_model
        self.forecast_error = forecast_error
        self.plant = Plant(scenario, storage=controller != "B0")
        self.gate = AuthorityGate(timeout_rounds)
        self.transport = Transport(scenario.seed, loss, delay_rounds, duplicate)
        self.rows, self.events = [], []
        self.forecasts = []
        self.rejected = 0
        self.failure_active = False
        self.failed_epoch = None
        self.failure_started_round = None
        self.detected_round = None
        self.awaiting_recovery = False
        self.config = dict(forecast_error=forecast_error, loss=loss, delay_rounds=delay_rounds,
                           duplicate=duplicate, timeout_rounds=timeout_rounds)
        self.paused = False
        self.last_plan = None

    @property
    def done(self):
        return len(self.rows) == len(self.scenario.critical_kw)

    def step(self):
        if self.done or self.paused:
            return None
        s, i = self.scenario, len(self.rows)
        faults = {f.kind for f in s.faults if f.start_step <= i < f.end_step}
        obs = Observation(step=i, timestamp=s.start+timedelta(minutes=i*s.interval_minutes), energy_kwh=self.plant.battery.energy,
            critical_kw=s.critical_kw[i], normal_kw=s.normal_kw[i], renewable_kw=s.pv_kw[i]+s.wind_kw[i], grid_limit_kw=s.grid_kw[i],
            battery_available="battery_unavailable" not in faults)
        f = forecast(obs, s.assets, s.interval_minutes, self.forecast_model, error_scale=self.forecast_error)
        self.forecasts.append(f)
        # Ten abstract protocol rounds per energy interval, NOT seconds or a real failover SLA.
        start_round = i*10
        failed = "controller_failure" in faults
        partition = "partition" in faults
        if not failed:
            self.failure_active = False
            self.failed_epoch = None
        selected = None
        accepted_reason = "no fresh command: local fallback"
        for r in range(start_round, start_round+10):
            if failed and not self.failure_active:
                self.failure_active = True
                self.failed_epoch = self.gate.epoch
                self.failure_started_round = r
                self.events.append(dict(event="controller_failure", round=r))
            # Replacement controller runs on the actuator side after its configurable heartbeat timeout.
            available = not failed or self.gate.epoch != self.failed_epoch
            if not available and self.gate.failover(r):
                available = True
                self.detected_round = r
                self.awaiting_recovery = True
                self.events.append(dict(event="failure_detected_and_replacement_granted", round=r,
                                        detection_latency_rounds=r-self.failure_started_round))
                if self.last_plan:
                    ok, why = self.gate.accept(self.last_plan, r)
                    self.rejected += not ok
                    self.events.append(dict(event=why, round=r))
            if available and not partition:
                self.gate.heartbeat(r)
                try:
                    plan = dispatch(self.controller, obs, f, s.assets, s.tasks, self.plant.remaining,
                                    s.interval_minutes/60, self.gate.epoch, r, r)
                    self.last_plan = plan
                    self.transport.send(plan, r)
                except (ValueError, ArithmeticError) as error:
                    self.events.append(dict(event="invalid controller plan; fallback", round=r, detail=str(error)))
            for packet in self.transport.receive(r):
                ok, why = self.gate.accept(packet, r, connected=not partition)
                if ok:
                    selected, accepted_reason = packet, why
                    if self.awaiting_recovery:
                        self.events.append(dict(event="first_accepted_replacement_command", round=r,
                                                recovery_latency_rounds=r-self.detected_round,
                                                reconciled_energy_kwh=obs.energy_kwh,
                                                remaining_tasks_kwh=dict(self.plant.remaining)))
                        self.awaiting_recovery = False
                else:
                    self.rejected += 1
                    self.events.append(dict(event=why, round=r))
        if selected is None or selected.expires_round < start_round+9 or partition:
            # Local meter observations only. No stale remote telemetry or hidden future data.
            selected = dispatch("B0" if self.controller == "B0" else "B1", obs, f, s.assets, s.tasks,
                                self.plant.remaining, s.interval_minutes/60, self.gate.epoch, start_round+9, start_round+9)
            accepted_reason = "bounded local fallback using local meter and SOC"
            selected = selected.model_copy(update={"reason": accepted_reason})
        row = self.plant.step(obs, selected)
        row.update(faults=sorted(faults), authority_epoch=self.gate.epoch,
                   actuation=ActuationResult(accepted=True, requested_kw=selected.battery_kw,
                                  actual_kw=row["discharge_kw"]-row["charge_kw"],
                                  reason=accepted_reason, epoch=self.gate.epoch, acknowledged=True).model_dump(),
                   fallback="fallback" in accepted_reason, forecast_next_demand_kw=f.demand_kw[0],
                   forecast_next_pv_kw=f.pv_kw[0], forecast_issue_step=i,
                   expected_shortfall_kwh=sum(max(0,d-p-obs.grid_limit_kw)*s.interval_minutes/60 for d,p in zip(f.demand_kw,f.lower_pv_kw)),
                   available_flexibility_kw=sum(t.max_kw for t in s.tasks if t.consent and t.release_step <= i < t.deadline_step and self.plant.remaining[t.id] > 1e-7))
        self.rows.append(row)
        return row

    def run(self):
        if self.paused:
            raise ValueError("resume before completing run")
        while not self.done:
            self.step()
        return self.export()

    def export(self):
        s = self.scenario
        m = metrics(s, self.rows, self.plant)
        errors = [(abs(self.forecasts[i].demand_kw[0]-s.critical_kw[i+1]-s.normal_kw[i+1]),
                   abs(self.forecasts[i].pv_kw[0]-s.pv_kw[i+1])) for i in range(max(0,len(self.rows)-1))]
        m.update(forecast_demand_mae_kw=sum(x[0] for x in errors)/len(errors) if errors else None,
                 forecast_pv_mae_kw=sum(x[1] for x in errors)/len(errors) if errors else None,
                 rejected_commands=self.rejected, fallback_intervals=sum(r["fallback"] for r in self.rows),
                 detection_latency_rounds=[e["detection_latency_rounds"] for e in self.events if "detection_latency_rounds" in e],
                 recovery_latency_rounds=[e["recovery_latency_rounds"] for e in self.events if "recovery_latency_rounds" in e])
        m["forecast_demand_nmae_mean"] = m["forecast_demand_mae_kw"]/(sum(s.critical_kw[i+1]+s.normal_kw[i+1] for i in range(len(errors)))/len(errors)) if errors and sum(s.critical_kw[i+1]+s.normal_kw[i+1] for i in range(len(errors))) else None
        m["forecast_pv_nmae_capacity"] = m["forecast_pv_mae_kw"]/s.assets.pv_kw if errors and s.assets.pv_kw else None
        revision, hashes = code_provenance()
        return dict(status="completed" if self.done else "paused" if self.paused else "ready", progress=len(self.rows)/len(s.critical_kw),
            manifest=dict(scenario_id=s.id, scenario_hash=digest(s.model_dump(mode="json")), seed=s.seed, controller=self.controller,
                controller_version=VERSION, forecast_version=self.forecast_model+"-v1", config=self.config,
                code_revision=revision, code_hash=digest(hashes), source_file_hashes=hashes,
                data_hashes={key:digest(getattr(s,key)) for key in ("critical_kw","normal_kw","pv_kw","wind_kw","grid_kw")},
                environment=dict(python=platform.python_version(), fastapi=version("fastapi"), pydantic=version("pydantic")),
                units=dict(power="kW", energy="kWh", protocol_latency="abstract rounds"),
                artifact_paths=["manifest.json", "metrics.json", "series.csv", "run.json"],
                provenance=s.provenance), scenario=s.model_dump(mode="json"), metrics=m, series=deepcopy(self.rows),
            tasks=[dict(**t.model_dump(), remaining_kwh=self.plant.remaining[t.id], completed_step=self.plant.completion.get(t.id)) for t in s.tasks],
            events=deepcopy(self.events))


def compare(scenario: Scenario, **config):
    baseline = Runner(scenario, "B1", **config).run()
    proposed = Runner(scenario, "P", **config).run()
    b, p = baseline["metrics"], proposed["metrics"]
    return dict(baseline=baseline, proposed=proposed,
                delta=dict(critical_interruption_hours_avoided=b["critical_interruption_hours"]-p["critical_interruption_hours"],
                           critical_availability_gain_pp=p["critical_availability_pct"]-b["critical_availability_pct"] if b["critical_availability_pct"] is not None else None,
                           total_ens_kwh=p["total_ens_kwh"]-b["total_ens_kwh"],
                           critical_ens_kwh=p["critical_ens_kwh"]-b["critical_ens_kwh"],
                           ens_reduction_pct=100*(b["total_ens_kwh"]-p["total_ens_kwh"])/b["total_ens_kwh"] if b["total_ens_kwh"] > 1e-9 else None,
                           terminal_battery_difference_kwh=p["terminal_battery_kwh"]-b["terminal_battery_kwh"]),
                comparison_note="P versus competent B1, identical external traces/assets. Terminal energy is reported, not forced equal; no isolated software-benefit claim without considering it.")
