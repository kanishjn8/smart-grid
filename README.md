# GridSathi — community energy resilience simulator

A local, deterministic energy simulator with a FastAPI dashboard, same-asset baseline comparison, finite battery storage, critical-load priority, flexible jobs and simulated controller failures. All community data is synthetic; no electrical equipment is controlled.

## Install and run

Python 3.11+ and [uv](https://docs.astral.sh/uv/) are required. From this repository:

```sh
uv sync --frozen
uv run --frozen python dashboard.py
```

Open [the local dashboard](http://127.0.0.1:8000). No internet is needed after dependencies are installed. `make setup` and `make run` are equivalent shortcuts. Do not initialize a new project over this checkout.

```sh
# Physical invariants, task accounting, deterministic replay, authority and API tests
make test

# 7 scenarios × 10 paired seeds; sensitivity and ablation reports
make evaluate

# Faster offline demo generation (one seed per scenario)
make demo
```

## Use

Choose a scenario, seed, battery capacity and participation rate, then **Run paired comparison**. The Community view reports executed P outcomes; Comparison shows B1 and P using identical inputs. Inspect an interval for the requested versus accepted battery command. Diagnostics supports isolated step/pause/resume/reset runs and controller/communication faults. Affordability exposes editable, explicitly assumed INR budgets.

The server runs only the deterministic GridSathi model. No physical hardware is required.

**Offline fallback:** open `web/offline.html` directly in a browser. It contains a saved seed-7 cloudy-evening comparison through `web/replay.js`; live calculations require the server. The replay is labeled and independent of the settings above it. `results/latest/report.md` and JSON/CSV run exports contain the computed evidence.

## Model and evidence

- Default 24-hour / 5-minute profiles; reproducible physical and independent communication seeds.
- Battery SOC, reserve, power limits, efficiency and AC energy conservation checked every interval.
- B0 no-storage asset reference; B1 competent same-asset rules; P three-hour forecast-aware heuristic with local fallback. P is not an optimizer and has no optimality guarantee.
- Critical/normal/flexible service, opt-out fixed requests, deadlines and unfinished task energy.
- Actuator-owned epochs reject stale, duplicate and expired commands. Latencies are abstract rounds, not seconds; this is not production distributed control.
- Paired reports retain negative results, imported energy and terminal battery energy. Critical-service improvement can accompany worse normal service or greater grid imports.

See [architecture](docs/architecture.md), [assumptions and metric definitions](docs/assumptions.md), [economics](docs/economics.md), [operations](docs/operations.md), [limitations](docs/limitations.md), [API](docs/api.md), [demo](docs/demo.md), and [submission draft](docs/submission.md). [Source and organizer verification](docs/sources.md) records external release gates.

## API example

```sh
curl -X POST http://127.0.0.1:8000/api/comparisons \
  -H 'Content-Type: application/json' \
  -d '{"scenario":"extended_outage","seed":7}'
```

Runs are bounded, isolated in-memory objects. Export before restarting the server. Localhost is the intended deployment boundary; authentication and public hosting are outside this release. No push, deployment, contact or competition submission occurs in the setup/evaluation commands.

## Attribution

This implementation was developed with AI assistance, which must be disclosed or cleared as required by competition rules. No third-party data was copied into the synthetic profiles. Dependency versions are pinned in `uv.lock`; dependency attribution is in `docs/sources.md`. The original repository provided no explicit license; no new license grant is inferred.

## Requirements 4 and 5

The software prototype runs with `make run`; no physical hardware build is needed. `make evaluate` generates the [reliability evidence](results/latest/report.md) for seven scenarios and ten paired seeds each.

The extended-outage case reduces mean simulated critical interruption from 3.167 hours (B1) to zero (P), with scarcity-window critical availability rising from 47.22% to 100%. This is a critical-service allocation improvement: total ENS increases from 165.50 to 177.24 kWh, and ending battery energy and imports differ. It is not an all-load uptime or field-performance claim. The report retains every scenario, including unchanged outcomes.
