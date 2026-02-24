# Claude Code OS

## Session Start

At the beginning of every session, read these files in order:
1. @.claude/personality.md — How to behave, communicate, and self-manage
2. @.claude/project-context.md — What this project is and its key files
3. `.memory/state.md` — Current state. Spawn memory subagent (execute `.memory/instructions.md`).

The global personality at `C:\\Users\\irphy\\.claude\\personality.md` always applies.

## File Architecture

```
SyntaxTreeHybrid/
├── CLAUDE.md                    ← This file (lean OS — do not bloat)
├── claude_docs/                 ← Portable config (travels with git)
│   ├── bootstrap/migrate_settings.py  ← Run once on new machine, then auto
│   ├── commands/                ← Master slash commands
│   ├── hooks/                   ← Master global hook scripts
│   ├── settings.global.json     ← Master for ~/.claude/settings.json
│   ├── settings.project.json    ← Master for .claude/settings.json
│   └── settings.local.template.json   ← Template only, never overwritten
└── .claude/
    ├── personality.md           ← Universal base + project-specific behavior
    ├── project-context.md       ← Project knowledge (update when things change)
    ├── settings.json            ← Auto-rebuilt by migrate_settings on each launch
    ├── settings.local.json      ← Machine-specific overrides (gitignored)
    ├── skills/                  ← Skills (on demand)
    └── commands/                ← Auto-rebuilt by migrate_settings on each launch
```

## New Machine Setup

Clone → run `python claude_docs/bootstrap/migrate_settings.py` once → auto-migrates via SessionStart hook on every future launch.

## Self-Management

- **This file:** Under 50 lines. No project content, behavior, or permissions.
- **personality.md:** Universal section untouched. Project section yours to evolve.
- **project-context.md:** Update when project structure changes. Under 80 lines.
- **settings.json:** Self-manage permissions with wildcards. Rules in personality.md.

## Self-Review (every 20 tasks)

1. CLAUDE.md — anything here that belongs elsewhere? Move it.
2. project-context.md — stale or wrong? Fix it.
3. personality.md project section — still accurate? Update it.
4. settings.json — permissions still accurate? settings.local.json — machine-specific only?
5. Report changes.

## Hooks

Active hooks in `.claude/settings.json`. Machine overrides in `.claude/settings.local.json` (gitignored).

## Git

If this is a git repo, commit and push at end of every completed task.
