from __future__ import annotations

import threading

FAULT_SCHEDULE = [
    (10, "solar_drop", "N1 power -> 0.0kW (cloud cover)"),
    (20, "demand_spike", "N4 consumption -> -6.0kW (spike)"),
    (30, "node_crash", "N2 Wind node crashes"),
    (45, "node_recover", "N2 Wind node recovers"),
    (55, "ev_connect", "N6 EV connects, draws -2.0kW"),
    (65, "storage_full", "N3 Storage at capacity, stops discharging"),
]


class FaultInjector(threading.Thread):
    def __init__(self, engine, schedule=None):
        super().__init__(daemon=True, name="fault-injector")
        self.engine = engine
        self.schedule = list(schedule or FAULT_SCHEDULE)
        self.index = 0
        self.stop_event = threading.Event()

    def run(self) -> None:
        while not self.stop_event.is_set():
            current_tick = self.engine.current_tick
            while self.index < len(self.schedule) and self.schedule[self.index][0] <= current_tick:
                _, action, description = self.schedule[self.index]
                self.engine.inject_fault(action, description)
                self.index += 1
            self.stop_event.wait(0.1)

    def stop(self) -> None:
        self.stop_event.set()

    def trigger_next(self) -> bool:
        if self.index >= len(self.schedule):
            return False
        _, action, description = self.schedule[self.index]
        self.engine.inject_fault(action, description, manual=True)
        self.index += 1
        return True
