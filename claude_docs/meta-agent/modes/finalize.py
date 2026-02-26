#!/usr/bin/env python3
"""
Finalize mode: Sync project → global (SessionEnd)

Runs when the session ends. Ensures the global ~/.claude/ hub gets everything
from this project: merged settings, copied hooks, copied commands.
Also stamps state.md with session-end timestamp.
Runs silently — user is leaving.
"""

import json
import shutil
import sys
from pathlib import Path
from datetime import datetime

# bootstrap.py is in the same directory
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bootstrap import merge_settings


def sync_to_global(src_dir, dst_dir):
    """Copy files from project dir to global dir that don't exist in global. Returns copied list."""
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


def run_finalize(project_root):
    """Main finalize entry point. Runs silently."""
    project_root = Path(project_root)
    home = Path.home()

    global_claude = home / '.claude'
    project_claude = project_root / '.claude'
    memory_dir = project_root / 'claude_docs' / 'memory'

    # 1. Sync settings.json (project → global, additive merge)
    project_settings_path = project_claude / 'settings.json'
    global_settings_path = global_claude / 'settings.json'

    if project_settings_path.exists() and global_settings_path.exists():
        try:
            project_settings = json.loads(project_settings_path.read_text(encoding='utf-8'))
            global_settings = json.loads(global_settings_path.read_text(encoding='utf-8'))
            # project → global: project_settings is "source", global is "base"
            merged = merge_settings(project_settings, global_settings)
            global_settings_path.write_text(json.dumps(merged, indent=2), encoding='utf-8')
        except Exception:
            pass

    # 2. Sync hooks/ (project → global, copy missing)
    sync_to_global(project_claude / 'hooks', global_claude / 'hooks')

    # 3. Sync commands/ (project → global, copy missing)
    sync_to_global(project_claude / 'commands', global_claude / 'commands')

    # Also sync master hooks from claude_docs/hooks/ → ~/.claude/hooks/
    master_hooks = project_root / 'claude_docs' / 'hooks'
    if master_hooks.exists():
        sync_to_global(master_hooks, global_claude / 'hooks')

    # Also sync master commands from claude_docs/commands/ → ~/.claude/commands/
    master_commands = project_root / 'claude_docs' / 'commands'
    if master_commands.exists():
        sync_to_global(master_commands, global_claude / 'commands')

    # 4. Stamp state.md with session-end timestamp
    state_md = memory_dir / 'state.md'
    if state_md.exists():
        try:
            content = state_md.read_text(encoding='utf-8').rstrip('\n')
            # Replace any existing session-end stamp
            content = re.sub(r'\n<!-- session-end:.*?-->', '', content) if hasattr(re, 'sub') else content
            ts = datetime.now().strftime('%Y-%m-%d %H:%M')
            content += f'\n<!-- session-end: {ts} -->'
            state_md.write_text(content, encoding='utf-8')
        except Exception:
            pass

    # Silent — no stdout output


if __name__ == "__main__":
    import re
    project_root = Path(__file__).resolve().parent.parent.parent
    run_finalize(project_root)
