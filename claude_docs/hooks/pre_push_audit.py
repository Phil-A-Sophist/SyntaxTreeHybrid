#!/usr/bin/env python3
"""
Claude Code Pre-Push Audit
===========================
Runs automatically before every `git push` via the PreToolUse hook.
Checks settings placement, memory health, CLAUDE.md hygiene, and git
hygiene. Blocks the push if any issues are found, returning a fix list
that Claude Code should resolve before retrying.

Install location: ~/.claude/hooks/pre_push_audit.py
Called by:        ~/.claude/hooks/pre_tool_gate.py
"""

import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

GLOBAL_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
CLAUDE_MD_MAX_LINES = 60  # slightly relaxed to allow new machine setup note
STATE_MD_MAX_LINES = 40
PROJECT_CONTEXT_MAX_LINES = 100  # soft limit — warn, don't block

# Machine-specific path patterns — built dynamically from Path.home()
_HOME = Path.home()
_HOME_FWD = str(_HOME).replace("\\", "/")          # C:/Users/username
_HOME_BACK = str(_HOME).replace("\\", "\\\\")      # C:\\Users\\username (regex)
if ":" in _HOME_FWD:
    _drive, _rest = _HOME_FWD.split(":", 1)
    _HOME_GITBASH = "/" + _drive.lower() + _rest    # /c/Users/username
else:
    _HOME_GITBASH = _HOME_FWD

# Patterns that indicate machine-specific content (should NOT be in settings.json)
MACHINE_SPECIFIC_PATTERNS = [
    _HOME_BACK,          # C:\\Users\\username style
    _HOME_FWD,           # C:/Users/username style
    _HOME_GITBASH,       # /c/Users/username style
    r"\.venv/Scripts/",
    r"\.venv\\\\Scripts\\\\",
    r"AppData",
]

# Patterns that indicate sensitive data (should NEVER be committed)
SENSITIVE_PATTERNS = [
    r"(?i)(api[_-]?key|secret[_-]?key|password|token)\s*[:=]\s*['\"][^'\"]{8,}",
    r"sk-[a-zA-Z0-9]{20,}",
    r"ghp_[a-zA-Z0-9]{20,}",
    r"AKIA[0-9A-Z]{16}",
]

SHOULD_BE_GITIGNORED = [
    ".claude/settings.local.json",
    ".env",
    ".env.local",
    ".env.production",
]

BAD_EXTENSIONS = [".bak", ".tmp", ".swp", ".orig"]


class Issue:
    def __init__(self, category, severity, message, fix):
        self.category = category
        self.severity = severity
        self.message = message
        self.fix = fix


def collect_issues(project_dir):
    issues = []
    issues.extend(check_settings_placement(project_dir))
    issues.extend(check_memory_health(project_dir))
    issues.extend(check_claude_md(project_dir))
    issues.extend(check_git_hygiene(project_dir))
    issues.extend(check_config_sync(project_dir))
    return issues


# === CHECK 1: SETTINGS FILE PLACEMENT ===

def check_settings_placement(project_dir):
    issues = []
    settings_json = project_dir / ".claude" / "settings.json"
    settings_local = project_dir / ".claude" / "settings.local.json"
    gitignore = project_dir / ".gitignore"

    # settings.local.json should be gitignored
    if settings_local.exists():
        is_gitignored = False
        if gitignore.exists():
            content = gitignore.read_text(encoding="utf-8", errors="replace")
            for pattern in [".claude/settings.local.json", "settings.local.json",
                            ".claude/*.local.*", "*.local.json"]:
                if pattern in content:
                    is_gitignored = True
                    break
            try:
                result = subprocess.run(
                    ["git", "check-ignore", "-q", ".claude/settings.local.json"],
                    cwd=project_dir, capture_output=True, timeout=5)
                if result.returncode == 0:
                    is_gitignored = True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
        if not is_gitignored:
            issues.append(Issue("settings", "CRITICAL",
                "settings.local.json is NOT gitignored",
                "Add '.claude/settings.local.json' to .gitignore"))

    # Hooks should be in settings.json, not only in settings.local.json
    if settings_local.exists():
        try:
            local_data = json.loads(settings_local.read_text(encoding="utf-8"))
            local_hooks = local_data.get("hooks", {})
            if local_hooks:
                shared_hooks = {}
                if settings_json.exists():
                    try:
                        shared_data = json.loads(settings_json.read_text(encoding="utf-8"))
                        shared_hooks = shared_data.get("hooks", {})
                    except json.JSONDecodeError:
                        pass
                local_only = [e for e in local_hooks if e not in shared_hooks]
                if local_only:
                    issues.append(Issue("settings", "CRITICAL",
                        f"Hooks only in settings.local.json (won't travel with repo): {', '.join(local_only)}",
                        f"Move {', '.join(local_only)} hooks from settings.local.json to settings.json"))
        except json.JSONDecodeError:
            issues.append(Issue("settings", "CRITICAL",
                "settings.local.json has invalid JSON",
                "Fix JSON syntax in .claude/settings.local.json"))

    # Machine-specific paths should NOT be in settings.json
    # Exception: {{PLACEHOLDER}} templates are allowed (they're templates, not machine paths)
    if settings_json.exists():
        try:
            content = settings_json.read_text(encoding="utf-8")
            for pattern in MACHINE_SPECIFIC_PATTERNS:
                if re.search(pattern, content):
                    issues.append(Issue("settings", "CRITICAL",
                        f"settings.json contains machine-specific path matching '{pattern}'",
                        "Move machine-specific paths to settings.local.json or use claude_docs/ templates"))
                    break
        except Exception:
            pass

    # No sensitive data in settings.json
    if settings_json.exists():
        try:
            content = settings_json.read_text(encoding="utf-8")
            for pattern in SENSITIVE_PATTERNS:
                match = re.search(pattern, content)
                if match:
                    issues.append(Issue("settings", "CRITICAL",
                        "settings.json may contain sensitive data",
                        "Remove sensitive data — use environment variables instead"))
                    break
        except Exception:
            pass

    # Redundant entries between project and global
    if settings_json.exists() and GLOBAL_SETTINGS_PATH.exists():
        try:
            project_data = json.loads(settings_json.read_text(encoding="utf-8"))
            global_data = json.loads(GLOBAL_SETTINGS_PATH.read_text(encoding="utf-8"))
            project_allow = set(project_data.get("permissions", {}).get("allow", []))
            global_allow = set(global_data.get("permissions", {}).get("allow", []))
            redundant = project_allow & global_allow
            if redundant:
                entries = ", ".join(list(redundant)[:5])
                suffix = f" (+{len(redundant)-5} more)" if len(redundant) > 5 else ""
                issues.append(Issue("settings", "WARNING",
                    f"{len(redundant)} entries already in global: {entries}{suffix}",
                    "Remove redundant allow entries from project settings.json"))
        except Exception:
            pass

    return issues


# === CHECK 2: MEMORY SYSTEM HEALTH ===

def check_memory_health(project_dir):
    issues = []
    memory_dir = project_dir / ".memory"
    if not memory_dir.exists():
        return issues

    state_md = memory_dir / "state.md"
    if not state_md.exists():
        issues.append(Issue("memory", "CRITICAL", "state.md is missing",
            "Run memory consolidation — state.md must exist before pushing"))
    else:
        try:
            lines = state_md.read_text(encoding="utf-8").strip().split("\n")
            if len(lines) > STATE_MD_MAX_LINES:
                issues.append(Issue("memory", "WARNING",
                    f"state.md is {len(lines)} lines (target: ≤{STATE_MD_MAX_LINES})",
                    "Compress state.md"))
            if not any(re.search(r"Task[:\s]+\d+", l) for l in lines):
                issues.append(Issue("memory", "CRITICAL",
                    "state.md has no task counter", "Add 'Task: {n}' to state.md"))
        except Exception:
            pass

    if not (memory_dir / "project-map.md").exists():
        issues.append(Issue("memory", "CRITICAL", "project-map.md is missing",
            "Create .memory/project-map.md"))

    if not (memory_dir / "knowledge-base.md").exists():
        issues.append(Issue("memory", "WARNING", "knowledge-base.md is missing",
            "Create .memory/knowledge-base.md"))

    # Session log freshness
    logs_dir = memory_dir / "logs"
    if logs_dir.exists() and state_md.exists():
        main_log = logs_dir / "SESSION_LOG.md"
        if main_log.exists():
            try:
                log_tasks = re.findall(r"Task\s+(\d+)", main_log.read_text(encoding="utf-8"))
                state_tasks = re.findall(r"Task[:\s]+(\d+)", state_md.read_text(encoding="utf-8"))
                if log_tasks and state_tasks:
                    if max(int(t) for t in state_tasks) - max(int(t) for t in log_tasks) > 2:
                        issues.append(Issue("memory", "WARNING",
                            "Session log is behind state.md",
                            "Update SESSION_LOG.md with recent task entries"))
            except Exception:
                pass

    # Unrouted downloads
    downloads = memory_dir / "downloads"
    if downloads.exists():
        items = [f for f in downloads.iterdir() if not f.name.startswith(".")]
        if items:
            issues.append(Issue("memory", "WARNING",
                f"Unrouted items in .memory/downloads/: {', '.join(f.name for f in items[:3])}",
                "Route downloaded files to their proper locations"))

    return issues


# === CHECK 3: CLAUDE.md HYGIENE ===

def check_claude_md(project_dir):
    issues = []
    claude_md = project_dir / "CLAUDE.md"
    if not claude_md.exists():
        return issues

    try:
        content = claude_md.read_text(encoding="utf-8")
        lines = content.strip().split("\n")

        if len(lines) > CLAUDE_MD_MAX_LINES:
            issues.append(Issue("claude_md", "CRITICAL",
                f"CLAUDE.md is {len(lines)} lines (max: {CLAUDE_MD_MAX_LINES})",
                "Move content to project-context.md or personality.md"))

        lower = content.lower()
        for indicator in ["pip install", "npm install", "requirements.txt", "package.json", "tech stack"]:
            if indicator in lower:
                issues.append(Issue("claude_md", "WARNING",
                    f"CLAUDE.md contains '{indicator}' — belongs in project-context.md",
                    "Move technical details to .claude/project-context.md"))
                break

        for indicator in ["you are a", "you should", "always respond", "communication style", "tone:"]:
            if indicator in lower:
                issues.append(Issue("claude_md", "WARNING",
                    f"CLAUDE.md contains '{indicator}' — belongs in personality.md",
                    "Move behavior content to .claude/personality.md"))
                break
    except Exception:
        pass

    ctx = project_dir / ".claude" / "project-context.md"
    if ctx.exists():
        try:
            ctx_lines = len(ctx.read_text(encoding="utf-8").strip().split("\n"))
            if ctx_lines > PROJECT_CONTEXT_MAX_LINES:
                issues.append(Issue("claude_md", "WARNING",
                    f"project-context.md is {ctx_lines} lines (target: ≤{PROJECT_CONTEXT_MAX_LINES})",
                    "Move detail to .memory/reference/"))
        except Exception:
            pass

    return issues


# === CHECK 4: GIT HYGIENE ===

def check_git_hygiene(project_dir):
    issues = []

    try:
        result = subprocess.run(["git", "ls-files"],
            cwd=project_dir, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            tracked = result.stdout.strip().split("\n")
            for f in tracked:
                for ext in BAD_EXTENSIONS:
                    if f.endswith(ext):
                        issues.append(Issue("git", "WARNING",
                            f"Tracked file with '{ext}' extension: {f}",
                            f"Run: git rm --cached \"{f}\""))
                for pattern in SHOULD_BE_GITIGNORED:
                    if f == pattern or f.endswith("/" + pattern):
                        issues.append(Issue("git", "CRITICAL",
                            f"'{f}' is tracked but should be gitignored",
                            f"Add '{pattern}' to .gitignore, run: git rm --cached \"{f}\""))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        result = subprocess.run(["git", "diff", "--cached", "-U0"],
            cwd=project_dir, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            for pattern in SENSITIVE_PATTERNS:
                if re.search(pattern, result.stdout):
                    issues.append(Issue("git", "CRITICAL",
                        "Staged changes may contain sensitive data",
                        "Review and remove sensitive data before pushing"))
                    break
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return issues


# === CHECK 5: CONFIG SYNC (live vs master templates) ===

def check_config_sync(project_dir):
    """
    Three sub-checks:
    5a. Live settings/commands are readable and valid
    5b. Live permissions haven't drifted ahead of master templates
    5c. Master templates themselves are clean and well-structured
    """
    issues = []
    claude_docs = project_dir / "claude_docs"

    # Skip entirely if no portable config system in this repo
    if not claude_docs.exists():
        return issues

    # --- Minimal placeholder translator for comparison ---
    home_fwd = str(Path.home()).replace("\\", "/")
    python_cmd = "python" if platform.system() == "Windows" else "python3"

    def _trans(obj):
        """Replace {{HOME}} and {{PYTHON}} in strings (enough for permission comparison)."""
        if isinstance(obj, str):
            return obj.replace("{{HOME}}", home_fwd).replace("{{PYTHON}}", python_cmd)
        if isinstance(obj, dict):
            return {k: _trans(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_trans(i) for i in obj]
        return obj

    def _load(path):
        """Load JSON file. Returns (data, error_string)."""
        try:
            return json.loads(Path(path).read_text(encoding="utf-8")), None
        except Exception as e:
            return None, str(e)

    # ----------------------------------------------------------------
    # 5a. LIVE FILE VALIDITY — quick read-through
    # ----------------------------------------------------------------
    live_files = [
        ("Project settings", project_dir / ".claude" / "settings.json"),
        ("Global settings",  GLOBAL_SETTINGS_PATH),
    ]
    for label, path in live_files:
        if not path.exists():
            continue  # missing files caught by check_settings_placement
        data, err = _load(path)
        if err:
            issues.append(Issue("config_sync", "CRITICAL",
                f"{label} is invalid JSON: {err}",
                f"Fix JSON syntax in {path}"))
        elif not isinstance(data, dict):
            issues.append(Issue("config_sync", "CRITICAL",
                f"{label} is not a JSON object",
                f"Verify structure of {path}"))

    # Commands files — verify each is non-empty and readable
    live_cmds_dir = project_dir / ".claude" / "commands"
    if live_cmds_dir.exists():
        for cmd_file in live_cmds_dir.glob("*.md"):
            try:
                content = cmd_file.read_text(encoding="utf-8").strip()
                if not content:
                    issues.append(Issue("config_sync", "WARNING",
                        f"Command file is empty: .claude/commands/{cmd_file.name}",
                        f"Add content or remove {cmd_file.name}"))
            except Exception as e:
                issues.append(Issue("config_sync", "WARNING",
                    f"Could not read .claude/commands/{cmd_file.name}: {e}",
                    "Fix or remove the file"))

    # ----------------------------------------------------------------
    # 5b. DRIFT DETECTION — live permissions not yet in master
    # ----------------------------------------------------------------
    drift_pairs = [
        ("Project", project_dir / ".claude" / "settings.json",
                    claude_docs / "settings.project.json"),
        ("Global",  GLOBAL_SETTINGS_PATH,
                    claude_docs / "settings.global.json"),
    ]
    for label, live_path, master_path in drift_pairs:
        if not live_path.exists() or not master_path.exists():
            continue
        live_data, err1 = _load(live_path)
        master_raw, err2 = _load(master_path)
        if err1 or err2 or not live_data or not master_raw:
            continue
        master_data = _trans(master_raw)

        for section in ("allow", "deny"):
            live_entries  = set(live_data.get("permissions", {}).get(section, []))
            master_entries = set(master_data.get("permissions", {}).get(section, []))
            drift = live_entries - master_entries
            if drift:
                sample = ", ".join(sorted(drift)[:3])
                suffix = f" (+{len(drift) - 3} more)" if len(drift) > 3 else ""
                master_file = "settings.global.json" if label == "Global" else "settings.project.json"
                issues.append(Issue("config_sync", "CRITICAL",
                    f"{label} {section} list has entries not in master: {sample}{suffix}",
                    f"Add these to claude_docs/{master_file} so they travel with the repo"))

    # Commands drift — live command files not in master
    master_cmds_dir = claude_docs / "commands"
    if master_cmds_dir.exists() and live_cmds_dir.exists():
        master_names = {f.name for f in master_cmds_dir.glob("*.md")}
        live_names   = {f.name for f in live_cmds_dir.glob("*.md")}
        live_only = live_names - master_names
        if live_only:
            issues.append(Issue("config_sync", "WARNING",
                f"Commands in .claude/commands/ not in master: {', '.join(sorted(live_only))}",
                "Copy these files to claude_docs/commands/"))

    # ----------------------------------------------------------------
    # 5c. MASTER QUALITY CHECKS
    # ----------------------------------------------------------------
    master_checks = [
        ("Global master",   claude_docs / "settings.global.json",   "PreToolUse",   None),
        ("Project master",  claude_docs / "settings.project.json",  None,  "SessionStart"),
    ]
    for label, path, expected_global_hook, expected_project_hook in master_checks:
        if not path.exists():
            issues.append(Issue("config_sync", "WARNING",
                f"{label} ({path.name}) is missing",
                f"Create {path}"))
            continue

        data, err = _load(path)
        if err:
            issues.append(Issue("config_sync", "CRITICAL",
                f"{label} has invalid JSON: {err}",
                f"Fix JSON syntax in {path}"))
            continue

        # $schema present
        if "$schema" not in data:
            issues.append(Issue("config_sync", "WARNING",
                f"{label} is missing the $schema field",
                f"Add '$schema' to {path.name}"))

        # No hardcoded home paths (should use {{HOME}})
        raw_text = path.read_text(encoding="utf-8")
        for bare_path in [home_fwd, str(Path.home())]:
            if bare_path in raw_text:
                issues.append(Issue("config_sync", "CRITICAL",
                    f"{label} contains hardcoded home path '{bare_path}' — use {{{{HOME}}}} placeholder",
                    f"Replace '{bare_path}' with '{{{{HOME}}}}' in {path.name}"))
                break

        # Duplicate or empty entries
        for section in ("allow", "deny"):
            entries = data.get("permissions", {}).get(section, [])
            seen: set = set()
            dupes = [e for e in entries if (e in seen) or seen.add(e)]  # type: ignore[func-returns-value]
            if dupes:
                issues.append(Issue("config_sync", "WARNING",
                    f"{label}: duplicate {section} entries: {', '.join(dupes[:3])}",
                    f"Remove duplicates from claude_docs/{path.name}"))
            empties = [e for e in entries if not e or not e.strip()]
            if empties:
                issues.append(Issue("config_sync", "WARNING",
                    f"{label}: empty string in {section} list",
                    f"Remove empty entries from claude_docs/{path.name}"))

        # Expected hook structure
        hooks = data.get("hooks", {})
        if expected_global_hook and expected_global_hook not in hooks:
            issues.append(Issue("config_sync", "WARNING",
                f"{label} is missing expected '{expected_global_hook}' hook",
                f"Add {expected_global_hook} hook to {path.name}"))
        if expected_project_hook and expected_project_hook not in hooks:
            issues.append(Issue("config_sync", "WARNING",
                f"{label} is missing expected '{expected_project_hook}' hook",
                f"Add {expected_project_hook} hook to {path.name}"))

    return issues


# === MAIN ===

def main():
    project_dir = Path.cwd()
    if not (project_dir / ".git").exists():
        for parent in project_dir.parents:
            if (parent / ".git").exists():
                project_dir = parent
                break
        else:
            print("Not a git repository — skipping audit", file=sys.stderr)
            sys.exit(0)

    issues = collect_issues(project_dir)
    if not issues:
        print(json.dumps({"status": "clean", "project": str(project_dir)}))
        sys.exit(0)

    critical = [i for i in issues if i.severity == "CRITICAL"]
    warnings = [i for i in issues if i.severity == "WARNING"]

    lines = [f"PRE-PUSH AUDIT FAILED — {len(critical)} critical, {len(warnings)} warnings",
             f"Project: {project_dir}", ""]
    if critical:
        lines.append("=== CRITICAL (must fix before push) ===")
        for n, i in enumerate(critical, 1):
            lines.append(f"{n}. [{i.category}] {i.message}")
            lines.append(f"   FIX: {i.fix}")
        lines.append("")
    if warnings:
        lines.append("=== WARNINGS (should fix) ===")
        for n, i in enumerate(warnings, 1):
            lines.append(f"{n}. [{i.category}] {i.message}")
            lines.append(f"   FIX: {i.fix}")
        lines.append("")
    lines.append("Fix all CRITICAL issues, then retry the push.")

    print("\n".join(lines), file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
