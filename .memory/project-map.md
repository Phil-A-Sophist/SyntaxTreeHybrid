# Project Map — SyntaxTreeHybrid

## Core Application Files
- index.html — Main HTML entry point; inline CSS; palette tiles for all syntactic categories; loads Fabric.js from CDN
- app.js — Application bootstrap on DOMContentLoaded; wires palette drag/drop, word input, sync toggle, zoom controls, export buttons, URL parameter loading
- tree-model.js — Core data model: TreeNode class, SyntaxTree class, NodeType enum, NodeColors map, getNodeTypeFromLabel(), getNodeColors()
- canvas-manager.js — Fabric.js canvas rendering engine; tile creation/styling, auto-connection with proximity scoring, bottom-up layout algorithm, subtree dragging, insertion between nodes, movement arrows, PNG export, fit-to-view
- bracket-parser.js — Parses bracket notation strings (e.g. "[S [NP ...]]") into SyntaxTree; handles unbalanced brackets, movement markers (_label, <label>), starred nodes (^)
- bracket-serializer.js — Serializes SyntaxTree to bracket notation; compact and pretty-print modes; position mapping for cursor-to-node lookup
- sync-engine.js — Bidirectional sync between bracket text panel and canvas; debounced text input (500ms), event-driven canvas-to-text, auto-sync toggle

## Configuration
- package.json — npm package metadata; devDependency on @playwright/test ^1.58.0; commonjs module type
- playwright.config.js — Playwright test config: chromium project, headless, 30s timeout, ./tests directory
- .claude/settings.local.json — Claude Code local permission settings

## Test Files (Playwright JS)
- tests/positioning.spec.js — Playwright spec verifying terminal child is vertically aligned below POS parent after drag-drop

## Test Files (Python + Playwright)
- test_diagrams.py — Main Python test suite: tests all 39 sentence diagram patterns via bracket input; SyntaxTreeTester class with HTTP server, drag-drop, and screenshot methods
- test_single.py — Python script to test a single diagram pattern
- test_all_diagrams.py — Python script to run all diagram tests
- test_spacing.py — Python script to test spacing/layout correctness
- test_dragdrop_ux.py — Python script to test drag-and-drop user experience
- regenerate_diagrams.py — Python script to regenerate all reference diagram PNG screenshots

## Reference Materials
- Examples and Saved Images/*.png — 39 reference diagram screenshots (01 through 39) covering simple intransitive through missing complementizer patterns
- Examples and Saved Images/extracted_diagrams/ — Extracted images from reference Word document
- Examples and Saved Images/F25 - Sentence Diagram Patterns by Phillip - Complete.docx — Reference document with all sentence diagram patterns

## Memory System
- .memory/instructions.md — Memory compression agent instructions
- .memory/state.md — Current compressed project state (updated every task cycle)
- .memory/project-map.md — This file
- .memory/knowledge-base.md — Decisions, solutions, and accumulated knowledge
