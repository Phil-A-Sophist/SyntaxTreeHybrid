#!/usr/bin/env python3
"""
Review mode: Quick capture from CLI transcript (Stop hook — after every response)

Runs silently after every Claude response. Looks at the transcript for obvious
things worth capturing: scripts created, agents defined, processes documented.
Does NOT compare disk vs. documentation — that's for --consolidate.
Does NOT call an LLM — heuristics only, so it stays fast.
"""

import json
import re
from pathlib import Path
from datetime import date

# File extensions that indicate reusable scripts
SCRIPT_EXTENSIONS = {'.py', '.sh', '.ps1', '.bat', '.cmd', '.js', '.ts'}

# Skip these path fragments — not reusable scripts
SKIP_PATH_FRAGMENTS = [
    '.venv', 'node_modules', '__pycache__', 'site-packages',
    '/test', '\\test', 'fixtures', 'snapshots',
]

# Skip these filename prefixes/suffixes
SKIP_NAME_PATTERNS = ['test_', '_test.', '.tmp', '.bak']


def encode_project_path(project_root):
    """
    Encode a project path the way Claude Code does for transcript directory names.
    C:\\Users\\irphy\\Music  →  C--Users-irphy-Music
    """
    path_str = str(project_root)
    # Replace backslashes first, then colons
    path_str = path_str.replace('\\', '-').replace(':', '-')
    return path_str


def find_transcript(project_root):
    """Find the most recently modified transcript JSONL for this project."""
    home = Path.home()
    encoded = encode_project_path(project_root)
    projects_dir = home / '.claude' / 'projects' / encoded

    if not projects_dir.exists():
        return None

    jsonl_files = list(projects_dir.glob('*.jsonl'))
    if not jsonl_files:
        return None

    return max(jsonl_files, key=lambda f: f.stat().st_mtime)


def read_recent_events(transcript_path, max_lines=200):
    """Read the most recent lines from a transcript JSONL. Returns list of parsed JSON objects."""
    if not transcript_path or not transcript_path.exists():
        return []
    try:
        lines = transcript_path.read_text(encoding='utf-8', errors='replace').strip().split('\n')
        recent = lines[-max_lines:] if len(lines) > max_lines else lines
        events = []
        for line in recent:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return events
    except Exception:
        return []


def extract_written_files(events):
    """Extract file paths from Write/Edit tool_use blocks in transcript events."""
    written = set()
    for event in events:
        # Format: {"type": "assistant", "message": {"role": "assistant", "content": [...]}}
        msg = event.get('message', {})
        content = msg.get('content', [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get('type') == 'tool_use' and block.get('name') in ('Write', 'Edit', 'MultiEdit'):
                inp = block.get('input', {})
                fp = inp.get('file_path', '')
                if fp:
                    written.add(fp)
    return list(written)


def is_notable_script(file_path):
    """Return True if this file is a reusable script worth capturing."""
    p = Path(file_path)
    if p.suffix not in SCRIPT_EXTENSIONS:
        return False
    name_lower = p.name.lower()
    if any(name_lower.startswith(skip) or name_lower.endswith(skip) for skip in SKIP_NAME_PATTERNS):
        return False
    path_lower = str(file_path).lower()
    if any(frag in path_lower for frag in SKIP_PATH_FRAGMENTS):
        return False
    return True


def already_in_project_map(file_path, map_content):
    """Check if a file is already indexed in project-map.md."""
    p = Path(file_path)
    # Check both the full path and just the filename
    return p.name in map_content or str(file_path).replace('\\', '/') in map_content


def update_project_map_minimal(project_root, new_files):
    """Add stub entries for new notable files to project-map.md."""
    if not new_files:
        return 0

    project_map = project_root / 'claude_docs' / 'memory' / 'project-map.md'
    if not project_map.exists():
        return 0

    try:
        content = project_map.read_text(encoding='utf-8')
        added = []

        for fp in new_files:
            if already_in_project_map(fp, content):
                continue
            try:
                rel = str(Path(fp).relative_to(project_root)).replace('\\', '/')
            except ValueError:
                rel = fp.replace('\\', '/')
            added.append(f"- `{rel}` — [captured this session — update description]\n")

        if added:
            section = "\n## Recently Captured (description pending)\n" + ''.join(added)
            # Insert before any existing "Recently Captured" section or append
            if '## Recently Captured' in content:
                # Replace existing section
                content = re.sub(
                    r'\n## Recently Captured \(description pending\)\n.*?(?=\n## |\Z)',
                    section,
                    content,
                    flags=re.DOTALL
                )
            else:
                content = content.rstrip('\n') + '\n' + section
            project_map.write_text(content, encoding='utf-8')

        return len(added)
    except Exception:
        return 0


def set_state_review_note(project_root, note):
    """Set the review note comment in state.md (replacing any existing one)."""
    state = project_root / 'claude_docs' / 'memory' / 'state.md'
    if not state.exists():
        return
    try:
        content = state.read_text(encoding='utf-8').rstrip('\n')
        # Remove existing review note
        content = re.sub(r'\n<!-- review:.*?-->', '', content)
        content += f'\n<!-- review: {note} -->'
        state.write_text(content, encoding='utf-8')
    except Exception:
        pass


def run_review(project_root):
    """Main review entry point. Runs silently — no stdout output."""
    project_root = Path(project_root)

    transcript_path = find_transcript(project_root)
    events = read_recent_events(transcript_path)

    if not events:
        set_state_review_note(project_root, "no transcript — nothing captured")
        return

    written_files = extract_written_files(events)
    notable = [f for f in written_files if is_notable_script(f)]

    added = update_project_map_minimal(project_root, notable) if notable else 0

    if added > 0:
        names = ', '.join(Path(f).name for f in notable[:3])
        suffix = f' (+{len(notable) - 3} more)' if len(notable) > 3 else ''
        set_state_review_note(project_root, f"captured {added} script(s): {names}{suffix}")
    else:
        set_state_review_note(project_root, "nothing notable")

    # Silent — no stdout output


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    run_review(project_root)
