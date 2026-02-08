#!/usr/bin/env bash
# ============================================================================
# SF-Skills Weekly Environment Check (SessionStart Hook)
# ============================================================================
# Lightweight wrapper that runs the version checker only when the cache is stale.
# Designed to be non-blocking and silent when everything is up-to-date.
#
# Behavior:
#   - If cache is fresh (<7 days): Exits silently (no output)
#   - If cache is stale (>7 days): Runs check and outputs warnings
#   - Never blocks startup longer than 5 seconds
#
# Usage:
#   Called automatically via SessionStart hook in hooks.json
# ============================================================================

set -euo pipefail

# Configuration
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/sf-skills"
TIMESTAMP_FILE="$CACHE_DIR/last_check_timestamp"
CACHE_FILE="$CACHE_DIR/version_check.json"
CACHE_TTL_DAYS=7
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION_CHECKER="$SCRIPT_DIR/../lsp-engine/check_lsp_versions.sh"

# Check if cache is fresh
cache_is_fresh() {
    if [[ ! -f "$TIMESTAMP_FILE" ]]; then
        return 1
    fi

    local last_check
    last_check=$(cat "$TIMESTAMP_FILE")
    local now
    now=$(date +%s)
    local age_days=$(( (now - last_check) / 86400 ))

    [[ $age_days -lt $CACHE_TTL_DAYS ]]
}

# Quick check if updates are available from cached data
has_cached_updates() {
    if [[ ! -f "$CACHE_FILE" ]]; then
        return 0  # No cache = assume updates needed
    fi

    grep -q '"updates_available":true' "$CACHE_FILE"
}

# Format a compact warning for SessionStart
print_compact_warning() {
    local cache_age_days="$1"

    echo ""
    echo "⚠️  SF-SKILLS ENVIRONMENT CHECK (last checked $cache_age_days days ago)"
    echo "───────────────────────────────────────────────────────────────────"

    # Parse cached results for UPDATE or NOT_INSTALLED items
    if [[ -f "$CACHE_FILE" ]]; then
        # Extract items needing updates using grep/sed
        local updates
        updates=$(grep -oE '"name":"[^"]+","installed":"[^"]*","latest":"[^"]*","status":"(UPDATE|NOT_INSTALLED)"' "$CACHE_FILE" | head -5)

        if [[ -n "$updates" ]]; then
            echo "Updates available:"
            echo "$updates" | while read -r line; do
                local name
                name=$(echo "$line" | sed 's/.*"name":"\([^"]*\)".*/\1/')
                local installed
                installed=$(echo "$line" | sed 's/.*"installed":"\([^"]*\)".*/\1/')
                local latest
                latest=$(echo "$line" | sed 's/.*"latest":"\([^"]*\)".*/\1/')
                local status
                status=$(echo "$line" | sed 's/.*"status":"\([^"]*\)".*/\1/')

                if [[ "$status" == "NOT_INSTALLED" ]]; then
                    echo "  ❌ $name: not installed (latest: $latest)"
                else
                    echo "  ⚠️  $name: $installed → $latest"
                fi
            done
        fi
    fi

    echo "───────────────────────────────────────────────────────────────────"
    echo "Run: cd shared/lsp-engine && ./check_lsp_versions.sh --force"
    echo ""
}

main() {
    # Silent exit if cache is fresh
    if cache_is_fresh; then
        # Even with fresh cache, skip output if no updates
        if ! has_cached_updates; then
            exit 0
        fi

        # Cache is fresh but has updates - show brief reminder
        if [[ -f "$TIMESTAMP_FILE" ]]; then
            local last_check
            last_check=$(cat "$TIMESTAMP_FILE")
            local now
            now=$(date +%s)
            local age_days=$(( (now - last_check) / 86400 ))

            # Only remind every 3 days if updates are pending
            if [[ $age_days -lt 3 ]]; then
                exit 0
            fi

            print_compact_warning "$age_days"
        fi
        exit 0
    fi

    # Cache is stale - run full check
    # Use timeout to prevent blocking startup
    if [[ -x "$VERSION_CHECKER" ]]; then
        # Run with 5 second timeout
        if command -v timeout &>/dev/null; then
            timeout 5 "$VERSION_CHECKER" 2>/dev/null || true
        else
            # macOS doesn't have timeout by default, use background + wait
            "$VERSION_CHECKER" 2>/dev/null &
            local pid=$!

            # Wait up to 5 seconds
            local count=0
            while [[ $count -lt 50 ]] && kill -0 "$pid" 2>/dev/null; do
                sleep 0.1
                ((count++))
            done

            # Kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
                echo "⚠️  Environment check timed out. Run manually:"
                echo "   cd shared/lsp-engine && ./check_lsp_versions.sh --force"
            fi
        fi
    fi
}

main "$@"
