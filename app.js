/**
 * Main Application - Ties all components together
 */

document.addEventListener('DOMContentLoaded', function() {
  // Initialize components
  const tree = new SyntaxTree();
  const canvasManager = new CanvasManager('diagram-canvas', tree);
  const bracketInput = document.getElementById('bracket-input');
  const bracketStatus = document.getElementById('bracket-status');

  const syncEngine = new SyncEngine(tree, canvasManager, bracketInput, bracketStatus);

  // Expose for testing and debugging
  window.canvasManager = canvasManager;
  window.tree = tree;
  window.syncEngine = syncEngine;

  // === Palette Drag & Drop ===
  setupPaletteDragDrop(canvasManager);

  // === Word Input Field ===
  setupWordInput(canvasManager);

  // === Sync Toggle ===
  setupSyncToggle(syncEngine);

  // === Zoom Controls ===
  setupZoomControls(canvasManager);

  // === Export Buttons ===
  setupExportButtons(canvasManager);

  // === URL Parameter Loading ===
  loadFromURL(tree, syncEngine);
});

/**
 * Setup palette drag and drop
 */
function setupPaletteDragDrop(canvasManager) {
  const paletteTiles = document.querySelectorAll('.palette-tile:not(.word-preview-tile)');

  paletteTiles.forEach(tile => {
    tile.addEventListener('dragstart', function(e) {
      this.classList.add('dragging');
      const data = {
        type: this.getAttribute('data-type'),
        value: this.getAttribute('data-abbrev') || this.getAttribute('data-value')
      };
      e.dataTransfer.setData('text/plain', JSON.stringify(data));
      e.dataTransfer.effectAllowed = 'copy';
    });

    tile.addEventListener('dragend', function() {
      this.classList.remove('dragging');
    });
  });

  // Canvas drop handling
  const canvasElement = canvasManager.canvas.upperCanvasEl;

  canvasElement.addEventListener('dragover', function(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    this.classList.add('drag-over');
  });

  canvasElement.addEventListener('dragleave', function() {
    this.classList.remove('drag-over');
  });

  canvasElement.addEventListener('drop', function(e) {
    e.preventDefault();
    this.classList.remove('drag-over');

    const data = e.dataTransfer.getData('text/plain');
    if (!data) return;

    try {
      const dropData = JSON.parse(data);

      // Get pointer coordinates transformed for zoom/pan
      const pointer = canvasManager.canvas.getPointer(e, true);

      canvasManager.handleDrop(dropData, pointer.x, pointer.y);
    } catch (error) {
      console.error('Drop error:', error);
    }
  });
}

/**
 * Setup word input field in palette
 */
function setupWordInput(canvasManager) {
  const wordInput = document.getElementById('word-input');
  const wordPreview = document.getElementById('word-preview');

  // Update preview as user types
  wordInput.addEventListener('input', function() {
    const text = this.value.trim();
    if (text) {
      wordPreview.textContent = text;
      wordPreview.classList.remove('empty');
      wordPreview.draggable = true;
    } else {
      wordPreview.textContent = '...';
      wordPreview.classList.add('empty');
      wordPreview.draggable = false;
    }
  });

  // Make preview tile draggable
  wordPreview.addEventListener('dragstart', function(e) {
    const text = wordInput.value.trim();
    if (!text) {
      e.preventDefault();
      return;
    }

    this.classList.add('dragging');
    const data = {
      type: 'terminal',
      value: text
    };
    e.dataTransfer.setData('text/plain', JSON.stringify(data));
    e.dataTransfer.effectAllowed = 'copy';
  });

  wordPreview.addEventListener('dragend', function() {
    this.classList.remove('dragging');
    // Clear input after successful drop
    wordInput.value = '';
    wordPreview.textContent = '...';
    wordPreview.classList.add('empty');
    wordPreview.draggable = false;
  });

  // Enter key in input creates terminal directly at default position
  wordInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
      const text = this.value.trim();
      if (text) {
        canvasManager.handleDrop(
          { type: 'terminal', value: text },
          canvasManager.canvas.getWidth() / 2,
          canvasManager.canvas.getHeight() / 2
        );
        this.value = '';
        wordPreview.textContent = '...';
        wordPreview.classList.add('empty');
        wordPreview.draggable = false;
      }
    }
  });
}

/**
 * Setup sync toggle button
 */
function setupSyncToggle(syncEngine) {
  const toggleBtn = document.getElementById('sync-toggle');
  let autoSync = true;

  toggleBtn.addEventListener('click', function() {
    autoSync = !autoSync;
    syncEngine.setAutoSync(autoSync);
    this.textContent = `Auto-sync: ${autoSync ? 'ON' : 'OFF'}`;
  });
}

/**
 * Setup zoom controls
 */
function setupZoomControls(canvasManager) {
  document.getElementById('zoom-in').addEventListener('click', () => {
    const zoom = Math.min(canvasManager.canvas.getZoom() * 1.2, 10);
    canvasManager.canvas.setZoom(zoom);
  });

  document.getElementById('zoom-out').addEventListener('click', () => {
    const zoom = Math.max(canvasManager.canvas.getZoom() * 0.8, 0.1);
    canvasManager.canvas.setZoom(zoom);
  });

  document.getElementById('zoom-reset').addEventListener('click', () => {
    canvasManager.canvas.setZoom(1);
    canvasManager.canvas.setViewportTransform([1, 0, 0, 1, 0, 0]);
  });
}

/**
 * Setup export buttons
 */
function setupExportButtons(canvasManager) {
  const statusEl = document.getElementById('export-status');
  const setStatus = (msg) => { statusEl.textContent = msg || ''; };
  const tree = canvasManager.tree;

  // Flash effect on success
  const flashSuccess = () => {
    const wrapper = document.getElementById('canvas-wrapper');
    wrapper.style.transition = 'box-shadow 0.2s ease';
    wrapper.style.boxShadow = '0 0 20px 5px rgba(0, 200, 100, 0.5)';
    setTimeout(() => {
      wrapper.style.boxShadow = '';
    }, 300);
  };

  // Copy to clipboard
  document.getElementById('copy-tree').addEventListener('click', async () => {
    try {
      setStatus('Copying...');
      const dataURL = await canvasManager.exportPNG(3);
      const res = await fetch(dataURL);
      const blob = await res.blob();

      await navigator.clipboard.write([
        new ClipboardItem({ 'image/png': blob })
      ]);

      flashSuccess();
      setStatus('Copied!');
    } catch (err) {
      console.error('Copy failed:', err);
      // Fallback: open in new tab
      try {
        const dataURL = await canvasManager.exportPNG(3);
        window.open(dataURL, '_blank');
        setStatus('Opened in new tab');
      } catch (e2) {
        setStatus('Copy failed');
      }
    }
    setTimeout(() => setStatus(''), 2500);
  });

  // Download
  document.getElementById('download-tree').addEventListener('click', async () => {
    try {
      setStatus('Preparing...');
      const dataURL = await canvasManager.exportPNG(3);

      const a = document.createElement('a');
      a.href = dataURL;
      a.download = 'syntax-tree.png';
      document.body.appendChild(a);
      a.click();
      a.remove();

      flashSuccess();
      setStatus('Downloaded!');
    } catch (err) {
      console.error('Download failed:', err);
      setStatus('Download failed');
    }
    setTimeout(() => setStatus(''), 2500);
  });
}

/**
 * Load tree from URL parameter
 */
function loadFromURL(tree, syncEngine) {
  const params = new URLSearchParams(window.location.search);
  const encoded = params.get('i') || params.get('tree');

  if (encoded) {
    try {
      const notation = decodeURIComponent(encoded);
      document.getElementById('bracket-input').value = notation;
      syncEngine.forceTextToCanvas();
    } catch (e) {
      console.error('Failed to load from URL:', e);
    }
  }
}

/**
 * Generate shareable URL
 */
function generateShareURL(tree) {
  const serializer = new BracketSerializer();
  const notation = serializer.serializeCompact(tree);
  const encoded = encodeURIComponent(notation);
  return `${window.location.origin}${window.location.pathname}?i=${encoded}`;
}

// Export for potential external use
window.generateShareURL = generateShareURL;
