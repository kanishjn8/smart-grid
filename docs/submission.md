# GridSathi — draft submission

## Problem and intended user

Renewable shortfalls and upstream outages force communities to choose how to use finite shared energy. A clinic's essential circuits, basic lighting, refrigeration, household/shop consumption and flexible EV or tank-refill jobs have different service needs. The community operator needs a clear view of which services can still run and why a task is deferred. A DISCOM engineer needs aggregate, actionable shortfall estimates without requiring individual household telemetry.

This prototype models an illustrative Indian community of 100 households, ten shops, essential clinic circuits and a water tank behind one common connection point. These are design assumptions, not a surveyed pilot. Outage continuity requires suitable island-capable equipment and approved isolation/protection. The software does not energize unrelated homes on a disconnected public feeder.

## Solution

GridSathi combines a physically constrained storage ledger, a three-hour profile forecast, consent-aware flexible scheduling and critical-service prioritization. A transparent rule baseline uses the same assets. The dashboard reports executed energy and explains each proposed/accepted command. A simulated actuator rejects invalid authority or stale commands and applies local fallback when communication is unavailable.

The implementation is single-process, deterministic and reproducible. Energy and controller timing are separate: five-minute energy intervals contain abstract protocol rounds, with no millisecond control or real-world recovery claim. No hardware build is required.

## Design package

[Architecture](architecture.md) separates energy, observations, command authority and proposed ownership/cost flows. [Assumptions](assumptions.md) defines every asset, task and metric. [API](api.md) specifies run creation, replay, controls, comparison and export. The browser interface supports community, paired comparison, operator, affordability and diagnostics views. Captured screens and the interactive offline replay accompany [the demo](demo.md).

## Reliability evidence

`results/latest/report.md` is generated, not hand-authored. The evaluation covers seven scenarios and ten paired seeds per scenario, with asset, forecast, participation, grid, outage and communication sensitivities. The main comparison is P versus B1, not P versus the different-asset B0 reference. Each result includes scenario and source hashes, initial/terminal energy, import energy, forecast errors, missed jobs and safety outcomes.

In the initial held-out evaluation, P protects critical service during the extended-outage and resource-exhaustion scenarios. It does not improve cloudy-evening total ENS, and extended-outage critical protection accompanies increased total ENS. These are service-allocation tradeoffs, not a blanket claim of lower energy use. Use the current generated report for exact values, ranges, seeds and ending energy; do not quote stale draft numbers.

Physical invariants, deadline accounting, zero denominators, opt-out behavior, repeatability, API lifecycle, stale/duplicate authority rejection, packet faults and recovery are covered by tests. The final test record appears in `docs/release-checklist.md` and the progress log in `agent.md`.

## Affordability, ownership and sustainability

The editable INR model includes equipment, protection, metering, installation, maintenance, connectivity, operator effort, replacement and recycling. Low/base/high costs are explicit assumed sensitivity cases, not quotations. Existing-asset retrofit and new acquisition are distinct. Larger-battery and no-PV battery-only references expose whether a selected critical-service target is met before comparing their assumed costs.

A cooperative or service provider is proposed to own/manage assets, with voluntary participation, fair-access rules and a complaints process. Local operators monitor service; qualified contractors commission and maintain equipment. [Operations](operations.md) explains this proposed model and consent/data boundaries. It has not been validated with stakeholders.

Renewable utilization and battery throughput are measured within the simulation. No emissions reduction or lifecycle benefit is claimed without verified factors and source attribution. Shared ownership does not by itself make the total installation affordable.

## Honest scope and next validation

No field trial, partnership, measured utility index, voltage/frequency control or production distributed-safety claim is made. The released scheduler is a forecast-aware heuristic, not a mathematical optimizer. Real load/weather data, stakeholder validation, quotes, equipment design and approvals are future validation work. The original repository and this implementation used AI assistance; obtain organizer confirmation of reuse and AI-disclosure rules before submitting. This document is a reviewable draft, not an entry submitted to the competition.
