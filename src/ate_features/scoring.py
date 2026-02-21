"""Scoring framework for collecting and analyzing treatment results."""

from __future__ import annotations

import json
import math
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from ate_features.models import TieredScore

# Tier class name patterns in acceptance tests
_TIER_PATTERNS: dict[str, str] = {
    "t1": "TestT1",
    "t2": "TestT2",
    "t3": "TestT3",
    "t4": "TestT4",
}


def parse_junit_xml(
    xml_path: Path,
    feature_id: str,
    treatment_id: int | str,
) -> TieredScore:
    """Parse a JUnit XML report into a TieredScore.

    Identifies tiers by test class name patterns (TestT1Basic, TestT2EdgeCases, etc.).
    Tests with <failure> or <error> elements count as failed.
    """
    tree = ET.parse(xml_path)  # noqa: S314
    root = tree.getroot()

    tier_totals: dict[str, int] = {"t1": 0, "t2": 0, "t3": 0, "t4": 0}
    tier_passed: dict[str, int] = {"t1": 0, "t2": 0, "t3": 0, "t4": 0}

    for testcase in root.iter("testcase"):
        classname = testcase.get("classname", "")
        tier = _classify_tier(classname)
        if tier is None:
            continue

        tier_totals[tier] += 1
        has_failure = testcase.find("failure") is not None
        has_error = testcase.find("error") is not None
        if not has_failure and not has_error:
            tier_passed[tier] += 1

    return TieredScore(
        feature_id=feature_id,
        treatment_id=treatment_id,
        t1_passed=tier_passed["t1"],
        t1_total=tier_totals["t1"],
        t2_passed=tier_passed["t2"],
        t2_total=tier_totals["t2"],
        t3_passed=tier_passed["t3"],
        t3_total=tier_totals["t3"],
        t4_passed=tier_passed["t4"],
        t4_total=tier_totals["t4"],
    )


def _classify_tier(classname: str) -> str | None:
    """Map a test class name to a tier key (t1-t4) or None."""
    for tier, pattern in _TIER_PATTERNS.items():
        if pattern in classname:
            return tier
    return None


# --- Persistence ---

_DEFAULT_DATA_DIR = Path(__file__).parent.parent.parent / "data"


def save_scores(
    scores: list[TieredScore],
    treatment_id: int | str,
    *,
    data_dir: Path = _DEFAULT_DATA_DIR,
) -> Path:
    """Persist a list of TieredScores to data/scores/treatment-{id}.json."""
    scores_dir = data_dir / "scores"
    scores_dir.mkdir(parents=True, exist_ok=True)
    path = scores_dir / f"treatment-{treatment_id}.json"
    data = [s.model_dump(mode="json") for s in scores]
    path.write_text(json.dumps(data, indent=2))
    return path


def load_scores(
    treatment_id: int | str,
    *,
    data_dir: Path = _DEFAULT_DATA_DIR,
) -> list[TieredScore]:
    """Load TieredScores for a treatment from JSON."""
    path = data_dir / "scores" / f"treatment-{treatment_id}.json"
    if not path.exists():
        msg = f"No scores found for treatment {treatment_id} at {path}"
        raise FileNotFoundError(msg)
    data = json.loads(path.read_text())
    return [TieredScore(**entry) for entry in data]


def load_all_scores(
    *,
    data_dir: Path = _DEFAULT_DATA_DIR,
) -> dict[str, list[TieredScore]]:
    """Load all treatment score files from data/scores/.

    Returns a dict keyed by treatment_id (as string).
    """
    scores_dir = data_dir / "scores"
    if not scores_dir.exists():
        return {}

    result: dict[str, list[TieredScore]] = {}
    for path in sorted(scores_dir.glob("treatment-*.json")):
        match = re.match(r"treatment-(.+)\.json$", path.name)
        if match:
            tid = match.group(1)
            data = json.loads(path.read_text())
            result[tid] = [TieredScore(**entry) for entry in data]
    return result


# --- Collection Pipeline ---


def collect_scores(
    treatment_id: int | str,
    langgraph_dir: Path,
    *,
    data_dir: Path = _DEFAULT_DATA_DIR,
) -> list[TieredScore]:
    """Collect scores by applying patches, running tests, and parsing results.

    For each feature with a patch file:
    1. Apply the patch to langgraph_dir
    2. Run pytest with --junitxml
    3. Parse the XML into a TieredScore
    4. Revert langgraph_dir

    Persists results to data/scores/treatment-{id}.json.
    Returns list of TieredScores (one per feature with a patch).
    """
    patch_dir = data_dir / "patches" / f"treatment-{treatment_id}"
    if not patch_dir.exists():
        return []

    scores: list[TieredScore] = []
    for patch_path in sorted(patch_dir.glob("*.patch")):
        feature_id = patch_path.stem

        # Apply patch (--check first)
        check = subprocess.run(
            ["git", "apply", "--check", str(patch_path)],
            cwd=langgraph_dir,
            capture_output=True,
        )
        if check.returncode != 0:
            continue

        subprocess.run(
            ["git", "apply", str(patch_path)],
            cwd=langgraph_dir,
            capture_output=True,
        )

        try:
            # Run pytest with junitxml output
            xml_path = data_dir / "scores" / "tmp" / f"{feature_id}.xml"
            xml_path.parent.mkdir(parents=True, exist_ok=True)

            subprocess.run(
                [
                    "pytest",
                    f"tests/acceptance/test_{feature_id.lower()}_*.py",
                    f"--junitxml={xml_path}",
                    "-q",
                ],
                cwd=langgraph_dir,
                capture_output=True,
            )

            if xml_path.exists():
                score = parse_junit_xml(xml_path, feature_id, treatment_id)
                scores.append(score)
        finally:
            # Always revert
            subprocess.run(
                ["git", "checkout", "."],
                cwd=langgraph_dir,
                capture_output=True,
            )
            subprocess.run(
                ["git", "clean", "-fd"],
                cwd=langgraph_dir,
                capture_output=True,
            )

    if scores:
        save_scores(scores, treatment_id, data_dir=data_dir)

    return scores


# --- Aggregation ---


def summarize_treatment(
    scores: list[TieredScore],
    weights: dict[str, float],
) -> dict[str, object]:
    """Compute per-treatment summary statistics.

    Returns dict with treatment_id, n_features, mean/min/max composite,
    and per_feature composite dict.
    """
    if not scores:
        return {
            "treatment_id": None,
            "n_features": 0,
            "mean_composite": 0.0,
            "min_composite": 0.0,
            "max_composite": 0.0,
            "per_feature": {},
        }

    per_feature: dict[str, float] = {}
    for s in scores:
        per_feature[s.feature_id] = s.composite(weights)

    composites = list(per_feature.values())
    return {
        "treatment_id": str(scores[0].treatment_id),
        "n_features": len(scores),
        "mean_composite": sum(composites) / len(composites),
        "min_composite": min(composites),
        "max_composite": max(composites),
        "per_feature": per_feature,
    }


def summarize_all(
    all_scores: dict[str, list[TieredScore]],
    weights: dict[str, float],
) -> dict[str, dict[str, object]]:
    """Compute summaries for all treatments."""
    return {
        tid: summarize_treatment(scores, weights)
        for tid, scores in all_scores.items()
    }


# --- Wave 2 Decision Gate ---


def evaluate_wave2(
    all_scores: dict[str, list[TieredScore]],
    weights: dict[str, float],
    cv_threshold: float,
) -> tuple[bool, str]:
    """Evaluate whether Wave 2 is recommended based on treatment variance.

    Computes coefficient of variation (CV) of mean composite scores
    across treatments. If CV > threshold, recommends Wave 2.

    Returns (recommend, reasoning).
    """
    if not all_scores:
        return False, "No scores available — insufficient data for decision."

    summaries = summarize_all(all_scores, weights)
    means: list[float] = [
        float(s["mean_composite"]) for s in summaries.values()  # type: ignore[arg-type]
    ]

    grand_mean = sum(means) / len(means)
    if grand_mean == 0.0:
        return False, (
            f"All treatments scored 0.0 — no variance to analyze. "
            f"CV threshold: {cv_threshold:.2f}."
        )

    variance = sum((m - grand_mean) ** 2 for m in means) / len(means)
    std = math.sqrt(variance)
    cv = std / grand_mean

    recommend = cv > cv_threshold
    action = "RECOMMEND Wave 2" if recommend else "DO NOT recommend Wave 2"

    reasoning = (
        f"{action}. "
        f"CV = {cv:.4f} ({'>' if recommend else '<='} threshold {cv_threshold:.2f}). "
        f"Mean composite across {len(means)} treatments: {grand_mean:.4f} "
        f"(min={min(means):.4f}, max={max(means):.4f}, SD={std:.4f})."
    )

    return recommend, reasoning
