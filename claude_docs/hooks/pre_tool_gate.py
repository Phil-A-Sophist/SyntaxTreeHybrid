#!/usr/bin/env python3
"""
Claude Code PreToolUse Hook: Smart Permission Gate
===================================================
Solves the pipe-breaking bug where commands like `foo | head -20` trigger
approval prompts even when both `foo` and `head` are individually allowed.

How it works:
  1. Reads JSON from stdin (Claude Code sends tool info)
  2. For Bash commands: checks deny list first (safety), then splits on
     shell operators and checks each piece against the allow list
  3. For git push: runs pre-push audit before allowing
  4. Outputs JSON decision: allow, deny, or pass-through (ask user)

Install location: ~/.claude/hooks/pre_tool_gate.py
Wired in:         ~/.claude/settings.json -> hooks.PreToolUse
"""

import json
import re
import subprocess as _subprocess
import sys
from pathlib import Path

# ============================================================================
# HOME DIRECTORY PATTERNS — built dynamically at startup (cross-platform)
# ============================================================================
_HOME = Path.home()
_HOME_FWD = str(_HOME).replace("\\", "/")          # C:/Users/username or /home/username
_HOME_BACK = str(_HOME).replace("\\", "\\\\")      # C:\\Users\\username (regex for backslash paths)
# Git Bash / MSYS2 style: C:/Users/foo -> /c/Users/foo
if ":" in _HOME_FWD:
    _drive, _rest = _HOME_FWD.split(":", 1)
    _HOME_GITBASH = "/" + _drive.lower() + _rest
else:
    _HOME_GITBASH = _HOME_FWD

# ============================================================================
# DENY PATTERNS — checked FIRST. If ANY part of a command matches, block it.
# These are catastrophic/irreversible operations.
# ============================================================================
DENY_PATTERNS = [
    # Destructive file operations — root/home/drive-wide only
    r"rm\s+-rf\s+/\s*$",          # rm -rf /
    r"rm\s+-rf\s+/\*",            # rm -rf /*
    r"rm\s+-rf\s+~\s*$",          # rm -rf ~
    r"rm\s+-rf\s+~/\*",           # rm -rf ~/*
    r"rm\s+-rf\s+C:\s*$",         # rm -rf C:
    r"rm\s+-rf\s+C:\\",           # rm -rf C:\...
    r"rm\s+-rf\s+\*",             # rm -rf *
    r"del\s+/[sS]\s+/[qQ]\s+C:", # del /s /q C:...
    r"rmdir\s+/[sS]\s+/[qQ]\s+C:",
    r"\bformat\s+[A-Za-z]:",
    # System operations
    r"\bshutdown\b",
    r"\breboot\b",
    r"\breg\s+delete\b",
    # Git destructive
    r"git\s+push\s+.*--force(?!-with-lease)",
    r"git\s+reset\s+--hard\s+HEAD~[5-9]",
    r"git\s+reset\s+--hard\s+HEAD~\d{2,}",
    r"git\s+clean\s+-fd\s+/",
]

# ============================================================================
# ALLOW PATTERNS — if ALL components of a command match, auto-approve.
# Each pattern matches the START of a command component (after splitting on
# shell operators). Case-insensitive.
# ============================================================================
ALLOW_PATTERNS = [
    # Python / Node
    r"python[23]?(?:\.exe)?",
    r"\bpy\b",
    r"node(?:\.exe)?",
    r"npm",
    r"npx",
    r"pip[23]?",
    r"uv\b",
    r"uvx\b",
    r"pip\s+install",

    # Git
    r"git\b",

    # File reading / listing
    r"cat\b",
    r"head\b",
    r"tail\b",
    r"less\b",
    r"more\b",
    r"ls\b",
    r"dir\b",
    r"tree\b",
    r"find\b",
    r"stat\b",
    r"file\b",
    r"wc\b",

    # File operations
    r"cp\b",
    r"copy\b",
    r"mv\b",
    r"move\b",
    r"rename\b",
    r"mkdir\b",
    r"touch\b",
    r"cd\b",
    r"rm\b",

    # Text processing (almost always piped)
    r"grep\b",
    r"rg\b",
    r"sed\b",
    r"awk\b",
    r"sort\b",
    r"uniq\b",
    r"cut\b",
    r"tr\b",
    r"diff\b",
    r"tee\b",
    r"xargs\b",
    r"jq\b",

    # Info / diagnostics
    r"echo\b",
    r"printf\b",
    r"which\b",
    r"where\b",
    r"type\b",
    r"whoami\b",
    r"hostname\b",
    r"date\b",
    r"env\b",
    r"set\b",
    r"printenv\b",
    r"pwd\b",

    # Network (safe read operations)
    r"curl\b",
    r"wget\b",

    # Archive / compression
    r"tar\b",
    r"unzip\b",
    r"zip\b",
    r"gzip\b",
    r"gunzip\b",

    # Windows-specific
    r"powershell\b",
    r"cmd\b",
    r"icacls\b",
    r"attrib\b",
    r"robocopy\b",
    r"xcopy\b",
    r"where\.exe\b",

    # Testing
    r"pytest\b",
    r"python\s+-m\s+pytest",

    # Safe utilities
    r"chmod\b",
    r"ln\b",
    r"readlink\b",
    r"realpath\b",
    r"basename\b",
    r"dirname\b",
    r"test\b",
    r"\[\s",
    r"true\b",
    r"false\b",
    r"sleep\b",
    r"timeout\b",
    r"tput\b",

    # Output formatting
    r"column\b",
    r"fmt\b",
    r"fold\b",
    r"paste\b",
    r"join\b",
    r"expand\b",
    r"unexpand\b",

    # Conditional / control
    r"if\b",
    r"then\b",
    r"else\b",
    r"fi\b",
    r"for\b",
    r"do\b",
    r"done\b",
    r"while\b",
    r"case\b",
    r"esac\b",

    # Env var prefixes
    r"PYTHONUTF8=",
    r"[A-Z_]+=\S",

    # Paths within user directory (dynamically built from Path.home())
    _HOME_FWD,
    _HOME_BACK,
    _HOME_GITBASH,
    r"\"C:",
    r"'C:",

    # MusicMaker-specific
    r"ListenBot",
    r"Conductor",
    r"Samplab",
    r"ableton",
]

# ============================================================================
# SAFE SUFFIXES — redirect patterns that should be stripped before checking
# ============================================================================
SAFE_SUFFIXES = [
    r"2>&1",
    r"2>/dev/null",
    r">/dev/null",
    r"2>nul",
    r">nul",
]


def split_command(cmd: str) -> list[str]:
    """Split a command string on shell operators into individual components."""
    cleaned = cmd
    for suffix in SAFE_SUFFIXES:
        cleaned = re.sub(re.escape(suffix), " ", cleaned)
    parts = re.split(r"\s*(?:\|\||&&|[|;])\s*", cleaned)
    return [p.strip() for p in parts if p.strip()]


def matches_deny(cmd: str) -> tuple[bool, str]:
    """Check if the FULL command matches any deny pattern."""
    for pattern in DENY_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return True, pattern
    return False, ""


def component_is_allowed(component: str) -> bool:
    """Check if a single command component matches any allow pattern."""
    for pattern in ALLOW_PATTERNS:
        if re.match(pattern, component.strip(), re.IGNORECASE):
            return True
    return False


def run_pre_push_audit():
    """Run the pre-push audit script. Returns (passed, message)."""
    audit_script = Path(__file__).parent / "pre_push_audit.py"
    if not audit_script.exists():
        return True, "Audit script not found — skipping"
    try:
        result = _subprocess.run(
            [sys.executable, str(audit_script)],
            capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip()
    except _subprocess.TimeoutExpired:
        return True, "Audit timed out — skipping"
    except Exception as e:
        return True, f"Audit error: {e} — skipping"


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if tool_name != "Bash":
        sys.exit(0)

    command = tool_input.get("command", "")
    if not command:
        sys.exit(0)

    # STEP 1: Check deny list against the FULL command
    denied, pattern = matches_deny(command)
    if denied:
        print(
            f"BLOCKED by safety gate: command matches deny pattern '{pattern}'",
            file=sys.stderr,
        )
        sys.exit(2)

    # STEP 1.5: If this is a git push, run the pre-push audit
    if re.match(r"git\s+push\b", command, re.IGNORECASE):
        passed, message = run_pre_push_audit()
        if not passed:
            print(message, file=sys.stderr)
            sys.exit(2)  # Block the push

    # STEP 2: Split and check each component
    components = split_command(command)
    if not components:
        sys.exit(0)

    all_allowed = all(component_is_allowed(c) for c in components)

    if all_allowed:
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "All command components match allowed patterns",
            }
        }
        print(json.dumps(result))
        sys.exit(0)

    # Not all components recognized — pass through to normal prompt
    sys.exit(0)


if __name__ == "__main__":
    main()
