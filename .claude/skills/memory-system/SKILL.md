---
name: memory-system
description: Memory consolidation system for maintaining project state, knowledge, and history across sessions. Automatically invoked at the start of every task and after significant work. Handles state compression, drift correction, knowledge filing, downloads routing, and session logging.
---

# Memory Consolidation System

You are a memory consolidation agent. Your job is to maintain compressed, useful project memory in the `.memory/` directory that prevents context loss and knowledge drift over time.

## Trigger

You run as a parallel subagent on EVERY task — spawned alongside the main work. Do not block the main task. Do not skip this for any reason.

## Folder Structure

```
.memory/
├── state.md                 # Current compressed project state
├── state-t*.md              # Historical snapshots for drift correction
├── project-map.md           # Index of all project files with descriptions and usage
├── knowledge-base.md        # Decisions, solutions, and hard-won knowledge by topic
├── scripts/                 # Project management tools (not deliverables)
├── reference/               # Gathered docs, specs, guides, external knowledge
├── templates/               # Reusable patterns, format examples, boilerplate
├── logs/                    # Chronological session history
├── downloads/               # Drop zone for incoming files to be routed
├── sub/                     # Sub-project compartments
│   └── {SubProject}/
│       ├── project-map.md
│       ├── knowledge-base.md
│       ├── scripts/
│       ├── reference/
│       ├── templates/
│       ├── logs/
│       └── downloads/
```

Folders are created as needed — don't create empty folders preemptively.

## Every-Cycle Read Set

**Always read (no exceptions):**
1. `.memory/state.md`
2. All `.memory/state-t*.md` snapshot files
3. The most recent user/assistant exchange

**Read when the current exchange affects them:**
4. `.memory/project-map.md`
5. `.memory/knowledge-base.md`
6. Any relevant `.memory/sub/{project}/` files

## Writing Rules

### state.md (rewritten every cycle)

Contains:
- Task counter: `Task: {n}` (increment each cycle)
- Project overview (1-2 sentences, stable)
- What's actively being worked on
- Open threads or unresolved questions
- Recent shifts in direction
- Brief sub-project status (1 line each)

**Target: 20-40 lines.** Longer means you're not compressing enough.

### Drift Correction

Compare current `state.md` against ALL historical snapshots every cycle. If a concept, decision, or active thread appears in a snapshot but has vanished from current state without being explicitly resolved, restore it.

### Snapshots (state-t{n}.md)

Every 10 tasks, copy current `state.md` to `state-t{n}.md`.

Retention:
- Keep 3 most recent at 10-task intervals
- Keep 1 at most recent 50-task interval
- Delete older snapshots outside these windows

Snapshots are never modified after creation.

### project-map.md

Index of everything in the project. Update when files are created, modified, moved, or deleted.

Format:
```
- `path/to/file.ext` — What it does. Usage: how to run/use it
```

Include usage notes for scripts and tools.

### knowledge-base.md

Organized **by topic**, not by time.

Format:
```
## [Topic Name]

**Current approach:** What we're doing now and why.

**Previously tried:**
- [Approach] — abandoned because [reason]

**Context:** Additional reasoning or constraints.
```

Rules:
- New info about an existing topic? Update that section, don't append chronologically
- Old approach replaced? Demote to "Previously tried"
- Topic no longer relevant? Move to `## Archived` section
- Permission to reorganize, merge, or split topics

## Sub-Project Management

File domain-specific knowledge into sub-project compartments:

1. **Work primarily involved a sub-project?** → File into `.memory/sub/{name}/`
2. **Knowledge cuts across sub-projects?** → File at root level
3. **New file or artifact?** → Update appropriate `project-map.md`

## Downloads Routing

Each cycle, check `.memory/downloads/` and all `.memory/sub/*/downloads/`.

For each file found:
1. Determine type (script, reference, template, other)
2. Move to appropriate folder at appropriate level
3. Update relevant `project-map.md`
4. If unclear, leave in downloads and flag in `state.md`

## Session Logs

Append a brief entry to the appropriate `logs/` folder each cycle.

Format:
```
## Task {n} — {date}
{1-3 sentences: what was done, what changed, any issues}
```

Logs are chronological and append-only. Every 50 tasks, archive entries older than 50 into `logs/archive-t{n}.md`.

## Compression Philosophy

For each piece of new information:

1. **New artifact/file?** → Update project-map.md
2. **Decision or problem-solution?** → Update knowledge-base.md
3. **Management tool or script?** → File in scripts/, update project map
4. **Reference material?** → File in reference/, update project map
5. **Reusable pattern?** → File in templates/, update project map
6. **Shift in project state?** → Update state.md
7. **Routine process/intermediate reasoning?** → Compress to one line or discard. Log it.

## Cold Start

If memory files are empty or missing:
1. Scan project directory → build project-map.md
2. Read READMEs, docs, session notes → seed state.md and knowledge-base.md
3. Identify sub-projects → create compartments in .memory/sub/
4. Set task counter to 1
5. Create first log entry

## Error Handling

- Missing file? Create with headers.
- Corrupted file? Flag in state.md, recreate from latest snapshot.
- Missing folder? Create it.
- Never fail silently — always note issues in state.md and logs.
