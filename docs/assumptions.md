# Assumptions and metric definitions

All numerical pilot inputs are **assumed**, dated 2026-09-20. No field measurements, interviews or vendor quotes were supplied. The default notional community is 100 equal-demand households, ten shops, essential clinic circuits and a tank-refill job. Demand aggregates those uses; the household service fraction assumes proportional equal allocation, not individual metered households.

|Input|Default|Unit / status / range|
|---|---:|---|
|PV|100|kW AC ceiling; assumed; sensitivity 50/100/150|
|Battery|160|kWh usable nameplate model; assumed; 80/160/320|
|Initial SOC|65%|assumed; 20/65/100%; exhaustion defaults to 20%|
|Battery reserve|10%|assumed hard floor|
|Charge / discharge limits|50 / 50|kW assumed|
|Charge / discharge efficiency|95% / 95%|assumed; 90.25% round-trip before other losses|
|Grid connection|65|kW assumed; sensitivity 25/45/65; stress evenings limited to 24|
|Export limit|0|kW; explicit export supported in custom assets|
|Critical demand|9, or 12 in evening|kW; essential circuits only|
|Normal demand|22 plus morning/evening ramps|kW aggregate synthetic profile; seeded ±6% variation|
|EV obligations|4 × 20|kWh; 4 × 55 in arrival scenario; 7.2 kW/job|
|Tank refill|18|kWh before 16:00; 6 kW; assumed tank buffer allows deferral between 09:00–16:00|
|Solar shape|zero at night|sine daylight template; seeded cloud factors; not location-calibrated|
|Wind / generator|0 / 0|no installed wind or fuel-backed generator in this pilot|
|Network losses|0|kW; aggregate bus assumption|

The model uses Asia/Kolkata timestamps and five-minute intervals over 24 hours. No PV below the horizon. All flexible tasks have deadlines within the evaluated horizon. Only interruptible jobs are accepted by the schema; non-interruptible appliance models are not implemented.

## Dispatch and participation

B1 immediately requests available jobs in deadline order, serves critical loads before normal loads and flexible jobs, charges renewable surplus, and discharges when the grid plus renewables cannot meet current demand. It uses the same capacities, participation and initial SOC as P. B0 disables storage and requests all tasks immediately; B0 is an asset reference only.

P uses a rolling three-hour forecast to shift consented tasks toward expected headroom, never intentionally waiting beyond their last feasible start. This is feasibility under full task-power availability, not a guarantee during a shortage. It builds a reserve toward initial energy or predicted shortfall using available grid headroom. During an observed upstream outage it budgets finite stored energy across the horizon while prioritizing current critical demand. No future outage schedule is disclosed to P. P can increase imports, retain more terminal energy, or increase normal-load ENS. Report those effects alongside critical-service gains.

Opted-out tasks follow a fixed immediate request schedule. Unserved opted-out energy remains a missed obligation and is not silently rescheduled. Consented tasks can retry through their deadline. All unfinished task energy counts once in total ENS, including infeasible arrival scenarios. Maximum completion delay is release-to-completion time, with unfinished jobs censored at the horizon, not a tardiness guarantee.

Normal service is allocated proportionally to identical modeled consumers; its disparity is identically zero by construction. Consecutive partial curtailment is tracked with a 60-minute advisory threshold. A finite-energy outage can violate that threshold. This is a disclosed soft fairness limit, not a guarantee of maximum interruption duration or individual appliance switching.

## Metrics

Energy balance tolerance: 1e-7 kW. Critical interval service uses the same shortfall tolerance. ENS sums critical and normal shortages × interval hours, plus missed task obligations once. Critical energy served is a ratio of kWh; critical availability is a fraction of demand-positive intervals with no shortfall. Empty denominators are JSON null / UI N/A.

Renewable utilization includes charging and export, not just direct delivery to loads. Battery throughput sums absolute AC charge and discharge kWh; equivalent full cycles divide by twice capacity. This is a wear proxy, not an aging model. Initial and terminal stored energy and terminal shortfall are exposed. Terminal values are not forcibly equal and no salvage credit is used. Comparisons must consider both them and imported energy.

Forecast MAE is evaluated one step ahead against subsequent truth; normalized PV MAE divides by installed PV kW. No MAPE. Three-hour forecast uncertainty is uncalibrated. Protocol recovery is in abstract rounds. Aggregate shortfall minutes are not SAIDI, SAIFI, frequency stability or measured customer minutes.

Versioned schemas are exported under `data/scenarios/`; scenario traces and file hashes appear with each result. Evaluation seeds 100–109 are disjoint from demo seed 7; no learned model or fitted preprocessing exists.

## Reliability time metrics

Critical interruption hours = count of executed intervals with critical unmet power above 1e-7 kW × interval hours. This measures modeled critical-service interruption, not upstream outage duration or customer SAIDI. Critical availability counts fully served intervals with positive critical demand.

Scarcity windows are selected identically for both controllers from external renewable availability + grid capacity < requested critical + normal demand (tolerance 1e-7 kW), before battery dispatch. Window availability excludes intervals without critical demand; no qualifying intervals yields null / N/A. These windows can include cloud loss, feeder constraints, night and upstream outages. Deferred flexible tasks remain counted separately in total ENS.
