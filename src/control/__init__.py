"""Same-asset B1 and transparent receding-horizon heuristic P (no solver claim)."""
from src.domain import Assets, Observation, ForecastBundle, DispatchPlan, Task


def dispatch(controller: str, obs: Observation, f: ForecastBundle, assets: Assets,
             tasks: tuple[Task, ...], remaining: dict[str, float], dt: float,
             epoch: int, round_: int, sequence: int) -> DispatchPlan:
    if controller not in {"B0", "B1", "P"}:
        raise ValueError("unknown controller")
    base = obs.critical_kw + obs.normal_kw
    spare = max(0, obs.renewable_kw + obs.grid_limit_kw-base)
    future_spare = max((p + obs.grid_limit_kw-d for p, d in zip(f.lower_pv_kw, f.demand_kw)), default=0)
    task_power = {}
    for task in sorted(tasks, key=lambda t: (t.deadline_step, t.id)):
        if not task.release_step <= obs.step < task.deadline_step or remaining[task.id] <= 1e-9:
            continue
        want = min(task.max_kw, remaining[task.id]/dt)
        # Opt-out fixes requested service to an immediate schedule in the plant.
        if not task.consent or controller in {"B0", "B1"}:
            power = want
        else:
            # Never defer past the last feasible start; use present headroom otherwise.
            must = max(0, remaining[task.id] - task.max_kw*(task.deadline_step-obs.step-1)*dt)/dt
            power = min(want, max(must, spare)) if future_spare > spare else want
        task_power[task.id] = power
        spare = max(0, spare-power)
    demand = base + sum(task_power.values())
    net = demand-obs.renewable_kw
    battery = 0.
    reason = "B0 asset reference: no storage; immediate tasks"
    if controller != "B0":
        deficit = max(0, net-obs.grid_limit_kw)
        battery = deficit if deficit else min(0, net)
        reason = "Serve critical first; charge renewable surplus; discharge feeder deficit; earliest-deadline tasks"
        if controller == "P":
            # Reserve forecast critical energy during a currently observed outage, allocating finite energy over 3h.
            if obs.grid_limit_kw == 0 and deficit > 0:
                usable = max(0, obs.energy_kwh-assets.battery_kwh*assets.reserve_soc)*assets.eta_discharge
                critical_gap = max(0, obs.critical_kw-obs.renewable_kw)
                budget = max(critical_gap, usable/max(dt, len(f.demand_kw)*dt))
                battery = min(deficit, budget)
            # Refill to initial energy using available grid headroom before a forecast supply gap.
            risk = sum(max(0, d-p-obs.grid_limit_kw)*dt for d,p in zip(f.demand_kw, f.lower_pv_kw))
            target = min(assets.battery_kwh, max(assets.initial_soc*assets.battery_kwh,
                         assets.reserve_soc*assets.battery_kwh+ risk/assets.eta_discharge))
            if deficit == 0 and obs.energy_kwh < target:
                headroom = max(0, obs.grid_limit_kw-net)
                battery = -min(headroom, (target-obs.energy_kwh)/assets.eta_charge/dt)
            reason = "3-hour profile risk reserve; deadline-safe task shifting; bounded island critical-energy budget"
    return DispatchPlan(issued_round=round_, expires_round=round_+2, epoch=epoch, sequence=sequence,
                        battery_kw=battery, task_kw=task_power, reason=reason, controller=controller)
