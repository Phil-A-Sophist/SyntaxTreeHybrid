# SyntaxTreeHybrid

## Normal Startup
Hooks run automatically. Proceed in RESEARCH mode once kickstart completes.

## If Kickstart Failed
Run: `python "C:/Users/irphy/Documents/MemoryBot/memorybot_core/agent.py" --kickstart --project-root .`
Or manually read: C:/Users/irphy/Documents/MemoryBot/memorybot_core/personality.md, memorybot-local/state.md,
memorybot-local/project-map.md, memorybot-local/knowledge-base.md

## Claude Desktop
Call `syntaxtree_kickstart()` via MCP server. If unavailable, use Supabase MCP
to read the above files from project id: d39d3edb-57f4-4863-adba-2ff724f83670.
Drop incoming files at data/dropzone/.
