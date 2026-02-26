# Memory Consolidation Instructions

This file redirects to the canonical memory system instructions.

**Read and execute:** `claude_docs/memory/skills/memory-system/SKILL.md`

That file contains the full memory consolidation cycle logic including:
- Every-cycle read set
- Writing rules for state.md, project-map.md, knowledge-base.md
- Drift correction and snapshot management
- Downloads routing
- Session logging
- Sub-project management
- Compression philosophy

## Meta-Agent Integration

The meta-agent (`claude_docs/meta-agent/agent.py`) handles programmatic memory tasks
automatically via hooks. You (the LLM subagent) handle the reasoning-heavy parts:

| Task | Handled by |
|------|-----------|
| Task counter increment | Meta-agent --consolidate |
| Snapshot creation/pruning | Meta-agent --consolidate |
| Drift detection (structural) | Meta-agent --consolidate |
| Session log entry | Meta-agent --consolidate |
| Downloads check | Meta-agent --consolidate |
| knowledge-base.md updates | LLM subagent (you) |
| Evaluating what to capture | LLM subagent (you) |
| Drift correction (semantic) | LLM subagent (you) |
| project-map.md deep updates | LLM subagent (you) |

The meta-agent runs first (via TaskCompleted hook). You run in parallel at session start.
Your job is the parts that require judgment — the meta-agent handles the rest.
