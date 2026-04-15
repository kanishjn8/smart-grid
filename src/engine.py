from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .fault_injector import FaultInjector

if TYPE_CHECKING:
    from .node import Node

NODE_LAYOUT = [
    ("N1", "Solar"),
    ("N2", "Wind"),
    ("N3", "Storage"),
    ("N4", "Consumer"),
    ("N5", "Microgrid"),
    ("N6", "EV"),
    ("N7", "Battery"),
    ("N8", "Backup"),
]


@dataclass
class SimulationSnapshot:
    tick: int
    elapsed: float
    nodes: list[dict[str, object]]
    messages: list[dict[str, object]]
    events: list[dict[str, str]]
    balance: float
    status: str
    convergence: str
    leader: str | None
    paused: bool


class GridSimulation:
    def __init__(self, tick_duration: float = 0.5, seed: int = 7):
        self.tick_duration = tick_duration
        self.seed = seed
        self.running = False
        self.paused = False
        self.current_tick = 0
        self.start_time = 0.0
        self.current_leader: str | None = None
        self.tick_condition = threading.Condition()
        self.random = __import__("random").Random(seed)
        self.log_lock = threading.Lock()
        self.messages: deque[dict[str, str]] = deque(maxlen=240)
        self.events: deque[dict[str, str]] = deque(maxlen=240)
        self.replicas: dict[str, dict[str, object]] = {}
        self.flags = {
            "solar_drop_until": 0,
            "demand_spike_until": 0,
            "ev_connected": False,
            "storage_full": False,
        }
        self.support_until = {"N3": 0, "N5": 0, "N6": 0, "N7": 0, "N8": 0}
        self.clock_thread: threading.Thread | None = None
        self.fault_injector = FaultInjector(self)
        self.nodes: dict[str, Node] = {}
        self._setup_nodes()

    def _setup_nodes(self) -> None:
        from .node import Node

        self.nodes = {
            node_id: Node(node_id=node_id, node_type=node_type, engine=self)
            for node_id, node_type in NODE_LAYOUT
        }

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.start_time = time.monotonic()
        for node in self.nodes.values():
            node.start()
        self.clock_thread = threading.Thread(target=self._tick_loop, daemon=True, name="grid-clock")
        self.clock_thread.start()
        self.fault_injector.start()
        self.log_event("info", "[Tick 00] Simulation started")

    def stop(self) -> None:
        if not self.running:
            return
        self.running = False
        self.fault_injector.stop()
        with self.tick_condition:
            self.tick_condition.notify_all()
        if self.clock_thread is not None:
            self.clock_thread.join(timeout=2)
        self.fault_injector.join(timeout=2)
        for node in self.nodes.values():
            node.join(timeout=2)
        self.log_event("info", f"[Tick {self.current_tick:02d}] Simulation stopped")

    def _tick_loop(self) -> None:
        while self.running:
            if self.paused:
                time.sleep(0.05)
                continue
            time.sleep(self.tick_duration)
            with self.tick_condition:
                self.current_tick += 1
                self.tick_condition.notify_all()

    def wait_for_tick(self, last_tick: int) -> int | None:
        with self.tick_condition:
            while self.running and self.current_tick <= last_tick:
                self.tick_condition.wait(timeout=0.5)
            if not self.running:
                return None
            return self.current_tick

    def toggle_pause(self) -> bool:
        self.paused = not self.paused
        self.log_event(
            "info",
            f"[Tick {self.current_tick:02d}] Simulation {'paused' if self.paused else 'resumed'}",
        )
        return self.paused

    def deliver_message(self, target_id: str, message: dict[str, object]) -> None:
        target = self.nodes.get(target_id)
        if target is None:
            return
        target.inbox.put(message)
        self.log_message(message)

    def get_live_node_ids(self, exclude_id: str | None = None) -> list[str]:
        live: list[str] = []
        for node_id, node in self.nodes.items():
            if exclude_id and node_id == exclude_id:
                continue
            if node.is_alive():
                live.append(node_id)
        return live

    def get_all_node_ids(self) -> list[str]:
        return list(self.nodes.keys())

    def set_leader(self, node_id: str) -> None:
        self.current_leader = node_id
        for node in self.nodes.values():
            with node.state_lock:
                node.state.is_leader = node.node_id == node_id

    def clear_leader(self) -> None:
        self.current_leader = None
        for node in self.nodes.values():
            with node.state_lock:
                node.state.is_leader = False

    def store_replica(self, node_id: str, snapshot: dict[str, object]) -> None:
        self.replicas[node_id] = snapshot
        self.log_event(
            "replication",
            f"[Tick {self.current_tick:02d}] N8 replicated state for {node_id}",
        )

    def get_replica(self, node_id: str) -> dict[str, object] | None:
        return self.replicas.get(node_id)

    def log_message(self, message: dict[str, object]) -> None:
        payload = dict(message.get("payload", {}))
        summary = self._payload_summary(message["type"], payload)
        with self.log_lock:
            self.messages.append(
                {
                    "type": str(message["type"]),
                    "sender": str(message["sender"]),
                    "receiver": str(message["receiver"]),
                    "lamport_ts": int(message["lamport_ts"]),
                    "summary": summary,
                    "text": (
                        f"[{int(message['lamport_ts']):03d}] {message['sender']} -> "
                        f"{message['receiver']}: {message['type']} {summary}"
                    ),
                }
            )

    def log_event(self, event_type: str, text: str) -> None:
        with self.log_lock:
            self.events.append({"type": event_type, "text": text})

    def _payload_summary(self, message_type: object, payload: dict[str, object]) -> str:
        if message_type == "GOSSIP":
            known_state = payload.get("known_state", {})
            if isinstance(known_state, dict):
                return f"{{merged state, {len(known_state)} nodes}}"
        if message_type == "REQUEST":
            return f"{{reason={payload.get('reason', 'grid-reroute')}}}"
        if message_type == "REPLICATE":
            if "restore" in payload:
                return "{restore from backup}"
            snapshot = payload.get("snapshot", {})
            if isinstance(snapshot, dict):
                return f"{{snapshot={snapshot.get('node_id', 'unknown')}}}"
        if message_type == "ELECTION":
            return f"{{trigger={payload.get('trigger', 'silence')}}}"
        if message_type == "COORDINATOR":
            return f"{{leader={payload.get('leader', 'unknown')}}}"
        return "{}"

    def inject_fault(self, action: str, description: str, manual: bool = False) -> None:
        prefix = "manual fault" if manual else "fault"
        self.log_event("fault", f"[Tick {self.current_tick:02d}] {prefix}: {description}")

        if action == "solar_drop":
            self.flags["solar_drop_until"] = max(self.flags["solar_drop_until"], self.current_tick + 15)
            self.trigger_mutex_request("N3", "rerouting solar shortfall", support_nodes=("N3", "N8"))
            self.trigger_mutex_request("N5", "critical solar shortfall", support_nodes=("N7", "N8"))
            return

        if action == "demand_spike":
            self.flags["demand_spike_until"] = max(self.flags["demand_spike_until"], self.current_tick + 10)
            self.trigger_mutex_request("N5", "balancing demand spike", support_nodes=("N3", "N8"))
            self.trigger_mutex_request("N7", "emergency power draw", support_nodes=("N3", "N8"))
            return

        if action == "node_crash":
            node = self.nodes["N2"]
            node.set_alive(False)
            node.set_power(0.0)
            self.log_event("crash", f"[Tick {self.current_tick:02d}] N2 crashed")
            return

        if action == "node_recover":
            node = self.nodes["N2"]
            node.set_alive(True)
            self.log_event("recovery", f"[Tick {self.current_tick:02d}] N2 recovered")
            self.nodes["N8"].restore_from_backup("N2")
            if self.current_leader:
                leader = self.nodes.get(self.current_leader)
                if leader is not None:
                    leader.broadcast_message("COORDINATOR_DONE", {"leader": self.current_leader})
                    self.log_event(
                        "recovery",
                        f"[Tick {self.current_tick:02d}] {self.current_leader} stepped down after recovery",
                    )
                    self.clear_leader()
            return

        if action == "ev_connect":
            self.flags["ev_connected"] = True
            self.trigger_mutex_request("N6", "safe EV connection", support_nodes=("N3", "N8"))
            return

        if action == "storage_full":
            self.flags["storage_full"] = True
            self.support_until["N8"] = max(self.support_until["N8"], self.current_tick + 20)
            self.log_event(
                "fault",
                f"[Tick {self.current_tick:02d}] N3 reached storage capacity; N8 carrying the remainder",
            )

    def trigger_next_fault(self) -> bool:
        return self.fault_injector.trigger_next()

    def trigger_mutex_request(self, node_id: str, reason: str, support_nodes: tuple[str, ...]) -> None:
        node = self.nodes[node_id]
        node.queue_mutex_request(reason, support_nodes)

    def mark_support(self, node_ids: tuple[str, ...], until_tick: int) -> None:
        for node_id in node_ids:
            self.support_until[node_id] = max(self.support_until.get(node_id, 0), until_tick)

    def status_label(self, balance: float) -> str:
        abs_balance = abs(balance)
        if abs_balance < 1.0:
            return "STABLE"
        if abs_balance < 2.5:
            return "STRESSED"
        return "CRITICAL"

    def snapshot(self) -> SimulationSnapshot:
        nodes = [self.nodes[node_id].snapshot() for node_id, _ in NODE_LAYOUT]
        balance = round(
            sum(float(node["power_output"]) for node in nodes if bool(node["alive"])),
            2,
        )
        convergence_count = self._convergence_count()
        with self.log_lock:
            messages = list(self.messages)[-12:]
            events = list(self.events)[-10:]

        return SimulationSnapshot(
            tick=self.current_tick,
            elapsed=time.monotonic() - self.start_time if self.start_time else 0.0,
            nodes=nodes,
            messages=messages,
            events=events,
            balance=balance,
            status=self.status_label(balance),
            convergence=f"{convergence_count}/8 nodes converged",
            leader=self.current_leader,
            paused=self.paused,
        )

    def _convergence_count(self) -> int:
        canonical: tuple[tuple[str, int], ...] | None = None
        converged = 0
        for node in self.nodes.values():
            known_state = node.export_known_state()
            digest = tuple(
                sorted(
                    (
                        entry_id,
                        int(details.get("lamport_ts", 0)),
                    )
                    for entry_id, details in known_state.items()
                )
            )
            if canonical is None:
                canonical = digest
                converged += 1
            elif digest == canonical:
                converged += 1
        return converged


def build_default_simulation(tick_duration: float = 0.5, seed: int = 7) -> GridSimulation:
    return GridSimulation(tick_duration=tick_duration, seed=seed)
