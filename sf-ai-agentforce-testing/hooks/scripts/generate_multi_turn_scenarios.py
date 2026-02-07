#!/usr/bin/env python3
"""
Multi-Turn Scenario Generator

Auto-generates YAML test scenarios from agent metadata JSON (output of agent_discovery.py).
Produces scenarios matching the multi-turn YAML template schema used by multi_turn_test_runner.py.

Usage:
    # Generate all patterns:
    python3 generate_multi_turn_scenarios.py --metadata agent-metadata.json --output scenarios.yaml

    # Generate specific patterns only:
    python3 generate_multi_turn_scenarios.py --metadata agent-metadata.json --output scenarios.yaml \
        --patterns topic_routing context_preservation

    # Pipe from agent_discovery.py:
    python3 agent_discovery.py local --project-dir . | \
        python3 generate_multi_turn_scenarios.py --metadata - --output scenarios.yaml

Patterns:
    topic_routing           — 2-turn: greeting → topic-specific utterance
    context_preservation    — 3-turn: provide info → follow-up → verify context
    escalation_flows        — 2-turn: trigger frustration → verify escalation
    guardrail_testing       — 2-turn: normal → out-of-scope request
    action_chain            — 3-turn: trigger action → verify → chain second
    error_recovery          — 3-turn: bad input → correction → good input

Dependencies:
    - pyyaml
    - Python 3.8+ standard library

Author: Jag Valaiyapathy
License: MIT
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required. Install with: pip3 install pyyaml", file=sys.stderr)
    sys.exit(2)


ALL_PATTERNS = [
    "topic_routing",
    "context_preservation",
    "escalation_flows",
    "guardrail_testing",
    "action_chain",
    "error_recovery",
    "cross_topic_switch",
]


# ═══════════════════════════════════════════════════════════════════════════
# Generators
# ═══════════════════════════════════════════════════════════════════════════

def generate_topic_routing(agent: Dict[str, Any]) -> List[Dict]:
    """Generate topic routing scenarios — one per topic."""
    scenarios = []
    topics = agent.get("topics", [])
    if not topics:
        # Fallback: generate a generic topic routing test
        scenarios.append({
            "name": f"topic_routing_general_{agent['name']}",
            "description": f"Verify agent {agent['name']} handles a general inquiry",
            "pattern": "topic_re_matching",
            "priority": "high",
            "turns": [
                {
                    "user": "Hello, I need some help.",
                    "expect": {
                        "response_not_empty": True,
                    },
                },
                {
                    "user": "Can you help me with my account?",
                    "expect": {
                        "response_not_empty": True,
                        "response_contains_any": ["account", "help", "assist"],
                    },
                },
            ],
        })
        return scenarios

    for topic in topics:
        topic_name = topic.get("name", "unknown")
        topic_desc = topic.get("description", "")
        safe_name = topic_name.replace(" ", "_").lower()

        scenarios.append({
            "name": f"topic_routing_{safe_name}",
            "description": f"Route to topic '{topic_name}': {topic_desc}",
            "pattern": "topic_re_matching",
            "priority": "high",
            "turns": [
                {
                    "user": "Hello, I need some help.",
                    "expect": {
                        "response_not_empty": True,
                    },
                },
                {
                    "user": f"I need help with {topic_name.replace('_', ' ').lower()}.",
                    "expect": {
                        "response_not_empty": True,
                        "topic_contains": safe_name.split("_")[0],
                    },
                },
            ],
        })

    return scenarios


def generate_context_preservation(agent: Dict[str, Any]) -> List[Dict]:
    """Generate context preservation scenarios."""
    return [{
        "name": f"context_preservation_{agent['name']}",
        "description": f"Verify {agent['name']} retains context across turns",
        "pattern": "context_preservation",
        "priority": "high",
        "turns": [
            {
                "user": "My name is Alex and I need help with order number 12345.",
                "expect": {
                    "response_not_empty": True,
                },
            },
            {
                "user": "What is the status of my order?",
                "expect": {
                    "response_not_empty": True,
                    "context_retained": True,
                    "no_re_ask_for": "order number",
                },
            },
            {
                "user": "Can you remind me what order we were discussing?",
                "expect": {
                    "response_not_empty": True,
                    "response_contains_any": ["12345", "order"],
                },
            },
        ],
    }]


def generate_escalation_flows(agent: Dict[str, Any]) -> List[Dict]:
    """Generate escalation flow scenarios."""
    return [{
        "name": f"escalation_frustration_{agent['name']}",
        "description": f"Verify {agent['name']} escalates on repeated frustration",
        "pattern": "multi_turn_escalation",
        "priority": "high",
        "turns": [
            {
                "user": "This is not working at all! I've been trying for hours!",
                "expect": {
                    "response_not_empty": True,
                    "response_acknowledges_error": True,
                },
            },
            {
                "user": "I want to speak to a real person right now! This is unacceptable!",
                "expect": {
                    "response_not_empty": True,
                    "escalation_triggered": True,
                },
            },
        ],
    }]


def generate_guardrail_testing(agent: Dict[str, Any]) -> List[Dict]:
    """Generate guardrail testing scenarios."""
    return [
        {
            "name": f"guardrail_outofscope_{agent['name']}",
            "description": f"Verify {agent['name']} declines out-of-scope requests",
            "pattern": "guardrail_testing",
            "priority": "medium",
            "turns": [
                {
                    "user": "Hello, I need some help.",
                    "expect": {
                        "response_not_empty": True,
                    },
                },
                {
                    "user": "Can you write me a poem about the weather?",
                    "expect": {
                        "response_not_empty": True,
                        "response_declines_gracefully": True,
                    },
                },
            ],
        },
        {
            "name": f"guardrail_recovery_{agent['name']}",
            "description": f"Verify {agent['name']} recovers after guardrail trigger",
            "pattern": "guardrail_testing",
            "priority": "medium",
            "turns": [
                {
                    "user": "Tell me something completely unrelated to your job.",
                    "expect": {
                        "response_not_empty": True,
                        "guardrail_triggered": True,
                    },
                },
                {
                    "user": "OK sorry, can you actually help me with my account?",
                    "expect": {
                        "response_not_empty": True,
                        "resumes_normal": True,
                    },
                },
            ],
        },
    ]


def generate_action_chain(agent: Dict[str, Any]) -> List[Dict]:
    """Generate action chain scenarios."""
    actions = agent.get("actions", [])
    if not actions:
        return [{
            "name": f"action_generic_{agent['name']}",
            "description": f"Verify {agent['name']} can invoke an action",
            "pattern": "action_chain",
            "priority": "high",
            "turns": [
                {
                    "user": "Can you look up my account information?",
                    "expect": {
                        "response_not_empty": True,
                    },
                },
                {
                    "user": "Please check order number 12345.",
                    "expect": {
                        "response_not_empty": True,
                        "has_action_result": True,
                    },
                },
                {
                    "user": "Can you also check if there are any related cases?",
                    "expect": {
                        "response_not_empty": True,
                        "action_uses_prior_output": True,
                    },
                },
            ],
        }]

    scenarios = []
    for action in actions[:3]:  # Limit to first 3 actions
        action_name = action.get("name", "unknown")
        safe_name = action_name.replace(" ", "_").lower()
        scenarios.append({
            "name": f"action_chain_{safe_name}",
            "description": f"Invoke action '{action_name}' and verify results",
            "pattern": "action_chain",
            "priority": "high",
            "turns": [
                {
                    "user": "I need help.",
                    "expect": {"response_not_empty": True},
                },
                {
                    "user": f"Please run {action_name.replace('_', ' ')}.",
                    "expect": {
                        "response_not_empty": True,
                        "action_invoked": action_name,
                    },
                },
                {
                    "user": "What did that show?",
                    "expect": {
                        "response_not_empty": True,
                        "context_retained": True,
                    },
                },
            ],
        })
    return scenarios


def generate_error_recovery(agent: Dict[str, Any]) -> List[Dict]:
    """Generate error recovery scenarios."""
    return [{
        "name": f"error_recovery_{agent['name']}",
        "description": f"Verify {agent['name']} recovers from bad input",
        "pattern": "error_recovery",
        "priority": "medium",
        "turns": [
            {
                "user": "asdfghjkl zxcvbnm qwerty 12345",
                "expect": {
                    "response_not_empty": True,
                    "response_offers_help": True,
                },
            },
            {
                "user": "Sorry, I meant to ask about my account.",
                "expect": {
                    "response_not_empty": True,
                    "resumes_normal": True,
                },
            },
            {
                "user": "Can you check my recent orders?",
                "expect": {
                    "response_not_empty": True,
                    "context_retained": True,
                },
            },
        ],
    }]


def generate_cross_topic_scenarios(agent: Dict[str, Any]) -> List[Dict]:
    """Generate cross-topic switching scenarios — test agent ability to handle topic changes mid-conversation."""
    scenarios = []
    topics = agent.get("topics", [])

    if len(topics) < 2:
        return scenarios  # Need at least 2 topics to test switching

    # Sort topics by action count (most interesting first)
    scored_topics = []
    for t in topics:
        action_count = len(t.get("actions", []))
        scored_topics.append((action_count, t))
    scored_topics.sort(key=lambda x: x[0], reverse=True)
    ranked_topics = [t for _, t in scored_topics]

    # Generate pairs from top topics (limit to 3 pairs)
    pairs = []
    for i in range(len(ranked_topics)):
        for j in range(i + 1, len(ranked_topics)):
            pairs.append((ranked_topics[i], ranked_topics[j]))
    pairs = pairs[:3]

    for topic_a, topic_b in pairs:
        name_a = topic_a.get("name", "unknown_a")
        name_b = topic_b.get("name", "unknown_b")
        safe_a = name_a.replace(" ", "_").lower()
        safe_b = name_b.replace(" ", "_").lower()
        desc_a = topic_a.get("description", name_a.replace("_", " "))
        desc_b = topic_b.get("description", name_b.replace("_", " "))

        scenarios.append({
            "name": f"cross_topic_{safe_a}_to_{safe_b}",
            "description": f"Switch from topic '{name_a}' to '{name_b}' mid-conversation",
            "pattern": "cross_topic_switch",
            "priority": "high",
            "turns": [
                {
                    "user": f"I need help with {name_a.replace('_', ' ').lower()}.",
                    "expect": {
                        "response_not_empty": True,
                        "topic_contains": safe_a.split("_")[0],
                    },
                },
                {
                    "user": f"Actually, I'd rather ask about {name_b.replace('_', ' ').lower()} instead.",
                    "expect": {
                        "response_not_empty": True,
                        "response_acknowledges_change": True,
                        "topic_contains": safe_b.split("_")[0],
                    },
                },
                {
                    "user": f"Can you continue helping me with {name_b.replace('_', ' ').lower()}?",
                    "expect": {
                        "response_not_empty": True,
                        "context_retained": True,
                    },
                },
            ],
        })

    return scenarios


GENERATORS = {
    "topic_routing": generate_topic_routing,
    "context_preservation": generate_context_preservation,
    "escalation_flows": generate_escalation_flows,
    "guardrail_testing": generate_guardrail_testing,
    "action_chain": generate_action_chain,
    "error_recovery": generate_error_recovery,
    "cross_topic_switch": generate_cross_topic_scenarios,
}


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def generate_scenarios(metadata: Dict, patterns: List[str]) -> Dict:
    """Generate YAML-compatible scenario document from agent metadata."""
    all_scenarios = []

    agents = metadata.get("agents", [])
    if not agents:
        print("WARNING: No agents found in metadata.", file=sys.stderr)
        return {"apiVersion": "v1", "kind": "MultiTurnTestScenario", "metadata": {}, "scenarios": []}

    for agent in agents:
        for pattern in patterns:
            generator = GENERATORS.get(pattern)
            if generator:
                scenarios = generator(agent)
                all_scenarios.extend(scenarios)

    return {
        "apiVersion": "v1",
        "kind": "MultiTurnTestScenario",
        "metadata": {
            "name": "auto-generated-scenarios",
            "testMode": "multi-turn-api",
            "description": f"Auto-generated from {len(agents)} agent(s) with {len(patterns)} pattern(s)",
        },
        "scenarios": all_scenarios,
    }


def generate_categorized_output(doc: Dict, output_dir: str) -> Dict[str, str]:
    """
    Write separate YAML files per scenario category into output_dir.

    Returns dict mapping category name to output file path.
    """
    scenarios = doc.get("scenarios", [])
    categories = {}
    for s in scenarios:
        cat = s.get("pattern", "uncategorized")
        categories.setdefault(cat, []).append(s)

    os.makedirs(output_dir, exist_ok=True)
    written = {}

    for cat_name, cat_scenarios in categories.items():
        cat_doc = {
            "apiVersion": "v1",
            "kind": "MultiTurnTestScenario",
            "metadata": {
                "name": f"scenarios-{cat_name}",
                "testMode": "multi-turn-api",
                "description": f"{cat_name} scenarios ({len(cat_scenarios)} total)",
                "category": cat_name,
            },
            "scenarios": cat_scenarios,
        }
        filename = f"scenarios-{cat_name}.yaml"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w") as f:
            yaml.dump(cat_doc, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        written[cat_name] = filepath

    return written


def main():
    parser = argparse.ArgumentParser(
        description="Generate multi-turn test scenarios from agent metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 generate_multi_turn_scenarios.py --metadata agent.json --output tests.yaml
  python3 generate_multi_turn_scenarios.py --metadata agent.json --output tests.yaml --patterns topic_routing escalation_flows
  python3 agent_discovery.py local --project-dir . | python3 generate_multi_turn_scenarios.py --metadata - --output tests.yaml
""",
    )

    parser.add_argument("--metadata", required=True,
                        help="Path to agent metadata JSON file (or '-' for stdin)")
    parser.add_argument("--output", required=True,
                        help="Output YAML scenario file path")
    parser.add_argument("--patterns", nargs="+", default=ALL_PATTERNS,
                        choices=ALL_PATTERNS,
                        help=f"Test patterns to generate (default: all)")
    parser.add_argument("--categorized", action="store_true",
                        help="Output separate YAML files per category into --output directory")
    parser.add_argument("--scenarios-per-topic", type=int, default=2,
                        help="Number of scenarios to generate per topic (default: 2)")
    parser.add_argument("--cross-topic", action="store_true",
                        help="Include cross-topic switching scenarios")

    args = parser.parse_args()

    # If --cross-topic is specified, ensure the pattern is included
    if args.cross_topic and "cross_topic_switch" not in args.patterns:
        args.patterns = list(args.patterns) + ["cross_topic_switch"]

    # Load metadata
    try:
        if args.metadata == "-":
            metadata = json.load(sys.stdin)
        else:
            with open(args.metadata) as f:
                metadata = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"ERROR: Failed to load metadata: {e}", file=sys.stderr)
        sys.exit(2)

    # Generate
    doc = generate_scenarios(metadata, args.patterns)

    scenario_count = len(doc.get("scenarios", []))

    # Write output
    if args.categorized:
        output_dir = args.output
        written = generate_categorized_output(doc, output_dir)
        for cat_name, filepath in written.items():
            cat_count = len([s for s in doc["scenarios"] if s.get("pattern") == cat_name])
            print(f"  {cat_name}: {cat_count} scenario(s) → {filepath}", file=sys.stderr)
        # Also write combined file
        combined_path = os.path.join(output_dir, "all-scenarios.yaml")
        with open(combined_path, "w") as f:
            yaml.dump(doc, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        print(f"Generated {scenario_count} scenario(s) across {len(written)} categories → {output_dir}/", file=sys.stderr)
    else:
        with open(args.output, "w") as f:
            yaml.dump(doc, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        print(f"Generated {scenario_count} scenario(s) → {args.output}", file=sys.stderr)

    if scenario_count == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
