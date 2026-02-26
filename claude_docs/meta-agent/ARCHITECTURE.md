# Meta-Agent Architecture

## The Sync Model

```
~/.claude/                    <- The Hub (global)
    sync (bidirectional)
.claude/ (any project)        <- Spokes (projects)
```

- Everything syncs everywhere, additive only — never remove entries
- Global is the hub connecting all projects
- Bootstrap: global → project (start of session)
- Finalize/Audit: project → global (end of session / before push)

## The Five Modes

| Mode         | Trigger       | Direction         | Purpose                          |
|--------------|---------------|-------------------|----------------------------------|
| --bootstrap  | SessionStart  | Global → Project  | Sync config, verify structure    |
| --review     | Stop          | —                 | Quick capture from transcript    |
| --consolidate| TaskCompleted | —                 | Thorough review + task increment |
| --finalize   | SessionEnd    | Project → Global  | Sync config, emergency save      |
| --audit      | PrePush       | Project → Global  | Validate + sync before push      |

## What Gets Synced

- `settings.json` — merged additively (permissions + hooks combined, no duplicates)
- `hooks/` — copy files that don't exist in destination
- `commands/` — copy files that don't exist in destination

## Files

```
claude_docs/meta-agent/
├── agent.py              <- Main entry point (dispatch to modes)
├── ARCHITECTURE.md       <- This file
└── modes/
    ├── bootstrap.py      <- Sync global → project
    ├── review.py         <- Quick capture from CLI transcript
    ├── consolidate.py    <- Thorough review + state management
    ├── finalize.py       <- Sync project → global
    └── audit.py          <- Validate + sync before push
```

## Hook Wiring

```
SessionStart  -> agent.py --bootstrap
Stop          -> agent.py --review
TaskCompleted -> agent.py --consolidate
SessionEnd    -> agent.py --finalize
PrePush       -> pre_tool_gate.py -> agent.py --audit  (via git push intercept)
```

## Memory System Integration

The meta-agent handles programmatic memory tasks:
- Task counter increment (--consolidate)
- Snapshot creation and pruning (--consolidate)
- Drift detection (--consolidate)
- Session log entries (--consolidate)
- Downloads check (--consolidate)

The LLM-based memory agent (claude_docs/memory/skills/memory-system/SKILL.md) handles
reasoning-heavy tasks that require judgment:
- Deciding what belongs in knowledge-base.md
- Writing human-readable summaries
- Evaluating whether drift is real or resolved

Both systems complement each other and should both run each session.

## Design Principles

1. **Additive only** — never remove entries from merged configs
2. **Fast modes run silently** — --review and --finalize produce no output
3. **Verbose modes summarize** — --bootstrap, --consolidate, --audit print status
4. **Graceful degradation** — if any step fails, continue and report; never crash
5. **Windows-first** — use `python` (not python3), forward-slash paths in output
6. **Project-portable** — all paths derived from PROJECT_ROOT, no hardcoded paths
