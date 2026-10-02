# Implemented, assumed and future

|Category|Status|
|---|---|
|Deterministic aggregate energy model, SOC, jobs, B0/B1/P, comparison API and dashboard|Implemented and tested|
|Forecast-aware scheduling|Implemented transparent receding-horizon heuristic; no solver or optimality claim|
|Communication faults and command fencing|Implemented single-actuator simulation; no distributed quorum / multi-device proof|
|Controller recovery|Current actuator telemetry is reconciled at replacement; no durable distributed replication claim|
|Household fairness|Equal proportional normal-service fractions assumed; 60-minute consecutive-curtailment advisory may be violated|
|Costs and operations|Editable assumptions and proposed ownership/O&M; no validated bill savings|
|Electrical installation and island capability|Assumed deployment prerequisites; not implemented hardware|
|PV/demand/weather|Synthetic traces; no field or calibrated weather data|
|Emissions|Not calculated without verified factors and source attribution|
|Learned forecasts, separate processes, hardware adapter, translated UI, tariff optimizer|P2 future work; not needed to use this release|

No AC power flow, voltage/frequency control, protection coordination, technical-loss reduction, real equipment actuation, production partition safety or real-world uptime claim. Default wind and generator output are zero. A generator-loss event can be represented in the fault schema but has no pilot effect because there is no generator; adding one requires a fuel and availability model.

P does not win all comparisons. Critical priority can reduce normal service. Forecast reserves and grid charging can increase terminal energy, imports or ENS elsewhere. Results expose end energy rather than silently normalizing away the difference. Fair comparisons use exactly the same environment hash; compare controller configuration and terminal state before describing causal software improvements.

The heuristic is the explicitly allowed simplified P1 path in the plan. Optimization, learned prediction, survey research and real-world service validation are not silently presented as completed. Run state is process-local and bounded; deployment beyond localhost would need authentication, durable storage and workload/security review.

Remaining external release gates: confirm competition status/deadline, eligibility, existing-work reuse and allowed AI assistance with the organizer; inspect current submission form fields/attachment limits with an authorized registered account; obtain supplier quotes and consented stakeholder feedback. The implementation does not send contacts, publish, submit or accept competition terms.
