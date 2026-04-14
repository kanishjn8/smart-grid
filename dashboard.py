from __future__ import annotations

import argparse
import threading
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.engine import GridSimulation, build_default_simulation

WEB_DIR = Path(__file__).parent / "web"


class SimulationController:
    def __init__(self, tick_duration: float, seed: int):
        self.tick_duration = tick_duration
        self.seed = seed
        self._lock = threading.RLock()
        self.simulation: GridSimulation = build_default_simulation(
            tick_duration=tick_duration,
            seed=seed,
        )

    def start(self) -> None:
        with self._lock:
            self.simulation.start()

    def stop(self) -> None:
        with self._lock:
            self.simulation.stop()

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            snapshot = self.simulation.snapshot()
        return asdict(snapshot)

    def toggle_pause(self) -> dict[str, object]:
        with self._lock:
            paused = self.simulation.toggle_pause()
        return {"paused": paused}

    def trigger_fault(self) -> dict[str, object]:
        with self._lock:
            triggered = self.simulation.trigger_next_fault()
        return {"triggered": triggered}

    def reset(self) -> dict[str, object]:
        with self._lock:
            self.simulation.stop()
            self.simulation = build_default_simulation(
                tick_duration=self.tick_duration,
                seed=self.seed,
            )
            self.simulation.start()
            snapshot = self.simulation.snapshot()
        return asdict(snapshot)


def create_app(tick_duration: float = 0.5, seed: int = 7) -> FastAPI:
    controller = SimulationController(tick_duration=tick_duration, seed=seed)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        controller.start()
        try:
            yield
        finally:
            controller.stop()

    app = FastAPI(title="Smart Grid Simulation", lifespan=lifespan)
    app.state.controller = controller
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/state")
    async def state() -> dict[str, object]:
        return controller.snapshot()

    @app.post("/api/control/pause")
    async def pause() -> dict[str, object]:
        return controller.toggle_pause()

    @app.post("/api/control/fault")
    async def fault() -> dict[str, object]:
        return controller.trigger_fault()

    @app.post("/api/control/reset")
    async def reset() -> dict[str, object]:
        return controller.reset()

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Browser-based smart-grid dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--tick-duration", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    uvicorn.run(
        create_app(tick_duration=args.tick_duration, seed=args.seed),
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
