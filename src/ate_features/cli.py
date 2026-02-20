"""CLI for the Agent Teams Eval (Feature Implementation) experiment."""

from __future__ import annotations

import typer

app = typer.Typer(help="Agent Teams Eval: feature implementation in LangGraph")
comms_app = typer.Typer(help="Communication analysis")
exec_app = typer.Typer(help="Execution management")
app.add_typer(comms_app, name="comms")
app.add_typer(exec_app, name="exec")


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


@exec_app.command("scaffold")
def exec_scaffold(
    treatment_id: str,
) -> None:
    """Scaffold session directories for a treatment."""
    from ate_features.harness import scaffold_treatment

    # Parse treatment_id: try int first, fall back to string
    tid: int | str
    try:
        tid = int(treatment_id)
    except ValueError:
        tid = treatment_id

    paths = scaffold_treatment(tid)
    typer.echo(f"Scaffolded {len(paths)} files:")
    for p in paths:
        typer.echo(f"  {p}")


@exec_app.command("status")
def exec_status() -> None:
    """Show 11x8 completion matrix for all treatments."""
    from ate_features.config import load_features, load_treatments
    from ate_features.harness import get_patch_path

    features = load_features().features
    treatments = load_treatments().treatments

    # Header
    feat_ids = [f.id for f in features]
    header = f"{'Treatment':<20}" + "".join(f"{fid:>6}" for fid in feat_ids)
    typer.echo(header)
    typer.echo("-" * len(header))

    for t in treatments:
        row = f"{t.id!s:<20}"
        for f in features:
            patch = get_patch_path(t.id, f.id)
            row += f"{'  ✓' if patch.exists() else '  ·':>6}"
        typer.echo(row)
