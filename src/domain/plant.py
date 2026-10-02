from __future__ import annotations
from src.domain import Battery, Scenario, Observation, DispatchPlan


class Plant:
    def __init__(self, scenario: Scenario, storage: bool = True):
        self.scenario = scenario
        self.battery = Battery(scenario.assets)
        self.storage = storage
        self.remaining = {t.id: t.required_kwh for t in scenario.tasks}
        self.completion: dict[str, int] = {}
        self.optout_requested = {t.id: 0. for t in scenario.tasks}
        self.consecutive = 0

    def step(self, obs: Observation, plan: DispatchPlan) -> dict:
        s, a = self.scenario, self.scenario.assets
        dt = s.interval_minutes/60
        requested = {}
        for task in s.tasks:
            if not task.release_step <= obs.step < task.deadline_step:
                continue
            if not task.consent or plan.controller == "B0":
                # Fixed immediate service request; missed opt-out service is NOT moved later without consent.
                outstanding = max(0, task.required_kwh-self.optout_requested[task.id])
                power = min(task.max_kw, outstanding/dt)
                self.optout_requested[task.id] += power*dt
            else:
                power = min(task.max_kw, max(0, plan.task_kw.get(task.id, 0)), self.remaining[task.id]/dt)
            requested[task.id] = power
        demand = obs.critical_kw+obs.normal_kw+sum(requested.values())
        connected = obs.grid_limit_kw > 0 or a.island_capable
        renewable = obs.renewable_kw if connected else 0.
        # Discharge cannot exceed bus demand; charging cannot exceed actual available supply.
        wanted = min(max(0, demand-renewable), plan.battery_kw) if plan.battery_kw >= 0 else -min(-plan.battery_kw, max(0, renewable+obs.grid_limit_kw-demand))
        power = self.battery.apply(wanted, dt, obs.battery_available and self.storage and connected)
        discharge, charge = max(0, power), max(0, -power)
        imported = min(obs.grid_limit_kw, max(0, demand+charge-renewable-discharge))
        supply = max(0, renewable+discharge+imported-charge)
        critical_served = min(obs.critical_kw, supply)
        supply -= critical_served
        normal_served = min(obs.normal_kw, supply)
        supply -= normal_served
        flexible_served = 0.
        task_actual = {}
        for task in sorted(s.tasks, key=lambda t: (t.deadline_step, t.id)):
            actual = min(requested.get(task.id, 0), supply)
            task_actual[task.id] = actual
            supply -= actual
            flexible_served += actual
            self.remaining[task.id] = max(0, self.remaining[task.id]-actual*dt)
            if self.remaining[task.id] < 1e-7 and task.id not in self.completion:
                self.completion[task.id] = obs.step+1
        exported = min(a.export_limit_kw, supply) if obs.grid_limit_kw > 0 and imported == 0 else 0.
        curtailment = max(0, obs.renewable_kw-renewable) + max(0, supply-exported)
        served = critical_served+normal_served+flexible_served
        renewable_used = obs.renewable_kw-curtailment
        residual = renewable_used+imported+discharge-served-charge-exported
        if abs(residual) > 1e-7:
            raise AssertionError(f"AC energy balance residual {residual}")
        self.consecutive = self.consecutive+1 if normal_served < obs.normal_kw-1e-7 else 0
        return dict(step=obs.step, timestamp=obs.timestamp.isoformat(), critical_requested_kw=obs.critical_kw,
                    normal_requested_kw=obs.normal_kw, critical_served_kw=critical_served, normal_served_kw=normal_served,
                    critical_unserved_kw=obs.critical_kw-critical_served, normal_unserved_kw=obs.normal_kw-normal_served,
                    flexible_requested_kw=sum(requested.values()), flexible_served_kw=flexible_served,
                    task_actual_kw=task_actual, task_remaining_kwh=dict(self.remaining),
                    renewable_available_kw=obs.renewable_kw, renewable_used_kw=renewable_used,
                    curtailed_kw=curtailment, grid_import_kw=imported, grid_export_kw=exported,
                    grid_limit_kw=obs.grid_limit_kw, charge_kw=charge, discharge_kw=discharge,
                    energy_kwh=self.battery.energy, soc=self.battery.energy/a.battery_kwh if a.battery_kwh else None,
                    served_kw=served, balance_residual_kw=residual, consecutive_curtailment_intervals=self.consecutive,
                    action_reason=plan.reason)
