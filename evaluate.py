"""Offline reproducible paired evaluation, sensitivities and replay exports."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
from statistics import mean
from src.domain import Assets
from src.scenarios import SCENARIOS, build
from src.evaluation.runner import Runner, compare
from src.evaluation.economics import economics, CostInputs


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n")


def export_run(path, run):
    path.mkdir(parents=True, exist_ok=True)
    for name in ("manifest", "metrics"):
        write_json(path/f"{name}.json", run[name])
    write_json(path/"run.json",run)
    if run["series"]:
        with (path/"series.csv").open("w", newline="") as handle:
            fields = [k for k,v in run["series"][0].items() if not isinstance(v,(dict,list))]
            writer = csv.DictWriter(handle,fieldnames=fields,extrasaction="ignore")
            writer.writeheader()
            writer.writerows(run["series"])


def summarize(values):
    values = [v for v in values if v is not None]
    return dict(mean=mean(values), minimum=min(values), maximum=max(values)) if values else dict(mean=None, minimum=None, maximum=None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds",type=int,default=10)
    parser.add_argument("--output",type=Path,default=Path("results/latest"))
    parser.add_argument("--sensitivity",action="store_true")
    args = parser.parse_args()
    if not 1 <= args.seeds <= 100:
        parser.error("seeds must be 1–100")
    out = args.output
    out.mkdir(parents=True,exist_ok=True)
    table, cases = [], []
    for name in SCENARIOS:
        pairs = []
        for seed in range(100,100+args.seeds): # Held-out evaluation seeds, demo seed 7.
            pair = compare(build(name, seed))
            pairs.append(pair)
            for label in ("baseline","proposed"):
                r = pair[label]
                table.append(dict(scenario=name,seed=seed,controller=r["manifest"]["controller"], **r["metrics"]))
                if seed == 100:
                    export_run(out/name/r["manifest"]["controller"], r)
        for controller in ("B1","P"):
            rows = [r for r in table if r["scenario"]==name and r["controller"]==controller]
            cases.append(dict(scenario=name,controller=controller,n=len(rows),
                metrics={key:summarize(r[key] for r in rows)
                         for key in ("critical_ens_kwh","total_ens_kwh","peak_import_kw","terminal_battery_kwh","flexible_missed_kwh","critical_interruption_hours","critical_availability_pct","scarcity_critical_availability_pct")}))
    write_json(out/"all_metrics.json",table)
    write_json(out/"summary.json",cases)
    report = ["# Computed held-out synthetic evaluation", "", f"{args.seeds} paired seeds per scenario (100 onward). P versus B1; kWh. Negative results retained.","",
              "|Scenario|Controller|n|Critical ENS mean [min, max]|Total ENS mean [min, max]|Terminal energy mean|", "|---|---|---:|---:|---:|---:|"]
    for row in cases:
        m=row["metrics"]
        fmt=lambda key: f'{m[key]["mean"]:.2f} [{m[key]["minimum"]:.2f}, {m[key]["maximum"]:.2f}]'
        report.append(f'|{row["scenario"]}|{row["controller"]}|{row["n"]}|{fmt("critical_ens_kwh")}|{fmt("total_ens_kwh")}|{m["terminal_battery_kwh"]["mean"]:.2f}|')
    report += ["", "## Requirement 4 — software prototype", "", "Run `make run` for the interactive simulator or open `web/offline.html` for saved playback. No hardware build is required.",
               "", "## Requirement 5 — measured reliability against B1", "",
               "B1 and P use identical assets, starting SOC, realized profiles and participation. B1 prioritizes critical demand, charges renewable surplus, discharges deficits and schedules available tasks by earliest deadline. P uses a three-hour forecast heuristic. Positive hours avoided means improvement; negative means regression.", "",
               "Critical interruption hours count intervals with any unmet critical demand. Scarcity windows are identical external-input intervals where renewable supply plus grid capacity is below fixed critical + normal demand, before battery dispatch. Availability is the percentage of positive-critical-demand intervals fully served, not the energy-served percentage.", "",
               "|Scenario|B1 critical interruption h|P critical interruption h|Paired hours avoided mean [min, max]|Scarcity critical availability B1 → P (%)|", "|---|---:|---:|---:|---:|"]
    for name in SCENARIOS:
        b = [r for r in table if r["scenario"] == name and r["controller"] == "B1"]
        p = [r for r in table if r["scenario"] == name and r["controller"] == "P"]
        avoided = [x["critical_interruption_hours"]-y["critical_interruption_hours"] for x,y in zip(b,p)]
        availability = lambda rows: "N/A" if any(r["scarcity_critical_availability_pct"] is None for r in rows) else f'{mean(r["scarcity_critical_availability_pct"] for r in rows):.2f}'
        report.append(f'|{name}|{mean(r["critical_interruption_hours"] for r in b):.3f}|{mean(r["critical_interruption_hours"] for r in p):.3f}|{mean(avoided):.3f} [{min(avoided):.3f}, {max(avoided):.3f}]|{availability(b)} → {availability(p)}|')
    report += ["", "No real-world reliability claim. Terminal SOC is reported; no salvage credit. Forecast and scenario assumptions are in each run manifest. Task misses count in total ENS once. Aggregated customer service uses equal proportional allocation."]
    (out/"report.md").write_text("\n".join(report)+"\n")
    demo=compare(build("cloudy_evening",7))
    write_json(out/"demo-comparison.json",demo)
    # Portable replay dataset served by the dashboard and directly opened by the offline HTML.
    Path("web/replay.js").write_text("window.GRID_REPLAY="+json.dumps(demo,separators=(",",":"),allow_nan=False)+";\n")
    write_json(out/"economics.json",economics(Assets(),CostInputs()))
    if args.sensitivity:
        variants = [("battery_kwh",v,dict(assets=Assets(battery_kwh=v))) for v in (80,160,320)]
        variants += [("initial_soc",v,dict(assets=Assets(initial_soc=v))) for v in (.2,.65,1)]
        variants += [("pv_kw",v,dict(assets=Assets(pv_kw=v))) for v in (50,100,150)]
        variants += [("grid_limit_kw",v,dict(assets=Assets(grid_limit_kw=v))) for v in (25,45,65)]
        variants += [("participation",v,dict(participation=v)) for v in (0,.5,1)]
        variants += [("outage_hours",v,dict(outage_hours=v)) for v in (2,4,6)]
        sensitivity=[]
        for dimension, value, config in variants:
            pair=compare(build("extended_outage",100,**config))
            sensitivity.append(dict(dimension=dimension,value=value,baseline=pair["baseline"]["metrics"],proposed=pair["proposed"]["metrics"]))
        for dimension, configs in (("forecast", [{"forecast_model":"persistence"},{"forecast_model":"profile"}]),
                                   ("forecast_error",[{"forecast_error":v} for v in (.7,1,1.3)]),
                                   ("communications",[{"loss":0},{"loss":.5,"duplicate":.5,"delay_rounds":3},{"loss":1}])):
            for config in configs:
                pair=compare(build("coordinator_failure",100),**config)
                sensitivity.append(dict(dimension=dimension,value=config,baseline=pair["baseline"]["metrics"],proposed=pair["proposed"]["metrics"]))
        for controller in ("B0","B1","P"):
            sensitivity.append(dict(dimension="asset_and_controller_ablation",value=controller,
                                    metrics=Runner(build("cloudy_evening",100),controller).run()["metrics"]))
        for scenario in ("cloudy_evening","coordinator_failure","partition"):
            sensitivity.append(dict(dimension="coordination_ablation",value=scenario,
                                    metrics=Runner(build(scenario,100),"P").run()["metrics"]))
        write_json(out/"sensitivities.json",sensitivity)
    alternatives=[]
    for pv_kw, controller, capacities in ((100,"P",(80,160,320)),(100,"B1",(80,160,320)),(0,"B1",(160,320,640))):
        for capacity in capacities:
            assets=Assets(pv_kw=pv_kw,battery_kwh=capacity)
            run=Runner(build("extended_outage",100,assets),controller).run()
            alternatives.append(dict(controller=controller,pv_kw=pv_kw,battery_kwh=capacity,
                critical_service_target_pct=99,meets_target=run["metrics"]["critical_energy_served_pct"]>=99,
                metrics=run["metrics"],economics=economics(assets,CostInputs())))
    write_json(out/"service_target_alternatives.json",alternatives)
    print("\n".join(report))


if __name__ == "__main__":
    main()
