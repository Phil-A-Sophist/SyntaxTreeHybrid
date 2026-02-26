# Claude Code OS

## Session Start

At the beginning of every session, read these files in order:
1. @claude_docs/personality/personality.md — How to behave, communicate, and self-manage
2. @claude_docs/personality/project-personality.md — This project's context, priorities, and behaviors
3. `claude_docs/memory/state.md` — Current state. Spawn memory subagent (execute `claude_docs/memory/instructions.md`).

The global personality at `C:\Users\irphy\.claude\personality.md` always applies.
Meta-agent runs automatically via hooks (bootstrap/review/consolidate/finalize).

## File Architecture

```
SyntaxTreeHybrid/
├── CLAUDE.md                              <- This file (lean OS)
├── claude_docs/
│   ├── meta-agent/agent.py                <- bootstrap/review/consolidate/finalize/audit
│   ├── commands/                          <- Master slash commands
│   ├── hooks/                             <- Master global hook scripts
│   ├── memory/                            <- Project memory (travels with git)
│   ├── personality/personality.md         <- Universal base behaviors
│   ├── personality/project-personality.md <- Project context and behaviors
│   └── settings.local.template.json       <- Template only, never overwritten
└── .claude/
    ├── settings.json                      <- Hooks + permissions (committed)
    ├── settings.local.json                <- Machine-specific, gitignored
    └── commands/                          <- Synced from claude_docs/commands/
```

## New Machine Setup

Clone -> open Claude Code -> meta-agent bootstraps automatically on first SessionStart.

## Self-Management

- **This file:** Under 60 lines. No project content, behavior, or permissions.
- **personality.md:** Universal section untouched. Project section in project-personality.md.
- **project-personality.md:** Update when project priorities or behaviors change.
- **settings.json:** Self-manage permissions with wildcards. Rules in personality.md.

## Self-Review (every 20 tasks)

1. CLAUDE.md — anything here that belongs elsewhere? Move it.
2. project-personality.md — stale or wrong? Fix it.
3. personality.md project section — still accurate? Update it.
4. settings.json — permissions accurate? settings.local.json — machine-specific only?
5. Report changes.

## Hooks

Active hooks in `.claude/settings.json`. Machine overrides in `settings.local.json` (gitignored).
Meta-agent: SessionStart=bootstrap, Stop=review, TaskCompleted=consolidate, SessionEnd=finalize.

## Git

If this is a git repo, commit and push at end of every completed task.
