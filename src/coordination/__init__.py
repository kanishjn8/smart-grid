"""Single simulated actuator authority; no distributed quorum or production safety claim."""
from __future__ import annotations
import random
from dataclasses import dataclass
from src.domain import DispatchPlan


class AuthorityGate:
    def __init__(self, timeout_rounds: int = 3):
        if timeout_rounds < 1:
            raise ValueError("positive timeout required")
        self.timeout = timeout_rounds
        self.epoch = 1
        self.last_heartbeat = 0
        self.last_sequence = -1
        self.events: list[dict] = []

    def heartbeat(self, round_: int):
        self.last_heartbeat = round_

    def failover(self, round_: int) -> bool:
        if round_ - self.last_heartbeat < self.timeout:
            return False
        self.epoch += 1
        self.last_sequence = -1
        self.last_heartbeat = round_
        self.events.append({"round": round_, "epoch": self.epoch, "event": "actuator grants replacement epoch"})
        return True

    def accept(self, plan: DispatchPlan, round_: int, connected: bool = True) -> tuple[bool, str]:
        if not connected:
            return False, "communication unavailable: local fallback"
        if plan.epoch != self.epoch:
            return False, "stale controller epoch"
        if plan.issued_round > round_ or plan.expires_round < round_:
            return False, "expired or future command"
        if plan.sequence <= self.last_sequence:
            return False, "duplicate or reordered command"
        self.last_sequence = plan.sequence
        return True, "accepted by simulated actuator"


@dataclass(frozen=True)
class Packet:
    delivery_round: int
    sequence: int
    payload: DispatchPlan


class Transport:
    def __init__(self, seed: int, loss: float = 0, delay_rounds: int = 0, duplicate: float = 0):
        if not 0 <= loss <= 1 or not 0 <= duplicate <= 1 or delay_rounds < 0:
            raise ValueError("invalid transport parameters")
        self.rng = random.Random(seed+1000003)
        self.loss, self.delay, self.duplicate = loss, delay_rounds, duplicate
        self.queue: list[Packet] = []

    def send(self, plan: DispatchPlan, round_: int, partition: bool = False):
        if partition or self.rng.random() < self.loss:
            return
        count = 2 if self.rng.random() < self.duplicate else 1
        for _ in range(count):
            self.queue.append(Packet(round_+self.rng.randint(0, self.delay), plan.sequence, plan))

    def receive(self, round_: int):
        ready = [p for p in self.queue if p.delivery_round <= round_]
        self.queue = [p for p in self.queue if p.delivery_round > round_]
        return [p.payload for p in sorted(ready, key=lambda p: (p.delivery_round, -p.sequence))]


class TelemetryStore:
    """Optional telemetry exchange; origin sequence wins, receipt time cannot refresh old data."""
    def __init__(self):
        self.samples: dict[str, tuple[int, int, dict]] = {}

    def merge(self, origin: str, sequence: int, sampled_round: int, payload: dict) -> bool:
        from copy import deepcopy
        previous = self.samples.get(origin)
        if sequence < 0 or sampled_round < 0 or (previous and sequence <= previous[0]):
            return False
        self.samples[origin] = (sequence, sampled_round, deepcopy(payload))
        return True

    def read(self, origin: str, round_: int, max_age_rounds: int) -> dict | None:
        from copy import deepcopy
        sample = self.samples.get(origin)
        if not sample or not 0 <= round_-sample[1] <= max_age_rounds:
            return None
        return deepcopy(sample[2])
