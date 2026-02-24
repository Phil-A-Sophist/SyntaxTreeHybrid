#!/usr/bin/env python3
"""
migrate_settings.py — Claude Code Configuration Migration

Reads master config files from claude_docs/ and deploys them to their live
locations, translating {{PLACEHOLDER}} values for the current machine.

Usage:
    python claude_docs/bootstrap/migrate_settings.py              # first-time setup
    python claude_docs/bootstrap/migrate_settings.py --session-start  # auto-run on launch

Run from the project root directory.
"""

import json
import os
import platform
import shutil
import sys
from pathlib import Path
from datetime import datetime

# Ensure UTF-8 output on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ============================================================================
# ENVIRONMENT DETECTION
# ============================================================================

def detect_env():
    """Detect the current machine's environment and return (home, placeholders)."""
    home = Path.home()
    is_windows = platform.system() == "Windows"
    python_cmd = "python" if is_windows else "python3"

    # PostToolUse git status check — OS-appropriate command
    if is_windows:
        post_tool_use = (
            'powershell -Command "if (Test-Path .git) { '
            '$status = git status --porcelain; '
            "if ($status) { echo '[GIT] Changes detected.' } }\""
        )
    else:
        post_tool_use = (
            "bash -c 'if [ -d .git ]; then "
            "status=$(git status --porcelain); "
            'if [ -n "$status" ]; then echo "[GIT] Changes detected."; fi; fi\''
        )

    # Forward-slash home path (works in all contexts including JSON)
    home_fwd = str(home).replace("\\", "/")

    placeholders = {
        "HOME": home_fwd,
        "PYTHON": python_cmd,
        "POST_TOOL_USE_COMMAND": post_tool_use,
    }

    return home, placeholders


# ============================================================================
# JSON UTILITIES
# ============================================================================

def translate_placeholders(obj, placeholders):
    """Recursively replace {{KEY}} in all string values."""
    if isinstance(obj, str):
        result = obj
        for key, value in placeholders.items():
            if isinstance(value, str):
                result = result.replace(f"{{{{{key}}}}}", value)
        return result
    elif isinstance(obj, dict):
        return {k: translate_placeholders(v, placeholders) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [translate_placeholders(item, placeholders) for item in obj]
    return obj


def read_json(path):
    """Read and parse a JSON file. Raises on error."""
    p = Path(path)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}")
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path}")


def write_json(path, data):
    """Write data as formatted JSON (creates parent dirs, overwrites)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def check_no_placeholders(path):
    """Verify no {{...}} placeholders remain in a written file."""
    content = Path(path).read_text(encoding="utf-8")
    import re
    remaining = re.findall(r"\{\{[A-Z_]+\}\}", content)
    return remaining


# ============================================================================
# DIRECTORY COPY
# ============================================================================

def copy_directory(src, dst):
    """Copy all files from src/ to dst/, overwriting existing. Returns list of paths."""
    src_path = Path(src)
    dst_path = Path(dst)
    dst_path.mkdir(parents=True, exist_ok=True)

    copied = []
    for f in src_path.iterdir():
        if f.is_file():
            dest = dst_path / f.name
            shutil.copy2(f, dest)
            copied.append(dest)
    return copied


# ============================================================================
# MIGRATION
# ============================================================================

def migrate(project_root, home, placeholders):
    """
    Run the full migration. Returns (actions, errors).

    actions: list of strings describing what was done
    errors:  list of strings describing problems (non-fatal)
    """
    actions = []
    errors = []

    claude_docs = project_root / "claude_docs"
    global_claude = home / ".claude"
    project_claude = project_root / ".claude"

    # 1. Global settings: translate → overwrite ~/.claude/settings.json
    global_template = claude_docs / "settings.global.json"
    global_target = global_claude / "settings.json"
    if global_template.exists():
        try:
            data = read_json(global_template)
            translated = translate_placeholders(data, placeholders)
            write_json(global_target, translated)
            remaining = check_no_placeholders(global_target)
            if remaining:
                errors.append(f"Untranslated placeholders in {global_target}: {remaining}")
            else:
                actions.append(f"Written: {global_target}")
        except Exception as e:
            errors.append(f"Global settings failed: {e}")
    else:
        errors.append(f"Missing template: {global_template}")

    # 2. Project settings: translate -> overwrite .claude/settings.json
    project_template = claude_docs / "settings.project.json"
    project_target = project_claude / "settings.json"
    if project_template.exists():
        try:
            data = read_json(project_template)
            translated = translate_placeholders(data, placeholders)
            write_json(project_target, translated)
            remaining = check_no_placeholders(project_target)
            if remaining:
                errors.append(f"Untranslated placeholders in {project_target}: {remaining}")
            else:
                actions.append(f"Written: {project_target}")
        except Exception as e:
            errors.append(f"Project settings failed: {e}")
    else:
        errors.append(f"Missing template: {project_template}")

    # 3. Local settings: skip if exists, create from template if missing
    local_target = project_claude / "settings.local.json"
    local_template = claude_docs / "settings.local.template.json"
    if local_target.exists():
        actions.append(f"Skipped (exists): {local_target}")
    elif local_template.exists():
        try:
            data = read_json(local_template)
            write_json(local_target, data)
            actions.append(f"Created from template: {local_target}")
        except Exception as e:
            errors.append(f"Local settings template failed: {e}")
    else:
        errors.append(f"Missing local template: {local_template}")

    # 4. Commands: copy all from claude_docs/commands/ -> .claude/commands/
    src_commands = claude_docs / "commands"
    dst_commands = project_claude / "commands"
    if src_commands.exists():
        try:
            copied = copy_directory(src_commands, dst_commands)
            actions.append(f"Commands: {len(copied)} files -> {dst_commands}")
        except Exception as e:
            errors.append(f"Commands copy failed: {e}")
    else:
        errors.append(f"Missing commands source: {src_commands}")

    # 5. Hooks: copy all from claude_docs/hooks/ -> ~/.claude/hooks/
    src_hooks = claude_docs / "hooks"
    dst_hooks = global_claude / "hooks"
    if src_hooks.exists():
        try:
            copied = copy_directory(src_hooks, dst_hooks)
            actions.append(f"Hooks: {len(copied)} files -> {dst_hooks}")
        except Exception as e:
            errors.append(f"Hooks copy failed: {e}")
    else:
        errors.append(f"Missing hooks source: {src_hooks}")

    return actions, errors


# ============================================================================
# AUDIT
# ============================================================================

def run_audit(project_root, home):
    """Return a formatted settings audit string."""
    lines = ["=== SETTINGS AUDIT ==="]

    global_settings = home / ".claude" / "settings.json"
    if global_settings.exists():
        try:
            data = json.loads(global_settings.read_text(encoding="utf-8"))
            n_hooks = sum(len(v) for v in data.get("hooks", {}).values())
            n_allow = len(data.get("permissions", {}).get("allow", []))
            n_deny = len(data.get("permissions", {}).get("deny", []))
            lines.append(f"Global:  {global_settings}")
            lines.append(f"         [OK] ({n_hooks} hooks, {n_allow} allow + {n_deny} deny)")
        except Exception as e:
            lines.append(f"Global:  {global_settings}")
            lines.append(f"         [!] invalid JSON: {e}")
    else:
        lines.append(f"Global:  {global_settings}")
        lines.append(f"         [!] missing")

    project_settings = project_root / ".claude" / "settings.json"
    if project_settings.exists():
        try:
            data = json.loads(project_settings.read_text(encoding="utf-8"))
            n_hooks = sum(len(v) for v in data.get("hooks", {}).values())
            n_allow = len(data.get("permissions", {}).get("allow", []))
            lines.append(f"Project: .claude/settings.json")
            lines.append(f"         [OK] ({n_hooks} hooks, {n_allow} allow)")
        except Exception as e:
            lines.append(f"Project: .claude/settings.json  [!] invalid JSON: {e}")
    else:
        lines.append(f"Project: .claude/settings.json  [!] missing")

    local_settings = project_root / ".claude" / "settings.local.json"
    status = "[OK] exists" if local_settings.exists() else "[!] missing (will be created from template next run)"
    lines.append(f"Local:   .claude/settings.local.json  {status}")

    commands_dir = project_root / ".claude" / "commands"
    if commands_dir.exists():
        n = len(list(commands_dir.glob("*.md")))
        lines.append(f"Commands: {n} files in .claude/commands/")
    else:
        lines.append(f"Commands: .claude/commands/ missing")

    hooks_dir = home / ".claude" / "hooks"
    if hooks_dir.exists():
        n = len(list(hooks_dir.glob("*.py")))
        lines.append(f"Hooks:    {n} files in ~/.claude/hooks/")
    else:
        lines.append(f"Hooks:    ~/.claude/hooks/ missing")

    lines.append("======================")
    return "\n".join(lines)


# ============================================================================
# MEMORY ACTIVATION
# ============================================================================

def print_memory_activation(project_root):
    """Output memory activation message for Claude Code to read."""
    state_md = project_root / ".memory" / "state.md"
    print("=== MEMORY SYSTEM ACTIVE ===")
    print("Spawn memory consolidation subagent NOW. Execute .memory/instructions.md")
    print("=== Current State ===")
    if state_md.exists():
        print(state_md.read_text(encoding="utf-8"))
    else:
        print("No state.md found — cold start needed")


# ============================================================================
# MAIN
# ============================================================================

def main():
    session_start = "--session-start" in sys.argv

    # Locate project root: this script lives at claude_docs/bootstrap/migrate_settings.py
    # so project root is two levels up
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent  # .../claude_docs/bootstrap/ → project/

    # Change to project root so relative paths in settings work correctly
    os.chdir(project_root)

    home, placeholders = detect_env()

    # Run migration (wrapped so errors don't abort session-start memory output)
    try:
        actions, errors = migrate(project_root, home, placeholders)
    except Exception as e:
        actions = []
        errors = [f"Migration failed: {e}"]

    if session_start:
        # Silent mode — only print warnings and then memory activation + audit
        if errors:
            for err in errors:
                print(f"[migrate_settings] WARNING: {err}", flush=True)

        print_memory_activation(project_root)
        print()
        print(run_audit(project_root, home))
        sys.stdout.flush()

    else:
        # Verbose mode — full report for manual runs
        print("=" * 50)
        print("  migrate_settings.py - Claude Code Config Migration")
        print("=" * 50)
        print(f"Project root: {project_root}")
        print(f"Platform:     {platform.system()} ({placeholders['HOME']})")
        print(f"Python cmd:   {placeholders['PYTHON']}")
        print()

        print("Actions:")
        for action in actions:
            print(f"  [OK] {action}")

        if errors:
            print()
            print("Errors:")
            for err in errors:
                print(f"  [!] {err}")

        print()
        print(run_audit(project_root, home))
        print()

        if errors:
            print("Migration completed with errors — review above.")
        else:
            print("Migration complete!")


if __name__ == "__main__":
    main()
