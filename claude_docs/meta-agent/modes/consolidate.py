#!/usr/bin/env python3
"""
Consolidate mode: Thorough review + safety check (TaskCompleted hook)

Runs when a task is marked as complete. Does what --review cannot:
- Compares disk state to documentation
- Increments task counter
- Creates snapshots at 10-task intervals
- Prunes old snapshots
- Checks for knowledge drift
- Updates session log
- Reports summary to stdout
"""

import json
import re
import shutil
from pathlib import Path
from datetime import date

SNAPSHOT_INTERVAL = 10
SNAPSHOT_RETAIN_RECENT = 3  # Keep 3 most recent at 10-task intervals
SNAPSHOT_RETAIN_50 = 1      # Keep 1 at most recent 50-task interval
SELF_REVIEW_INTERVAL = 20   # Prompt Claude to self-review every N tasks

# Directories to never scan for scripts
SCAN_EXCLUDE = {
    '.venv', 'venv', 'env', '__pycache__', 'site-packages', 'node_modules',
    '.git', 'reference', '_reference', 'tests', 'test', 'dist', 'build',
    '.eggs', '.mypy_cache', '.pytest_cache', 'htmlcov', 'appdata',
}


def get_task_number(state_md):
    """Extract current task number from state.md. Returns 0 if not found."""
    if not state_md.exists():
        return 0
    try:
        content = state_md.read_text(encoding='utf-8')
        m = re.search(r'Task:\s*(\d+)', content)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return 0


def increment_task(state_md, new_task):
    """Update task counter and last-updated date in state.md. Remove review notes."""
    if not state_md.exists():
        return
    try:
        content = state_md.read_text(encoding='utf-8')
        content = re.sub(r'(Task:\s*)\d+', f'\\g<1>{new_task}', content)
        today = date.today().isoformat()
        content = re.sub(r'(Last updated:\s*)[\d-]+', f'\\g<1>{today}', content)
        # Remove ephemeral review/session-end notes
        content = re.sub(r'\n<!-- (review|session-end):.*?-->', '', content)
        state_md.write_text(content, encoding='utf-8')
    except Exception:
        pass


def create_snapshot(memory_dir, task_n):
    """Create state-t{n}.md snapshot. Returns path or None if already exists."""
    state_md = memory_dir / 'state.md'
    snapshot_path = memory_dir / f'state-t{task_n}.md'
    if state_md.exists() and not snapshot_path.exists():
        shutil.copy2(state_md, snapshot_path)
        return snapshot_path
    return None


def prune_snapshots(memory_dir):
    """Prune snapshots: keep 3 most recent at 10-task intervals + 1 at 50-task interval."""
    snapshots = []
    for f in memory_dir.glob('state-t*.md'):
        m = re.match(r'state-t(\d+)\.md', f.name)
        if m:
            snapshots.append((int(m.group(1)), f))
    snapshots.sort(reverse=True)

    to_keep = set()

    # 3 most recent at 10-task intervals
    by_10 = [s for s in snapshots if s[0] % 10 == 0]
    for _, f in by_10[:SNAPSHOT_RETAIN_RECENT]:
        to_keep.add(f)

    # 1 at most recent 50-task interval
    by_50 = [s for s in snapshots if s[0] % 50 == 0]
    if by_50:
        to_keep.add(by_50[0][1])

    pruned = []
    for _, snap_file in snapshots:
        if snap_file not in to_keep:
            snap_file.unlink(missing_ok=True)
            pruned.append(snap_file.name)

    return pruned


def check_drift(memory_dir):
    """
    Compare state.md against snapshots.
    Look for NEXT/ACTIVE/TODO threads in snapshots that have vanished from current state.
    Returns list of drift warnings.
    """
    state_md = memory_dir / 'state.md'
    if not state_md.exists():
        return ['state.md missing']

    try:
        current = state_md.read_text(encoding='utf-8').lower()
    except Exception:
        return []

    warnings = []
    snapshots = list(memory_dir.glob('state-t*.md'))

    for snap in snapshots:
        try:
            snap_content = snap.read_text(encoding='utf-8')
            # Find active threads: lines like "- **NEXT** — ..." or "- **ACTIVE** — ..."
            threads = re.findall(
                r'\*\*(NEXT|ACTIVE|TODO|IN PROGRESS)\*\*.*?[-—]\s*(.+?)(?:\n|$)',
                snap_content,
                re.IGNORECASE
            )
            for status, thread in threads:
                key_words = [w for w in thread.strip().lower().split() if len(w) > 4][:3]
                if key_words and not any(w in current for w in key_words):
                    warnings.append(
                        f"Thread from {snap.name} may be lost: '{thread.strip()[:60]}'"
                    )
        except Exception:
            pass

    return warnings


def discover_scan_dirs(project_root):
    """
    Auto-discover top-level directories that contain Python files.
    Skips hidden dirs, known non-project dirs, and the memory/personality folders.
    """
    scan_dirs = []
    for item in sorted(project_root.iterdir()):
        if not item.is_dir():
            continue
        if item.name.startswith('.'):
            continue
        if item.name.lower() in SCAN_EXCLUDE:
            continue
        # Check if this dir contains any .py files
        try:
            next(item.rglob('*.py'))
            scan_dirs.append(item)
        except StopIteration:
            pass
    return scan_dirs


def scan_untracked_scripts(project_root, memory_dir):
    """
    Find .py files on disk that aren't mentioned in project-map.md.
    Scans all project directories dynamically instead of a hardcoded list.
    Returns list of relative paths.
    """
    project_map = memory_dir / 'project-map.md'
    if not project_map.exists():
        return []

    try:
        map_content = project_map.read_text(encoding='utf-8')
    except Exception:
        return []

    untracked = []
    for scan_dir in discover_scan_dirs(project_root):
        for script_file in scan_dir.rglob('*.py'):
            # Skip excluded subdirectories
            parts_lower = {p.lower() for p in script_file.parts}
            if parts_lower & SCAN_EXCLUDE:
                continue
            rel = str(script_file.relative_to(project_root)).replace('\\', '/')
            if script_file.name not in map_content and rel not in map_content:
                untracked.append(rel)

    return untracked[:10]  # Cap to avoid noise


def check_downloads(memory_dir):
    """Check all downloads/ folders for unrouted items. Returns list of (folder, items)."""
    results = []

    dl_root = memory_dir / 'downloads'
    if dl_root.exists():
        items = [f for f in dl_root.iterdir() if not f.name.startswith('.')]
        if items:
            results.append((str(dl_root), [f.name for f in items]))

    sub_dir = memory_dir / 'sub'
    if sub_dir.exists():
        for sub in sub_dir.iterdir():
            if sub.is_dir():
                dl = sub / 'downloads'
                if dl.exists():
                    items = [f for f in dl.iterdir() if not f.name.startswith('.')]
                    if items:
                        results.append((str(dl), [f.name for f in items]))

    return results


def append_session_log(memory_dir, task_n, note):
    """Append a task entry to SESSION_LOG.md."""
    log = memory_dir / 'logs' / 'SESSION_LOG.md'
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        today = date.today().isoformat()
        entry = f"\n## Task {task_n} — {today}\n{note}\n"
        if log.exists():
            content = log.read_text(encoding='utf-8')
            log.write_text(content.rstrip('\n') + entry, encoding='utf-8')
        else:
            log.write_text(f"# Session Log\n{entry}", encoding='utf-8')
    except Exception:
        pass


def run_consolidate(project_root):
    """Main consolidate entry point. Outputs summary to stdout."""
    project_root = Path(project_root)
    memory_dir = project_root / 'claude_docs' / 'memory'

    if not memory_dir.exists():
        print("=== CONSOLIDATE: No memory dir — skipping ===")
        return

    state_md = memory_dir / 'state.md'
    current_task = get_task_number(state_md)
    new_task = current_task + 1

    print(f"=== CONSOLIDATE: Task {current_task} ->{new_task} ===")

    # 1. Drift check
    drift_warnings = check_drift(memory_dir)
    if drift_warnings:
        print(f"[DRIFT] {len(drift_warnings)} warning(s):")
        for w in drift_warnings[:3]:
            print(f"  - {w}")
        if len(drift_warnings) > 3:
            print(f"  ... and {len(drift_warnings) - 3} more")
    else:
        print("[DRIFT] Clean")

    # 2. Untracked scripts scan
    untracked = scan_untracked_scripts(project_root, memory_dir)
    if untracked:
        print(f"[SCAN] {len(untracked)} potentially untracked script(s):")
        for u in untracked[:3]:
            print(f"  - {u}")
        if len(untracked) > 3:
            print(f"  ... and {len(untracked) - 3} more")
    else:
        print("[SCAN] Nothing missed by --review")

    # 3. Downloads check
    pending_downloads = check_downloads(memory_dir)
    if pending_downloads:
        for folder, items in pending_downloads:
            short = Path(folder).relative_to(project_root) if project_root in Path(folder).parents else folder
            print(f"[DOWNLOADS] {len(items)} item(s) in {short}: {', '.join(items[:3])}")
    else:
        print("[DOWNLOADS] Clean")

    # 4. Increment task counter
    increment_task(state_md, new_task)
    print(f"[STATE] Task counter: {current_task} ->{new_task}")

    # 5. Snapshot management
    if new_task % SNAPSHOT_INTERVAL == 0:
        snap = create_snapshot(memory_dir, new_task)
        if snap:
            print(f"[SNAPSHOT] Created {snap.name}")
            pruned = prune_snapshots(memory_dir)
            if pruned:
                print(f"[SNAPSHOT] Pruned: {', '.join(pruned)}")
        else:
            print(f"[SNAPSHOT] state-t{new_task}.md already exists")
    else:
        next_snap = (new_task // SNAPSHOT_INTERVAL + 1) * SNAPSHOT_INTERVAL
        print(f"[SNAPSHOT] Not due (next at Task {next_snap})")

    # 6. Self-review check
    if new_task % SELF_REVIEW_INTERVAL == 0:
        print(f"\n[SELF-REVIEW] Task {new_task} — self-review due!")
        print("  Please review these files before continuing:")
        print("  1. CLAUDE.md — under 60 lines? Nothing that belongs elsewhere?")
        print("  2. claude_docs/personality/project-personality.md — still accurate?")
        print("  3. claude_docs/personality/personality.md (project section) — still current?")
        print("  4. .claude/settings.json — permissions accurate? Wildcards where possible?")
        print("  5. .claude/settings.local.json — machine-specific only?")
        print("  Report what you changed (or 'no changes needed').\n")

    # 7. Session log
    log_parts = [f"Meta-agent consolidation. Task {current_task} ->{new_task}."]
    if drift_warnings:
        log_parts.append(f"Drift: {len(drift_warnings)} warning(s).")
    if untracked:
        log_parts.append(f"{len(untracked)} untracked script(s) flagged.")
    if pending_downloads:
        total = sum(len(items) for _, items in pending_downloads)
        log_parts.append(f"{total} download(s) pending routing.")
    append_session_log(memory_dir, new_task, ' '.join(log_parts))
    print("[LOG] Session log updated")

    print("=== CONSOLIDATE DONE ===")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    run_consolidate(project_root)
