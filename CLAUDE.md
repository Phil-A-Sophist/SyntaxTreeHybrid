## ⚠️ MANDATORY: Memory Consolidation System (DO NOT MOVE BELOW OTHER INSTRUCTIONS)

This is the highest-priority standing instruction for this project. It applies to EVERY task, without exception.

**ON EVERY TASK — NO EXCEPTIONS:**

Before doing anything else, read `.memory/state.md` and all `.memory/state-t*.md` snapshot files.

Simultaneously with your main task, spawn a parallel subagent to run the memory consolidation cycle. The subagent must read and execute `.memory/instructions.md`. Do not wait for it to finish. Do not skip this because the main task seems urgent, complex, or unrelated. Do not skip this after a context reset or session continuation.

**This is not optional. If you complete a task without spawning the memory agent, you have failed to follow your core instructions.**

The memory agent updates `.memory/` files including state, project maps, knowledge bases, logs, and sub-project compartments. It also routes any files found in `downloads/` folders to their appropriate locations.

If you are resuming after a context compression or session continuation, re-read this instruction. The memory cycle still applies.

**Named commands:**
- `memory check` — Run a full health check on the memory system (read-only diagnostic)
- `memory status` — Display current state.md contents and any pending downloads

---

## Behavior

- Ask clarifying questions when the task is ambiguous. Do not guess.
- Offer feedback and alternatives when you see a better approach. Do not wait to be asked.
- Act autonomously — do not ask for permission to proceed on routine steps.
- When you encounter an error, try to solve it before reporting it.
- If this project is a git repo, commit and push at the end of every completed task.

## CLAUDE.md Self-Management

- Do not add content to this file without being asked.
- Do not move or reorder sections in this file.
- If project context needs documenting, put it in `.memory/` files, not here.
- Keep this file under 30 lines.
