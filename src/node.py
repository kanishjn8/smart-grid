from __future__ import annotations

import math
import queue
import threading
from dataclasses import dataclass, field

from . import election, gossip, mutex, replication
from .lamport import on_receive, on_send


@dataclass
class NodeState:
    node_id: str
    node_type: str
    power_output: float
    lamport_clock: int
    known_state: dict[str, dict[str, object]] = field(default_factory=dict)
    is_leader: bool = False
    in_critical_section: bool = False
    requesting_mutex: bool = False
    alive: bool = True
    deferred_replies: list[str] = field(default_factory=list)
    election_replied: bool = False


class Node(threading.Thread):
    def __init__(self, node_id: str, node_type: str, engine):
        super().__init__(daemon=True, name=f"node-{node_id}")
        self.node_id = node_id
        self.node_type = node_type
        self.engine = engine
        self.inbox: queue.Queue[dict[str, object]] = queue.Queue()
        self.state_lock = threading.Lock()
        self.state = NodeState(
            node_id=node_id,
            node_type=node_type,
            power_output=0.0,
            lamport_clock=0,
        )
        self.last_seen: dict[str, int] = {}
        self.last_tick = 0
        self.request_ts: int | None = None
        self.request_reason = ""
        self.pending_support_nodes: tuple[str, ...] = ()
        self.pending_mutex_reason: str | None = None
        self.mutex_waiting_for: set[str] = set()
        self.critical_section_until: int | None = None
        self.election_in_progress = False
        self.received_higher_alive = False
        self.election_deadline: int | None = None
        self.replication_flash_until = 0

    def run(self) -> None:
        while self.engine.running:
            next_tick = self.engine.wait_for_tick(self.last_tick)
            if next_tick is None:
                break
            self.last_tick = next_tick
            self.execute_tick(next_tick)

    def execute_tick(self, tick: int) -> None:
        self.process_inbox(tick)
        self.update_power_for_tick(tick)
        self.update_own_known_state()
        self.maybe_trigger_scheduled_actions(tick)
        self.maybe_enter_or_release_cs(tick)
        self.maybe_detect_election(tick)
        election.maybe_finalize_election(self, tick)

        if self.is_alive():
            peers = self.engine.get_live_node_ids(exclude_id=self.node_id)
            gossip.gossip_round(self, peers, self.engine.random)
            if tick % 5 == 0:
                replication.replicate_to_backup(self)

    def process_inbox(self, tick: int) -> None:
        while True:
            try:
                msg = self.inbox.get_nowait()
            except queue.Empty:
                return

            self.apply_receive_clock(int(msg["lamport_ts"]))
            sender = str(msg["sender"])
            self.last_seen[sender] = tick

            if not self.is_alive() and str(msg["type"]) not in {"REPLICATE", "COORDINATOR", "COORDINATOR_DONE"}:
                continue

            msg_type = str(msg["type"])
            if msg_type == "GOSSIP":
                payload = dict(msg.get("payload", {}))
                incoming = payload.get("known_state", {})
                if isinstance(incoming, dict):
                    with self.state_lock:
                        gossip.merge_known_state(self.state.known_state, incoming)
                continue

            if msg_type == "REQUEST":
                mutex.handle_request(self, msg)
                continue

            if msg_type == "REPLY":
                self.mutex_waiting_for.discard(sender)
                continue

            if msg_type == "ELECTION":
                election.handle_election_msg(self, msg, self.engine.get_all_node_ids())
                continue

            if msg_type == "ALIVE":
                election.handle_alive(self, msg)
                continue

            if msg_type == "COORDINATOR":
                election.handle_coordinator(self, msg)
                continue

            if msg_type == "COORDINATOR_DONE":
                election.handle_coordinator_done(self, msg)
                continue

            if msg_type == "REPLICATE":
                replication.handle_replicate(self, msg)

    def maybe_trigger_scheduled_actions(self, tick: int) -> None:
        if self.pending_mutex_reason and self.is_alive():
            live_peers = self.engine.get_live_node_ids(exclude_id=self.node_id)
            mutex.request_cs(self, live_peers, self.pending_mutex_reason)
            self.pending_mutex_reason = None

        if self.node_id == "N5" and tick >= 33 and not self.engine.current_leader:
            last_seen = self.last_seen.get("N2", 0)
            if tick - last_seen >= 3 and not self.election_in_progress:
                election.start_election(self, self.engine.get_all_node_ids(), "N2 silence")

    def maybe_enter_or_release_cs(self, tick: int) -> None:
        if self.state.requesting_mutex and not self.mutex_waiting_for and not self.state.in_critical_section:
            with self.state_lock:
                self.state.in_critical_section = True
                self.state.requesting_mutex = False
                self.critical_section_until = tick + 1
            self.engine.mark_support(self.pending_support_nodes, tick + 3)
            self.engine.log_event(
                "mutex",
                f"[Tick {tick:02d}] {self.node_id} acquired MUTEX -> {self.request_reason}",
            )

        if self.state.in_critical_section and self.critical_section_until is not None and tick >= self.critical_section_until:
            mutex.release_cs(self)

    def maybe_detect_election(self, tick: int) -> None:
        if self.node_id != "N5" or not self.is_alive():
            return
        last_seen = self.last_seen.get("N2", tick)
        if tick >= 33 and tick - last_seen >= 3 and not self.engine.current_leader and not self.election_in_progress:
            election.start_election(self, self.engine.get_all_node_ids(), "N2 silence")

    def queue_mutex_request(self, reason: str, support_nodes: tuple[str, ...]) -> None:
        self.pending_mutex_reason = reason
        self.pending_support_nodes = support_nodes

    def restore_from_backup(self, target_id: str) -> None:
        replication.restore_node_from_backup(self, target_id)

    def send_message(self, target_id: str, msg_type: str, payload: dict[str, object]) -> None:
        if not self.is_alive() and msg_type not in {"COORDINATOR_DONE"}:
            return
        lamport_ts = self.bump_clock()
        message = {
            "type": msg_type,
            "sender": self.node_id,
            "receiver": target_id,
            "lamport_ts": lamport_ts,
            "payload": payload,
        }
        self.engine.deliver_message(target_id, message)

    def broadcast_message(self, msg_type: str, payload: dict[str, object]) -> None:
        for target_id in self.engine.get_all_node_ids():
            if target_id == self.node_id:
                continue
            self.send_message(target_id, msg_type, payload)

    def bump_clock(self) -> int:
        with self.state_lock:
            self.state.lamport_clock = on_send(self.state.lamport_clock)
            return self.state.lamport_clock

    def bump_clock_locked(self) -> int:
        self.state.lamport_clock = on_send(self.state.lamport_clock)
        return self.state.lamport_clock

    def apply_receive_clock(self, msg_ts: int) -> None:
        with self.state_lock:
            self.state.lamport_clock = on_receive(self.state.lamport_clock, msg_ts)

    def update_power_for_tick(self, tick: int) -> None:
        if not self.is_alive():
            self.set_power(0.0)
            return

        power = 0.0
        if self.node_id == "N1":
            solar_wave = max(0.2, math.sin((tick / 8.0) + 0.35))
            power = round(3.2 * solar_wave, 1)
            if tick <= self.engine.flags["solar_drop_until"]:
                power = 0.0
        elif self.node_id == "N2":
            power = round(self.engine.random.uniform(0.4, 4.0), 1)
        elif self.node_id == "N3":
            power = 0.0 if self.engine.flags["storage_full"] else 0.5
            if tick <= self.engine.support_until["N3"]:
                power = 2.0
        elif self.node_id == "N4":
            power = -8.0 if tick <= self.engine.flags["demand_spike_until"] else -3.0
        elif self.node_id == "N5":
            power = 0.3
            if tick <= self.engine.support_until["N5"]:
                power = 0.8
        elif self.node_id == "N6":
            power = -3.5 if self.engine.flags["ev_connected"] else 0.0
        elif self.node_id == "N7":
            power = 0.0
            if self.state.is_leader or tick <= self.engine.support_until["N7"]:
                power = 1.2
        elif self.node_id == "N8":
            power = 1.4
            if tick <= self.engine.support_until["N8"]:
                power = 3.0

        self.set_power(round(power, 1))

    def update_own_known_state(self) -> None:
        with self.state_lock:
            self.state.known_state[self.node_id] = {
                "node_type": self.node_type,
                "power_output": self.state.power_output,
                "lamport_ts": self.state.lamport_clock,
                "alive": self.state.alive,
            }

    def export_known_state(self) -> dict[str, dict[str, object]]:
        with self.state_lock:
            return {key: dict(value) for key, value in self.state.known_state.items()}

    def can_participate_in_election(self) -> bool:
        return self.is_alive() and self.node_id != "N8"

    def is_alive(self) -> bool:
        with self.state_lock:
            return self.state.alive

    def set_alive(self, alive: bool) -> None:
        with self.state_lock:
            self.state.alive = alive
            if not alive:
                self.state.power_output = 0.0
                self.state.requesting_mutex = False
                self.state.in_critical_section = False
                self.mutex_waiting_for.clear()

    def set_power(self, power: float) -> None:
        with self.state_lock:
            self.state.power_output = power

    def snapshot(self) -> dict[str, object]:
        with self.state_lock:
            if not self.state.alive:
                status = "CRASHED"
            elif self.state.in_critical_section:
                status = "MUTEX"
            elif self.state.requesting_mutex:
                status = "REQUESTING"
            elif self.state.is_leader:
                status = "LEADER"
            else:
                status = "ONLINE"

            return {
                "node_id": self.node_id,
                "node_type": self.node_type,
                "power_output": self.state.power_output,
                "lamport_clock": self.state.lamport_clock,
                "alive": self.state.alive,
                "is_leader": self.state.is_leader,
                "in_critical_section": self.state.in_critical_section,
                "requesting_mutex": self.state.requesting_mutex,
                "status": status,
                "replicating": self.engine.current_tick < self.replication_flash_until,
                "known_state_size": len(self.state.known_state),
            }
