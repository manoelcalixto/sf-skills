#!/bin/bash
#
# sf-skills Hook Installation Script (Shell Wrapper)
# ===================================================
#
# Quick installer for sf-skills Claude Code hooks.
#
# Usage:
#   ./install-hooks.sh          # Install hooks
#   ./install-hooks.sh uninstall # Remove hooks
#   ./install-hooks.sh status    # Check status
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "${1:-install}" in
    install)
        python3 "$SCRIPT_DIR/install-hooks.py" "${@:2}"
        ;;
    uninstall)
        python3 "$SCRIPT_DIR/install-hooks.py" --uninstall "${@:2}"
        ;;
    status)
        python3 "$SCRIPT_DIR/install-hooks.py" --status
        ;;
    help|--help|-h)
        echo "sf-skills Hook Installer"
        echo ""
        echo "Usage: ./install-hooks.sh [command] [options]"
        echo ""
        echo "Commands:"
        echo "  install     Install sf-skills hooks (default)"
        echo "  uninstall   Remove sf-skills hooks"
        echo "  status      Show current installation status"
        echo ""
        echo "Options:"
        echo "  --dry-run   Preview changes without applying"
        echo "  --verbose   Show detailed output"
        echo ""
        ;;
    *)
        echo "Unknown command: $1"
        echo "Run './install-hooks.sh help' for usage"
        exit 1
        ;;
esac
