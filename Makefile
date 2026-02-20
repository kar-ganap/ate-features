.PHONY: test test-all test-int test-acceptance lint typecheck pin-langgraph setup-langgraph

test:
	uv run pytest tests/unit/ -v

test-all:
	uv run pytest tests/ -v

test-int:
	uv run pytest tests/integration/ -v

test-acceptance:
	uv run pytest tests/acceptance/ -v --timeout=60

lint:
	uv run ruff check src/ tests/

typecheck:
	uv run mypy src/ate_features/

pin-langgraph:
	bash scripts/pin_langgraph.sh

setup-langgraph:
	bash scripts/setup_langgraph.sh
