from __future__ import annotations
import threading
from uuid import uuid4
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import Field
from src.domain import Contract, Assets, Scenario, Fault
from src.scenarios import build, SCENARIOS
from src.evaluation.runner import Runner, compare
from src.evaluation.economics import CostInputs, economics


class RunRequest(Contract):
    scenario: str = "cloudy_evening"
    controller: Literal["B0", "B1", "P"] = "P"
    seed: int = Field(default=7, ge=0, le=2**31-1)
    assets: Assets | None = None
    participation: float = Field(default=1, ge=0, le=1)
    forecast_model: Literal["profile", "persistence"] = "profile"
    forecast_error: float = Field(default=1, ge=0, le=3)
    loss: float = Field(default=0, ge=0, le=1)
    delay_rounds: int = Field(default=0, ge=0, le=10)
    duplicate: float = Field(default=0, ge=0, le=1)
    custom_scenario: Scenario | None = None

    def environment(self):
        if self.custom_scenario is not None:
            return self.custom_scenario
        try:
            return build(self.scenario, self.seed, self.assets, self.participation)
        except ValueError as e:
            raise HTTPException(422, str(e)) from e

    def config(self):
        return dict(forecast_model=self.forecast_model, forecast_error=self.forecast_error,
                    loss=self.loss, delay_rounds=self.delay_rounds, duplicate=self.duplicate)


class ControlRequest(Contract):
    action: Literal["pause", "resume", "step", "complete", "reset", "fault"]
    steps: int = Field(default=1, ge=1, le=288)
    fault: Literal["controller_failure", "partition", "battery_unavailable"] = "controller_failure"
    duration_steps: int = Field(default=12, ge=1, le=288)


class EconomicsRequest(Contract):
    assets: Assets = Assets()
    costs: CostInputs = CostInputs()


def router():
    api = APIRouter(prefix="/api")
    lock = threading.RLock()
    runs, comparisons = {}, {}

    def get(mapping, id):
        if id not in mapping:
            raise HTTPException(404, "Unknown or deleted ID")
        return mapping[id]

    @api.get("/scenarios")
    def scenarios():
        return [dict(id=k, name=v, provenance="synthetic", interval_minutes=5, duration_hours=24) for k,v in SCENARIOS.items()]

    @api.post("/runs", status_code=201)
    def create(req: RunRequest):
        with lock:
            if len(runs) >= 12:
                raise HTTPException(429, "12-run session limit; delete a run before adding another")
            run = Runner(req.environment(), req.controller, **req.config())
            id = uuid4().hex
            runs[id] = run
            return dict(id=id, status="ready", progress=0)

    @api.get("/runs/{id}")
    @api.get("/runs/{id}/export")
    def read(id: str):
        with lock:
            return get(runs,id).export()

    @api.delete("/runs/{id}")
    def delete(id: str):
        with lock:
            get(runs,id)
            del runs[id]
            return {"deleted": id}

    @api.post("/runs/{id}/control")
    def control(id: str, req: ControlRequest):
        with lock:
            run = get(runs,id)
            if req.action == "pause":
                run.paused = True
            elif req.action == "resume":
                run.paused = False
            elif req.action == "reset":
                run = Runner(run.scenario, run.controller, run.forecast_model, **run.config)
                runs[id] = run
            elif req.action == "fault":
                if run.done:
                    raise HTTPException(409, "Completed run cannot receive a fault; reset first")
                event = Fault(kind=req.fault, start_step=len(run.rows), end_step=min(len(run.scenario.critical_kw),len(run.rows)+req.duration_steps))
                # Preserve the injected event in the exported, re-playable scenario and its hash.
                run.scenario = Scenario.model_validate(run.scenario.model_copy(update={"faults": run.scenario.faults+(event,)}).model_dump())
                run.plant.scenario = run.scenario
            elif req.action == "complete":
                if run.paused:
                    raise HTTPException(409,"Resume the run before completing")
                run.run()
            elif req.action == "step":
                for _ in range(req.steps):
                    run.step()
            return run.export()

    @api.post("/comparisons", status_code=201)
    def paired(req: RunRequest):
        with lock:
            if len(comparisons) >= 12:
                # Bounded session cache; oldest comparison may be exported by client before replacement.
                del comparisons[next(iter(comparisons))]
            result = compare(req.environment(), **req.config())
            id = uuid4().hex
            comparisons[id] = result
            return dict(id=id, **result)

    @api.get("/comparisons/{id}")
    def comparison(id: str):
        with lock:
            return get(comparisons,id)

    @api.post("/economics")
    def costs(req: EconomicsRequest):
        return economics(req.assets, req.costs)

    return api
