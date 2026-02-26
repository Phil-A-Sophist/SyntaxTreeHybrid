#!/usr/bin/env python3
"""
Meta-Agent: Manages Claude Code configuration and project memory.

The sync model:
- ~/.claude/ is the hub (global)
- .claude/ in each project is a spoke
- Sync everything everywhere, additive only

Usage:
    python agent.py --bootstrap     # SessionStart: global → project sync
    python agent.py --review        # Stop: quick capture from CLI
    python agent.py --consolidate   # TaskCompleted: thorough review
    python agent.py --finalize      # SessionEnd: project → global sync
    python agent.py --audit         # PrePush: validate + sync
"""

import sys
import argparse
from pathlib import Path

# Add modes directory to path
SCRIPT_DIR = Path(__file__).resolve().parent
MODES_DIR = SCRIPT_DIR / "modes"
sys.path.insert(0, str(MODES_DIR))

# Project root is two levels up from meta-agent/agent.py
PROJECT_ROOT = SCRIPT_DIR.parent.parent


def main():
    parser = argparse.ArgumentParser(description="Meta-Agent for Claude Code")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--bootstrap", action="store_true",
                       help="SessionStart: sync global → project")
    group.add_argument("--review", action="store_true",
                       help="Stop: quick capture from CLI transcript")
    group.add_argument("--consolidate", action="store_true",
                       help="TaskCompleted: thorough review + safety check")
    group.add_argument("--finalize", action="store_true",
                       help="SessionEnd: sync project → global + emergency save")
    group.add_argument("--audit", action="store_true",
                       help="PrePush: validate + sync project → global")

    args = parser.parse_args()

    # Change to project root so relative paths work
    import os
    os.chdir(PROJECT_ROOT)

    if args.bootstrap:
        from bootstrap import run_bootstrap
        run_bootstrap(PROJECT_ROOT)

    elif args.review:
        from review import run_review
        run_review(PROJECT_ROOT)

    elif args.consolidate:
        from consolidate import run_consolidate
        run_consolidate(PROJECT_ROOT)

    elif args.finalize:
        from finalize import run_finalize
        run_finalize(PROJECT_ROOT)

    elif args.audit:
        from audit import run_audit
        sys.exit(run_audit(PROJECT_ROOT))


if __name__ == "__main__":
    main()
