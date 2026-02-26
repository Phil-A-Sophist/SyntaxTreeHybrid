#!/usr/bin/env python3
"""
Bootstrap mode: Sync global → project (SessionStart)

Runs at the start of every session. Ensures the project has everything
from the global ~/.claude/ hub: merged settings, copied hooks, copied commands,
and a settings.local.json from template if missing.
"""

import json
import shutil
from pathlib import Path


def get_home():
    """Get user home directory."""
    return Path.home()


def merge_settings(global_settings, project_settings):
    """
    Merge settings additively.
    - Combine permission arrays (no duplicates)
    - Combine hook arrays (by hook type, no duplicate commands)
    - Project values win for non-array scalar conflicts
    Returns merged dict.
    """
    merged = json.loads(json.dumps(project_settings))  # deep copy

    # Merge permissions
    if "permissions" in global_settings:
        if "permissions" not in merged:
            merged["permissions"] = {}

        for key in ["allow", "deny"]:
            global_list = global_settings.get("permissions", {}).get(key, [])
            project_list = merged.get("permissions", {}).get(key, [])
            combined = list(project_list)
            for item in global_list:
                if item not in combined:
                    combined.append(item)
            merged["permissions"][key] = combined

    # Merge hooks (additive by hook type)
    if "hooks" in global_settings:
        if "hooks" not in merged:
            merged["hooks"] = {}

        for hook_type, hook_list in global_settings.get("hooks", {}).items():
            if hook_type not in merged["hooks"]:
                merged["hooks"][hook_type] = []

            # Collect existing commands to avoid duplicates
            existing_commands = []
            for h in merged["hooks"][hook_type]:
                for inner in h.get("hooks", []):
                    cmd = inner.get("command", "")
                    if cmd:
                        existing_commands.append(cmd)

            for hook in hook_list:
                hook_cmds = [inner.get("command", "") for inner in hook.get("hooks", [])]
                if not any(cmd in existing_commands for cmd in hook_cmds if cmd):
                    merged["hooks"][hook_type].append(hook)

    return merged


def sync_directory(src_dir, dst_dir):
    """Copy files from src to dst that don't exist in dst. Returns list of copied filenames."""
    copied = []
    src_path = Path(src_dir)
    dst_path = Path(dst_dir)

    if not src_path.exists():
        return copied

    dst_path.mkdir(parents=True, exist_ok=True)

    for src_file in src_path.iterdir():
        if src_file.is_file():
            dst_file = dst_path / src_file.name
            if not dst_file.exists():
                shutil.copy2(src_file, dst_file)
                copied.append(src_file.name)

    return copied


def run_bootstrap(project_root):
    """Main bootstrap entry point."""
    project_root = Path(project_root)
    home = get_home()

    global_claude = home / ".claude"
    project_claude = project_root / ".claude"
    claude_docs = project_root / "claude_docs"

    print("=== META-AGENT: BOOTSTRAP ===")

    # Ensure .claude/ exists
    project_claude.mkdir(parents=True, exist_ok=True)

    # 1. Sync settings.json (global → project, additive merge)
    global_settings_path = global_claude / "settings.json"
    project_settings_path = project_claude / "settings.json"

    if global_settings_path.exists():
        try:
            global_settings = json.loads(global_settings_path.read_text(encoding="utf-8"))

            if project_settings_path.exists():
                project_settings = json.loads(project_settings_path.read_text(encoding="utf-8"))
            else:
                project_settings = {"$schema": "https://json.schemastore.org/claude-code-settings.json"}

            merged = merge_settings(global_settings, project_settings)

            old_perms = len(project_settings.get("permissions", {}).get("allow", []))
            new_perms = len(merged.get("permissions", {}).get("allow", []))
            added = new_perms - old_perms

            project_settings_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")

            if added > 0:
                print(f"[SYNC] settings.json: added {added} permissions from global")
            else:
                print(f"[SYNC] settings.json: already in sync")

        except Exception as e:
            print(f"[!!] settings.json sync failed: {e}")
    else:
        print(f"[SKIP] No global settings.json found")

    # 2. Sync hooks/ (global → project, copy missing)
    global_hooks = global_claude / "hooks"
    project_hooks = project_claude / "hooks"

    copied = sync_directory(global_hooks, project_hooks)
    if copied:
        print(f"[SYNC] hooks/: copied {len(copied)} files from global ({', '.join(copied)})")
    else:
        print(f"[SYNC] hooks/: already in sync")

    # 3. Sync commands/ (global → project, copy missing)
    global_commands = global_claude / "commands"
    project_commands = project_claude / "commands"

    copied = sync_directory(global_commands, project_commands)
    if copied:
        print(f"[SYNC] commands/: copied {len(copied)} files from global ({', '.join(copied)})")
    else:
        print(f"[SYNC] commands/: already in sync")

    # 4. Create settings.local.json from template if missing
    local_settings = project_claude / "settings.local.json"
    local_template = claude_docs / "settings.local.template.json"

    if not local_settings.exists():
        if local_template.exists():
            shutil.copy2(local_template, local_settings)
            print(f"[NEW] settings.local.json created from template")
        else:
            default = {
                "$schema": "https://json.schemastore.org/claude-code-settings.json",
                "permissions": {"allow": [], "deny": []}
            }
            local_settings.write_text(json.dumps(default, indent=2), encoding="utf-8")
            print(f"[NEW] settings.local.json created (default)")
    else:
        print(f"[OK] settings.local.json exists")

    # 5. Verify structure
    required = [
        claude_docs / "memory",
        claude_docs / "personality",
    ]
    all_exist = all(p.exists() for p in required)

    if all_exist:
        print(f"[OK] Structure verified")
    else:
        missing = [str(p.relative_to(project_root)) for p in required if not p.exists()]
        print(f"[!!] Missing directories: {', '.join(missing)}")

    print("=== READY ===")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    run_bootstrap(project_root)
