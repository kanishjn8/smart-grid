.PHONY: setup run test evaluate demo
setup:
	uv sync --frozen
run:
	uv run --frozen python dashboard.py
test:
	uv run --frozen python -m unittest discover -s tests -v
evaluate:
	uv run --frozen python evaluate.py --seeds 10 --sensitivity
demo:
	uv run --frozen python evaluate.py --seeds 1
