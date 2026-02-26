#!/usr/bin/env python3
"""
Audit mode: Validate + sync project → global (PrePush)

Called by pre_tool_gate.py before every git push.
Exit code 0 = push allowed.
Exit code 1 = CRITICAL issues found, push blocked.

Checks:
- Memory health (state.md, project-map.md, session log freshness, downloads)
- CLAUDE.md hygiene (line count, correct references, no leaked content)
- Git hygiene (.bak files, tracked files that should be gitignored, sensitive data)
- File locations (personality files in correct places)
- JSON validity (settings files parseable)
- Also syncs project → global before checking
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bootstrap import merge_settings

CLAUDE_MD_MAX_LINES = 60
STATE_MD_MAX_LINES = 40

SENSITIVE_PATTERNS = [
    r"(?i)(api[_-]?key|secret[_-]?key|password|token)\s*[:=]\s*['\"][^'\"]{8,}",
    r"sk-[a-zA-Z0-9]{20,}",
    r"ghp_[a-zA-Z0-9]{20,}",
    r"AKIA[0-9A-Z]{16}",
]

BAD_EXTENSIONS = ['.bak', '.tmp', '.swp', '.orig']
SHOULD_BE_GITIGNORED = ['.claude/settings.local.json']


class Issue:
    def __init__(self, category, severity, message, fix):
        self.category = category
        self.severity = severity
        self.message = message
        self.fix = fix

    def __repr__(self):
        return f"[{self.severity}] [{self.category}] {self.message}"


# ── Sync ──────────────────────────────────────────────────────────────────────

def sync_project_to_global(project_root, home):
    """Sync project .claude/ → global ~/.claude/ (additive)."""
    project_claude = project_root / '.claude'
    global_claude = home / '.claude'

    # settings.json merge
    p_s = project_claude / 'settings.json'
    g_s = global_claude / 'settings.json'
    if p_s.exists() and g_s.exists():
        try:
            p_data = json.loads(p_s.read_text(encoding='utf-8'))
            g_data = json.loads(g_s.read_text(encoding='utf-8'))
            merged = merge_settings(p_data, g_data)
            g_s.write_text(json.dumps(merged, indent=2), encoding='utf-8')
        except Exception:
            pass

    # hooks/ and commands/ (copy missing)
    for subdir in ('hooks', 'commands'):
        src = project_claude / subdir
        dst = global_claude / subdir
        if src.exists():
            dst.mkdir(parents=True, exist_ok=True)
            for f in src.iterdir():
                if f.is_file() and not (dst / f.name).exists():
                    shutil.copy2(f, dst / f.name)

    # Also sync claude_docs/hooks/ and claude_docs/commands/ → global
    for subdir_name, src_subdir in [('hooks', 'hooks'), ('commands', 'commands')]:
        src = project_root / 'claude_docs' / src_subdir
        dst = global_claude / subdir_name
        if src.exists():
            dst.mkdir(parents=True, exist_ok=True)
            for f in src.iterdir():
                if f.is_file() and not (dst / f.name).exists():
                    shutil.copy2(f, dst / f.name)


# ── Check: Memory health ──────────────────────────────────────────────────────

def check_memory_health(project_root):
    issues = []
    memory_dir = project_root / 'claude_docs' / 'memory'

    if not memory_dir.exists():
        return issues  # No memory system — skip

    state_md = memory_dir / 'state.md'
    if not state_md.exists():
        issues.append(Issue('memory', 'CRITICAL', 'state.md is missing',
                            'Run memory consolidation before pushing'))
    else:
        try:
            lines = state_md.read_text(encoding='utf-8').strip().split('\n')
            if len(lines) > STATE_MD_MAX_LINES:
                issues.append(Issue('memory', 'WARNING',
                                    f'state.md is {len(lines)} lines (target <={STATE_MD_MAX_LINES})',
                                    'Compress state.md'))
            if not any(re.search(r'Task[:\s]+\d+', ln) for ln in lines):
                issues.append(Issue('memory', 'CRITICAL',
                                    'state.md has no task counter',
                                    "Add 'Task: {n}' to state.md"))
        except Exception:
            pass

    if not (memory_dir / 'project-map.md').exists():
        issues.append(Issue('memory', 'CRITICAL', 'project-map.md is missing',
                            'Create claude_docs/memory/project-map.md'))

    # Session log freshness
    main_log = memory_dir / 'logs' / 'SESSION_LOG.md'
    if main_log.exists() and state_md.exists():
        try:
            log_tasks = re.findall(r'Task\s+(\d+)', main_log.read_text(encoding='utf-8'))
            state_tasks = re.findall(r'Task[:\s]+(\d+)', state_md.read_text(encoding='utf-8'))
            if log_tasks and state_tasks:
                lag = max(int(t) for t in state_tasks) - max(int(t) for t in log_tasks)
                if lag > 2:
                    issues.append(Issue('memory', 'WARNING',
                                        'Session log is behind state.md',
                                        'Update SESSION_LOG.md'))
        except Exception:
            pass

    # Unrouted downloads
    dl = memory_dir / 'downloads'
    if dl.exists():
        items = [f for f in dl.iterdir() if not f.name.startswith('.')]
        if items:
            issues.append(Issue('memory', 'WARNING',
                                f'Unrouted items in downloads/: {", ".join(f.name for f in items[:3])}',
                                'Route downloaded files'))

    return issues


# ── Check: CLAUDE.md hygiene ──────────────────────────────────────────────────

def check_claude_md(project_root):
    issues = []
    claude_md = project_root / 'CLAUDE.md'
    if not claude_md.exists():
        return issues

    try:
        content = claude_md.read_text(encoding='utf-8')
        lines = content.strip().split('\n')

        if len(lines) > CLAUDE_MD_MAX_LINES:
            issues.append(Issue('claude_md', 'CRITICAL',
                                f'CLAUDE.md is {len(lines)} lines (max {CLAUDE_MD_MAX_LINES})',
                                'Move content to project-personality.md'))

        lower = content.lower()
        for indicator in ['pip install', 'npm install', 'tech stack']:
            if indicator in lower:
                issues.append(Issue('claude_md', 'WARNING',
                                    f"CLAUDE.md contains '{indicator}' — belongs in project-personality.md",
                                    'Move to claude_docs/personality/project-personality.md'))
                break

        # Old path references
        old_refs = ['@.claude/personality.md', '@.claude/project-personality.md']
        for ref in old_refs:
            if ref in content:
                issues.append(Issue('claude_md', 'CRITICAL',
                                    f"CLAUDE.md references old path: '{ref}'",
                                    'Update to @claude_docs/personality/personality.md'))

        # Correct reference should be present
        if '@claude_docs/personality/personality.md' not in content:
            issues.append(Issue('claude_md', 'WARNING',
                                'CLAUDE.md missing @claude_docs/personality/personality.md reference',
                                'Add to Session Start section'))
    except Exception:
        pass

    return issues


# ── Check: Git hygiene ────────────────────────────────────────────────────────

def check_git_hygiene(project_root):
    issues = []

    try:
        result = subprocess.run(['git', 'ls-files'],
                                cwd=project_root, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            tracked = result.stdout.strip().split('\n')
            for f in tracked:
                for ext in BAD_EXTENSIONS:
                    if f.endswith(ext):
                        issues.append(Issue('git', 'WARNING',
                                            f"Tracked backup file: {f}",
                                            f'git rm --cached "{f}"'))
                for pattern in SHOULD_BE_GITIGNORED:
                    if f == pattern or f.endswith('/' + pattern):
                        issues.append(Issue('git', 'CRITICAL',
                                            f"'{f}' is tracked but should be gitignored",
                                            f'Add to .gitignore and git rm --cached "{f}"'))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        result = subprocess.run(['git', 'diff', '--cached', '-U0'],
                                cwd=project_root, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            for pattern in SENSITIVE_PATTERNS:
                if re.search(pattern, result.stdout):
                    issues.append(Issue('git', 'CRITICAL',
                                        'Staged changes may contain sensitive data',
                                        'Review staged changes — remove secrets'))
                    break
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return issues


# ── Check: File locations ─────────────────────────────────────────────────────

def check_file_locations(project_root):
    issues = []
    claude_docs = project_root / 'claude_docs'

    if not claude_docs.exists():
        return issues

    # Home directory: .claude/personality.md IS the global personality — not a stale copy
    is_home = project_root.resolve() == Path.home().resolve()

    personality_dir = claude_docs / 'personality'

    if not is_home and (project_root / '.claude' / 'personality.md').exists():
        issues.append(Issue('files', 'CRITICAL',
                            'personality.md is in .claude/ — won\'t travel with git',
                            'Move to claude_docs/personality/personality.md'))

    if not (personality_dir / 'personality.md').exists():
        issues.append(Issue('files', 'WARNING',
                            'personality.md missing at claude_docs/personality/',
                            'Create claude_docs/personality/personality.md'))

    if (project_root / '.claude' / 'project-personality.md').exists():
        issues.append(Issue('files', 'CRITICAL',
                            'project-personality.md is in .claude/ — won\'t travel with git',
                            'Move to claude_docs/personality/project-personality.md'))

    if not (personality_dir / 'project-personality.md').exists():
        issues.append(Issue('files', 'WARNING',
                            'project-personality.md missing at claude_docs/personality/',
                            'Create claude_docs/personality/project-personality.md'))

    return issues


# ── Check: JSON validity ──────────────────────────────────────────────────────

def check_json_validity(project_root):
    issues = []
    files_to_check = [
        project_root / '.claude' / 'settings.json',
        project_root / '.claude' / 'settings.local.json',
        Path.home() / '.claude' / 'settings.json',
    ]
    for f in files_to_check:
        if not f.exists():
            continue
        try:
            json.loads(f.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            label = str(f.relative_to(project_root)) if project_root in f.parents else str(f)
            issues.append(Issue('json', 'CRITICAL',
                                f'Invalid JSON in {label}: {e}',
                                f'Fix JSON syntax in {label}'))
    return issues


# ── Main ──────────────────────────────────────────────────────────────────────

def run_audit(project_root):
    """Main audit entry point. Returns 0 (allow push) or 1 (block push)."""
    project_root = Path(project_root)
    home = Path.home()

    # Step 1: Sync project → global
    try:
        sync_project_to_global(project_root, home)
    except Exception:
        pass

    # Step 2: Collect issues
    issues = []
    issues.extend(check_memory_health(project_root))
    issues.extend(check_claude_md(project_root))
    issues.extend(check_git_hygiene(project_root))
    issues.extend(check_file_locations(project_root))
    issues.extend(check_json_validity(project_root))

    critical = [i for i in issues if i.severity == 'CRITICAL']
    warnings = [i for i in issues if i.severity == 'WARNING']

    if not issues:
        print(json.dumps({'status': 'clean', 'project': str(project_root)}))
        return 0

    lines = [
        f'PRE-PUSH AUDIT: {len(critical)} critical, {len(warnings)} warning(s)',
        f'Project: {project_root}',
        ''
    ]

    if critical:
        lines.append('=== CRITICAL (must fix before push) ===')
        for n, i in enumerate(critical, 1):
            lines.append(f'{n}. [{i.category}] {i.message}')
            lines.append(f'   FIX: {i.fix}')
        lines.append('')

    if warnings:
        lines.append('=== WARNINGS (should fix) ===')
        for n, i in enumerate(warnings, 1):
            lines.append(f'{n}. [{i.category}] {i.message}')
            lines.append(f'   FIX: {i.fix}')
        lines.append('')

    if critical:
        lines.append('Fix all CRITICAL issues, then retry the push.')
        print('\n'.join(lines), file=sys.stderr)
        return 1
    else:
        lines.append('Warnings noted — push allowed.')
        print('\n'.join(lines))
        return 0


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    sys.exit(run_audit(project_root))
