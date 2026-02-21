"""CLI for the Agent Teams Eval (Feature Implementation) experiment."""

from __future__ import annotations

import typer

app = typer.Typer(help="Agent Teams Eval: feature implementation in LangGraph")
comms_app = typer.Typer(help="Communication analysis")
exec_app = typer.Typer(help="Execution management")
score_app = typer.Typer(help="Scoring and analysis")
app.add_typer(comms_app, name="comms")
app.add_typer(exec_app, name="exec")
app.add_typer(score_app, name="score")


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


@exec_app.command("preflight")
def exec_preflight(
    langgraph_dir: str = "data/langgraph",
) -> None:
    """Run preflight checks on the LangGraph directory."""
    from pathlib import Path

    from ate_features.config import load_features
    from ate_features.harness import preflight_check

    lg_path = Path(langgraph_dir)
    portfolio = load_features()

    result = preflight_check(lg_path, expected_pin=portfolio.langgraph_pin)

    if result.issues:
        typer.echo("Preflight FAILED:")
        for issue in result.issues:
            typer.echo(f"  - {issue}")
    else:
        typer.echo("Preflight PASSED")

    typer.echo(f"Claude Code version: {result.claude_code_version}")


@exec_app.command("verify-patches")
def exec_verify_patches(
    treatment_id: str,
    langgraph_dir: str | None = None,
) -> None:
    """Verify patch files for a treatment (F1-F8)."""
    from pathlib import Path

    from ate_features.harness import verify_patches

    tid = _parse_tid(treatment_id)
    lg_path = Path(langgraph_dir) if langgraph_dir else None

    result = verify_patches(tid, langgraph_dir=lg_path)

    for fid, status in sorted(result.items()):
        typer.echo(f"  {fid}: {status.value}")

    valid = sum(1 for s in result.values() if s.value == "valid")
    total = len(result)
    typer.echo(f"\n{valid}/{total} valid patches")


@exec_app.command("runbook")
def exec_runbook(
    treatment_id: str,
    mode: str = typer.Option("isolated", help="Scoring mode: isolated or cumulative"),
) -> None:
    """Generate and print a runbook for one treatment."""
    from ate_features.config import load_features, load_treatments
    from ate_features.runbook import generate_runbook

    tid = _parse_tid(treatment_id)
    config = load_treatments()
    treatment = next(t for t in config.treatments if t.id == tid)
    features = load_features().features

    runbook = generate_runbook(
        treatment,
        features,
        assignments=config.feature_assignments.explicit,
        scoring_mode=mode,
    )
    typer.echo(runbook)


@exec_app.command("runbooks")
def exec_runbooks(
    output_dir: str = "docs/runbooks",
    mode: str = typer.Option("isolated", help="Scoring mode: isolated or cumulative"),
) -> None:
    """Generate all 11 runbooks to docs/runbooks/."""
    from pathlib import Path

    from ate_features.runbook import generate_all_runbooks, save_runbooks

    runbooks = generate_all_runbooks(scoring_mode=mode)
    paths = save_runbooks(runbooks, Path(output_dir))
    typer.echo(f"Generated {len(paths)} runbooks:")
    for p in paths:
        typer.echo(f"  {p}")


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


# --- Score Commands ---


def _parse_tid(treatment_id: str) -> int | str:
    """Parse treatment_id: try int first, fall back to string."""
    try:
        return int(treatment_id)
    except ValueError:
        return treatment_id


def _load_weights() -> dict[str, float]:
    """Load scoring weights from config."""
    from ate_features.config import load_scoring_config

    config = load_scoring_config()
    raw_weights = config.get("weights")
    if not isinstance(raw_weights, dict):
        msg = "scoring.yaml missing 'weights' dict"
        raise ValueError(msg)
    return {str(k): float(v) for k, v in raw_weights.items()}


@score_app.command("collect")
def score_collect(
    treatment_id: str,
    langgraph_dir: str = "data/langgraph",
    mode: str = typer.Option("isolated", help="Scoring mode: isolated or cumulative"),
) -> None:
    """Collect scores by applying patches and running acceptance tests."""
    from pathlib import Path

    from ate_features.scoring import collect_scores

    tid = _parse_tid(treatment_id)
    lg_path = Path(langgraph_dir)

    if not lg_path.exists():
        typer.echo(f"LangGraph directory not found: {lg_path}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Collecting scores for treatment {tid} (mode={mode})...")
    scores = collect_scores(tid, lg_path, mode=mode)

    if not scores:
        typer.echo("No patches found — nothing to score.")
        return

    typer.echo(f"Scored {len(scores)} features:")
    for s in scores:
        typer.echo(
            f"  {s.feature_id}: T1={s.t1_passed}/{s.t1_total} "
            f"T2={s.t2_passed}/{s.t2_total} "
            f"T3={s.t3_passed}/{s.t3_total} "
            f"T4={s.t4_passed}/{s.t4_total}"
        )


@score_app.command("show")
def score_show(
    treatment_id: str | None = typer.Argument(None),
) -> None:
    """Display scores for a treatment (or all treatments)."""
    from ate_features.scoring import (
        load_all_scores,
        load_scores,
        summarize_treatment,
    )

    weights = _load_weights()

    if treatment_id is not None:
        tid = _parse_tid(treatment_id)
        try:
            scores = load_scores(tid)
        except FileNotFoundError:
            typer.echo(f"No scores found for treatment {tid}.", err=True)
            raise typer.Exit(1)
        summary = summarize_treatment(scores, weights)
        _print_treatment_summary(tid, summary)
    else:
        all_scores = load_all_scores()
        if not all_scores:
            typer.echo("No scores collected yet.")
            return
        for tid_str, scores in sorted(all_scores.items()):
            summary = summarize_treatment(scores, weights)
            _print_treatment_summary(tid_str, summary)
            typer.echo("")


def _print_treatment_summary(
    tid: int | str,
    summary: dict[str, object],
) -> None:
    """Print a formatted treatment summary."""
    typer.echo(f"Treatment {tid}:")
    typer.echo(f"  Features scored: {summary['n_features']}")
    mean_c = float(str(summary["mean_composite"]))
    min_c = float(str(summary["min_composite"]))
    max_c = float(str(summary["max_composite"]))
    typer.echo(f"  Mean composite:  {mean_c:.4f}")
    typer.echo(f"  Min composite:   {min_c:.4f}")
    typer.echo(f"  Max composite:   {max_c:.4f}")
    per_feature = summary.get("per_feature")
    if isinstance(per_feature, dict) and per_feature:
        typer.echo("  Per feature:")
        for fid, score in sorted(per_feature.items()):
            typer.echo(f"    {fid}: {float(str(score)):.4f}")


@score_app.command("decide-wave2")
def score_decide_wave2() -> None:
    """Evaluate the Wave 2 decision gate."""
    from ate_features.config import load_scoring_config
    from ate_features.scoring import evaluate_wave2, load_all_scores

    config = load_scoring_config()
    weights = _load_weights()
    cv_threshold = float(str(config.get("wave2_cv_threshold", 0.10)))

    all_scores = load_all_scores()
    if not all_scores:
        typer.echo("No scores collected yet — cannot evaluate Wave 2.")
        raise typer.Exit(1)

    _recommend, reasoning = evaluate_wave2(all_scores, weights, cv_threshold)
    typer.echo(reasoning)
