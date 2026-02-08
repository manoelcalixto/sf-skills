# LSP Engine for sf-skills

Language Server Protocol integration for Salesforce development skills in Claude Code.

## Overview

This module provides a shared LSP engine that enables real-time validation of Salesforce files during Claude Code authoring sessions. Currently supports:

- **Agent Script** (`.agent` files) - via Salesforce VS Code extension (required)
- **Apex** (`.cls`, `.trigger` files) - via Salesforce Apex extension (required)
- **LWC** (`.js`, `.html` files) - via standalone npm package ✅

## Prerequisites

### Quick Reference: VS Code vs npm

| Language | VS Code Required? | npm Package Available? |
|----------|-------------------|------------------------|
| **LWC** | ❌ No | ✅ `@salesforce/lwc-language-server` |
| **Apex** | ✅ Yes | ❌ No (Java JAR only) |
| **Agent Script** | ✅ Yes | ❌ No |

### For LWC (.js, .html files) - npm Package

LWC is the **only** language with a standalone npm package:

```bash
npm install -g @salesforce/lwc-language-server
```

That's it! No VS Code required.

### For Agent Script (.agent files) - VS Code Required

**Why VS Code?** The Agent Script LSP is only distributed bundled within the VS Code extension. There is no standalone npm package or separate download available.

1. **VS Code with Agent Script Extension** (REQUIRED)
   - Open VS Code
   - Go to Extensions (Cmd+Shift+X)
   - Search: "Agent Script" by Salesforce
   - Install

2. **Node.js 18+**
   - Required by the LSP server
   - Check: `node --version`

### For Apex (.cls, .trigger files) - VS Code Required

**Why VS Code?** The Apex LSP is a Java-based JAR file (`apex-jorje-lsp.jar`) that is only distributed bundled within the VS Code Salesforce Extension Pack. There is no standalone npm package or separate download available.

1. **VS Code with Salesforce Extension Pack** (REQUIRED)
   - Open VS Code
   - Go to Extensions (Cmd+Shift+X)
   - Search: "Salesforce Extension Pack"
   - Install

2. **Java 11+ (Adoptium/OpenJDK recommended)**
   - Required by the Apex LSP server
   - Check: `java --version`
   - Download: https://adoptium.net/temurin/releases/

## Usage

### In Hooks (Recommended)

```python
#!/usr/bin/env python3
import sys
import json
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared" / "lsp-engine"))

from lsp_client import get_diagnostics
from diagnostics import format_diagnostics_for_claude

# Read hook input
hook_input = json.load(sys.stdin)
file_path = hook_input.get("tool_input", {}).get("file_path", "")

# Validate .agent files
if file_path.endswith(".agent"):
    result = get_diagnostics(file_path)
    output = format_diagnostics_for_claude(result)
    if output:
        print(output)
```

### Standalone CLI

```bash
# Test LSP validation
python3 lsp_client.py /path/to/file.agent
```

## Module Structure

```
lsp-engine/
├── __init__.py              # Package exports
├── agentscript_wrapper.sh   # Shell wrapper for Agent Script LSP
├── apex_wrapper.sh          # Shell wrapper for Apex LSP
├── lwc_wrapper.sh           # Shell wrapper for LWC LSP
├── lsp_client.py            # Python LSP client (multi-language)
├── diagnostics.py           # Diagnostic formatting
└── README.md               # This file
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LSP_LOG_FILE` | Path to log file | `/dev/null` |
| `NODE_PATH` | Custom Node.js path (Agent Script) | Auto-detected |
| `JAVA_HOME` | Custom Java path (Apex) | Auto-detected |
| `APEX_LSP_MEMORY` | JVM heap size in MB (Apex) | 2048 |

## Environment Health Check

The LSP engine includes a version checker that monitors your development environment and alerts you when updates are available.

### What It Checks

| Component | Source | Minimum | Recommended |
|-----------|--------|---------|-------------|
| **VS Code Extensions** | | | |
| └─ Apex LSP | VS Code Marketplace | - | Latest |
| └─ LWC LSP | VS Code Marketplace | - | Latest |
| └─ Agent Script LSP | VS Code Marketplace | - | Latest |
| **Runtimes** | | | |
| └─ Java | Local install | 11 | 21 LTS |
| └─ Node.js | Local install | 18 | 22 LTS |
| **Salesforce CLI** | npm registry | - | Latest stable |

### Automatic Checks (Weekly)

The environment check runs automatically via a SessionStart hook when you use sf-skills. It:

1. **Caches results** for 7 days to avoid excessive API calls
2. **Runs silently** if everything is current
3. **Shows warnings** only when updates are available or cache is stale

Cache location: `~/.cache/sf-skills/version_check.json`

### Manual Usage

```bash
# Run with cached results (if fresh)
./check_lsp_versions.sh

# Force refresh (ignore cache)
./check_lsp_versions.sh --force

# Quiet mode (exit code only: 0=current, 1=updates available)
./check_lsp_versions.sh --quiet

# JSON output (for scripting)
./check_lsp_versions.sh --json
```

### Sample Output

```
🔍 SF-SKILLS ENVIRONMENT CHECK (cached 2 days ago)
════════════════════════════════════════════════════════════════

📦 VS CODE EXTENSIONS
───────────────────────────────────────┬────────────┬──────────┬────────
Component                              │ Installed  │ Latest   │ Status
───────────────────────────────────────┼────────────┼──────────┼────────
salesforce.salesforcedx-vscode-apex    │ 62.8.0     │ 62.10.0  │ ⚠️
salesforce.agent-script-language-client│ 1.2.0      │ 1.2.0    │ ✅

⚙️  RUNTIMES
───────────────────────────────────────┬────────────┬──────────┬────────
Component                              │ Installed  │ Latest   │ Status
───────────────────────────────────────┼────────────┼──────────┼────────
Java                                   │ 21         │ 21 LTS   │ ✅
Node.js                                │ 22         │ 22 LTS   │ ✅

🛠️  SALESFORCE CLI
───────────────────────────────────────┬────────────┬──────────┬────────
Component                              │ Installed  │ Latest   │ Status
───────────────────────────────────────┼────────────┼──────────┼────────
sf (@salesforce/cli)                   │ 2.72.0     │ 2.75.0   │ ⚠️

════════════════════════════════════════════════════════════════
💡 UPDATE COMMANDS:
   code --install-extension salesforce.salesforcedx-vscode-apex
   brew upgrade sf

🔄 Next check: Jan 27, 2026 (or run with --force)
```

### Disabling Automatic Checks

To disable the weekly check, remove the `SessionStart` hook from your skill's `hooks.json`:

```json
{
  "hooks": {
    "SessionStart": []  // Empty array disables
  }
}
```

## Troubleshooting

### Agent Script Issues

#### "LSP server not found"

The VS Code Agent Script extension is not installed:
1. Install from VS Code Marketplace
2. Verify the extension folder exists:
   - Local VS Code: `ls ~/.vscode/extensions/salesforce.agent-script-*`
   - VS Code Remote/WSL: `ls ~/.vscode-server/extensions/salesforce.agent-script-*`

#### "Node.js not found"

Install Node.js 18+:
- macOS: `brew install node`
- Or download from https://nodejs.org

#### "Node.js version too old"

Upgrade to Node.js 18+:
- macOS: `brew upgrade node`

### Apex Issues

#### "Apex Language Server not found"

The VS Code Salesforce Extension Pack is not installed:
1. Install from VS Code Marketplace: "Salesforce Extension Pack"
2. Verify the extension folder exists:
   - Local VS Code: `ls ~/.vscode/extensions/salesforce.salesforcedx-vscode-apex-*`
   - VS Code Remote/WSL: `ls ~/.vscode-server/extensions/salesforce.salesforcedx-vscode-apex-*`
3. Check JAR exists:
   - Local VS Code: `ls ~/.vscode/extensions/salesforce.salesforcedx-vscode-apex-*/dist/apex-jorje-lsp.jar`
   - VS Code Remote/WSL: `ls ~/.vscode-server/extensions/salesforce.salesforcedx-vscode-apex-*/dist/apex-jorje-lsp.jar`

#### "Java not found"

Install Java 11+:
- macOS: `brew install openjdk@11`
- Or download from https://adoptium.net/temurin/releases/

#### "Java version too old"

Upgrade to Java 11+:
- macOS: `brew install openjdk@21`
- Set JAVA_HOME: `export JAVA_HOME=/opt/homebrew/opt/openjdk@21`

### LWC Issues

#### "LWC Language Server not found"

The standalone npm package is not installed:
```bash
npm install -g @salesforce/lwc-language-server
```

Verify installation:
```bash
which lwc-language-server
# Should return: /opt/homebrew/bin/lwc-language-server (or similar)
```

**Note:** Unlike Apex and Agent Script, LWC does NOT require VS Code. The npm package works standalone.

#### "Node.js not found" or "Node.js version too old"

Same as Agent Script - install/upgrade Node.js 18+.

## How It Works

```
1. Hook triggers after Write/Edit on supported file
         │
         ▼
2. lsp_client.py detects language from extension
   (.agent → agentscript, .cls → apex, .js/.html → lwc)
         │
         ▼
3. Spawns appropriate LSP server via wrapper script
   - agentscript_wrapper.sh for .agent
   - apex_wrapper.sh for .cls/.trigger
   - lwc_wrapper.sh for .js/.html (LWC)
         │
         ▼
4. Sends textDocument/didOpen with file content
         │
         ▼
5. Parses textDocument/publishDiagnostics response
         │
         ▼
6. Formats errors for Claude → Auto-fix loop
```

## License

MIT - See LICENSE file in repository root.
