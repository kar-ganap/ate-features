#!/usr/bin/env bash
set -euo pipefail

# Install pinned LangGraph libs in editable mode.
# Requires: pin_langgraph.sh has been run first.
# Usage: bash scripts/setup_langgraph.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LG_DIR="$PROJECT_ROOT/data/langgraph"

if [ ! -d "$LG_DIR/.git" ]; then
    echo "Error: LangGraph not found at $LG_DIR"
    echo "Run 'make pin-langgraph' first."
    exit 1
fi

echo "Installing LangGraph libs in editable mode..."
uv pip install -e "$LG_DIR/libs/checkpoint" -e "$LG_DIR/libs/langgraph"

echo "LangGraph installed. Verify with: python -c 'import langgraph; print(langgraph.__version__)'"
