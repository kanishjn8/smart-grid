# Local API

FastAPI interactive schema is at `/docs`. JSON uses kW, kWh, interval indexes, ISO-8601 timestamps with UTC offsets, and explicit abstract-round command timing. Invalid/unknown fields and nonfinite numbers are rejected. `data/scenarios/schema.json` describes custom scenarios.

|Method / route|Behavior|
|---|---|
|GET `/api/scenarios`|Seven synthetic scenario choices|
|POST `/api/runs`|Create isolated ready run; returns ID and progress; max 12 retained|
|GET `/api/runs/{id}`|Consistent status, progress, manifest, partial metrics, tasks, events and series|
|POST `/api/runs/{id}/control`|`step`, `pause`, `resume`, `complete`, `reset`, `fault`|
|GET `/api/runs/{id}/export`|Full re-playable JSON result|
|DELETE `/api/runs/{id}`|Release a local run|
|POST `/api/comparisons`|Compute B1 and P synchronously on one immutable scenario; returns ID plus both runs and differences|
|GET `/api/comparisons/{id}`|Read cached comparison; oldest is evicted after 12|
|POST `/api/economics`|Editable `assets` and `costs`; low/base/high assumed capital and O&M costs|

Example run request: `{"scenario":"extended_outage","controller":"P","seed":7,"forecast_model":"profile","participation":1}`. Optional `assets` validates limits and units. `custom_scenario` accepts an entire validated trace and supersedes the scenario/seed/assets construction fields; it does not execute arbitrary files. `loss`, `duplicate`, `delay_rounds`, and `forecast_error` parameterize transport/forecast experiments. Profiles are bounded to 2016 intervals, household counts to 10000, and numerical limits to finite declared ranges.

Control body: `{"action":"step","steps":12}` advances one modeled hour at defaults. `pause` makes step a no-op; resume is explicit, and `complete` returns 409 while paused. Fault injection uses `{"action":"fault","fault":"partition","duration_steps":12}`. Allowed demo faults are controller failure, partition and battery unavailability; they are preserved in the exported scenario/hash. Reset replays that same scenario including injected events; create another run for a clean scenario.

Partial-run `total_ens_kwh` includes outstanding flexible obligations provisionally. It is not a final deadline-violation metric until the run completes. Final comparisons always run through all deadlines. A ready/paused run has no wall-clock auto-advance; only explicit steps change it. This makes playback speed irrelevant to energy outcomes.

Recovery reconciles in-memory plant/task state and does not import arbitrary checkpoint energy. These APIs are intended for a trusted localhost session. The lock protects coherent snapshots and bounded shared maps; a public service needs authentication, per-user quotas and durable persistence.
