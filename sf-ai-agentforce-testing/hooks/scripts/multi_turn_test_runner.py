#!/usr/bin/env python3
"""
Multi-Turn Agent Test Runner

Executes multi-turn test scenarios against Agentforce agents via the Agent Runtime API.
Reads YAML scenario templates, manages sessions, evaluates per-turn expectations,
and produces structured JSON results for the agentic fix loop.

Usage:
    # Basic usage with scenario file:
    python3 multi_turn_test_runner.py \
        --my-domain your-domain.my.salesforce.com \
        --consumer-key YOUR_KEY \
        --consumer-secret YOUR_SECRET \
        --agent-id 0XxRM0000004ABC \
        --scenarios templates/multi-turn-comprehensive.yaml

    # With context variables:
    python3 multi_turn_test_runner.py \
        --my-domain your-domain.my.salesforce.com \
        --consumer-key YOUR_KEY \
        --consumer-secret YOUR_SECRET \
        --agent-id 0XxRM0000004ABC \
        --scenarios templates/multi-turn-topic-routing.yaml \
        --var '$Context.AccountId=001XXXXXXXXXXXX' \
        --var '$Context.EndUserLanguage=en_US'

    # With JSON output for fix loop:
    python3 multi_turn_test_runner.py \
        --agent-id 0XxRM0000004ABC \
        --scenarios templates/multi-turn-comprehensive.yaml \
        --output results.json \
        --verbose

    # From environment variables (no args needed for credentials):
    export SF_MY_DOMAIN=your-domain.my.salesforce.com
    export SF_CONSUMER_KEY=YOUR_KEY
    export SF_CONSUMER_SECRET=YOUR_SECRET
    export SF_AGENT_ID=0XxRM0000004ABC
    python3 multi_turn_test_runner.py --scenarios templates/multi-turn-comprehensive.yaml

Exit Codes:
    0 = All scenarios passed
    1 = Some scenarios failed (fix loop should process results)
    2 = Execution error (auth failure, connection error, etc.)

Dependencies:
    - pyyaml (pip3 install pyyaml) — for YAML template parsing
    - agent_api_client.py (sibling module) — Agent Runtime API client

Author: Jag Valaiyapathy
License: MIT
"""

import argparse
import concurrent.futures
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Import sibling module
sys.path.insert(0, str(Path(__file__).parent))
from agent_api_client import (
    AgentAPIClient, AgentSession, TurnResult, AgentAPIError, parse_variables,
)

# YAML import with helpful error
try:
    import yaml
except ImportError:
    print(
        "ERROR: pyyaml is required for YAML template parsing.\n"
        "Install with: pip3 install pyyaml",
        file=sys.stderr,
    )
    sys.exit(2)


# ═══════════════════════════════════════════════════════════════════════════
# Turn Evaluation
# ═══════════════════════════════════════════════════════════════════════════

# Patterns that indicate a guardrail was triggered (agent declined the request)
GUARDRAIL_PATTERNS = [
    r"(?i)i\s*(?:can(?:'t|not)|am\s+(?:not\s+)?(?:able|allowed))\s+(?:to\s+)?(?:help|assist|provide|share|do\s+that)",
    r"(?i)(?:sorry|apologies?)[\s,]+(?:but\s+)?i\s+(?:can(?:'t|not))",
    r"(?i)(?:not\s+)?(?:able|allowed|permitted)\s+to\s+(?:provide|share|disclose|give)",
    r"(?i)(?:against|violates?)\s+(?:my|our|the)\s+(?:policy|policies|guidelines|rules)",
    r"(?i)(?:sensitive|confidential|private)\s+(?:information|data)",
    r"(?i)i\s+(?:must|need\s+to)\s+(?:decline|refuse|respectfully)",
]

# Patterns that suggest escalation (agent handing off to human)
ESCALATION_PATTERNS = [
    r"(?i)(?:connect|transfer|escalat)\w*\s+(?:you\s+)?(?:to|with)\s+(?:a\s+)?(?:human|agent|specialist|representative|someone|person|team)",
    r"(?i)(?:let\s+me\s+)?(?:get|find)\s+(?:you\s+)?(?:a\s+)?(?:human|real\s+person|specialist|agent)",
    r"(?i)(?:hand|pass)\w*\s+(?:you\s+)?(?:off|over)\s+to",
]


def evaluate_turn(
    turn: TurnResult,
    expectations: Dict[str, Any],
    prior_turns: List[TurnResult],
) -> Dict[str, Any]:
    """
    Evaluate a single turn's response against its expectations.

    Args:
        turn: The TurnResult to evaluate.
        expectations: Dict of expectation checks (from YAML).
        prior_turns: All turns that came before this one (for context checks).

    Returns:
        Dict with 'passed', 'failed', 'checks' (list of individual check results).
    """
    checks = []

    for check_name, expected_value in expectations.items():
        result = _run_check(check_name, expected_value, turn, prior_turns)
        checks.append(result)

    passed = [c for c in checks if c["passed"]]
    failed = [c for c in checks if not c["passed"]]

    return {
        "passed": len(failed) == 0,
        "pass_count": len(passed),
        "fail_count": len(failed),
        "total_checks": len(checks),
        "checks": checks,
    }


def _run_check(
    name: str, expected: Any, turn: TurnResult, prior_turns: List[TurnResult]
) -> Dict[str, Any]:
    """Run a single expectation check against a turn."""
    check = {
        "name": name,
        "expected": expected,
        "passed": False,
        "actual": None,
        "detail": "",
    }

    text = turn.agent_text.lower()

    try:
        if name == "response_not_empty":
            check["actual"] = turn.has_response
            check["passed"] = turn.has_response == expected
            check["detail"] = f"Response {'has' if turn.has_response else 'has no'} content"

        elif name == "response_contains":
            if isinstance(expected, bool):
                check["passed"] = False
                check["detail"] = (
                    "response_contains expects a string, got bool. "
                    "Use response_not_empty for boolean checks."
                )
            else:
                val = str(expected).lower()
                found = val in text
                check["actual"] = found
                check["passed"] = found
                check["detail"] = f"'{expected}' {'found' if found else 'not found'} in response"

        elif name == "response_contains_any":
            found_any = any(v.lower() in text for v in expected)
            found_which = [v for v in expected if v.lower() in text]
            check["actual"] = found_which
            check["passed"] = found_any
            check["detail"] = f"Found: {found_which}" if found_any else f"None of {expected} found"

        elif name == "response_not_contains":
            val = expected.lower()
            found = val in text
            check["actual"] = not found
            check["passed"] = not found
            check["detail"] = f"'{expected}' {'absent (good)' if not found else 'found (bad)'}"

        elif name == "topic_contains":
            # Heuristic: infer topic from response language (API doesn't return topic name)
            # Use word-boundary matching to avoid false positives on substrings
            val = expected.lower()
            found = bool(re.search(rf"\b{re.escape(val)}\b", text))
            check["actual"] = found
            check["passed"] = found
            check["detail"] = (
                f"Topic keyword '{expected}' {'inferred' if found else 'not found'} in response"
                " (heuristic — word-boundary match)"
            )

        elif name == "escalation_triggered":
            has_esc = turn.has_escalation or _matches_patterns(turn.agent_text, ESCALATION_PATTERNS)
            check["actual"] = has_esc
            check["passed"] = has_esc == expected
            check["detail"] = (
                f"Escalation {'detected' if has_esc else 'not detected'}"
                f" (types: {turn.message_types})"
            )

        elif name == "guardrail_triggered":
            is_declined = _matches_patterns(turn.agent_text, GUARDRAIL_PATTERNS)
            check["actual"] = is_declined
            check["passed"] = is_declined == expected
            check["detail"] = (
                f"Guardrail {'triggered' if is_declined else 'not triggered'}"
            )

        elif name == "action_invoked":
            has_action = turn.has_action_result
            if isinstance(expected, bool):
                check["actual"] = has_action
                check["passed"] = has_action == expected
                check["detail"] = (
                    f"Action result {'present' if has_action else 'absent'}"
                    f" (expected: {expected})"
                )
            else:
                # String: check action was invoked AND the action name matches
                action_name = str(expected)
                raw_json = json.dumps(turn.raw_response)
                name_found = action_name.lower() in raw_json.lower()
                check["actual"] = has_action and name_found
                check["passed"] = has_action and name_found
                if not has_action:
                    check["detail"] = f"No action result (expected action '{action_name}')"
                elif not name_found:
                    check["detail"] = f"Action invoked but '{action_name}' not found in response"
                else:
                    check["detail"] = f"Action '{action_name}' invoked successfully"

        elif name == "has_action_result":
            check["actual"] = turn.has_action_result
            check["passed"] = turn.has_action_result == expected

        elif name == "turn_elapsed_max":
            elapsed = turn.elapsed_ms
            check["actual"] = elapsed
            check["passed"] = elapsed <= expected
            check["detail"] = (
                f"Turn took {elapsed:.0f}ms (max: {expected}ms)"
                if elapsed <= expected
                else f"Turn took {elapsed:.0f}ms — EXCEEDED max {expected}ms"
            )

        elif name == "response_acknowledges_change":
            # Heuristic: look for acknowledgment phrases
            ack_patterns = [
                r"(?i)(?:instead|sure|of\s+course|no\s+problem|let\s+me|I'?ll)",
                r"(?i)(?:change|switch|update|rather|reschedule)",
            ]
            acknowledged = _matches_patterns(turn.agent_text, ack_patterns)
            check["actual"] = acknowledged
            check["passed"] = acknowledged
            check["detail"] = "Response acknowledges intent change" if acknowledged else "No acknowledgment detected"

        elif name == "response_offers_help":
            help_patterns = [
                r"(?i)(?:help|assist|can\s+I|would\s+you\s+like|let\s+me|try|here)",
            ]
            offers_help = _matches_patterns(turn.agent_text, help_patterns)
            check["actual"] = offers_help
            check["passed"] = offers_help
            check["detail"] = "Help offered" if offers_help else "No help offered"

        elif name == "response_offers_alternative":
            alt_patterns = [
                r"(?i)(?:alternatively|another\s+option|you\s+(?:could|can)\s+also|try|instead|otherwise|how\s+about)",
            ]
            has_alt = _matches_patterns(turn.agent_text, alt_patterns)
            check["actual"] = has_alt
            check["passed"] = has_alt
            check["detail"] = "Alternative offered" if has_alt else "No alternative detected"

        elif name == "response_acknowledges_error":
            err_patterns = [
                r"(?i)(?:sorry|apologize|error|issue|problem|unfortunately|went\s+wrong)",
            ]
            acknowledged = _matches_patterns(turn.agent_text, err_patterns)
            check["actual"] = acknowledged
            check["passed"] = acknowledged
            check["detail"] = "Error acknowledged" if acknowledged else "No error acknowledgment"

        elif name == "resumes_normal":
            # Check that the response is non-empty and doesn't contain guardrail language
            is_normal = turn.has_response and not _matches_patterns(turn.agent_text, GUARDRAIL_PATTERNS)
            check["actual"] = is_normal
            check["passed"] = is_normal
            check["detail"] = "Normal conversation resumed" if is_normal else "Did not resume normally"

        elif name == "no_re_ask_for":
            # Check that the agent doesn't re-ask for information already provided
            re_ask_patterns = [
                rf"(?i)(?:what|which|could\s+you\s+(?:please\s+)?(?:provide|give|tell)).*{re.escape(expected.lower())}",
                rf"(?i)(?:can\s+you|please)\s+(?:provide|share|give|tell).*{re.escape(expected.lower())}",
            ]
            re_asked = _matches_patterns(turn.agent_text, re_ask_patterns)
            check["actual"] = not re_asked
            check["passed"] = not re_asked
            check["detail"] = (
                f"Agent did NOT re-ask for '{expected}' (good)"
                if not re_asked
                else f"Agent RE-ASKED for '{expected}' (bad)"
            )

        elif name == "response_references":
            val = str(expected).lower()
            found = val in text
            check["actual"] = found
            check["passed"] = found
            check["detail"] = f"Reference to '{expected}' {'found' if found else 'not found'}"

        elif name == "response_references_both":
            found_all = all(str(v).lower() in text for v in expected)
            missing = [str(v) for v in expected if str(v).lower() not in text]
            check["actual"] = found_all
            check["passed"] = found_all
            check["detail"] = f"All references found" if found_all else f"Missing: {missing}"

        elif name == "context_retained":
            # Soft check: the response is non-empty and doesn't indicate confusion
            confusion_patterns = [
                r"(?i)I\s+don'?t\s+have\s+(?:that|this)\s+information",
                r"(?i)(?:could|can)\s+you\s+(?:please\s+)?(?:remind|tell)\s+me\s+again",
                r"(?i)I'?m\s+not\s+(?:sure|aware)\s+(?:what|which)",
            ]
            no_confusion = turn.has_response and not _matches_patterns(turn.agent_text, confusion_patterns)
            check["actual"] = no_confusion
            check["passed"] = no_confusion
            check["detail"] = "Context appears retained" if no_confusion else "Context may be lost"

        elif name == "context_uses":
            val = str(expected).lower()
            found = val in text
            check["actual"] = found
            check["passed"] = found
            check["detail"] = f"Context '{expected}' {'used' if found else 'not used'} in response"

        elif name == "action_uses_variable":
            # Heuristic: extract keyword from variable name and check agent didn't re-ask
            keyword = _extract_variable_keyword(str(expected))
            if keyword:
                re_ask_patterns = [
                    rf"(?i)(?:what|which|could\s+you\s+(?:please\s+)?(?:provide|give|tell)).*{re.escape(keyword)}",
                    rf"(?i)(?:can\s+you|please)\s+(?:provide|share|give|tell).*{re.escape(keyword)}",
                ]
                re_asked = _matches_patterns(turn.agent_text, re_ask_patterns)
                check["actual"] = not re_asked
                check["passed"] = not re_asked
                check["detail"] = (
                    f"Variable {expected} appears used (agent did not re-ask for '{keyword}')"
                    if not re_asked
                    else f"Agent re-asked for '{keyword}' — variable {expected} may not be used"
                )
            else:
                check["actual"] = "cannot_verify"
                check["passed"] = True  # Soft pass if we can't extract a keyword
                check["detail"] = f"Variable {expected} usage cannot be verified from response alone (check STDM)"

        elif name == "action_uses_prior_output":
            # Heuristic: check that agent doesn't re-ask for data from prior action
            if prior_turns:
                re_ask = _matches_patterns(turn.agent_text, [
                    r"(?i)which\s+(?:account|record|order|contact|case)",
                    r"(?i)(?:could|can)\s+you\s+(?:provide|specify|tell\s+me)",
                ])
                check["actual"] = not re_ask
                check["passed"] = not re_ask
                check["detail"] = (
                    "Agent used prior action output (no re-ask)"
                    if not re_ask
                    else "Agent may have re-asked for prior action data"
                )
            else:
                check["actual"] = True
                check["passed"] = True
                check["detail"] = "First turn — no prior output to check"

        elif name == "conversation_resolved":
            # Heuristic: response indicates resolution
            resolve_patterns = [
                r"(?i)(?:anything\s+else|is\s+there\s+anything|glad\s+I\s+could|happy\s+to\s+help)",
                r"(?i)(?:done|complete|resolved|taken\s+care\s+of|all\s+set)",
            ]
            resolved = _matches_patterns(turn.agent_text, resolve_patterns)
            check["actual"] = resolved
            check["passed"] = resolved
            check["detail"] = "Conversation appears resolved" if resolved else "Resolution not detected"

        elif name == "response_declines_gracefully":
            decline_patterns = [
                r"(?i)(?:I'?m\s+)?(?:not\s+(?:able|equipped)|(?:can(?:'t|not))\s+(?:help|assist|provide))",
                r"(?i)(?:outside|beyond)\s+(?:my|the)\s+(?:scope|area|capabilities)",
                r"(?i)(?:focus|specialize)\s+(?:on|in)\s+(?:other|different)",
            ]
            declined = _matches_patterns(turn.agent_text, decline_patterns) or \
                       _matches_patterns(turn.agent_text, GUARDRAIL_PATTERNS)
            check["actual"] = declined
            check["passed"] = declined
            check["detail"] = "Gracefully declined" if declined else "Did not decline"

        elif name == "response_matches_regex":
            try:
                match = re.search(expected, turn.agent_text)
                check["actual"] = bool(match)
                check["passed"] = bool(match)
                check["detail"] = (
                    f"Regex '{expected}' matched" if match
                    else f"Regex '{expected}' did not match"
                )
            except re.error as regex_err:
                check["passed"] = False
                check["detail"] = f"Invalid regex '{expected}': {regex_err}"

        elif name == "response_length_min":
            actual_len = len(turn.agent_text.strip())
            check["actual"] = actual_len
            check["passed"] = actual_len >= expected
            check["detail"] = (
                f"Response length {actual_len} >= {expected} (min)"
                if actual_len >= expected
                else f"Response length {actual_len} < {expected} (min)"
            )

        elif name == "response_length_max":
            actual_len = len(turn.agent_text.strip())
            check["actual"] = actual_len
            check["passed"] = actual_len <= expected
            check["detail"] = (
                f"Response length {actual_len} <= {expected} (max)"
                if actual_len <= expected
                else f"Response length {actual_len} > {expected} (max)"
            )

        elif name == "action_result_contains":
            results = turn.action_results
            results_str = json.dumps(results) if results else ""
            found = str(expected).lower() in results_str.lower()
            check["actual"] = found
            check["passed"] = found
            if not results:
                check["detail"] = f"No action results to search for '{expected}'"
                check["passed"] = False
            elif found:
                check["detail"] = f"'{expected}' found in action results"
            else:
                check["detail"] = f"'{expected}' not found in action results"

        else:
            check["detail"] = f"Unknown check '{name}' — skipped"
            check["passed"] = True  # Don't fail on unknown checks

    except Exception as e:
        check["detail"] = f"Check error: {e}"
        check["passed"] = False

    return check


def _matches_patterns(text: str, patterns: List[str]) -> bool:
    """Check if text matches any of the given regex patterns."""
    return any(re.search(p, text) for p in patterns)


def _extract_variable_keyword(variable_name: str) -> Optional[str]:
    """
    Extract a human-readable keyword from a variable name for re-ask detection.

    Examples:
        "$Context.AccountId" → "account"
        "$Context.EndUserLanguage" → "language"
        "CaseId" → "case"
        "Verified_Check" → "verified"
    """
    # Strip $Context. prefix
    name = variable_name.replace("$Context.", "").replace("$", "")
    # Split on camelCase or underscores
    parts = re.split(r'(?<=[a-z])(?=[A-Z])|_', name)
    # Filter out common suffixes like 'Id', 'Key', 'Name'
    keywords = [p.lower() for p in parts if p.lower() not in ("id", "key", "name", "type", "value")]
    return keywords[0] if keywords else None


# ═══════════════════════════════════════════════════════════════════════════
# Scenario Execution
# ═══════════════════════════════════════════════════════════════════════════

def load_scenarios(path: str) -> Dict[str, Any]:
    """Load YAML scenario file."""
    with open(path, "r") as f:
        return yaml.safe_load(f)


def execute_scenario(
    client: AgentAPIClient,
    agent_id: str,
    scenario: Dict[str, Any],
    global_variables: List[Dict] = None,
    verbose: bool = False,
    turn_retry: int = 0,
) -> Dict[str, Any]:
    """
    Execute a single multi-turn test scenario.

    Args:
        client: Authenticated AgentAPIClient.
        agent_id: BotDefinition ID.
        scenario: Scenario dict from YAML template.
        global_variables: CLI-level variables to merge with scenario variables.
        verbose: Print progress to stderr.
        turn_retry: Number of retries per turn on transient failures (default 0).

    Returns:
        Scenario result dict with turn results and evaluation.
    """
    name = scenario.get("name", "unnamed")
    description = scenario.get("description", "")
    turns_spec = scenario.get("turns", [])
    scenario_vars = scenario.get("session_variables", [])

    # Merge variables: scenario-specific + global CLI variables
    all_variables = list(scenario_vars)
    if global_variables:
        # Global vars override scenario vars with same name
        global_names = {v["name"] for v in global_variables}
        all_variables = [v for v in all_variables if v["name"] not in global_names]
        all_variables.extend(global_variables)

    if verbose:
        print(f"\n  ▶ Scenario: {name}", file=sys.stderr)
        if all_variables:
            print(f"    Variables: {[v['name'] for v in all_variables]}", file=sys.stderr)

    result = {
        "name": name,
        "description": description,
        "status": "error",
        "turns": [],
        "pass_count": 0,
        "fail_count": 0,
        "total_turns": len(turns_spec),
        "elapsed_ms": 0,
        "error": None,
    }

    start_time = time.time()
    prior_turn_results: List[TurnResult] = []

    try:
        with client.session(
            agent_id=agent_id,
            variables=all_variables if all_variables else None,
        ) as session:
            for i, turn_spec in enumerate(turns_spec, 1):
                user_message = turn_spec.get("user", "")
                expectations = turn_spec.get("expect", {})
                turn_variables = turn_spec.get("variables", None)

                if verbose:
                    print(f"    Turn {i}: \"{user_message[:50]}{'...' if len(user_message) > 50 else ''}\"", file=sys.stderr)

                # Send message with optional per-turn retry
                turn_result = None
                for attempt in range(turn_retry + 1):
                    try:
                        turn_result = session.send(user_message, variables=turn_variables)
                        if not turn_result.is_error:
                            break
                    except Exception as send_err:
                        if attempt < turn_retry:
                            if verbose:
                                print(f"      ⟳ Retry {attempt + 1}/{turn_retry}: {send_err}", file=sys.stderr)
                            time.sleep(1 * (attempt + 1))
                        else:
                            raise
                    if attempt < turn_retry and turn_result and turn_result.is_error:
                        if verbose:
                            print(f"      ⟳ Retry {attempt + 1}/{turn_retry}: turn error", file=sys.stderr)
                        time.sleep(1 * (attempt + 1))

                # Evaluate against expectations
                evaluation = evaluate_turn(turn_result, expectations, prior_turn_results)

                turn_data = {
                    "turn_number": i,
                    "user_message": user_message,
                    "agent_text": turn_result.agent_text,
                    "message_types": turn_result.message_types,
                    "elapsed_ms": round(turn_result.elapsed_ms, 1),
                    "has_response": turn_result.has_response,
                    "has_escalation": turn_result.has_escalation,
                    "has_action_result": turn_result.has_action_result,
                    "error": turn_result.error,
                    "evaluation": evaluation,
                }

                result["turns"].append(turn_data)

                if evaluation["passed"]:
                    result["pass_count"] += 1
                    if verbose:
                        print(f"      ✅ {evaluation['pass_count']}/{evaluation['total_checks']} checks passed", file=sys.stderr)
                else:
                    result["fail_count"] += 1
                    if verbose:
                        failed_checks = [c for c in evaluation["checks"] if not c["passed"]]
                        for fc in failed_checks:
                            print(f"      ❌ {fc['name']}: {fc['detail']}", file=sys.stderr)

                prior_turn_results.append(turn_result)

    except AgentAPIError as e:
        result["error"] = str(e)
        result["status"] = "error"
        if verbose:
            print(f"    ❌ API Error: {e}", file=sys.stderr)
        return result
    except Exception as e:
        result["error"] = f"Unexpected error: {type(e).__name__}: {e}"
        result["status"] = "error"
        if verbose:
            print(f"    ❌ Unexpected Error: {type(e).__name__}: {e}", file=sys.stderr)
        return result

    result["elapsed_ms"] = round((time.time() - start_time) * 1000, 1)

    if result["fail_count"] == 0 and result["error"] is None:
        result["status"] = "passed"
    elif result["fail_count"] > 0:
        result["status"] = "failed"

    return result


# ═══════════════════════════════════════════════════════════════════════════
# Results Formatting
# ═══════════════════════════════════════════════════════════════════════════

def format_results(results: Dict[str, Any]) -> str:
    """Format test results as terminal-friendly report."""
    lines = []
    scenarios = results.get("scenarios", [])
    summary = results.get("summary", {})

    lines.append("")
    lines.append("📊 MULTI-TURN TEST RESULTS")
    lines.append("=" * 64)
    lines.append("")
    lines.append(f"Agent ID:    {results.get('agent_id', 'Unknown')}")
    lines.append(f"Scenarios:   {results.get('scenario_file', 'Unknown')}")
    lines.append(f"Timestamp:   {results.get('timestamp', '')}")
    lines.append(f"Duration:    {results.get('total_elapsed_ms', 0):.0f}ms")
    lines.append("")

    # Scenario summary
    lines.append("SCENARIO RESULTS")
    lines.append("-" * 64)

    for s in scenarios:
        status_icon = {"passed": "✅", "failed": "❌", "error": "💥"}.get(s["status"], "⚠️")
        turn_info = f"{s['pass_count']}/{s['total_turns']} turns passed"
        lines.append(f"{status_icon} {s['name']:<40} {turn_info}")

        # Show failed turns inline
        if s["status"] == "failed":
            for t in s["turns"]:
                if not t["evaluation"]["passed"]:
                    failed_checks = [c for c in t["evaluation"]["checks"] if not c["passed"]]
                    for fc in failed_checks:
                        lines.append(f"   └─ Turn {t['turn_number']}: {fc['name']} — {fc['detail']}")

        if s["status"] == "error":
            lines.append(f"   └─ Error: {s.get('error', 'Unknown')}")

    lines.append("")

    # Aggregate summary
    lines.append("SUMMARY")
    lines.append("-" * 64)
    lines.append(f"Scenarios:        {summary.get('total_scenarios', 0)} total | "
                 f"{summary.get('passed_scenarios', 0)} passed | "
                 f"{summary.get('failed_scenarios', 0)} failed | "
                 f"{summary.get('error_scenarios', 0)} errors")
    lines.append(f"Turns:            {summary.get('total_turns', 0)} total | "
                 f"{summary.get('passed_turns', 0)} passed | "
                 f"{summary.get('failed_turns', 0)} failed")

    total_turns = summary.get("total_turns", 0)
    if total_turns > 0:
        pass_rate = (summary.get("passed_turns", 0) / total_turns) * 100
        lines.append(f"Turn Pass Rate:   {pass_rate:.1f}%")
    lines.append("")

    # Failed turns detail
    failed_turns = []
    for s in scenarios:
        for t in s.get("turns", []):
            if not t["evaluation"]["passed"]:
                failed_turns.append((s["name"], t))

    if failed_turns:
        lines.append("FAILED TURNS — DETAIL")
        lines.append("-" * 64)

        for scenario_name, t in failed_turns:
            failed_checks = [c for c in t["evaluation"]["checks"] if not c["passed"]]
            lines.append(f"")
            lines.append(f"❌ {scenario_name} → Turn {t['turn_number']}")
            lines.append(f"   Input:    \"{t['user_message'][:70]}\"")
            if t.get("agent_text"):
                lines.append(f"   Response: \"{t['agent_text'][:70]}{'...' if len(t.get('agent_text', '')) > 70 else ''}\"")
            for fc in failed_checks:
                lines.append(f"   Check:    {fc['name']}")
                lines.append(f"   Expected: {fc['expected']}")
                lines.append(f"   Actual:   {fc['actual']}")
                lines.append(f"   Detail:   {fc['detail']}")
                # Suggest failure category
                category = _infer_failure_category(fc["name"], t)
                if category:
                    lines.append(f"   Category: {category}")

        lines.append("")

    # Machine-readable section for fix loop
    if summary.get("failed_scenarios", 0) > 0 or summary.get("error_scenarios", 0) > 0:
        lines.append("=" * 64)
        lines.append("AGENTIC FIX INSTRUCTIONS")
        lines.append("=" * 64)
        lines.append("")
        lines.append("To automatically fix these failures, invoke sf-ai-agentscript:")
        lines.append("")

        categories_seen = set()
        for scenario_name, t in failed_turns:
            for fc in t["evaluation"]["checks"]:
                if not fc["passed"]:
                    cat = _infer_failure_category(fc["name"], t)
                    if cat and cat not in categories_seen:
                        categories_seen.add(cat)
                        fix = _suggest_fix(cat)
                        lines.append(f"  {cat}:")
                        lines.append(f"    → {fix}")
                        lines.append("")

    lines.append("=" * 64)
    lines.append("")

    return "\n".join(lines)


def _infer_failure_category(check_name: str, turn: Dict) -> Optional[str]:
    """Infer failure category from check name and turn data."""
    mapping = {
        "topic_contains": "TOPIC_RE_MATCHING_FAILURE",
        "response_contains": "CONTEXT_PRESERVATION_FAILURE",
        "context_retained": "CONTEXT_PRESERVATION_FAILURE",
        "context_uses": "CONTEXT_PRESERVATION_FAILURE",
        "no_re_ask_for": "CONTEXT_PRESERVATION_FAILURE",
        "response_references": "CONTEXT_PRESERVATION_FAILURE",
        "response_references_both": "CONTEXT_PRESERVATION_FAILURE",
        "escalation_triggered": "MULTI_TURN_ESCALATION_FAILURE",
        "guardrail_triggered": "GUARDRAIL_NOT_TRIGGERED",
        "action_invoked": "ACTION_NOT_INVOKED",
        "action_uses_prior_output": "ACTION_CHAIN_FAILURE",
        "response_not_empty": "RESPONSE_QUALITY_ISSUE",
        "response_declines_gracefully": "GUARDRAIL_NOT_TRIGGERED",
        "resumes_normal": "GUARDRAIL_RECOVERY_FAILURE",
        "turn_elapsed_max": "RESPONSE_QUALITY_ISSUE",
        "response_matches_regex": "CONTEXT_PRESERVATION_FAILURE",
        "response_length_min": "RESPONSE_QUALITY_ISSUE",
        "response_length_max": "RESPONSE_QUALITY_ISSUE",
        "action_result_contains": "ACTION_CHAIN_FAILURE",
    }
    return mapping.get(check_name)


def _suggest_fix(category: str) -> str:
    """Suggest fix strategy for a failure category."""
    fixes = {
        "TOPIC_RE_MATCHING_FAILURE": "Add transition phrases to target topic classificationDescription",
        "CONTEXT_PRESERVATION_FAILURE": "Add 'use context from prior messages' to topic instructions",
        "MULTI_TURN_ESCALATION_FAILURE": "Add frustration detection keywords to escalation triggers",
        "GUARDRAIL_NOT_TRIGGERED": "Add explicit guardrail statements to system instructions",
        "ACTION_NOT_INVOKED": "Improve action description and trigger conditions",
        "ACTION_CHAIN_FAILURE": "Verify action output variable mappings between actions",
        "RESPONSE_QUALITY_ISSUE": "Review agent instructions for completeness",
        "GUARDRAIL_RECOVERY_FAILURE": "Ensure guardrail response doesn't terminate session state",
    }
    return fixes.get(category, "Review agent configuration for this failure type")


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Multi-Turn Agent Test Runner — execute YAML test scenarios via Agent Runtime API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run comprehensive tests:
  python3 multi_turn_test_runner.py \\
      --scenarios templates/multi-turn-comprehensive.yaml

  # With context variables:
  python3 multi_turn_test_runner.py \\
      --scenarios templates/multi-turn-topic-routing.yaml \\
      --var '$Context.AccountId=001XXXXXXXXXXXX'

  # Save JSON results:
  python3 multi_turn_test_runner.py \\
      --scenarios templates/multi-turn-comprehensive.yaml \\
      --output results.json

Environment Variables:
  SF_MY_DOMAIN         Salesforce My Domain URL
  SF_CONSUMER_KEY      ECA Consumer Key
  SF_CONSUMER_SECRET   ECA Consumer Secret
  SF_AGENT_ID          BotDefinition ID
""",
    )

    # Credentials (CLI args or env vars)
    parser.add_argument("--my-domain", default=os.environ.get("SF_MY_DOMAIN", ""),
                        help="Salesforce My Domain URL (or SF_MY_DOMAIN env)")
    parser.add_argument("--consumer-key", default=os.environ.get("SF_CONSUMER_KEY", ""),
                        help="ECA Consumer Key (or SF_CONSUMER_KEY env)")
    parser.add_argument("--consumer-secret", default=os.environ.get("SF_CONSUMER_SECRET", ""),
                        help="ECA Consumer Secret (or SF_CONSUMER_SECRET env)")
    parser.add_argument("--agent-id", default=os.environ.get("SF_AGENT_ID", ""),
                        help="BotDefinition ID (or SF_AGENT_ID env)")

    # Scenario configuration
    parser.add_argument("--scenarios", required=True,
                        help="Path to YAML scenario file")
    parser.add_argument("--scenario-filter", default=None,
                        help="Only run scenarios matching this name pattern")
    parser.add_argument("--var", action="append", default=[],
                        help="Global variable: 'name=value' or '$Context.Field=value' (repeatable)")

    # Output
    parser.add_argument("--output", default=None,
                        help="Write JSON results to this file path")
    parser.add_argument("--verbose", action="store_true",
                        help="Print progress to stderr")
    parser.add_argument("--json-only", action="store_true",
                        help="Only output JSON (no terminal report)")

    # Robustness
    parser.add_argument("--turn-retry", type=int, default=0,
                        help="Number of retries per turn on transient failures (default: 0)")
    parser.add_argument("--parallel", type=int, default=0,
                        help="Run scenarios in parallel with N workers (default: 0 = sequential)")

    args = parser.parse_args()

    # Validate required args
    if not args.agent_id:
        print("ERROR: --agent-id required (or set SF_AGENT_ID env var)", file=sys.stderr)
        sys.exit(2)

    if not os.path.isfile(args.scenarios):
        print(f"ERROR: Scenario file not found: {args.scenarios}", file=sys.stderr)
        sys.exit(2)

    # Parse global variables
    global_variables = parse_variables(args.var) if args.var else None

    # Load scenarios
    try:
        scenario_data = load_scenarios(args.scenarios)
    except Exception as e:
        print(f"ERROR: Failed to load scenarios: {e}", file=sys.stderr)
        sys.exit(2)

    scenarios = scenario_data.get("scenarios", [])
    if not scenarios:
        print("ERROR: No scenarios found in YAML file", file=sys.stderr)
        sys.exit(2)

    # Apply filter
    if args.scenario_filter:
        pattern = args.scenario_filter.lower()
        scenarios = [s for s in scenarios if pattern in s.get("name", "").lower()]
        if not scenarios:
            print(f"ERROR: No scenarios match filter '{args.scenario_filter}'", file=sys.stderr)
            sys.exit(2)

    # Create client
    client = AgentAPIClient(
        my_domain=args.my_domain,
        consumer_key=args.consumer_key,
        consumer_secret=args.consumer_secret,
        verbose=args.verbose,
    )

    # Authenticate
    try:
        client.authenticate()
        if args.verbose:
            print("✅ Authentication successful", file=sys.stderr)
    except AgentAPIError as e:
        print(f"❌ Authentication failed: {e.message}", file=sys.stderr)
        sys.exit(2)

    # Execute scenarios
    parallel = getattr(args, 'parallel', 0)
    if args.verbose:
        mode = f"parallel ({parallel} workers)" if parallel else "sequential"
        print(f"\nRunning {len(scenarios)} scenario(s) from {args.scenarios} [{mode}]...", file=sys.stderr)

    start_time = time.time()
    scenario_results = []

    def _run_one(scenario):
        return execute_scenario(
            client=client,
            agent_id=args.agent_id,
            scenario=scenario,
            global_variables=global_variables,
            verbose=args.verbose,
            turn_retry=args.turn_retry,
        )

    if parallel and parallel > 0 and len(scenarios) > 1:
        max_workers = min(parallel, len(scenarios))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_run_one, s): s for s in scenarios}
            for future in concurrent.futures.as_completed(futures):
                scenario_results.append(future.result())
    else:
        for scenario in scenarios:
            scenario_results.append(_run_one(scenario))

    total_elapsed = (time.time() - start_time) * 1000

    # Build aggregate results
    passed_scenarios = sum(1 for s in scenario_results if s["status"] == "passed")
    failed_scenarios = sum(1 for s in scenario_results if s["status"] == "failed")
    error_scenarios = sum(1 for s in scenario_results if s["status"] == "error")
    total_turns = sum(s["total_turns"] for s in scenario_results)
    passed_turns = sum(s["pass_count"] for s in scenario_results)
    failed_turns = sum(s["fail_count"] for s in scenario_results)

    results = {
        "agent_id": args.agent_id,
        "scenario_file": args.scenarios,
        "timestamp": datetime.now().isoformat(),
        "total_elapsed_ms": round(total_elapsed, 1),
        "summary": {
            "total_scenarios": len(scenario_results),
            "passed_scenarios": passed_scenarios,
            "failed_scenarios": failed_scenarios,
            "error_scenarios": error_scenarios,
            "total_turns": total_turns,
            "passed_turns": passed_turns,
            "failed_turns": failed_turns,
        },
        "global_variables": global_variables,
        "scenarios": scenario_results,
    }

    # Output
    if not args.json_only:
        report = format_results(results)
        print(report)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        if args.verbose:
            print(f"\n📄 JSON results written to: {args.output}", file=sys.stderr)

    if args.json_only:
        print(json.dumps(results, indent=2))

    # Machine-readable output for fix loop integration
    if failed_scenarios > 0 or error_scenarios > 0:
        print("---BEGIN_MACHINE_READABLE---")
        print(f"FIX_NEEDED: true")
        print(f"SCENARIOS_TOTAL: {len(scenario_results)}")
        print(f"SCENARIOS_PASSED: {passed_scenarios}")
        print(f"SCENARIOS_FAILED: {failed_scenarios}")
        print(f"SCENARIOS_ERROR: {error_scenarios}")
        print(f"TURNS_TOTAL: {total_turns}")
        print(f"TURNS_PASSED: {passed_turns}")
        print(f"TURNS_FAILED: {failed_turns}")
        if args.output:
            print(f"RESULTS_FILE: {args.output}")
        print("---END_MACHINE_READABLE---")

    # Exit code
    if error_scenarios > 0:
        sys.exit(2)
    elif failed_scenarios > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
