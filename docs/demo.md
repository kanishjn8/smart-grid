# Five-minute demo and offline backup

All demonstrations use simulated data, never live hardware. Start `make run`, or open `web/offline.html` for the saved cloudy-evening replay. The local dashboard opens at http://127.0.0.1:8000. A saved replay ignores the current controls until a new calculation is run.

1. **0:00–0:40 — Community and physical boundary.** Explain the assumed community and common island-capable connection point. Show demand, actual served power and stored energy. There is no controller-generated power.
2. **0:40–1:40 — Honest baseline.** Run the cloudy-evening scenario at seed 7. Both B1 and P use identical assets and traces. Show that total ENS is unchanged in this case; P retains more energy and uses more imports. Do not describe this as a universal efficiency gain.
3. **1:40–2:40 — Finite energy and service priority.** Select extended upstream outage and run comparison. Show critical ENS together with total ENS, imports and terminal energy. P prioritizes essential service, with a normal-service tradeoff. Inspect the action explanation and flexible-task completion.
4. **2:40–3:40 — Failure and recovery.** Open Diagnostics, start an interactive run, advance into constrained dispatch (or select coordinator-failure scenario and finish). Inject controller failure, advance and inspect failure, new epoch, rejected old command and replacement acceptance. Inject a communication partition and advance to show bounded local fallback. Explain that abstract rounds are not physical seconds.
5. **3:40–4:30 — Affordability and operation.** Calculate base/low/high costs. All values are editable assumptions. Identify the proposed community operator, residents' opt-out and electrical prerequisites. Cost per household is not a validated affordable tariff.
6. **4:30–5:00 — Evidence and limits.** Export the comparison. Open `results/latest/report.md` for all seven scenarios and ten paired seeds. Show that unfavorable results and resource exhaustion remain in the report.

## Backup package

- `web/offline.html`, `community.css`, `community.js`, `replay.js`: portable offline replay, no third-party scripts or network fonts.
- `results/latest/demo-comparison.json`: exact saved seed-7 result and manifest.
- `results/latest/*/B1` and `P`: representative per-scenario JSON/CSV traces and provenance.
- `results/latest/all_metrics.json`, `summary.json`, `sensitivities.json`, `service_target_alternatives.json`: held-out numerical evidence, including low/base/high cost cases and larger-storage alternatives at an explicit critical-service target.
- `docs/screenshots/`: five actual captured UI states. Video encoding was declined during this session; no video or GIF is claimed as delivered. The interactive offline replay remains the usable backup. `scripts/record_demo.py` is prepared for a later authorized encoding run with the optional `demo` dependency group.

Rehearsal checks: run comparison; compare visible precision-rounded table values with the exported JSON; pause and advance without changing state; resume; inject controller/partition faults; reset and reproduce; calculate economics; open the standalone replay. The release checklist records which checks actually ran.
