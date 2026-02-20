"""CLI for the Agent Teams Eval (Feature Implementation) experiment."""

from __future__ import annotations

import typer

app = typer.Typer(help="Agent Teams Eval: feature implementation in LangGraph")
comms_app = typer.Typer(help="Communication analysis")
app.add_typer(comms_app, name="comms")


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


@comms_app.command("parse")
def comms_parse(session_id: str) -> None:
    """Parse a transcript and show communication events."""
    from ate_features.communication import get_transcript_dir, parse_transcript

    transcript_dir = get_transcript_dir()
    transcript_path = transcript_dir / f"{session_id}.jsonl"

    if not transcript_path.exists():
        typer.echo(f"Transcript not found: {transcript_path}", err=True)
        raise typer.Exit(1)

    events = parse_transcript(transcript_path)
    typer.echo(f"Found {len(events)} communication events")
    for event in events:
        typer.echo(
            f"  [{event.timestamp}] {event.sender} -> {event.recipient}: "
            f"{event.content[:80]}"
        )


@comms_app.command("summary")
def comms_summary(session_id: str, treatment_id: str) -> None:
    """Show communication summary for a session."""
    from ate_features.communication import (
        get_transcript_dir,
        parse_transcript,
        summarize_communication,
    )

    transcript_dir = get_transcript_dir()
    transcript_path = transcript_dir / f"{session_id}.jsonl"

    if not transcript_path.exists():
        typer.echo(f"Transcript not found: {transcript_path}", err=True)
        raise typer.Exit(1)

    events = parse_transcript(transcript_path)
    summary = summarize_communication(events, treatment_id, session_id)

    typer.echo(f"Treatment: {summary.treatment_id}")
    typer.echo(f"Total events: {summary.total_events}")
    typer.echo(f"Unique senders: {summary.unique_senders}")
    typer.echo(f"Unique recipients: {summary.unique_recipients}")
    typer.echo(f"Unique pairs: {summary.unique_pairs}")
    if summary.events_by_taxonomy:
        typer.echo("Taxonomy breakdown:")
        for tax, count in sorted(summary.events_by_taxonomy.items()):
            typer.echo(f"  {tax}: {count}")
