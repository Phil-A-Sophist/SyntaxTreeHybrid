# Knowledge Base — SyntaxTreeHybrid

## Architecture Pattern
**Current approach:** Single-page app with no build step. All JS modules export via `window.*` globals. Scripts are loaded in dependency order in index.html: tree-model.js -> bracket-parser.js -> bracket-serializer.js -> canvas-manager.js -> sync-engine.js -> app.js. Fabric.js 5.2.4 loaded from CDN.
**Previously tried:** N/A (initial architecture).
**Context:** The app is designed as a teaching/learning tool for linguistics. Simplicity of deployment (just open the HTML file) is a priority.

## Tree Model Design
**Current approach:** SyntaxTree holds an array of `roots` (supports forest/multiple trees). TreeNode has id, label, nodeType, children, parent, position (x,y), movement markers, and canvas object reference. Node types: CLAUSE, PHRASE, POS, TERMINAL. Event system with beginBatch/endBatch for complex operations.
**Previously tried:** N/A.
**Context:** The tree model is the single source of truth. Both bracket notation and canvas rendering derive from it.

## Layout Algorithm
**Current approach:** Bottom-up layout. Step 1: calculate leaf counts per subtree. Step 2: calculate depths. Step 3: collect leaves left-to-right. Step 4: position leaves with fixed UNIT_WIDTH spacing. Step 5: center parents over their children. Step 6: animate to target positions with ease-out cubic. Key constants: UNIT_WIDTH=145, LEVEL_HEIGHT=105, TOP_MARGIN=40, ANIMATION_DURATION=150ms.
**Previously tried:** N/A.
**Context:** Layout is triggered after every structural change (add, remove, connect, disconnect, reorder).

## Auto-Connection System
**Current approach:** Proximity-based with weighted scoring. Horizontal distance weighted 1.5x more than vertical. CONNECTION_THRESHOLD=360px, DISCONNECT_THRESHOLD=540px (hysteresis). Parent must be above child by at least MIN_VERTICAL_GAP=25px. Also supports insertion between existing nodes when dragged near a connection line (LINE_INSERTION_THRESHOLD=40px).
**Previously tried:** N/A.
**Context:** This is the core UX innovation -- nodes auto-connect when dragged near potential parents, with visual preview lines.

## Bracket Notation
**Current approach:** Parser auto-balances unmatched brackets for live preview during typing. Supports movement notation: `_label` for movement head, `<label>` for movement tail/trace. Supports `^` for starred/triangle nodes. Serializer has compact and pretty-print modes plus position mapping for cursor-to-node lookup.
**Previously tried:** N/A.
**Context:** Bidirectional sync between bracket text and canvas with 500ms debounce on text input.

## Supported Syntactic Categories
**Current approach:** Clauses: S, IC, DC, RC, CC, CP, IP, TP. Phrases: NP, VP, PP, ADJP, ADVP, DP. POS (full): NOUN, VERB, ADJ, ADV, DET, PRON, PREP, CONJ, MOD, AUX, SUB, REL, COMP. POS (single letter): N, V, A, P, D, C, T, I. Penn Treebank: NN, NNS, NNP, NNPS, VB, VBD, VBG, VBN, VBP, VBZ, JJ, JJR, JJS, RB, RBR, RBS, IN, DT, PRP, PRP$, WP, WDT, WRB, MD, TO. Each has a specific color mapping.
**Previously tried:** N/A.
**Context:** Color coding helps visually distinguish category types. Clauses are white, phrases are saturated colors, POS tags are lighter shades.

## Testing Strategy
**Current approach:** Two testing layers. (1) Playwright JS specs in `tests/` for unit-level browser tests. (2) Python Playwright scripts for visual regression across all 39 diagram patterns (from simple intransitive sentences through complement clauses). Python tests spin up a local HTTP server, load the app, and take screenshots.
**Previously tried:** N/A.
**Context:** The 39 test patterns come from "F25 - Sentence Diagram Patterns by Phillip" and cover comprehensive English syntax structures.

## Export
**Current approach:** PNG export at 4x resolution via Fabric.js `toDataURL`. Tight bounding box with 10% padding. Temporary border rectangle added during export. Supports clipboard copy and file download. Shareable URLs via `?i=` or `?tree=` query parameter with URI-encoded bracket notation.
**Previously tried:** N/A.
**Context:** High-resolution export is important for use in academic papers and presentations.
