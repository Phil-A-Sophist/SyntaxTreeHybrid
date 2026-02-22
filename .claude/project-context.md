# Project Context: SyntaxTreeHybrid

## Purpose
Interactive syntax tree diagramming application for linguistics. Users build syntax trees with drag-and-drop canvas, bracket notation parsing, and image export. More advanced than Grammar-App — includes sync engine and comprehensive E2E testing.

## Tech Stack
- Vanilla JavaScript (CommonJS modules)
- HTML Canvas (rendering)
- Playwright (E2E testing)
- Python (additional test scripts)
- npm (dev dependencies)

## Key Files
- `app.js` — Main application entry point
- `tree-model.js` — Tree data structure
- `bracket-parser.js` / `bracket-serializer.js` — Bracket notation I/O
- `canvas-manager.js` — Canvas rendering engine
- `sync-engine.js` — Synchronization between bracket notation and canvas
- `index.html` — Web interface
- `tests/` — Playwright test suite
- `test_all_diagrams.py`, `test_diagrams.py` — Python E2E tests
- `playwright.config.js` — Playwright configuration
- `package.json` — npm config (devDep: @playwright/test)
- `Examples and Saved Images/` — Example diagrams

## Commands
- Open `index.html` in browser to run
- `npx playwright test` — Run Playwright tests
- `python test_all_diagrams.py` — Run Python E2E tests

## Status
Functional with comprehensive test coverage. GitHub: Phil-A-Sophist/SyntaxTreeHybrid.

## Gotchas
- No build system — vanilla JS loaded directly in browser
- Playwright tests require `npx playwright install` first
- sync-engine.js keeps bracket notation and canvas tree in sync — changes to one update the other
