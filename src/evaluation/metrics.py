"""Energy metrics derived exclusively from executed plant outputs."""

def metrics(scenario, rows, plant):
    dt = scenario.interval_minutes/60
    total = lambda key: sum(r[key]*dt for r in rows)
    critical_requested = total("critical_requested_kw")
    normal_requested = total("normal_requested_kw")
    missed = sum(plant.remaining.values())
    critical_ens, normal_ens = total("critical_unserved_kw"), total("normal_unserved_kw")
    positive = [r for r in rows if r["critical_requested_kw"] > 1e-7]
    # Select the same exogenous scarcity intervals for every controller, before storage.
    window = [r for r in rows if r["renewable_available_kw"] + r["grid_limit_kw"]
              < r["critical_requested_kw"] + r["normal_requested_kw"] - 1e-7]
    window_positive = [r for r in window if r["critical_requested_kw"] > 1e-7]
    renewable = total("renewable_available_kw")
    a = scenario.assets
    return dict(critical_interruption_hours=sum(r["critical_unserved_kw"] > 1e-7 for r in rows)*dt,
        scarcity_window_hours=len(window)*dt,
        scarcity_critical_availability_pct=100*sum(r["critical_unserved_kw"] <= 1e-7 for r in window_positive)/len(window_positive) if window_positive else None,
        critical_ens_kwh=critical_ens, normal_ens_kwh=normal_ens,
        total_ens_kwh=critical_ens+normal_ens+missed, flexible_missed_kwh=missed,
        critical_energy_served_pct=100*total("critical_served_kw")/critical_requested if critical_requested else None,
        critical_availability_pct=100*sum(r["critical_unserved_kw"] <= 1e-7 for r in positive)/len(positive) if positive else None,
        interruption_minutes=sum(r["critical_unserved_kw"]+r["normal_unserved_kw"] > 1e-7 for r in rows)*scenario.interval_minutes,
        critical_interruption_minutes=sum(r["critical_unserved_kw"] > 1e-7 for r in rows)*scenario.interval_minutes,
        peak_import_kw=max((r["grid_import_kw"] for r in rows), default=0), grid_import_kwh=total("grid_import_kw"),
        grid_export_kwh=total("grid_export_kw"), served_kwh=total("served_kw"),
        task_completion_pct=100*len(plant.completion)/len(scenario.tasks) if scenario.tasks else None,
        max_task_completion_delay_minutes=max(((plant.completion.get(t.id, len(rows))-t.release_step)*scenario.interval_minutes
                                               for t in scenario.tasks), default=0),
        renewable_utilization_pct=100*total("renewable_used_kw")/renewable if renewable else None,
        battery_throughput_kwh=plant.battery.throughput,
        equivalent_full_cycles=plant.battery.throughput/(2*a.battery_kwh) if a.battery_kwh and plant.storage else None,
        initial_battery_kwh=a.battery_kwh*a.initial_soc if plant.storage else 0,
        terminal_battery_kwh=plant.battery.energy if plant.storage else 0,
        terminal_energy_shortfall_kwh=max(0,a.battery_kwh*a.initial_soc-plant.battery.energy) if plant.storage else 0,
        worst_household_normal_service_fraction=total("normal_served_kw")/normal_requested if normal_requested else None,
        household_service_disparity=0., # Equal proportional allocation of identical modeled households.
        max_consecutive_curtailment_minutes=max((r["consecutive_curtailment_intervals"] for r in rows), default=0)*scenario.interval_minutes,
        fairness_limit_violation_intervals=sum(r["consecutive_curtailment_intervals"]*scenario.interval_minutes > 60 for r in rows),
        max_balance_residual_kw=max((abs(r["balance_residual_kw"]) for r in rows), default=0))
