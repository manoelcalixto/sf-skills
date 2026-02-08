#!/usr/bin/env python3
"""
Main validation runner for sf-ai-agentforce-observability.

Runs pytest test suite across all tiers and calculates weighted scores.

Usage:
    # Quick offline test (T3, T4, T5 only)
    python3 validation/scripts/run_validation.py --offline

    # Full validation against live org
    python3 validation/scripts/run_validation.py --org Vivint-DevInt

    # Generate report and update VALIDATION.md
    python3 validation/scripts/run_validation.py --org Vivint-DevInt --report

    # Run specific tier
    python3 validation/scripts/run_validation.py --org Vivint-DevInt --tier T1
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Rich for pretty output
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# Paths
VALIDATION_DIR = Path(__file__).parent.parent
SCENARIOS_DIR = VALIDATION_DIR / "scenarios"
REGISTRY_PATH = VALIDATION_DIR / "scenario_registry.json"
VALIDATION_MD_PATH = VALIDATION_DIR / "VALIDATION.md"


def load_registry() -> dict:
    """Load scenario registry configuration."""
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def run_pytest(
    tier: Optional[str] = None,
    offline: bool = False,
    org_alias: str = "Vivint-DevInt",
    verbose: bool = False
) -> Tuple[int, int, int, str]:
    """
    Run pytest and return results.

    Returns:
        Tuple of (passed, failed, skipped, output)
    """
    cmd = [
        sys.executable, "-m", "pytest",
        str(SCENARIOS_DIR),
        "-v",
        "--tb=short",
        f"--org={org_alias}",
    ]

    if offline:
        cmd.append("--offline")

    if tier:
        # Map tier to marker
        tier_markers = {
            "T1": "tier1",
            "T2": "tier2",
            "T3": "tier3",
            "T4": "tier4",
            "T5": "tier5",
        }
        marker = tier_markers.get(tier.upper())
        if marker:
            cmd.extend(["-m", marker])

    if verbose:
        cmd.append("-vv")

    # Run pytest
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=VALIDATION_DIR.parent  # Run from skill root
    )

    output = result.stdout + result.stderr

    # Parse results from output
    passed = 0
    failed = 0
    skipped = 0

    # Look for summary line like "5 passed, 2 failed, 1 skipped"
    for line in output.split('\n'):
        if 'passed' in line or 'failed' in line or 'skipped' in line:
            if ' passed' in line:
                try:
                    passed = int(line.split(' passed')[0].split()[-1])
                except (ValueError, IndexError):
                    pass
            if ' failed' in line:
                try:
                    failed = int(line.split(' failed')[0].split()[-1])
                except (ValueError, IndexError):
                    pass
            if ' skipped' in line:
                try:
                    skipped = int(line.split(' skipped')[0].split()[-1])
                except (ValueError, IndexError):
                    pass

    return passed, failed, skipped, output


def calculate_tier_score(tier_name: str, passed: int, total: int, weight: int) -> float:
    """Calculate score for a tier based on pass rate."""
    if total == 0:
        return 0.0

    pass_rate = passed / total
    return pass_rate * weight


def run_tier_tests(
    tier_name: str,
    offline: bool,
    org_alias: str,
    verbose: bool
) -> Dict:
    """Run tests for a specific tier and return results."""
    passed, failed, skipped, output = run_pytest(
        tier=tier_name,
        offline=offline,
        org_alias=org_alias,
        verbose=verbose
    )

    total = passed + failed

    return {
        "tier": tier_name,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "total": total,
        "output": output
    }


def print_results_rich(results: List[Dict], registry: dict):
    """Print results using Rich tables."""
    console = Console()

    # Header
    console.print(Panel.fit(
        "[bold cyan]sf-ai-agentforce-observability Validation Results[/bold cyan]",
        border_style="cyan"
    ))
    console.print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    console.print()

    # Results table
    table = Table(title="Tier Results")
    table.add_column("Tier", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Passed", justify="right", style="green")
    table.add_column("Failed", justify="right", style="red")
    table.add_column("Skipped", justify="right", style="yellow")
    table.add_column("Score", justify="right")
    table.add_column("Status")

    total_score = 0
    max_score = 0

    tiers_config = registry.get("tiers", {})

    for result in results:
        tier_name = result["tier"]
        tier_config = tiers_config.get(tier_name, {})
        weight = tier_config.get("weight", 0)
        name = tier_config.get("name", tier_name)

        score = calculate_tier_score(
            tier_name,
            result["passed"],
            result["total"],
            weight
        )
        total_score += score
        max_score += weight

        # Status indicator
        if result["failed"] == 0 and result["total"] > 0:
            status = "[green]✅ PASS[/green]"
        elif result["total"] == 0:
            status = "[yellow]⏳ SKIP[/yellow]"
        else:
            status = "[red]❌ FAIL[/red]"

        table.add_row(
            tier_name,
            name,
            str(result["passed"]),
            str(result["failed"]),
            str(result["skipped"]),
            f"{score:.1f}/{weight}",
            status
        )

    console.print(table)

    # Summary
    console.print()
    pass_threshold = registry.get("pass_threshold", 80)
    warn_threshold = registry.get("warn_threshold", 70)

    score_pct = (total_score / max_score * 100) if max_score > 0 else 0

    if score_pct >= pass_threshold:
        status_msg = f"[bold green]✅ PASS ({total_score:.1f}/{max_score} = {score_pct:.1f}%)[/bold green]"
    elif score_pct >= warn_threshold:
        status_msg = f"[bold yellow]⚠️ WARN ({total_score:.1f}/{max_score} = {score_pct:.1f}%)[/bold yellow]"
    else:
        status_msg = f"[bold red]❌ FAIL ({total_score:.1f}/{max_score} = {score_pct:.1f}%)[/bold red]"

    console.print(Panel(status_msg, title="Overall Result"))


def print_results_plain(results: List[Dict], registry: dict):
    """Print results without Rich (plain text)."""
    print("=" * 60)
    print("sf-ai-agentforce-observability Validation Results")
    print("=" * 60)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    print("TIER RESULTS")
    print("-" * 60)
    print(f"{'Tier':<6} {'Name':<25} {'Pass':<6} {'Fail':<6} {'Score':<10}")
    print("-" * 60)

    total_score = 0
    max_score = 0

    tiers_config = registry.get("tiers", {})

    for result in results:
        tier_name = result["tier"]
        tier_config = tiers_config.get(tier_name, {})
        weight = tier_config.get("weight", 0)
        name = tier_config.get("name", tier_name)[:25]

        score = calculate_tier_score(
            tier_name,
            result["passed"],
            result["total"],
            weight
        )
        total_score += score
        max_score += weight

        print(f"{tier_name:<6} {name:<25} {result['passed']:<6} {result['failed']:<6} {score:.1f}/{weight}")

    print("-" * 60)

    score_pct = (total_score / max_score * 100) if max_score > 0 else 0
    pass_threshold = registry.get("pass_threshold", 80)

    status = "PASS" if score_pct >= pass_threshold else "FAIL"
    print(f"\nTOTAL: {total_score:.1f}/{max_score} = {score_pct:.1f}% [{status}]")


def update_validation_md(results: List[Dict], registry: dict):
    """Update VALIDATION.md with latest results."""
    # This would update the tracking file
    # For now, just print a message
    print(f"\nTo update VALIDATION.md, run: python3 validation/scripts/generate_report.py")


def main():
    parser = argparse.ArgumentParser(
        description="Run validation tests for sf-ai-agentforce-observability",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Quick offline test
    python3 validation/scripts/run_validation.py --offline

    # Full validation
    python3 validation/scripts/run_validation.py --org Vivint-DevInt

    # Specific tier
    python3 validation/scripts/run_validation.py --org Vivint-DevInt --tier T1
        """
    )

    parser.add_argument(
        "--org",
        default="Vivint-DevInt",
        help="Salesforce org alias (default: Vivint-DevInt)"
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Run only offline tests (skip live API tests)"
    )
    parser.add_argument(
        "--tier",
        choices=["T1", "T2", "T3", "T4", "T5"],
        help="Run specific tier only"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate report and update VALIDATION.md"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    # Load registry
    try:
        registry = load_registry()
    except FileNotFoundError:
        print(f"Error: Registry not found at {REGISTRY_PATH}")
        sys.exit(1)

    # Determine which tiers to run
    if args.tier:
        tiers_to_run = [args.tier]
    else:
        tiers_to_run = ["T1", "T2", "T3", "T4", "T5"]

    # Run tests
    results = []
    for tier in tiers_to_run:
        tier_config = registry.get("tiers", {}).get(tier, {})

        # Skip live API tiers in offline mode
        if args.offline and tier_config.get("requires_live_api", False):
            results.append({
                "tier": tier,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "total": 0,
                "output": "Skipped (offline mode)"
            })
            continue

        result = run_tier_tests(
            tier_name=tier,
            offline=args.offline,
            org_alias=args.org,
            verbose=args.verbose
        )
        results.append(result)

        if args.verbose:
            print(f"\n--- {tier} Output ---")
            print(result["output"])

    # Output results
    if args.json:
        print(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "org": args.org,
            "offline": args.offline,
            "results": results
        }, indent=2))
    elif RICH_AVAILABLE:
        print_results_rich(results, registry)
    else:
        print_results_plain(results, registry)

    # Generate report if requested
    if args.report:
        update_validation_md(results, registry)

    # Exit code based on results
    total_failed = sum(r["failed"] for r in results)
    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()
