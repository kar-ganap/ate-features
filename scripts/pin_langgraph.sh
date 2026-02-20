#!/usr/bin/env bash
set -euo pipefail

# Pin LangGraph to a specific commit for reproducibility.
# Usage: bash scripts/pin_langgraph.sh

LANGGRAPH_REPO="https://github.com/langchain-ai/langgraph.git"
LANGGRAPH_PIN="b0f14649e0669a6399cb790d23672591a2a52884"
TARGET_DIR="data/langgraph"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FULL_TARGET="$PROJECT_ROOT/$TARGET_DIR"

if [ -d "$FULL_TARGET/.git" ]; then
    echo "LangGraph repo already exists at $FULL_TARGET"
    echo "Checking out pinned commit..."
    git -C "$FULL_TARGET" checkout "$LANGGRAPH_PIN"
else
    echo "Cloning LangGraph..."
    git clone "$LANGGRAPH_REPO" "$FULL_TARGET"
    echo "Checking out pinned commit..."
    git -C "$FULL_TARGET" checkout "$LANGGRAPH_PIN"
fi

echo "LangGraph pinned to $LANGGRAPH_PIN"
