#!/usr/bin/env python3
"""
Generate validation report and update VALIDATION.md.

Usage:
    python3 validation/scripts/generate_report.py --results results.json
    python3 validation/scripts/generate_report.py --run --org Vivint-DevInt
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


VALIDATION_DIR = Path(__file__).parent.parent
VALIDATION_MD_PATH = VALIDATION_DIR / "VALIDATION.md"
REGISTRY_PATH = VALIDATION_DIR / "scenario_registry.json"


def load_registry() -> dict:
    """Load scenario registry."""
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def calculate_scores(results: list, registry: dict) -> dict:
    """Calculate tier and total scores."""
    tiers_config = registry.get("tiers", {})
    scores = {}
    total_score = 0
    max_score = 0

    for result in results:
        tier = result["tier"]
        tier_config = tiers_config.get(tier, {})
        weight = tier_config.get("weight", 0)

        if result["total"] > 0:
            pass_rate = result["passed"] / result["total"]
            score = pass_rate * weight
        else:
            score = 0

        scores[tier] = {
            "score": score,
            "max": weight,
            "passed": result["passed"],
            "failed": result["failed"],
            "skipped": result["skipped"],
        }

        total_score += score
        max_score += weight

    scores["total"] = {
        "score": total_score,
        "max": max_score,
        "percentage": (total_score / max_score * 100) if max_score > 0 else 0
    }

    return scores


def generate_status_badge(scores: dict, registry: dict) -> str:
    """Generate status badge text."""
    pct = scores["total"]["percentage"]
    pass_threshold = registry.get("pass_threshold", 80)
    warn_threshold = registry.get("warn_threshold", 70)

    if pct >= pass_threshold:
        return "🟢 PASS"
    elif pct >= warn_threshold:
        return "🟡 WARN"
    else:
        return "🔴 FAIL"


def generate_run_entry(results: list, scores: dict, registry: dict, org: str) -> str:
    """Generate a validation run entry for VALIDATION.md."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    tiers_config = registry.get("tiers", {})

    lines = [
        f"### Run - {timestamp}",
        "",
        f"**Org:** {org}",
        f"**Status:** {generate_status_badge(scores, registry)}",
        "",
        "| Tier | Score | Status | Notes |",
        "|------|-------|--------|-------|",
    ]

    for tier in ["T1", "T2", "T3", "T4", "T5"]:
        tier_scores = scores.get(tier, {"score": 0, "max": 0, "passed": 0, "failed": 0})
        tier_config = tiers_config.get(tier, {})
        max_score = tier_config.get("weight", 0)

        if tier_scores["failed"] == 0 and tier_scores["passed"] > 0:
            status = "✅"
        elif tier_scores["passed"] == 0 and tier_scores["failed"] == 0:
            status = "⏳"
        else:
            status = "❌"

        notes = ""
        if tier_scores["skipped"] > 0:
            notes = f"{tier_scores['skipped']} skipped"

        lines.append(
            f"| {tier} | {tier_scores['score']:.0f}/{max_score} | {status} | {notes} |"
        )

    total = scores["total"]
    lines.append(f"| **Total** | **{total['score']:.0f}/{total['max']}** | "
                 f"**{total['percentage']:.0f}%** | |")
    lines.append("")

    return "\n".join(lines)


def update_validation_md(new_entry: str, scores: dict, registry: dict):
    """Update VALIDATION.md with new results."""
    if not VALIDATION_MD_PATH.exists():
        print(f"Error: {VALIDATION_MD_PATH} not found")
        return False

    content = VALIDATION_MD_PATH.read_text()

    # Update current status section
    status_badge = generate_status_badge(scores, registry)
    total = scores["total"]

    # Update Last Validation
    content = re.sub(
        r"\| Last Validation \| .* \|",
        f"| Last Validation | {datetime.now().strftime('%Y-%m-%d')} |",
        content
    )

    # Update Overall Score
    content = re.sub(
        r"\| Overall Score \| .* \|",
        f"| Overall Score | {total['score']:.0f}/{total['max']} ({total['percentage']:.0f}%) |",
        content
    )

    # Update Status
    content = re.sub(
        r"\| Status \| .* \|",
        f"| Status | {status_badge} |",
        content
    )

    # Add new run entry to Validation History
    history_marker = "## Validation History"
    if history_marker in content:
        # Insert new entry after the header
        parts = content.split(history_marker)
        if len(parts) == 2:
            content = parts[0] + history_marker + "\n\n" + new_entry + parts[1].lstrip()

    VALIDATION_MD_PATH.write_text(content)
    print(f"Updated {VALIDATION_MD_PATH}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Generate validation report")
    parser.add_argument(
        "--results",
        type=Path,
        help="Path to JSON results file"
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run validation first"
    )
    parser.add_argument(
        "--org",
        default="Vivint-DevInt",
        help="Org alias for validation"
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Run offline tests only"
    )

    args = parser.parse_args()

    registry = load_registry()

    if args.run:
        # Run validation and capture results
        import subprocess
        cmd = [
            sys.executable,
            str(VALIDATION_DIR / "scripts" / "run_validation.py"),
            "--org", args.org,
            "--json"
        ]
        if args.offline:
            cmd.append("--offline")

        result = subprocess.run(cmd, capture_output=True, text=True)
        try:
            data = json.loads(result.stdout)
            results = data["results"]
        except json.JSONDecodeError:
            print(f"Error parsing validation output:\n{result.stdout}")
            sys.exit(1)
    elif args.results:
        with open(args.results) as f:
            data = json.load(f)
            results = data.get("results", data)
    else:
        print("Error: Either --run or --results required")
        sys.exit(1)

    scores = calculate_scores(results, registry)
    entry = generate_run_entry(results, scores, registry, args.org)

    print("\n" + entry)

    if args.run or args.results:
        update_validation_md(entry, scores, registry)


if __name__ == "__main__":
    main()
