# Decentralized Smart Grid Simulation

A threaded smart-grid simulation that demonstrates gossip-based state sharing, Lamport clocks,
Ricart-Agrawala mutual exclusion, bully-style leader election, scheduled faults, and backup
replication through a live browser dashboard.

## Setup

```bash
# Install uv (if not present)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create project and install deps
uv init smart_grid_sim
cd smart_grid_sim
uv add fastapi uvicorn rich
```

## Run

```bash
# Browser dashboard
uv run python dashboard.py

# Then open:
# http://127.0.0.1:8000

# Optional fallback Rich terminal mode
uv run python simulation.py
```

The browser UI polls the simulation every 500ms and exposes controls to pause/resume the grid,
trigger the next scheduled fault, and reset the simulation.

## Useful Development Commands

```bash
# Run tests
uv run python -m unittest discover -s tests -v

# Start the dashboard on a custom port
uv run python dashboard.py --port 8050 --tick-duration 0.1

# Fallback terminal smoke run
uv run python simulation.py --ticks 8 --tick-duration 0.1
```

## Browser Controls

```text
Pause / Resume   toggle the simulation clock
Trigger Fault    inject the next scheduled disruption
Reset Grid       restart the full simulation
```
