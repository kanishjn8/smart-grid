from __future__ import annotations

import time
import unittest

from fastapi.testclient import TestClient

from dashboard import create_app
from src.engine import build_default_simulation
from src.gossip import merge_known_state
from src.lamport import on_receive, on_send


class LamportTests(unittest.TestCase):
    def test_on_send_increments_clock(self) -> None:
        self.assertEqual(on_send(4), 5)

    def test_on_receive_obeys_max_plus_one(self) -> None:
        self.assertEqual(on_receive(4, 10), 11)
        self.assertEqual(on_receive(12, 10), 13)


class GossipTests(unittest.TestCase):
    def test_merge_known_state_prefers_higher_timestamp(self) -> None:
        local_state = {"N1": {"power_output": 1.0, "lamport_ts": 5}}
        incoming_state = {"N1": {"power_output": 2.0, "lamport_ts": 8}}
        changed = merge_known_state(local_state, incoming_state)
        self.assertTrue(changed)
        self.assertEqual(local_state["N1"]["power_output"], 2.0)


class SimulationSmokeTests(unittest.TestCase):
    def test_simulation_advances_and_records_faults(self) -> None:
        sim = build_default_simulation(tick_duration=0.02, seed=3)
        sim.start()
        try:
            deadline = time.time() + 1.5
            snapshot = sim.snapshot()
            while time.time() < deadline:
                snapshot = sim.snapshot()
                if snapshot.tick >= 12 and any("cloud cover" in event["text"] for event in snapshot.events):
                    break
                time.sleep(0.02)
            self.assertGreaterEqual(snapshot.tick, 10)
            self.assertTrue(any("cloud cover" in event["text"] for event in snapshot.events))
            self.assertGreater(len(snapshot.messages), 0)
        finally:
            sim.stop()

    def test_manual_fault_trigger_advances_schedule(self) -> None:
        sim = build_default_simulation(tick_duration=0.02, seed=5)
        sim.start()
        try:
            self.assertTrue(sim.trigger_next_fault())
            time.sleep(0.1)
            snapshot = sim.snapshot()
            self.assertTrue(any("manual fault" in event["text"] for event in snapshot.events))
        finally:
            sim.stop()


class ApiSmokeTests(unittest.TestCase):
    def test_state_endpoint_returns_snapshot(self) -> None:
        app = create_app(tick_duration=0.02, seed=2)
        with TestClient(app) as client:
            response = client.get("/api/state")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertIn("nodes", payload)
            self.assertIn("messages", payload)
            self.assertIn("paused", payload)

    def test_control_endpoints_work(self) -> None:
        app = create_app(tick_duration=0.02, seed=4)
        with TestClient(app) as client:
            pause_response = client.post("/api/control/pause")
            self.assertEqual(pause_response.status_code, 200)
            self.assertIn("paused", pause_response.json())

            fault_response = client.post("/api/control/fault")
            self.assertEqual(fault_response.status_code, 200)
            self.assertIn("triggered", fault_response.json())

            reset_response = client.post("/api/control/reset")
            self.assertEqual(reset_response.status_code, 200)
            self.assertIn("tick", reset_response.json())


if __name__ == "__main__":
    unittest.main()
