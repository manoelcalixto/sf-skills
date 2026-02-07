#!/usr/bin/env python3
"""
Agent Discovery — Metadata Introspection for Salesforce Agents

Discovers and introspects Agentforce agent metadata from either local SFDX
project files (XML parsing) or a live Salesforce org (Tooling API queries).

Usage:
    # Local mode — parse SFDX project metadata:
    python3 agent_discovery.py local --project-dir /path/to/sfdx-project

    # Local mode — filter by agent name:
    python3 agent_discovery.py local --project-dir /path/to/project --agent-name MyAgent

    # Live mode — query org via sf CLI:
    python3 agent_discovery.py live --target-org my-org-alias

    # Live mode — filter by agent name:
    python3 agent_discovery.py live --target-org my-org-alias --agent-name MyAgent

Output:
    JSON to stdout with discovered agent metadata:
    {
      "mode": "local|live",
      "agents": [
        {
          "name": "MyAgent",
          "type": "BotDefinition|GenAiPlanner",
          "id": "0Xx...",
          "description": "...",
          "topics": [...],
          "actions": [...]
        }
      ]
    }

Dependencies:
    - Python 3.8+ standard library only (xml.etree, subprocess, json, argparse)
    - For live mode: sf CLI v2 installed and authenticated

Author: Jag Valaiyapathy
License: MIT
"""

import argparse
import glob
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════
# Local Mode — SFDX XML Parsing
# ═══════════════════════════════════════════════════════════════════════════

def discover_local(project_dir: str, agent_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Discover agents from local SFDX project metadata (XML files).

    Scans for:
    - BotDefinition (force-app/**/bots/*/*.bot-meta.xml)
    - GenAiPlanner (force-app/**/genAiPlanners/*/*.genAiPlanner-meta.xml)
    - GenAiFunction (force-app/**/genAiFunctions/*/*.genAiFunction-meta.xml)

    Args:
        project_dir: Path to SFDX project root.
        agent_name: Optional filter — only return agents matching this name.

    Returns:
        List of agent metadata dicts.
    """
    agents = []
    project = Path(project_dir)

    # Discover BotDefinition XML files
    bot_patterns = [
        str(project / "force-app" / "**" / "bots" / "**" / "*.bot-meta.xml"),
        str(project / "**" / "bots" / "**" / "*.bot-meta.xml"),
    ]
    for pattern in bot_patterns:
        for xml_path in glob.glob(pattern, recursive=True):
            agent = _parse_bot_xml(xml_path)
            if agent:
                agents.append(agent)

    # Discover GenAiPlanner XML files
    planner_patterns = [
        str(project / "force-app" / "**" / "genAiPlanners" / "**" / "*.genAiPlanner-meta.xml"),
        str(project / "**" / "genAiPlanners" / "**" / "*.genAiPlanner-meta.xml"),
    ]
    for pattern in planner_patterns:
        for xml_path in glob.glob(pattern, recursive=True):
            agent = _parse_planner_xml(xml_path)
            if agent:
                agents.append(agent)

    # Discover GenAiFunction XML files (actions)
    func_patterns = [
        str(project / "force-app" / "**" / "genAiFunctions" / "**" / "*.genAiFunction-meta.xml"),
        str(project / "**" / "genAiFunctions" / "**" / "*.genAiFunction-meta.xml"),
    ]
    functions = []
    for pattern in func_patterns:
        for xml_path in glob.glob(pattern, recursive=True):
            func = _parse_function_xml(xml_path)
            if func:
                functions.append(func)

    # Attach functions as standalone entries if no parent agent found
    if functions and not agents:
        agents.append({
            "name": "standalone_functions",
            "type": "GenAiFunction",
            "id": "",
            "description": "Standalone GenAI functions found in project",
            "topics": [],
            "actions": functions,
        })

    # Deduplicate by name
    seen = set()
    unique_agents = []
    for a in agents:
        if a["name"] not in seen:
            seen.add(a["name"])
            unique_agents.append(a)

    # Apply name filter
    if agent_name:
        unique_agents = [
            a for a in unique_agents
            if agent_name.lower() in a["name"].lower()
        ]

    return unique_agents


def _parse_bot_xml(xml_path: str) -> Optional[Dict[str, Any]]:
    """Parse a BotDefinition XML file."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        ns = _get_namespace(root)

        name = Path(xml_path).parent.name
        description = _find_text(root, "description", ns) or ""
        label = _find_text(root, "label", ns) or _find_text(root, "masterLabel", ns) or name

        topics = []
        for version in root.findall(f".//{ns}botVersions") if ns else root.findall(".//botVersions"):
            for topic in version.findall(f"{ns}botDialogs") if ns else version.findall("botDialogs"):
                topic_name = _find_text(topic, "developerName", ns) or ""
                topic_desc = _find_text(topic, "description", ns) or ""
                if topic_name:
                    topics.append({"name": topic_name, "description": topic_desc})

        return {
            "name": name,
            "type": "BotDefinition",
            "id": "",
            "label": label,
            "description": description,
            "topics": topics,
            "actions": [],
            "source_path": xml_path,
        }
    except ET.ParseError as e:
        print(f"WARNING: Failed to parse {xml_path}: {e}", file=sys.stderr)
        return None


def _parse_planner_xml(xml_path: str) -> Optional[Dict[str, Any]]:
    """Parse a GenAiPlanner XML file."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        ns = _get_namespace(root)

        name = Path(xml_path).stem.replace(".genAiPlanner-meta", "")
        description = _find_text(root, "description", ns) or ""
        label = _find_text(root, "masterLabel", ns) or name

        return {
            "name": name,
            "type": "GenAiPlanner",
            "id": "",
            "label": label,
            "description": description,
            "topics": [],
            "actions": [],
            "source_path": xml_path,
        }
    except ET.ParseError as e:
        print(f"WARNING: Failed to parse {xml_path}: {e}", file=sys.stderr)
        return None


def _parse_function_xml(xml_path: str) -> Optional[Dict[str, str]]:
    """Parse a GenAiFunction XML file into a simple action dict."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        ns = _get_namespace(root)

        name = Path(xml_path).stem.replace(".genAiFunction-meta", "")
        description = _find_text(root, "description", ns) or ""

        return {"name": name, "description": description}
    except ET.ParseError as e:
        print(f"WARNING: Failed to parse {xml_path}: {e}", file=sys.stderr)
        return None


def _get_namespace(root: ET.Element) -> str:
    """Extract XML namespace from root element tag."""
    tag = root.tag
    if tag.startswith("{"):
        ns_end = tag.index("}")
        return tag[:ns_end + 1]
    return ""


def _find_text(element: ET.Element, tag: str, ns: str) -> Optional[str]:
    """Find text of a child element, with namespace support."""
    child = element.find(f"{ns}{tag}")
    if child is not None and child.text:
        return child.text.strip()
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Live Mode — Tooling API Queries
# ═══════════════════════════════════════════════════════════════════════════

def discover_live(target_org: str, agent_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Discover agents from a live Salesforce org via sf CLI Tooling API.

    Queries:
    - BotDefinition (Id, DeveloperName, Description)
    - GenAiPlanner (Id, DeveloperName, Description, MasterLabel)
    - GenAiFunction (Id, DeveloperName, Description)

    Args:
        target_org: sf CLI org alias or username.
        agent_name: Optional filter — only return agents matching this name.

    Returns:
        List of agent metadata dicts.
    """
    agents = []

    # Query BotDefinition
    name_filter = f" WHERE DeveloperName LIKE '%{agent_name}%'" if agent_name else ""
    bots = _sf_tooling_query(
        f"SELECT Id, DeveloperName, Description FROM BotDefinition{name_filter} LIMIT 200",
        target_org,
    )
    for bot in bots:
        agents.append({
            "name": bot.get("DeveloperName", ""),
            "type": "BotDefinition",
            "id": bot.get("Id", ""),
            "description": bot.get("Description") or "",
            "topics": [],
            "actions": [],
        })

    # Query GenAiPlanner
    planners = _sf_tooling_query(
        f"SELECT Id, DeveloperName, Description, MasterLabel FROM GenAiPlanner{name_filter} LIMIT 200",
        target_org,
    )
    for planner in planners:
        agents.append({
            "name": planner.get("DeveloperName", ""),
            "type": "GenAiPlanner",
            "id": planner.get("Id", ""),
            "label": planner.get("MasterLabel", ""),
            "description": planner.get("Description") or "",
            "topics": [],
            "actions": [],
        })

    # Query GenAiFunction (actions)
    functions = _sf_tooling_query(
        "SELECT Id, DeveloperName, Description FROM GenAiFunction LIMIT 200",
        target_org,
    )
    for func in functions:
        # Attach as actions to any existing agent, or add standalone
        action = {
            "name": func.get("DeveloperName", ""),
            "id": func.get("Id", ""),
            "description": func.get("Description") or "",
        }
        if agents:
            agents[0].setdefault("actions", []).append(action)
        else:
            agents.append({
                "name": "discovered_functions",
                "type": "GenAiFunction",
                "id": "",
                "description": "Functions discovered in org",
                "topics": [],
                "actions": [action],
            })

    return agents


def _sf_tooling_query(query: str, target_org: str) -> List[Dict]:
    """Run a Tooling API SOQL query via sf CLI and return records."""
    try:
        result = subprocess.run(
            [
                "sf", "data", "query",
                "--use-tooling-api",
                "--query", query,
                "--target-org", target_org,
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            # Some objects may not exist — that's OK
            if "INVALID_TYPE" in stderr or "sObject type" in stderr:
                return []
            print(f"WARNING: sf query failed: {stderr[:200]}", file=sys.stderr)
            return []

        data = json.loads(result.stdout)
        return data.get("result", {}).get("records", [])

    except subprocess.TimeoutExpired:
        print(f"WARNING: sf query timed out: {query[:80]}", file=sys.stderr)
        return []
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"WARNING: sf query error: {e}", file=sys.stderr)
        return []


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Agent Discovery — Discover Agentforce agent metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Local SFDX project:
  python3 agent_discovery.py local --project-dir ./my-project

  # Live org:
  python3 agent_discovery.py live --target-org DevHub

  # Filter by name:
  python3 agent_discovery.py local --project-dir . --agent-name CustomerService
""",
    )

    subparsers = parser.add_subparsers(dest="mode", help="Discovery mode")
    subparsers.required = True

    # Local subcommand
    local_parser = subparsers.add_parser("local", help="Parse local SFDX project metadata")
    local_parser.add_argument("--project-dir", required=True,
                              help="Path to SFDX project root directory")
    local_parser.add_argument("--agent-name", default=None,
                              help="Filter by agent name (case-insensitive substring)")

    # Live subcommand
    live_parser = subparsers.add_parser("live", help="Query live Salesforce org via Tooling API")
    live_parser.add_argument("--target-org", required=True,
                             help="sf CLI org alias or username")
    live_parser.add_argument("--agent-name", default=None,
                             help="Filter by agent name (case-insensitive substring)")

    args = parser.parse_args()

    if args.mode == "local":
        project_dir = args.project_dir
        if not os.path.isdir(project_dir):
            print(f"ERROR: Project directory not found: {project_dir}", file=sys.stderr)
            sys.exit(1)
        agents = discover_local(project_dir, args.agent_name)
    elif args.mode == "live":
        agents = discover_live(args.target_org, args.agent_name)
    else:
        parser.print_help()
        sys.exit(1)

    output = {
        "mode": args.mode,
        "agent_count": len(agents),
        "agents": agents,
    }

    print(json.dumps(output, indent=2))

    if not agents:
        print("WARNING: No agents discovered.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
