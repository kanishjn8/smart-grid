# Decentralized Smart Grid Simulation — Agent Plan

## Project Overview

Simulate a **peer-to-peer decentralized smart energy grid** with a **live browser frontend**.
The simulation runs continuously, injecting faults and events, while the UI renders real-time node
states, gossip flows, Lamport clocks, elections, and mutex contention in a responsive web dashboard.

Distributed computing concepts demonstrated:
- Gossip-based asynchronous communication
- Lamport logical clocks for event ordering
- Ricart–Agrawala distributed mutual exclusion
- Bully Election Algorithm for leader election
- State replication for fault tolerance

---

## Package Manager: uv

**All dependency management must use `uv`.** Do not use `pip` or `poetry`.

### Setup commands the README must include:
```bash
# Install uv (if not present)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create project and install deps
uv init smart_grid_sim
cd smart_grid_sim
uv add fastapi uvicorn rich

# Run simulation
uv run python dashboard.py
```

### `pyproject.toml` dependencies block:
```toml
[project]
name = "smart-grid-sim"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "rich>=13.7.0",
    "uvicorn>=0.35.0",
]
```

> Use `uv run python <file>` for every execution command in the README.

---

## Visual Simulation — What the User Sees

The simulation uses a **FastAPI backend + browser frontend** to render a live dashboard
that updates every 500ms. The page is divided into panels:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│  DECENTRALIZED SMART GRID SIMULATION    Tick 023 | 11.5s | STABLE          │
├──────────────────────────────┬──────────────────────────────────────────────┤
│  GRID HEALTH + CONTROLS      │  LIVE NETWORK MAP                            │
│  Balance meter               │  Animated links for gossip / mutex / faults  │
│  Convergence indicator       │  Node badges with live clocks and status     │
│  Pause / Fault / Reset       │  Leader glow, crash state, replication pulse │
├──────────────────────────────┴──────────────────────────────────────────────┤
│  NODE CARDS                                                         │
│  Solar | Wind | Storage | Consumer | Microgrid | EV | Battery | Backup     │
├──────────────────────────────┬──────────────────────────────────────────────┤
│  GOSSIP FEED                 │  EVENT TIMELINE                              │
│  [014] N1 -> N5 GOSSIP       │  [Tick 10] Solar output dropped             │
│  [015] N3 -> N8 REPLICATE    │  [Tick 30] N2 crashed                       │
│  [016] N5 -> N2 GOSSIP       │  [Tick 45] N2 recovered                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Visual Highlights per Concept:

| DC Concept | Visual Representation |
|---|---|
| Gossip | Scrolling message feed with sender→receiver arrows; active SVG links pulse cyan |
| Lamport Clocks | Each node shows `[clock]` value in brackets, incrementing live |
| Mutual Exclusion | Node card turns **yellow** when requesting mutex; **orange** when in critical section |
| Leader Election | Winning node gets a `★` badge and halo; election messages shown in orange in event log |
| Node Crash | Node card turns **red** with `✗ CRASHED`; incident edges break visually |
| Recovery | Card fades back to normal; leader steps down; green recovery event logged |
| Replication | N8 pulses briefly every 5 ticks when receiving replicated state |
| Grid Stability | Meter bar: green=stable, yellow=stressed, red=critical (based on supply-demand delta) |

---

## Node Types

Each node runs as a **separate thread** with an inbox `queue.Queue`:

| Node ID | Type | Behaviour |
|---|---|---|
| N1 | Solar | Power follows a sine wave (day/night cycle), disrupted at tick 10 |
| N2 | Wind | Random bursts 0–4kW; crashes at tick 30, recovers at tick 45 |
| N3 | Storage | Buffers surplus; discharges when grid deficit detected via gossip |
| N4 | Consumer | Steady -3kW draw; spikes to -6kW at tick 20 |
| N5 | Microgrid | Aggregates local supply/demand; initiates elections |
| N6 | EV | Offline until tick 55; connects and draws -2kW |
| N7 | Battery | Default election winner (highest priority); temporary leader |
| N8 | Backup/Grid | Last resort source; stores replicated state from all nodes |

---

## Node State (per node, in memory)

```python
@dataclass
class NodeState:
    node_id: str          # "N1"
    node_type: str        # "Solar"
    power_output: float   # kW (positive=generating, negative=consuming)
    lamport_clock: int    # logical timestamp
    known_state: dict     # gossip table: {node_id: (power, lamport_ts)}
    is_leader: bool
    in_critical_section: bool
    requesting_mutex: bool
    alive: bool
    deferred_replies: list  # for Ricart-Agrawala
    election_replied: bool
```

---

## Core Modules

### `node.py` — Base Node Thread
- Runs in a `threading.Thread`, loops every 0.5s (one tick)
- Has `inbox: queue.Queue` for receiving messages
- Methods: `send(target_node, msg)`, `tick()`, `update_lamport(ts)`
- On each tick: update power output, run gossip round, check inbox

### `gossip.py` — Gossip Protocol
- Each node picks **2 random live neighbours** per tick
- Sends `GOSSIP` message: `{sender, lamport_clock, known_state}`
- Receiver merges: for each node in payload, keep entry with **higher Lamport timestamp**
- Convergence in ~`log(N)` rounds → all nodes share same global view

### `lamport.py` — Logical Clocks
- `on_send()`: `clock += 1`
- `on_receive(msg_ts)`: `clock = max(clock, msg_ts) + 1`
- Every message carries current clock value
- Used to order: load balance decisions, mutex requests, election messages

### `mutex.py` — Distributed Mutual Exclusion (Ricart–Agrawala)
- Triggered when a node needs to **reroute power** (critical shared resource)
- Node broadcasts `REQUEST(node_id, lamport_ts)` to all live nodes
- Waits for `REPLY` from all; enters critical section; sends deferred replies on exit
- A node defers its reply if it is also requesting and has a lower Lamport timestamp
- Dashboard: node row yellow (requesting) → orange (in CS) → normal (released)

### `election.py` — Bully Election Algorithm
- Triggered when a node detects a neighbour silent for **3+ ticks**
- Node sends `ELECTION` to all nodes with **higher numeric ID**
- If no `ALIVE` response within 2 ticks → declares itself **COORDINATOR**
- Winner broadcasts `COORDINATOR` message; shown as `★` in dashboard
- After grid stabilizes, leader sends `COORDINATOR_DONE` and steps down

### `replication.py` — State Replication
- Every 5 ticks, each node sends `REPLICATE` message to N8
- N8 stores snapshot: `{node_id: last_known_state}`
- On node crash and recovery, N8 broadcasts last known state for that node
- N8 row pulses in dashboard when receiving/sending replica data

### `fault_injector.py` — Scheduled Faults
Runs in its own thread, injects faults at specific ticks:

```python
FAULT_SCHEDULE = [
    (10, "solar_drop",    "N1 power → 0.0kW (cloud cover)"),
    (20, "demand_spike",  "N4 consumption → -6.0kW (spike)"),
    (30, "node_crash",    "N2 Wind Node crashes"),
    (45, "node_recover",  "N2 Wind Node recovers"),
    (55, "ev_connect",    "N6 EV connects, draws -2.0kW"),
    (65, "storage_full",  "N3 Storage at capacity, stops discharging"),
]
```

### `dashboard.py` — Browser Dashboard Server (MAIN ENTRY POINT)

Build a FastAPI app that:

- starts the threaded simulation at startup
- serves `web/index.html`, `web/styles.css`, and `web/app.js`
- exposes `GET /api/state` for live snapshots
- exposes `POST /api/control/pause`, `/fault`, and `/reset` for UI controls
- stops the simulation cleanly on shutdown

Frontend details:
- **Hero metrics**: tick, elapsed time, grid balance, convergence, leader, status
- **Network map**: SVG lines between nodes with color-coded animation for gossip, mutex, replication, and crash states
- **Node cards**: responsive grid of the 8 nodes with power, clock, status, leader badge, and replication pulse
- **Feeds**: scrolling gossip activity and event timeline rendered from the JSON snapshot
- **Controls**: pause/resume, trigger next fault, reset grid

---

## Message Schema

```python
{
    "type": "GOSSIP" | "REQUEST" | "REPLY" | "ELECTION" | "ALIVE" |
            "COORDINATOR" | "COORDINATOR_DONE" | "REPLICATE" | "FAULT",
    "sender": "N1",
    "receiver": "N3",      # or "BROADCAST"
    "lamport_ts": 14,
    "payload": { ... }     # type-specific data
}
```

---

## Simulation Tick Narrative

```
Ticks 01–09   Normal operation. Gossip converges across all 8 nodes.
              Lamport clocks increment with each message. Dashboard shows
              steady green bars, scrolling gossip feed, rising clock values.

Tick 10       FAULT: Solar (N1) drops to 0kW.
              Storage (N3) detects deficit via gossip → requests MUTEX.
              Dashboard: N3 row turns yellow → orange → normal.
              Backup (N8) reroutes 1.5kW. Grid restabilises.

Tick 20       FAULT: Consumer (N4) demand spikes to -6kW.
              Grid balance bar turns yellow. Microgrid (N5) requests MUTEX
              to coordinate rerouting. Storage and Backup both contribute.
              Grid balance returns to green after 3 ticks.

Tick 30       FAULT: Wind (N2) crashes (alive=False).
              N2 row turns red: "✗ CRASHED". Gossip stops propagating N2 state.
              N5 detects N2 silence after 3 ticks → initiates ELECTION.
              ELECTION messages fly to N6, N7, N8 (higher IDs).
              N7 (Battery) wins → ★ COORDINATOR badge appears.
              N7 coordinates load redistribution.

Ticks 31–44   N7 leads recovery. Solar recovers naturally (sine curve rises).
              System operates in semi-centralised mode under N7.

Tick 45       RECOVERY: N2 (Wind) comes back online.
              N7 detects full grid stability → sends COORDINATOR_DONE.
              ★ badge removed. System returns to fully decentralised mode.

Tick 55       FAULT: EV (N6) connects, draws -2kW suddenly.
              N6 requests MUTEX for safe grid switching.
              Storage and Solar absorb the load.

Tick 65       Storage (N3) hits capacity limit, stops discharging.
              Backup (N8) picks up remaining load via gossip-informed decision.

Tick 70+      Continuous steady-state operation. All concepts demonstrated.
              Simulation continues until the user stops the web server.
```

---

## File Structure

```
smart_grid_sim/
├── pyproject.toml          # uv project file with dependencies
├── README.md               # setup + run instructions using uv
├── dashboard.py            # MAIN: FastAPI server for browser dashboard
├── simulation.py           # fallback: simple rich terminal (no Textual)
├── web/
│   ├── index.html          # browser dashboard shell
│   ├── styles.css          # visual system and layout
│   └── app.js              # polling + DOM updates
└── src/
    ├── __init__.py
    ├── node.py             # Node dataclass + thread
    ├── gossip.py           # Gossip protocol
    ├── lamport.py          # Logical clock helpers
    ├── mutex.py            # Ricart-Agrawala mutual exclusion
    ├── election.py         # Bully election algorithm
    ├── replication.py      # N8 state replication
    └── fault_injector.py   # Scheduled fault injection thread
```

---

## How to Run

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Set up project
uv init smart_grid_sim
cd smart_grid_sim

# 3. Install dependencies
uv add fastapi uvicorn rich

# 4. Run visual dashboard (recommended — browser UI)
uv run python dashboard.py

# 5. Open the frontend
#    http://127.0.0.1:8000

# 6. OR run simple terminal mode (fallback)
uv run python simulation.py

# Controls (browser mode)
#   Pause / Resume
#   Trigger Fault
#   Reset Grid
```

---

## Concept-to-Code Mapping

| DC Concept | File | Key function/class |
|---|---|---|
| Distributed Architecture | `src/node.py` | `class Node(threading.Thread)` |
| Async Message Passing | `src/node.py` | `Node.send()`, `Node.inbox (Queue)` |
| Gossip Protocol | `src/gossip.py` | `gossip_round(node, all_nodes)` |
| Lamport Clocks | `src/lamport.py` | `on_send(clock)`, `on_receive(clock, msg_ts)` |
| Mutual Exclusion | `src/mutex.py` | `request_cs()`, `release_cs()`, `handle_request()` |
| Leader Election | `src/election.py` | `start_election(node, all_nodes)`, `handle_election_msg()` |
| Replication | `src/replication.py` | `replicate_to_backup(node, backup)` |
| Fault Injection | `src/fault_injector.py` | `class FaultInjector(threading.Thread)` |
| Visual Dashboard | `dashboard.py` + `web/app.js` | `create_app()`, `SimulationController`, browser renderer |

---

## Agent Implementation Notes

- **Lamport rule**: increment clock BEFORE sending; `max(local, received) + 1` on receive.
- **Bully rule**: nodes numbered N1(1)…N8(8). Higher number = higher priority. N7 wins by design; N8 excluded from leadership since it's the backup/data node.
- **Ricart–Agrawala**: node defers REPLY if it is also requesting AND its own `(lamport_ts, node_id)` tuple is LESS than the incoming request's tuple (lexicographic compare). Otherwise reply immediately.
- **Web architecture**: keep the simulation threaded; the browser frontend only polls `/api/state` every 500ms and renders from the JSON snapshot.
- **Thread safety**: all node state reads from API handlers must go through the simulation snapshot API; never read node state directly from the frontend layer.
- **Power diagram**: render via SVG + absolutely positioned node cards. Edge classes should reflect gossip, mutex, replication, and crash activity.
- **Grid stability metric**: `balance = sum(n.power_output for n in nodes if n.alive)`. Green if `abs(balance) < 1.0`, yellow if `< 2.5`, red otherwise.
- **Gossip convergence indicator**: count how many nodes have identical `known_state` snapshots. Show as "X/8 nodes converged" in the status panel.
- **Tick speed**: default 500ms per tick. Make it configurable via a constant `TICK_DURATION = 0.5` at top of `simulation.py`.
- **Do not use asyncio for node threads** — use `threading.Thread` + `queue.Queue` throughout. The FastAPI layer only orchestrates lifecycle and control endpoints.
