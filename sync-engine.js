/**
 * Sync Engine - Keeps bracket notation and canvas synchronized
 */

class SyncEngine {
  constructor(tree, canvasManager, bracketInput, statusElement) {
    this.tree = tree;
    this.canvasManager = canvasManager;
    this.bracketInput = bracketInput;
    this.statusElement = statusElement;

    this.parser = new BracketParser();
    this.serializer = new BracketSerializer();

    // Sync state
    this.autoSync = true;
    this.isSyncing = false;
    this.textIsFocused = false;
    this.pendingTextSync = false;

    // Debounce timer for text input
    this.textDebounceTimer = null;
    this.TEXT_DEBOUNCE_MS = 500;

    this.setupEventListeners();
    this.setupTreeListeners();
  }

  setupEventListeners() {
    // Text input events
    this.bracketInput.addEventListener('focus', () => {
      this.textIsFocused = true;
      this.setStatus('Editing...', 'editing');
    });

    this.bracketInput.addEventListener('blur', () => {
      this.textIsFocused = false;
      if (this.pendingTextSync) {
        this.syncTextToCanvas();
        this.pendingTextSync = false;
      }
      this.setStatus('Ready');
    });

    this.bracketInput.addEventListener('input', () => {
      if (!this.autoSync) return;

      // Clear existing timer
      if (this.textDebounceTimer) {
        clearTimeout(this.textDebounceTimer);
      }

      // Validate in real-time
      const validation = this.parser.validate(this.bracketInput.value);
      if (!validation.valid) {
        this.setStatus(validation.error, 'error');
      } else {
        this.setStatus('Editing...', 'editing');
      }

      // Schedule sync
      this.textDebounceTimer = setTimeout(() => {
        this.syncTextToCanvas();
      }, this.TEXT_DEBOUNCE_MS);
    });

    // Enter key commits immediately
    this.bracketInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        if (this.textDebounceTimer) {
          clearTimeout(this.textDebounceTimer);
        }
        this.syncTextToCanvas();
      }
    });
  }

  setupTreeListeners() {
    this.tree.addEventListener((event, data) => {
      if (this.isSyncing) return;

      // Tree changed - sync to text
      if (!this.textIsFocused) {
        this.syncCanvasToText();
      } else {
        // Don't interrupt typing, but mark as pending
        this.pendingTextSync = false; // Canvas changes take precedence when text loses focus
      }

      // Handle specific events for canvas updates
      switch (event) {
        case 'root-added':
        case 'nodes-connected':
          this.canvasManager.relayout();
          break;
        case 'nodes-disconnected':
        case 'root-removed':
          this.canvasManager.relayout();
          break;
        case 'nodes-deleted':
          data.nodes.forEach(node => {
            this.canvasManager.removeTileForNode(node);
          });
          this.canvasManager.updateConnectionLines();
          this.canvasManager.relayout();
          break;
        case 'node-updated':
          this.canvasManager.updateTileLabel(data.node);
          break;
        case 'tree-changed':
          this.canvasManager.syncFromTree();
          this.canvasManager.relayout();
          break;
        case 'tree-cleared':
          this.canvasManager.syncFromTree();
          break;
      }
    });

    // Canvas changes callback
    this.canvasManager.onTreeChanged = () => {
      if (!this.textIsFocused) {
        this.syncCanvasToText();
      }
    };
  }

  /**
   * Sync bracket text to canvas
   * Always attempts to parse and render, even with incomplete input.
   * The parser auto-balances brackets to handle partial input.
   */
  syncTextToCanvas() {
    if (!this.autoSync || this.isSyncing) return;

    const text = this.bracketInput.value.trim();

    // Validate to show status, but don't block parsing
    const validation = this.parser.validate(text);

    this.isSyncing = true;

    try {
      // Parse the text into the tree (clears and rebuilds)
      // The parser auto-balances brackets, so incomplete input still renders
      this.parser.parse(text, this.tree);

      // Rebuild canvas
      this.canvasManager.syncFromTree();

      // Show appropriate status
      if (!validation.valid) {
        this.setStatus(validation.error, 'warning');
      } else {
        this.setStatus('Synced');
      }
    } catch (e) {
      this.setStatus('Parse error: ' + e.message, 'error');
    }

    this.isSyncing = false;
  }

  /**
   * Sync canvas to bracket text
   */
  syncCanvasToText() {
    if (this.isSyncing) return;

    this.isSyncing = true;

    try {
      const text = this.serializer.serialize(this.tree);
      this.bracketInput.value = text;
      this.setStatus('Ready');
    } catch (e) {
      console.error('Serialization error:', e);
    }

    this.isSyncing = false;
  }

  /**
   * Force sync from canvas to text
   */
  forceCanvasToText() {
    const wasSyncing = this.isSyncing;
    this.isSyncing = false;
    this.syncCanvasToText();
    this.isSyncing = wasSyncing;
  }

  /**
   * Force sync from text to canvas
   */
  forceTextToCanvas() {
    const wasSyncing = this.isSyncing;
    this.isSyncing = false;
    this.syncTextToCanvas();
    this.isSyncing = wasSyncing;
  }

  /**
   * Toggle auto-sync
   */
  setAutoSync(enabled) {
    this.autoSync = enabled;
    if (enabled) {
      this.syncCanvasToText();
    }
  }

  /**
   * Set status message
   */
  setStatus(message, type = '') {
    this.statusElement.textContent = message;
    this.statusElement.className = 'bracket-status';
    if (type) {
      this.statusElement.classList.add(type);
    }
  }

  /**
   * Get the serialized bracket notation with position mapping
   * (for cursor-to-node mapping)
   */
  getTextWithPositions() {
    return this.serializer.serializeWithPositions(this.tree);
  }

  /**
   * Find which node is at a given cursor position
   */
  getNodeAtCursor(cursorPos) {
    const { positions } = this.getTextWithPositions();
    const nodeId = this.serializer.findNodeAtPosition(cursorPos, positions);
    return nodeId ? this.tree.findById(nodeId) : null;
  }

  /**
   * Highlight text for a node
   */
  highlightNodeInText(node) {
    if (!node) return;

    const { positions } = this.getTextWithPositions();
    const pos = positions.get(node.id);

    if (pos) {
      this.bracketInput.focus();
      this.bracketInput.setSelectionRange(pos.start, pos.end);
    }
  }
}

// Export for use in other modules
window.SyncEngine = SyncEngine;
