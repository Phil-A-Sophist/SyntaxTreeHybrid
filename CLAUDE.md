# CLAUDE.md - Project Configuration for SyntaxTreeHybrid

## Overview

SyntaxTreeHybrid is a browser-based interactive syntax tree diagram builder for linguistic analysis. It provides a dual-interface approach: users can either visually drag-and-drop syntactic category tiles onto an HTML5 canvas, or type bracket notation (e.g., `[S [NP the cat] [VP ran]]`) into a text panel. Both views stay synchronized in real time via a sync engine. The app supports clauses (S, IC, DC, RC, CC), phrase types (NP, VP, PP, ADJP, ADVP), parts of speech (NOUN, VERB, ADJ, ADV, DET, PRON, PREP, etc.), and terminal/word nodes. It also supports Penn Treebank-style POS tags, movement notation, and starred nodes for triangle rendering. Trees can be exported as high-resolution PNG images or shared via URL parameters.

## Tech Stack

- **Language:** JavaScript (vanilla, no bundler, no framework)
- **Rendering:** Fabric.js 5.2.4 (loaded via CDN) for HTML5 canvas manipulation
- **UI:** Single-page `index.html` with inline CSS, no build step
- **Testing (E2E):** Playwright (`@playwright/test`) for browser-based integration tests
- **Testing (visual regression):** Python scripts using `playwright` (Python) for automated screenshot generation of all 39 diagram patterns
- **Module system:** Browser globals (`window.*` exports); `package.json` uses `"type": "commonjs"` for the Playwright config only
- **Repository:** GitHub at `Phil-A-Sophist/SyntaxTreeHybrid`

## Project Structure

```
SyntaxTreeHybrid/
  index.html              -- Main HTML entry point (inline CSS, loads all JS)
  app.js                  -- Application bootstrap and UI wiring (palette drag/drop, zoom, export, URL loading)
  tree-model.js           -- Core data model: TreeNode, SyntaxTree, NodeType, NodeColors
  canvas-manager.js       -- Fabric.js canvas rendering, tile creation, auto-layout, auto-connection, export
  bracket-parser.js       -- Parses bracket notation strings into tree model
  bracket-serializer.js   -- Serializes tree model back to bracket notation
  sync-engine.js          -- Bidirectional sync between bracket text and canvas
  package.json            -- npm metadata, Playwright devDependency
  playwright.config.js    -- Playwright test configuration (chromium, headless)
  tests/
    positioning.spec.js   -- Playwright spec: verifies tile positioning after drag-drop
  test_diagrams.py        -- Python Playwright: tests all 39 sentence diagram patterns
  test_single.py          -- Python Playwright: tests a single diagram
  test_all_diagrams.py    -- Python Playwright: runs all diagram tests
  test_spacing.py         -- Python Playwright: tests spacing/layout
  test_dragdrop_ux.py     -- Python Playwright: tests drag-and-drop UX
  regenerate_diagrams.py  -- Python script to regenerate all reference diagram PNGs
  Examples and Saved Images/
    *.png                 -- Reference diagram screenshots (39 patterns)
    extracted_diagrams/   -- Extracted images from reference docx
  .claude/
    settings.local.json   -- Claude Code local permissions
```

## Build / Run Instructions

**No build step required.** This is a static single-page application.

### Run locally
1. Serve the project directory with any static HTTP server:
   ```
   python -m http.server 8080
   ```
   or use VS Code Live Server, `npx serve`, etc.
2. Open `http://localhost:8080/index.html` in a browser.

Alternatively, open `index.html` directly as a `file://` URL (Fabric.js is loaded from CDN, so internet access is required).

### Run tests (Playwright JS)
```
npm install
npx playwright test
```

### Run tests (Python visual regression)
```
pip install playwright
python -m playwright install chromium
python test_diagrams.py
```

## Key Files

| File | Purpose |
|------|---------|
| `tree-model.js` | Single source of truth: `TreeNode`, `SyntaxTree`, node types, color mappings |
| `canvas-manager.js` | All Fabric.js rendering, drag logic, auto-connection, layout algorithm, PNG export |
| `bracket-parser.js` | Converts bracket notation string to `SyntaxTree` (handles unbalanced brackets, movement markers) |
| `bracket-serializer.js` | Converts `SyntaxTree` to bracket notation (compact and pretty-print modes) |
| `sync-engine.js` | Keeps canvas and bracket text in sync; debounced text input, event-driven canvas changes |
| `app.js` | Wires everything together on `DOMContentLoaded`; palette setup, zoom, export, URL loading |
| `index.html` | All HTML structure and CSS styles; palette tiles for clauses/phrases/POS |

## Conventions

- All JS modules export via `window.*` (no import/export statements).
- Node colors are defined in `NodeColors` (tree-model.js) and matched in palette tile `style` attributes in `index.html`.
- The tree model uses an event system (`addEventListener`/`emit`) for change propagation.
- Auto-connection uses proximity-based scoring with weighted horizontal distance.
- Layout is bottom-up: leaves are positioned first with fixed spacing, then parents are centered over children.

## Memory System

This project uses an ongoing memory consolidation system. Follow these rules on every task:

1. **Before starting any task:** Read `.memory/state.md` and all `.memory/state-t*.md` snapshot files.
2. **During every task:** Spawn a parallel subagent to handle memory consolidation. The subagent should read and follow the instructions in `.memory/instructions.md`. This runs alongside the main task -- do not wait for it to complete.
3. **The memory agent updates:** `.memory/state.md` every cycle, and `.memory/project-map.md` and `.memory/knowledge-base.md` when the current task produces relevant changes.
4. **Never skip the memory cycle.** Even for small tasks, the parallel agent should run.
