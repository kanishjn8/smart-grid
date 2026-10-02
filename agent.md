# Agent Development Plan — Smart Grid Hackathon Prototype

## Current scope override — 2026-10-01

The user explicitly requested removal of the legacy system. This supersedes historical migration instructions below to preserve `plan.md`, the threaded demo, its routes or terminal UI. GridSathi's deterministic model, current API, dashboard and offline replay are the sole implementation. The companion complete project explanation remains the design reference. The immediate deliverables are requirement 4 (software simulation without hardware) and requirement 5 (reproducible same-asset reliability evidence).

## 1. Purpose and operating instructions

This document is the complete implementation handoff for upgrading `kanishjn8/smart-grid` into a credible submission for Yuva Yodha Energy Tech Hackathon, Challenge 03: Grid Reliability / Renewable Intermittency.

Read this document before implementing. Work through the milestones in dependency order. Keep a short progress log at the bottom, recording completed work, tests run, actual results, and remaining blockers. Do not mark planned functionality as implemented.

The user has approximately 15 development days. The objective is a strong, evidence-backed prototype and submission package, not production utility-control software. No plan can guarantee a win. Earlier conversational score estimates and reuse percentages were subjective, not judge feedback or measured facts; do not include them in the submission.

This file is named `agent.md` as requested. Tools that automatically discover `AGENTS.md` may need to be explicitly instructed to read this file. It is a project plan, not an installed skill.

### Implementation guardrails

- Inspect the current branch, worktree, repository instructions and dependencies before changing code. Preserve unrelated work.
- This handoff reflects the repository read during the preceding review; re-check changed files before implementation.
- Use `uv` for Python dependency management. Retain FastAPI and the existing browser frontend unless a concrete limitation requires change.
- Implement incrementally with passing tests and documented interfaces. Avoid a wholesale rewrite before establishing a baseline.
- Do not publish, deploy, push, submit forms, incur charges, or connect real electrical equipment without the user's authorization.
- No autonomous control of mains equipment. Every actuator in this prototype is simulated.
- Treat numerical inputs as assumptions until sourced or measured. Never fabricate performance, quotations, interviews, partnerships, field trials or results.
- Maintain a distinction between actual measurements, modeled estimates, design proposals and future work.
- Do not turn this into a blockchain, chatbot or generic AI-agent project. Solve the energy reliability problem first.

## 2. Project and challenge context

### Sources

- Challenge brief: https://www.yuvayodhatech.com/challenges — select `03 Grid`, then expand all three detail sections.
- Judging: https://www.yuvayodhatech.com/faq — expand the judging question.
- Terms: https://www.yuvayodhatech.com/terms

These were inspected in the preceding conversation. Before final submission, verify dates, eligibility, permitted reuse of existing work, AI-assistance rules, required form fields and attachment limits directly with the organizer. Fifteen days is a planning window supplied by the user, not a verified official deadline. The terms refer to unauthorized AI-generated content; obtain clarification on permitted assistance rather than assuming all use is allowed or prohibited.

### Challenge summary

Build affordable local flexibility that helps communities withstand renewable-generation shortfalls. The solution should operate at neighbourhood scale, work for low-income users and give distribution utilities useful information. The brief requests a solution explanation, architecture and supporting designs, baseline-based reliability evidence, plus ownership, maintenance and affordability analysis. A software simulation is acceptable; hardware is not expected. Source: challenge page above.

### First-stage judging weights

| Criterion | Weight | Evidence we will supply |
|---|---:|---|
| Problem understanding and idea quality | 20% | Specific community, constraints and user workflow |
| Architecture and design | 20% | Energy/data/control diagrams and tested components |
| Impact and measurability | 25% | Reproducible paired baseline experiments |
| Feasibility and affordability | 20% | Deployment boundaries, cost model and operating plan |
| Sustainability | 15% | Renewable utilization, battery wear and qualified emissions estimates |

Source: official FAQ. These are first-stage weights, not a verified final-round rubric.

## 3. Current implementation: what exists and what does not

The repository is a Python threaded distributed-systems simulation with a FastAPI server and HTML/CSS/JavaScript dashboard. It has eight fixed nodes: solar, wind, storage, consumer, microgrid, EV, battery and backup. Threads exchange in-memory queued messages. This is simulated distribution within one process, not independently deployed devices.

| Files | Observed purpose | Development treatment |
|---|---|---|
| `src/engine.py` | Clock, shared flags, fixed faults, snapshots, coordinator state | Separate physical model, controllers and telemetry |
| `src/node.py` | Threads, inboxes, scheduled output and protocol hooks | Remove hard-coded energy behaviour from protocol nodes |
| `src/gossip.py`, `src/lamport.py` | State exchange and logical ordering | Retain for coordination experiments; verify freshness semantics |
| `src/mutex.py`, `src/election.py` | Mutual exclusion and bully-style election | Test safety/failure handling before relying on them |
| `src/replication.py` | In-memory backup state | Add versioned recovery and clearly disclose limitations |
| `src/fault_injector.py` | Scheduled disturbances | Extend to independent physical and communication faults |
| `dashboard.py` | FastAPI lifecycle, snapshots and controls | Retain and add run/comparison APIs |
| `simulation.py` | Rich terminal UI | Retain as offline fallback |
| `web/` | Live network map, cards, logs and controls | Reorient main screen to community outcomes |
| `tests/test_core.py` | Clock, gossip, simulation/API smoke tests | Extend with physical invariants and outcome tests |
| `plan.md` | Original distributed-systems teaching plan | Preserve as historical context; this plan defines the new target |

### Specific gaps observed in the code review

- Battery output has no stored-energy ledger, capacity, efficiency or SOC constraints.
- The microgrid/controller node contributes power despite no defined generation asset. A controller must not create energy.
- Solar uses a sine curve with a positive floor; it is not a physically meaningful day/night profile.
- Wind output is random rather than a documented time series.
- Backup supply is a fixed positive output with no grid/generator availability or cost model.
- Fault injection directly queues selected support actions. The controller must instead respond to observations; the fault engine must not choose the solution.
- The `storage_full` event stops discharge. A full battery should normally prevent further charging; empty/reserve-limited storage prevents discharge.
- Grid status is based on absolute aggregate imbalance. Surplus, unmet demand, curtailment and export need separate accounting.
- The engine exposes global live-node knowledge and globally sets leader flags. Do not mistake that simulation convenience for decentralized fault detection.
- Frontend network edges are illustrative; they are not a validated electrical topology or communication restriction.
- The shared random generator and threaded execution do not establish deterministic replay simply because a seed exists.
- There is no baseline controller, energy-reliability evaluation, economics model, forecasting evaluation or critical-load policy.

The preceding review read source files; it did not establish that tests pass or measure live performance. Verify both during implementation.

## 4. Product direction and honest scope

Working name: **GridSathi** (optional; naming is not a development dependency).

Product description: a neighbourhood energy-resilience simulator and supervisory controller that anticipates supply gaps, coordinates shared storage and flexible loads, prioritizes essential services and reports performance under communication/controller failures.

### Pilot setting

Start with a configurable community such as 100 households, 10 shops, a clinic and a water pump. These are illustrative design inputs, not a surveyed site. Choose battery, PV and feeder capacities after checking plausible load/energy totals. Do not freeze arbitrary capacities just to produce attractive results.

Primary users: community operator and DISCOM engineer. Residents supply participation preferences and can opt out of flexible-load scheduling.

### Electrical deployment boundary

Use an explicitly modeled local microgrid behind a common connection point, with suitable island-capable equipment assumed for outage scenarios. Shared storage cannot automatically supply unrelated homes over a disconnected public feeder. Explain the required inverter, transfer/isolation, protection, metering and approvals as deployment dependencies, not features implemented in Python.

Keep grid-connected demand response separate from islanded service continuity. Only evaluate outage backup where the physical topology and equipment assumptions permit it. Do not claim voltage, frequency stability, protection coordination or technical-loss reduction from aggregate kW accounting.

## 5. Priorities and cut line

### P0 — must ship

1. Physically consistent energy model and deterministic scenario runner.
2. Baseline and improved controller using identical assets and external inputs.
3. Critical/normal/flexible loads with honest deferred-demand accounting.
4. Battery SOC, efficiencies, limits and energy-balance tests.
5. Reproducible reliability KPIs and baseline comparison dashboard.
6. Parameterized affordability/O&M model, evidence sources and submission documents.
7. Offline demo and one-command setup/run/evaluation instructions.

### P1 — strong differentiators after P0

1. Forecast-aware rolling-horizon optimization with a safe heuristic fallback.
2. Controller-failure resilience tied to dispatch, not just visual election events.
3. Fair allocation, resident opt-out and clear action explanations.
4. DISCOM-facing feeder stress and demand-response event summary.
5. Sensitivity experiments and controller/forecast ablations.

### P2 — stretch only

Learned forecasts if suitable data exists; separate-process edge demo; richer tariff cases; translated UI labels; read-only adapter mock for a future meter/inverter integration.

Never sacrifice physical correctness, fair comparisons or submission evidence for P2. Defer hardware, a mobile app, peer-to-peer settlement, deep learning, blockchain and full AC power flow.

## 6. Architecture and boundaries

Use five layers with explicit interfaces:

1. **Scenario/environment:** immutable demand, weather/generation, grid limits and fault events; hidden future truth is available only to the evaluator.
2. **Physical plant:** assets, energy balance, delivered energy, SOC and constraints.
3. **Controller:** forecasts and observations in; proposed dispatch out.
4. **Coordination/safety:** leadership authority, command validation, acknowledgements and local fallback.
5. **Evaluation/UI:** run artifacts, paired comparison, economics and stakeholder views.

The optimizer is a supervisory scheduler, not a millisecond inverter controller. A simulated local actuator enforces bounds even when the coordinator fails. Telemetry can be eventually consistent; shared-battery command authority cannot rely on gossip alone.

### Proposed modules

```text
src/
  domain/         # assets, loads, energy ledger, grid connection
  scenarios/      # schemas, profiles, fault event loading
  forecasting/    # persistence, profile forecast, optional learned model
  control/        # baseline, heuristic, optimizer, fallback
  coordination/   # adapted gossip/election/mutex/replication + transport
  evaluation/     # metrics, economics, experiment runner, reports
  engine.py       # deterministic step orchestration
  api/            # optional extraction from dashboard.py
data/
  scenarios/
  profiles/
  assumptions.yaml
tests/
  unit/
  integration/
  scenarios/
docs/
  architecture.md
  assumptions.md
  economics.md
  operations.md
  limitations.md
  demo.md
results/          # generated artifacts, not manually authored outcomes
web/
dashboard.py
simulation.py
```

Do not reorganize everything immediately. Establish interfaces and tests first; migrate gradually.

### Core contracts

- `Scenario`: ID, timezone, start timestamp, interval minutes, duration, seed, assets, load profiles, grid constraints, fault events and provenance.
- `Observation`: simulation timestamp, per-asset telemetry, freshness, SOC, available capabilities, current demand and grid state.
- `ForecastBundle`: issue time, horizon, demand/PV predictions, uncertainty bounds, model version and input provenance.
- `DispatchPlan`: issue time, validity window, controller epoch, per-asset setpoints, flexible-task schedule and decision reasons.
- `ActuationResult`: requested/accepted/actual power, rejection reasons, authority and acknowledgement status.
- `StepResult`: available/used generation, served/unserved energy, curtailment, import/export, SOC, task progress and faults.
- `RunManifest`: scenario hash, code revision, config, seed, controller/forecast versions, data hashes, environment versions and artifact paths.

Use typed dataclasses or Pydantic schemas. Reject missing units, negative capacities, invalid timestamps and inconsistent time-series lengths.

## 7. Simulation and physical model

### Time and reproducibility

- Default energy interval: 5 minutes. Default demo horizon: 24 hours; evaluation can run multiple days.
- Keep simulated time separate from wall-clock playback speed. Pause/speed changes must not alter energy outcomes.
- Use deterministic `step()` execution for evaluation. Pre-generate physical input profiles and use separate seeded random streams for communication faults.
- Express communication latency/failover in a separate event clock or clearly specified protocol rounds. Do not present a 5-minute energy tick as one second of failover.
- Reset must restore identical initial state and input profiles. API snapshots must be consistent copies.

### Battery

Track energy `E` in kWh, capacity, minimum reserve, charge/discharge power limits, efficiencies and throughput. With interval `dt` in hours:

`E_next = E + eta_charge * P_charge * dt - P_discharge * dt / eta_discharge`

Enforce energy and power bounds before applying commands. Disallow simultaneous charging/discharging. A full battery blocks charging; reserve-limited storage blocks discharge. Capacity loss and replacement assumptions belong in sensitivity analysis.

### Energy conservation

At the modeled AC bus, for every step:

`PV_used + wind_used + grid_import + battery_discharge + generator_output`

`= served_load + battery_charge + grid_export + modeled_network_losses`

Generation availability equals generation used plus curtailed generation. Battery losses are accounted through efficiency, not counted twice as network losses. Default modeled network losses can be zero, explicitly disclosed. Treat backup as an identified resource, not free energy.

### Loads and flexibility

- Critical: essential clinic circuits, basic lighting, essential refrigeration. Separate critical circuits from the entire building load.
- Normal: nonessential household/shop consumption.
- Flexible: EV charging, water-pumping task or other explicitly deferrable jobs.
- Each flexible job has required kWh, release time, deadline, power limit, remaining energy, consent and interruption constraints where relevant.
- Moving a task is not saving its entire energy. Track later completion and rebound. Unfinished tasks at the horizon must be counted as unmet obligations or evaluated through their deadlines.
- A water pump is flexible only while modeled storage/service requirements remain satisfied.
- Apply fairness limits such as maximum consecutive curtailment and a cap on household service disparity. Criticality is explicit, not based on ability to pay.

## 8. Baselines, forecasting and dispatch

### Comparison controllers

Implement at least:

- `B0`: no-storage/no-flexibility reference, labeled as an asset comparison only.
- `B1`: competent rule-based controller with the SAME assets as the proposed system. Serve critical loads first, use surplus to charge, discharge during deficits within reserves and schedule flexible loads by a documented simple rule.
- `P`: forecast-aware controller with the same asset limits and participation budget.

The primary claim is P versus B1. P versus B0 cannot isolate the value of software because asset availability differs. Do not intentionally cripple B1 to inflate gains.

### Forecasting

Begin with persistence and a time-of-day/profile forecast; neither may read future realized inputs. Use a documented zero-night solar profile. If using a learned model, split chronologically and fit preprocessing only on training data. Keep final evaluation scenarios held out.

Use MAE and a clearly defined normalized error. Avoid ordinary MAPE when solar/demand values approach zero. A perfect-future forecast may appear only as a labeled oracle upper bound, never as the deployed controller.

Record uncertainty bands or forecast-error scenarios. Evaluate whether forecast improvement actually improves service; retain the simpler model if it does not.

### Dispatch optimizer

Re-solve over a rolling 1–6-hour horizon, execute the first action, then update from observations. Start with a tested lightweight solver such as PuLP/CBC if available; verify installation on the team's platforms before committing. Use a deterministic heuristic if solver setup or reliability threatens the schedule.

Decision variables: battery charging/discharging, served demand by class, flexible-job power, grid import/export, renewable curtailment and unmet demand.

Constraints: energy balance, SOC evolution, battery limits, grid/feeder import limits, task deadlines, participation/opt-out, fairness and command validity. Prevent simultaneous charge/discharge and pathological simultaneous import/export through explicit constraints or a justified formulation.

Priority order: minimize critical unserved energy, then normal unmet service and deadline violations, then cost/peaks/wear. Prefer lexicographic stages or justify penalty weights and units. Include terminal SOC/reserve treatment so a short horizon does not drain storage opportunistically.

Bound solve time. Log solver status. If infeasible, timed out, invalid or stale: reject the plan and apply a bounded local fallback. Never translate solver failure into unbounded power or zero-demand reporting.

## 9. Distributed resilience: make it meaningful

Retain existing protocol modules only where they support tested behaviour. Do not preserve every protocol merely because it already exists.

- Gossip shares telemetry with origin sequence numbers/timestamps and freshness limits; Lamport clocks order events but are not wall-clock freshness measurements.
- Leader selection must respond to configurable heartbeat timeouts rather than a hard-coded N2 failure after tick 33.
- A simulated actuator authority gate accepts commands only from the active controller epoch and rejects stale, duplicate or expired commands. Election alone does not guarantee safe actuation.
- If implementing quorum/leases, document membership and timing assumptions. Without quorum, fall back locally rather than allowing both network partitions to control shared equipment.
- Existing Ricart–Agrawala can block while awaiting failed peers. Do not claim partition tolerance by simply dropping missing replies; either implement justified membership/authority semantics or remove mutex from the safety-critical path.
- Replication restores controller decisions/task state, not fictional battery energy. Reconcile with current actuator telemetry before resuming dispatch.
- Separate communications outage, controller process failure, generator loss, upstream electrical outage and battery unavailability.
- Inject delay, loss, duplication, reordering and partitions through a transport abstraction. Nodes must not consult global physical truth to bypass unavailable telemetry.
- Local fallback respects SOC and critical-load priority while communications are absent. Define restoration and stale-command rejection tests.

Keep single-process simulation if necessary and label it honestly. A separate-process demonstration is optional, not evidence of physical grid readiness.

## 10. Scenarios and experiment design

| Scenario | Disturbance | Required comparison/evidence |
|---|---|---|
| Normal operation | Day/night generation and routine demand | Energy balance, baseline sanity, no invented gain |
| Cloudy evening peak | Renewable shortfall plus demand ramp | Critical ENS, total ENS, SOC, service completion |
| Extended upstream outage | Finite shared energy in an island-capable model | Critical-service duration, unmet demand, fairness |
| Coordinator failure | Failure during constrained dispatch | Recovery latency, rejected stale commands, fallback outcome |
| Communication partition | Loss/delay and conflicting candidates | Single-authority behaviour or safe local fallback |
| Large flexible-load arrival | EV/task demand near feeder limit | Peak import, deadlines, rebound, resident consent |
| Resource exhaustion | Low SOC, prolonged shortfall, poor forecast | Honest unavoidable deficits; no false reliability guarantee |

Use paired external traces and equal initial/terminal assumptions across controllers. Start with at least 10 seeded variants of stochastic stress scenarios and expand if cheap. Report each scenario plus mean, range and sample count; do not cherry-pick the best run.

Sensitivity dimensions: battery size and initial SOC, PV capacity, participation rate, forecast error, outage duration, grid import limit, battery cost/replacement and communication disruption. Vary one factor at a time initially.

Ablations: B1 versus forecast-aware dispatch; persistence versus improved forecast; coordination with versus without failure; storage-only versus storage plus flexibility. Establish which feature causes which improvement.

## 11. Metrics: exact meanings

Let `dt` be hours and `unserved_kw` be requested minus served non-deferred demand.

- ENS (kWh): sum of `unserved_kw * dt`. Report critical and total separately.
- Critical energy served (%): `100 * critical_served_kwh / critical_requested_kwh`. If denominator is zero, report N/A.
- Critical service availability (%): fraction of demand-positive intervals where all modeled critical demand is served within a declared tolerance. This differs from energy served percentage.
- Service interruption minutes: duration of intervals with defined service shortfall. Per-household/customer minutes require explicit customer-level allocation; do not relabel aggregate shortfall as measured utility SAIDI/SAIFI.
- ENS reduction (%): `100 * (ENS_B1 - ENS_P) / ENS_B1`; if baseline ENS is zero, use absolute change and report percentage N/A.
- Peak feeder import: maximum interval-average import kW, not instantaneous protection-level peak.
- Flexible service: task completion rate, missed kWh and maximum delay; include end-of-horizon obligations.
- Renewable utilization: used renewable kWh divided by available renewable kWh, with storage-origin accounting if claiming renewable energy delivered to loads.
- Battery wear proxy: documented throughput or equivalent-full-cycle calculation; label it a proxy, not a measured lifetime prediction.
- Recovery latency: time/rounds from detected failure to first accepted valid replacement-controller command; also report detection latency.
- Fairness: worst household service fraction and consecutive curtailment, alongside aggregate improvement.

Emissions: calculate only with cited factors and explicit grid/generator attribution. Include storage losses; do not equate all battery discharge with avoided emissions or claim lifecycle benefits without lifecycle inputs.

Do not prewrite improved KPI values. Example numbers from the earlier conversation were illustrative only.

## 12. Affordability and operations

Build an editable scenario cost model, not personalized financial advice or a promise of savings. Each input needs source/date, currency/unit, range and status: sourced, measured or assumed.

Include PV/storage/inverter costs if new, protection and isolation, meters, gateway, installation, connectivity, maintenance, replacement, recycling and operator effort. Distinguish existing-asset retrofit from new infrastructure. Shared storage and low-cost software do not imply a low-cost total installation.

Report annualized system cost, cost per participating household/month, cost per served or avoided-unserved kWh and low/base/high cases. Separate household cash bill savings from modeled avoided economic losses. Avoid double-counting tariff savings, incentive revenue and avoided outage costs. Do not assume DISCOM demand-response payments exist; include a no-incentive case.

Compare against B1, larger battery-only backup and appropriate existing backup alternatives using the same service target. Include households without owned PV or batteries. Second-life storage is a scenario option with testing, usable capacity, warranty and maintenance uncertainty, not an automatic sustainability win.

Proposed operating model: cooperative/community operator or energy-service provider owns/manages assets; trained local staff handle routine checks; qualified contractors handle electrical installation and battery safety; DISCOM receives aggregate forecasts/response reports where authorized. Describe resident opt-out, complaints, fair-access rules, maintenance schedule, failure escalation, data retention and consent. Record this as proposed until validated with stakeholders.

Obtain a few consented user/operator interviews if feasible. Capture actual observations and resulting design changes; do not invent endorsements. Any external contact requires user authorization.

## 13. Dashboard, API and demonstration

### Main screens

1. Community overview: served demand, critical-service status, SOC, actual/forecast supply, upcoming risk and current actions.
2. Paired comparison: identical scenario, B1/P traces, ENS/availability/peak/task completion and assumptions.
3. Operator/DISCOM view: aggregate expected shortfall, available flexibility, proposed/requested response and delivered response.
4. Economics: editable assumptions, annualized costs and sensitivity.
5. Technical diagnostics: gossip, logical clocks, elections, acknowledgements and failure timeline.

Use clear labels: simulated data, modeled topology, actual versus forecast, observed versus estimated. Separate electrical and communication connections. Show why an action occurred and whether it was merely proposed or actually accepted by the simulated actuator.

### Proposed API additions

- `GET /api/scenarios`
- `POST /api/runs` with scenario/controller/config, returning a run ID
- `GET /api/runs/{id}` for progress, manifest and current/final metrics
- `POST /api/comparisons` for paired B1/P runs
- `GET /api/comparisons/{id}` for aligned series and results
- `POST /api/runs/{id}/control` for pause/resume or an allowed demo fault
- `GET /api/runs/{id}/export` for metrics and provenance

These endpoints are targets, not existing features. Preserve existing routes while migrating. Use polling initially; WebSockets are not required. Validate controls, limit workloads and avoid shared-global state leaking between concurrent runs. Public deployment would require separate access/security review.

### Five-minute demo

- Explain the selected community and limited-energy problem.
- Run B1 and P on the same cloudy-evening trace; show the actual computed difference.
- Show the forecast, SOC reservation and completed shifted task.
- Fail the controller; show bounded fallback, command authority and recovery.
- Show affordability, who operates the system, and physical limitations.

Keep an offline recorded demo and precomputed versioned result artifacts. Never present replay as a live hardware trial.

## 14. Testing and quality gates

### Unit and property tests

- Conservation residual within a declared numerical tolerance each step.
- SOC/power bounds, efficiencies and full/empty battery behaviour.
- Zero solar at night for the configured model.
- No controller-created power; unavailable grid cannot import.
- Critical priority, valid opt-out, deadline accounting and fair curtailment.
- Metric formulas checked against tiny hand-calculated fixtures.
- Forecast pipeline cannot access future realized values.
- No simultaneous charge/discharge or invalid import/export cycle.
- Economics/emissions units and zero-denominator handling.

### Integration and scenario tests

- Deterministic repeat runs produce matching outputs except wall-clock metadata.
- B1 and P consume identical exogenous profiles and asset budgets.
- API pause/playback/reset does not alter the underlying scenario outcome.
- Missing telemetry, invalid optimization and solver timeout trigger safe fallback.
- Failed/stale leaders cannot actuate; duplicate commands are idempotent.
- Network partition cannot create dual accepted control of a shared battery.
- Recovery reconciles telemetry rather than replaying stale energy state.
- Terminal flexible demand and battery energy are not hidden to inflate gains.
- UI displays numeric exported results consistently.

Before changing code, run existing tests and record failures. Add CI for tests if authorized within the implementation task. A clean fresh checkout must install from the committed lockfile and run the demo offline after dependencies are installed.

## 15. Fifteen-day delivery schedule 

Assumption: a small team with focused daily work; staffing and hours are not yet known. Workstreams below are roles, not authorization to spawn agents. If capacity is limited, cut P2 and simplify P1 rather than weakening P0.

| Day | Deliverable | Exit gate |
|---|---|---|
| 1 | Inspect current repo/tests; confirm challenge rules; fix scope, units and schemas | Written assumptions and baseline definition |
| 2 | Deterministic runner and input profiles | Repeatability test and valid scenario loading |
| 3 | Battery, grid, generation and load ledger | Energy/SOC unit tests pass |
| 4 | Critical allocation, flexible tasks and B1 | Hand-checked scenario produces correct results |
| 5 | Metrics, paired experiment runner and exports | Reproducible baseline report; P0 gate |
| 6 | Persistence/profile forecast and uncertainty handling | No future leakage; forecast error report |
| 7 | Forecast-aware heuristic and rolling optimizer | Valid setpoints, solver failure fallback |
| 8 | Fairness, deadline and terminal-energy refinement | Same-asset comparison with honest outcomes |
| 9 | Transport faults, authority gate and configurable failover | Stale/dual-command safety tests |
| 10 | Integrate resilience with dispatch and recovery | Failure scenario and measured latency |
| 11 | Dashboard comparison/operator views | KPIs match exports and actions explainable |
| 12 | Economics, O&M and sustainability evidence | Cost ranges, provenance and deployment limits |
| 13 | Held-out evaluation, sensitivities and ablations | Results reproducible, negative cases retained |
| 14 | Architecture/submission write-up, demo recording and fresh-install check | Complete draft package and offline backup |
| 15 | Feature freeze, rehearse, verify submission requirements | Release checklist complete; user submits/authorizes submission |

Start cost-source research and stakeholder validation on day 1 in parallel with coding; day 12 integrates findings rather than starting research. Documentation evolves with each milestone.

### Contingency gates

- End day 5: if the physical model or baseline is not sound, stop feature expansion.
- End day 8: if optimization is unstable, ship the transparent forecast-aware heuristic with fallback; report its limitations.
- End day 10: if resilient coordination is not safe, disable unsafe shared actuation and demonstrate local fallback. Do not make distributed reliability claims without evidence.
- Day 13 onward: fix defects only; do not add frameworks or redesign architecture.
- If P does not beat B1, investigate input leakage, horizon settings, objective mismatch and actual opportunity. Report where it helps and where it does not; never manipulate the baseline.

## 16. Submission package and claim discipline

Prepare:

- Clear problem/solution write-up with the selected Indian-community assumptions.
- Architecture diagrams separating energy, data, command and ownership/money flows.
- UI screenshots/wireframes and a decision workflow.
- Reproducible results tables with scenario IDs, controllers, units, seeds, uncertainty and limitations.
- Cost assumptions, ownership/O&M model and deployment prerequisites.
- Sustainability calculations with factors and boundaries.
- README with exact setup, run, test and evaluation commands; do not tell judges to initialize a new project instead of installing this repository.
- Short demo video, offline fallback, dependency lockfile and license/source attribution.
- Transparent list of simulated versus implemented versus future components and permitted AI assistance if disclosure is required.

Claims must follow evidence. Use “reduced simulated critical ENS by X in scenario Y under assumptions Z” only after the experiment exists. Do not claim proven real-world uptime, guaranteed household savings, feeder voltage control, production partition safety, validated digital twin or a guaranteed competition score.

### Final definition of done

- [ ] Fresh checkout installs and runs from documented commands.
- [ ] No physically impossible energy creation or SOC violations.
- [ ] At least one credible same-asset comparison, with all planned scenarios reported.
- [ ] Forecasts respect information available at decision time.
- [ ] Flexible demand and end-state energy accounted for fairly.
- [ ] Resilience claims backed by tests and explicit assumptions.
- [ ] Dashboard numbers equal exported calculation outputs.
- [ ] Costs and sustainability inputs have sources or visible assumption labels.
- [ ] Operator, customer consent, maintenance and electrical boundaries explained.
- [ ] Submission requirements and reuse/AI rules reverified.
- [ ] Demo rehearsed and backup recording/results available.
- [ ] No invented wins, results, pilots or partner endorsements.

## 17. First actions for the implementing agent

1. Read this plan and repository instructions and current files.
2. Run existing tests using `uv run python -m unittest discover -s tests -v`; record actual output.
3. Inventory reusable code and changes since the review; do not silently assume the source snapshot is current.
4. Write scenario/asset/metric contracts and tiny hand-calculated energy fixtures.
5. Implement deterministic runner, physical ledger and B1 before optimization or UI expansion.
6. Keep the original demo runnable during migration where feasible.
7. At each milestone, update progress and report tests, evidence, unresolved risks and next work.

 |

## Progress log — 2026-10-01

- User scope override applied: removed threaded engine, protocol modules, terminal simulation, legacy frontend/routes, old teaching plan/tests and unused Rich dependency. Preserved the current energy model and both governing documents.
- Before changes: 29 tests passed, including seven legacy tests. After removal and two new reliability/API checks: 24 current tests passed (2.404 seconds).
- Added critical interruption hours, exogenously defined scarcity-window availability, comparison deltas, UI measures and generated requirement 4/5 evidence. Hand-calculated tests cover time metrics and absent windows.
- Completed seven scenarios × ten paired seeds (100–109), plus sensitivity/ablation exports. Extended outage: mean critical interruption 3.167 h → 0 h; scarcity critical availability 47.22% → 100%. Total ENS worsens 165.50 → 177.24 kWh; ending energy/import differences remain visible. Resource exhaustion: critical interruption 5.342 h → 1.717 h. These are synthetic simulation outcomes only.
- Current run command: `make run`; evidence command: `make evaluate`; offline replay remains available. No hardware build, publication or submission performed. Full design-plan stretch items and external validation are not claimed complete.
