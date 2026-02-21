"""Scoring framework for collecting and analyzing treatment results."""

from __future__ import annotations

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
