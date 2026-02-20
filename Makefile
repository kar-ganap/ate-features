.PHONY: test test-all test-int lint typecheck pin-langgraph

test:
	uv run pytest tests/unit/ -v

test-all:
	uv run pytest tests/ -v

test-int:
	uv run pytest tests/integration/ -v

lint:
	uv run ruff check src/ tests/

typecheck:
	uv run mypy src/ate_features/

pin-langgraph:
	bash scripts/pin_langgraph.sh
