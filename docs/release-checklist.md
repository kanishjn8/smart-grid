# Local verification — 2026-10-01

- `uv run --frozen python -m unittest discover -s tests -v`: 24 tests passed.
- `uv run --frozen python evaluate.py --seeds 10 --sensitivity`: completed all seven scenarios, seeds 100–109, sensitivity and ablation exports.
- Current dashboard and health route checked through FastAPI TestClient; legacy routes return 404.
- Generated report: `results/latest/report.md`. Complete seed-100 traces and manifests, all-seed metrics, summaries and portable replay regenerated.
- Reliability time metrics checked against a hand-calculated fixture; physical invariants, forecast leakage, deterministic replay, consent, authority and API lifecycle covered by the current suite.
- Fresh-machine installation, visual browser review, physical validation and organizer submission checks were not performed in this change.
