"""CLI for the Agent Teams Eval (Feature Implementation) experiment."""

from __future__ import annotations

import typer

app = typer.Typer(help="Agent Teams Eval: feature implementation in LangGraph")


@app.command()
def info() -> None:
    """Show experiment configuration summary."""
    from ate_features.config import load_features, load_treatments

    portfolio = load_features()
    treatments = load_treatments()

    typer.echo(f"LangGraph pin: {portfolio.langgraph_pin}")
    typer.echo(f"Features: {len(portfolio.features)}")
    typer.echo(f"Treatments: {len(treatments.treatments)}")
    typer.echo(f"Correlation pairs: {len(treatments.correlation_pairs)}")
