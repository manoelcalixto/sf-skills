#!/usr/bin/env python3
"""
Agent Discovery — Salesforce Agentforce Metadata Introspection

Discovers and introspects Agentforce agent metadata from either local SFDX
project files (XML parsing) or a live Salesforce org (Tooling API queries).
Works for ANY Salesforce agent — no customer-specific data baked in.

Two modes:
  local — Parse BotDefinition, GenAiPlanner, and GenAiFunction XML files
          from a local sfdx-project directory.
  live  — Query the Tooling API via `sf data query --use-tooling-api`
          for the same metadata types in a running org.

Usage:
    # Local mode — scan an entire project
    python3 agent_discovery.py local --project-dir /path/to/project

    # Local mode — filter to a specific agent
    python3 agent_discovery.py local --project-dir /path/to/project --agent-name MyAgent

    # Live mode — query an org
    python3 agent_discovery.py live --target-org my-org

    # Live mode — filter to a specific agent
    python3 agent_discovery.py live --target-org my-org --agent-name MyAgent

Output (JSON to stdout):
    {
      "mode": "local|live",
      "agents": [
        {
          "name": "MyAgent",
          "type": "BotDefinition|GenAiPlanner|GenAiFunction",
          "id": null,
          "description": "...",
          "label": "...",
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
# XML Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _get_namespace(root: ET.Element) -> str:
    """Extract XML namespace prefix (including braces) from root element tag.

    Salesforce metadata XML typically uses:
        xmlns="http://soap.sforce.com/2006/04/metadata"
    This returns the namespace in {uri} form for ElementTree lookups.
    """
    tag = root.tag
    if tag.startswith("{"):
        return tag[: tag.index("}") + 1]
    return ""


def _find_text(element: ET.Element, tag: str, ns: str) -> Optional[str]:
    """Find text of a direct child element, with namespace support.

    Args:
        element: Parent XML element to search within.
        tag: Local name of the child element (e.g. "description").
        ns: Namespace prefix in {uri} form, or empty string.

    Returns:
        Stripped text content, or None if not found/empty.
    """
    child = element.find(f"{ns}{tag}")
    if child is not None and child.text:
        return child.text.strip()
    return None


def _find_all_ns(element: ET.Element, tag: str, ns: str) -> List[ET.Element]:
    """Find all direct children matching tag, with namespace support."""
    return element.findall(f"{ns}{tag}")


def _find_descendants(root: ET.Element, tag: str, ns: str) -> List[ET.Element]:
    """Find all descendants matching tag (recursive), with namespace support."""
    return root.findall(f".//{ns}{tag}")


# ═══════════════════════════════════════════════════════════════════════════
# Local Mode — SFDX XML Parsing
# ═══════════════════════════════════════════════════════════════════════════

def _parse_bot_xml(xml_path: str) -> Optional[Dict[str, Any]]:
    """Parse a BotDefinition .bot-meta.xml file.

    Extracts the agent name from the parent directory, plus description,
    label, dialog topics from botVersions/botDialogs.
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        ns = _get_namespace(root)

        # BotDefinition name comes from the directory name (convention)
        name = Path(xml_path).parent.name
        description = _find_text(root, "description", ns)
        label = (
            _find_text(root, "label", ns)
            or _find_text(root, "masterLabel", ns)
            or name
        )

        # Extract topics from botVersions > botDialogs
        topics: List[Dict[str, Any]] = []
        for version_el in _find_descendants(root, "botVersions", ns):
            for dialog_el in _find_all_ns(version_el, "botDialogs", ns):
                topic_name = _find_text(dialog_el, "developerName", ns)
                topic_label = (
                    _find_text(dialog_el, "label", ns)
                    or _find_text(dialog_el, "masterLabel", ns)
                )
                topic_desc = _find_text(dialog_el, "description", ns)
                if topic_name:
                    entry: Dict[str, Any] = {"name": topic_name}
                    if topic_label:
                        entry["label"] = topic_label
                    if topic_desc:
                        entry["description"] = topic_desc
                    topics.append(entry)

        return {
            "name": name,
            "type": "BotDefinition",
            "id": None,
            "description": description,
            "label": label,
            "topics": topics,
            "actions": [],
            "source_path": xml_path,
        }
    except ET.ParseError as e:
        print(f"WARNING: Failed to parse {xml_path}: {e}", file=sys.stderr)
        return None


def _parse_planner_xml(xml_path: str) -> Optional[Dict[str, Any]]:
    """Parse a GenAiPlanner .genAiPlanner-meta.xml file.

    Extracts planner name, label, description, and associated
    genAiPlannerFunctions (action references).
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        ns = _get_namespace(root)

        name = Path(xml_path).stem.replace(".genAiPlanner-meta", "")
        description = _find_text(root, "description", ns)
        label = _find_text(root, "masterLabel", ns) or name

        # Extract actions from genAiPlannerFunctions
        actions: List[Dict[str, Any]] = []
        for fn_el in _find_all_ns(root, "genAiPlannerFunctions", ns):
            fn_name = (
                _find_text(fn_el, "genAiFunction", ns)
                or _find_text(fn_el, "functionName", ns)
            )
            if fn_name:
                actions.append({"name": fn_name})

        return {
            "name": name,
            "type": "GenAiPlanner",
            "id": None,
            "description": description,
            "label": label,
            "topics": [],
            "actions": actions,
            "source_path": xml_path,
        }
    except ET.ParseError as e:
        print(f"WARNING: Failed to parse {xml_path}: {e}", file=sys.stderr)
        return None


def _parse_function_xml(xml_path: str) -> Optional[Dict[str, Any]]:
    """Parse a GenAiFunction .genAiFunction-meta.xml file.

    Extracts function name, description, label, and the invocable
    action reference if present.
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        ns = _get_namespace(root)

        name = Path(xml_path).stem.replace(".genAiFunction-meta", "")
        description = _find_text(root, "description", ns)
        label = _find_text(root, "masterLabel", ns) or name

        # Extract invocable action reference
        actions: List[Dict[str, Any]] = []
        action_type = _find_text(root, "invocableActionType", ns)
        action_name = _find_text(root, "invocableActionName", ns)
        if action_type or action_name:
            actions.append({
                "type": action_type,
                "name": action_name,
            })

        return {
            "name": name,
            "type": "GenAiFunction",
            "id": None,
            "description": description,
            "label": label,
            "topics": [],
            "actions": actions,
            "source_path": xml_path,
        }
    except ET.ParseError as e:
        print(f"WARNING: Failed to parse {xml_path}: {e}", file=sys.stderr)
        return None


def _parse_planner_bundle_xml(xml_path: str) -> Optional[Dict[str, Any]]:
    """Parse a GenAiPlannerBundle .genAiPlannerBundle file.

    Extracts the full agent topology including:
      - localTopics with instructions, local actions, and action links
      - attributeMappings for context variables (ContextVariable type)
      - plannerActions (root-level global actions)
      - localActionLinks (root-level function references)

    The GenAiPlannerBundle is the richest metadata type — it contains the
    complete agent definition with topics, actions, instructions, and
    variable bindings all in one file.
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        ns = _get_namespace(root)

        # Name from directory (e.g., Product_Troubleshooting2_v2_v3_v4_v5_v6)
        name = Path(xml_path).parent.name
        description = _find_text(root, "description", ns)
        label = _find_text(root, "masterLabel", ns) or name

        # --- Context Variables from attributeMappings ---
        context_variables: List[str] = []
        seen_ctx_vars: set = set()
        for mapping_el in _find_all_ns(root, "attributeMappings", ns):
            mapping_type = _find_text(mapping_el, "mappingType", ns)
            if mapping_type == "ContextVariable":
                target = _find_text(mapping_el, "mappingTargetName", ns)
                if target and target not in seen_ctx_vars:
                    seen_ctx_vars.add(target)
                    context_variables.append(target)

        # --- Topics from localTopics ---
        topics: List[Dict[str, Any]] = []
        for topic_el in _find_all_ns(root, "localTopics", ns):
            # Prefer localDeveloperName (clean) over developerName (has UUID suffix)
            topic_name = (
                _find_text(topic_el, "localDeveloperName", ns)
                or _find_text(topic_el, "developerName", ns)
            )
            topic_label = _find_text(topic_el, "masterLabel", ns)
            topic_desc = _find_text(topic_el, "description", ns)
            topic_scope = _find_text(topic_el, "scope", ns)
            can_escalate_str = _find_text(topic_el, "canEscalate", ns)
            can_escalate = can_escalate_str == "true" if can_escalate_str else False

            # Collect instructions
            instructions: List[str] = []
            for instr_el in _find_all_ns(topic_el, "genAiPluginInstructions", ns):
                instr_text = _find_text(instr_el, "description", ns)
                if instr_text:
                    instructions.append(instr_text)

            # Collect local actions within this topic
            topic_actions: List[Dict[str, Any]] = []
            for action_el in _find_all_ns(topic_el, "localActions", ns):
                action_entry: Dict[str, Any] = {}
                a_name = (
                    _find_text(action_el, "localDeveloperName", ns)
                    or _find_text(action_el, "developerName", ns)
                )
                if a_name:
                    action_entry["name"] = a_name
                a_label = _find_text(action_el, "masterLabel", ns)
                if a_label:
                    action_entry["label"] = a_label
                a_desc = _find_text(action_el, "description", ns)
                if a_desc:
                    action_entry["description"] = a_desc
                a_target = _find_text(action_el, "invocationTarget", ns)
                if a_target:
                    action_entry["invocationTarget"] = a_target
                a_type = _find_text(action_el, "invocationTargetType", ns)
                if a_type:
                    action_entry["invocationTargetType"] = a_type
                if action_entry:
                    topic_actions.append(action_entry)

            # Collect local action link references within this topic
            topic_action_links: List[str] = []
            for link_el in _find_all_ns(topic_el, "localActionLinks", ns):
                fn_name = _find_text(link_el, "functionName", ns)
                if fn_name:
                    topic_action_links.append(fn_name)

            entry: Dict[str, Any] = {"name": topic_name}
            if topic_label:
                entry["label"] = topic_label
            if topic_desc:
                entry["description"] = topic_desc
            if topic_scope:
                entry["scope"] = topic_scope
            entry["canEscalate"] = can_escalate
            if instructions:
                entry["instructions"] = instructions
            if topic_actions:
                entry["actions"] = topic_actions
            if topic_action_links:
                entry["actionLinks"] = topic_action_links
            topics.append(entry)

        # --- Root-level actions ---
        actions: List[Dict[str, Any]] = []

        # plannerActions (global actions available across all topics)
        for pa_el in _find_all_ns(root, "plannerActions", ns):
            pa_entry: Dict[str, Any] = {}
            pa_name = (
                _find_text(pa_el, "localDeveloperName", ns)
                or _find_text(pa_el, "developerName", ns)
            )
            if pa_name:
                pa_entry["name"] = pa_name
            pa_label = _find_text(pa_el, "masterLabel", ns)
            if pa_label:
                pa_entry["label"] = pa_label
            pa_desc = _find_text(pa_el, "description", ns)
            if pa_desc:
                pa_entry["description"] = pa_desc
            pa_target = _find_text(pa_el, "invocationTarget", ns)
            if pa_target:
                pa_entry["invocationTarget"] = pa_target
            pa_type = _find_text(pa_el, "invocationTargetType", ns)
            if pa_type:
                pa_entry["invocationTargetType"] = pa_type
            if pa_entry:
                actions.append(pa_entry)

        # localActionLinks at root level (global function references)
        for link_el in _find_all_ns(root, "localActionLinks", ns):
            fn_name = _find_text(link_el, "genAiFunctionName", ns)
            if fn_name:
                actions.append({"name": fn_name, "type": "actionLink"})

        return {
            "name": name,
            "type": "GenAiPlannerBundle",
            "id": None,
            "description": description,
            "label": label,
            "topics": topics,
            "actions": actions,
            "source_path": xml_path,
            "context_variables": context_variables,
        }
    except ET.ParseError as e:
        print(f"WARNING: Failed to parse {xml_path}: {e}", file=sys.stderr)
        return None


def discover_local(project_dir: str, agent_name: Optional[str] = None) -> Dict[str, Any]:
    """Discover agents from local SFDX project metadata (XML files).

    Scans for BotDefinition, GenAiPlanner, and GenAiFunction XML files
    under the project directory. Uses recursive glob patterns to handle
    various source directory layouts (force-app/, src/, etc.).

    Args:
        project_dir: Path to SFDX project root.
        agent_name: Optional filter — only return agents whose name or
                    label matches (case-insensitive).

    Returns:
        Discovery result dict: {"mode": "local", "agents": [...]}.
    """
    project = Path(project_dir).resolve()
    if not project.is_dir():
        print(f"ERROR: Project directory not found: {project}", file=sys.stderr)
        sys.exit(1)

    # Warn if no sfdx-project.json (but scan anyway)
    if not (project / "sfdx-project.json").exists():
        print(
            f"WARNING: No sfdx-project.json at {project}. "
            "Scanning anyway but results may be incomplete.",
            file=sys.stderr,
        )

    agents: List[Dict[str, Any]] = []
    seen_paths: set = set()

    # Metadata type → (glob suffix, parser function)
    scan_config = [
        ("*.bot-meta.xml", _parse_bot_xml),
        ("*.genAiPlanner-meta.xml", _parse_planner_xml),
        ("*.genAiFunction-meta.xml", _parse_function_xml),
        ("*.genAiPlannerBundle", _parse_planner_bundle_xml),
    ]

    for suffix, parser in scan_config:
        pattern = str(project / "**" / suffix)
        for xml_path in glob.glob(pattern, recursive=True):
            # Deduplicate by resolved path (glob may match same file twice)
            resolved = str(Path(xml_path).resolve())
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)

            agent = parser(xml_path)
            if agent:
                agents.append(agent)

    # Apply name filter (case-insensitive match on name or label)
    if agent_name:
        filter_lower = agent_name.lower()
        agents = [
            a for a in agents
            if filter_lower in a["name"].lower()
            or filter_lower in (a.get("label") or "").lower()
        ]

    return {"mode": "local", "agents": agents}


# ═══════════════════════════════════════════════════════════════════════════
# Live Mode — Tooling API Queries via sf CLI
# ═══════════════════════════════════════════════════════════════════════════

def _sf_tooling_query(query: str, target_org: str) -> List[Dict[str, Any]]:
    """Run a Tooling API SOQL query via sf CLI and return parsed records.

    Args:
        query: SOQL query string.
        target_org: sf CLI org alias or username.

    Returns:
        List of record dicts from the query result.
        Returns empty list on error (with warning to stderr).
    """
    cmd = [
        "sf", "data", "query",
        "--use-tooling-api",
        "--query", query,
        "--target-org", target_org,
        "--json",
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60
        )
    except FileNotFoundError:
        print(
            "ERROR: 'sf' CLI not found. Install from "
            "https://developer.salesforce.com/tools/salesforcecli",
            file=sys.stderr,
        )
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(
            f"WARNING: sf query timed out (60s): {query[:80]}...",
            file=sys.stderr,
        )
        return []

    if result.returncode != 0:
        # Parse error from stdout (sf CLI puts JSON errors there)
        err_msg = ""
        try:
            err_data = json.loads(result.stdout)
            err_msg = err_data.get("message", "")
        except (json.JSONDecodeError, KeyError):
            err_msg = result.stderr.strip() or result.stdout.strip()

        # INVALID_TYPE is expected when metadata type doesn't exist in the org
        if "INVALID_TYPE" in err_msg or "sObject type" in err_msg:
            return []

        print(f"WARNING: sf query failed: {err_msg[:200]}", file=sys.stderr)
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"WARNING: Failed to parse sf output: {e}", file=sys.stderr)
        return []

    return data.get("result", {}).get("records", [])


def _sf_data_query(query: str, target_org: str) -> List[Dict[str, Any]]:
    """Run a regular (non-Tooling) SOQL query via sf CLI and return parsed records.

    Fallback for objects like BotDefinition that may not be available via the
    Tooling API in all org configurations.

    Args:
        query: SOQL query string.
        target_org: sf CLI org alias or username.

    Returns:
        List of record dicts from the query result.
        Returns empty list on error (with warning to stderr).
    """
    cmd = [
        "sf", "data", "query",
        "--query", query,
        "--target-org", target_org,
        "--json",
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60
        )
    except FileNotFoundError:
        print(
            "ERROR: 'sf' CLI not found. Install from "
            "https://developer.salesforce.com/tools/salesforcecli",
            file=sys.stderr,
        )
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(
            f"WARNING: sf query timed out (60s): {query[:80]}...",
            file=sys.stderr,
        )
        return []

    if result.returncode != 0:
        err_msg = ""
        try:
            err_data = json.loads(result.stdout)
            err_msg = err_data.get("message", "")
        except (json.JSONDecodeError, KeyError):
            err_msg = result.stderr.strip() or result.stdout.strip()

        if "INVALID_TYPE" in err_msg or "sObject type" in err_msg:
            return []

        print(f"WARNING: sf data query failed: {err_msg[:200]}", file=sys.stderr)
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"WARNING: Failed to parse sf output: {e}", file=sys.stderr)
        return []

    return data.get("result", {}).get("records", [])


def discover_live(target_org: str, agent_name: Optional[str] = None) -> Dict[str, Any]:
    """Discover agents from a live Salesforce org via Tooling API.

    Queries BotDefinition, GenAiPlanner, and GenAiFunction objects.
    Each type becomes its own agent entry in the result.

    Args:
        target_org: sf CLI org alias or username.
        agent_name: Optional filter — WHERE DeveloperName = 'name'.

    Returns:
        Discovery result dict: {"mode": "live", "agents": [...]}.
    """
    agents: List[Dict[str, Any]] = []

    # Build WHERE clause for name filtering
    where = f" WHERE DeveloperName = '{agent_name}'" if agent_name else ""

    # --- BotDefinition ---
    bot_soql = (
        f"SELECT Id, DeveloperName, Description, MasterLabel "
        f"FROM BotDefinition{where} ORDER BY DeveloperName LIMIT 200"
    )
    bot_records = _sf_tooling_query(bot_soql, target_org)
    if not bot_records:
        print("INFO: BotDefinition not in Tooling API, trying regular API...", file=sys.stderr)
        bot_records = _sf_data_query(bot_soql, target_org)
    for rec in bot_records:
        agents.append({
            "name": rec.get("DeveloperName"),
            "type": "BotDefinition",
            "id": rec.get("Id"),
            "description": rec.get("Description"),
            "label": rec.get("MasterLabel"),
            "topics": [],
            "actions": [],
        })

    # --- GenAiPlanner ---
    planner_soql = (
        f"SELECT Id, DeveloperName, Description, MasterLabel "
        f"FROM GenAiPlanner{where} ORDER BY DeveloperName LIMIT 200"
    )
    for rec in _sf_tooling_query(planner_soql, target_org):
        agents.append({
            "name": rec.get("DeveloperName"),
            "type": "GenAiPlanner",
            "id": rec.get("Id"),
            "description": rec.get("Description"),
            "label": rec.get("MasterLabel"),
            "topics": [],
            "actions": [],
        })

    # --- GenAiFunction (each as its own entry) ---
    func_soql = (
        f"SELECT Id, DeveloperName, Description, MasterLabel "
        f"FROM GenAiFunction{where} ORDER BY DeveloperName LIMIT 200"
    )
    for rec in _sf_tooling_query(func_soql, target_org):
        agents.append({
            "name": rec.get("DeveloperName"),
            "type": "GenAiFunction",
            "id": rec.get("Id"),
            "description": rec.get("Description"),
            "label": rec.get("MasterLabel"),
            "topics": [],
            "actions": [],
        })

    return {"mode": "live", "agents": agents}


# ═══════════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser with local/live subcommands."""
    parser = argparse.ArgumentParser(
        prog="agent_discovery",
        description="Discover Salesforce Agentforce agent metadata from local files or a live org.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan a local SFDX project for all agents
  python3 agent_discovery.py local --project-dir ./my-project

  # Filter to a specific agent by developer name
  python3 agent_discovery.py local --project-dir ./my-project --agent-name Customer_Service

  # Query a live org for all agent metadata
  python3 agent_discovery.py live --target-org my-scratch-org

  # Query a live org for a specific agent
  python3 agent_discovery.py live --target-org my-scratch-org --agent-name Customer_Service
        """,
    )

    subparsers = parser.add_subparsers(dest="mode", help="Discovery mode")
    subparsers.required = True

    # Local subcommand
    local_parser = subparsers.add_parser(
        "local", help="Parse agent metadata from local SFDX project XML files"
    )
    local_parser.add_argument(
        "--project-dir", required=True,
        help="Path to the sfdx-project root directory",
    )
    local_parser.add_argument(
        "--agent-name", default=None,
        help="Filter results by agent name or label (case-insensitive substring)",
    )

    # Live subcommand
    live_parser = subparsers.add_parser(
        "live", help="Query agent metadata from a live Salesforce org via Tooling API"
    )
    live_parser.add_argument(
        "--target-org", required=True,
        help="sf CLI org alias or username",
    )
    live_parser.add_argument(
        "--agent-name", default=None,
        help="Filter results by agent DeveloperName (exact match)",
    )

    return parser


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if args.mode == "local":
        result = discover_local(args.project_dir, args.agent_name)
    elif args.mode == "live":
        result = discover_live(args.target_org, args.agent_name)
    else:
        parser.print_help()
        sys.exit(1)

    # Output JSON to stdout
    json.dump(result, sys.stdout, indent=2)
    print()  # trailing newline for clean terminal output

    # Warn if nothing found
    if not result["agents"]:
        print("WARNING: No agents discovered.", file=sys.stderr)


if __name__ == "__main__":
    main()
