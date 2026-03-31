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

  const tableGenerator = new TableGenerator();

  // Expose for testing and debugging
  window.canvasManager = canvasManager;
  window.tree = tree;
  window.syncEngine = syncEngine;
  window.tableGenerator = tableGenerator;

  // === Palette Drag & Drop ===
  setupPaletteDragDrop(canvasManager);

  // === Word Input Field ===
  setupWordInput(canvasManager);

  // === Sync Toggle ===
  setupSyncToggle(syncEngine);

  // === Zoom Controls ===
  setupZoomControls(canvasManager);

  // === Presentation Mode Toggle ===
  setupPresentationToggle(canvasManager);

  // === Table View Toggle ===
  setupTableToggle(tableGenerator, tree, canvasManager);

  // === Export Buttons ===
  setupExportButtons(canvasManager);
  setupTableExportButtons();

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

  // Canvas drop handling — use wrapper div so events survive zoom changes
  const canvasWrapper = document.getElementById('canvas-wrapper');
  const canvasElement = canvasManager.canvas.upperCanvasEl;

  // Helper to restore zoom state
  const restoreZoom = () => {
    if (canvasManager._preShiftZoom !== null) {
      canvasManager.canvas.setViewportTransform(canvasManager._preShiftVpt);
      canvasManager._preShiftZoom = null;
      canvasManager._preShiftVpt = null;
      canvasManager.canvas.requestRenderAll();
    }
  };

  canvasWrapper.addEventListener('dragover', function(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    canvasElement.classList.add('drag-over');

    // Show preview lines for potential connection at current drag position
    const pointer = canvasManager.canvas.getPointer(e);
    canvasManager.showDropPreview(pointer.x, pointer.y);

    // Shift-zoom during palette drag (keydown doesn't fire during HTML5 drag)
    const canvasRect = canvasElement.getBoundingClientRect();
    const offsetX = e.clientX - canvasRect.left;
    const offsetY = e.clientY - canvasRect.top;

    if (e.shiftKey && canvasManager._preShiftZoom === null) {
      canvasManager._lastPointer = { x: offsetX, y: offsetY };
      canvasManager._preShiftZoom = canvasManager.canvas.getZoom();
      canvasManager._preShiftVpt = canvasManager.canvas.viewportTransform.slice();
      const targetZoom = canvasManager._preShiftZoom * canvasManager.SHIFT_ZOOM_LEVEL;
      canvasManager.canvas.zoomToPoint({ x: offsetX, y: offsetY }, targetZoom);
      canvasManager.canvas.requestRenderAll();
    } else if (!e.shiftKey && canvasManager._preShiftZoom !== null) {
      restoreZoom();
    }
  });

  canvasWrapper.addEventListener('dragleave', function(e) {
    // Only trigger on leaving the wrapper, not internal child boundaries
    if (e.relatedTarget && this.contains(e.relatedTarget)) return;
    canvasElement.classList.remove('drag-over');
    canvasManager.hideDropPreview();
    restoreZoom();
  });

  canvasWrapper.addEventListener('drop', function(e) {
    e.preventDefault();
    canvasElement.classList.remove('drag-over');
    canvasManager.hideDropPreview();
    // Restore zoom before processing drop so coordinates are correct
    restoreZoom();

    const data = e.dataTransfer.getData('text/plain');
    if (!data) return;

    try {
      const dropData = JSON.parse(data);

      // Get pointer coordinates in canvas object space (accounts for zoom/pan)
      const pointer = canvasManager.canvas.getPointer(e);

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

  document.getElementById('zoom-fit').addEventListener('click', () => {
    canvasManager.fitToView(true);
  });

  document.getElementById('zoom-reset').addEventListener('click', () => {
    canvasManager.canvas.setZoom(1);
    canvasManager.canvas.setViewportTransform([1, 0, 0, 1, 0, 0]);
  });

}

/**
 * Setup presentation mode toggle
 */
function setupPresentationToggle(canvasManager) {
  const btn = document.getElementById('presentation-toggle');
  if (!btn) return;

  btn.addEventListener('click', () => {
    const isPresenting = canvasManager.togglePresentationMode();
    btn.textContent = isPresenting ? 'Edit' : 'Present';
    btn.style.background = isPresenting ? '#333' : 'white';
    btn.style.color = isPresenting ? 'white' : '#333';
  });
}

/**
 * Setup table view toggle
 */
function setupTableToggle(tableGenerator, tree, canvasManager) {
  const btn = document.getElementById('view-toggle');
  const canvasWrapper = document.getElementById('canvas-wrapper');
  const tableContainer = document.getElementById('table-container');
  const paletteBar = document.querySelector('.palette-bar');
  const roleBar = document.getElementById('role-bar');
  const copyTree = document.getElementById('copy-tree');
  const downloadTree = document.getElementById('download-tree');
  const copyTable = document.getElementById('copy-table');
  const downloadTable = document.getElementById('download-table');
  let isTableView = false;
  let refreshTimeout = null;

  function refreshTable() {
    if (isTableView) {
      // Save current role values before regenerating
      const savedRoles = {};
      const roleCells = tableContainer.querySelectorAll('td.role[contenteditable="true"]');
      for (const cell of roleCells) {
        const level = cell.getAttribute('data-level');
        const col = cell.getAttribute('data-col');
        if (cell.textContent.trim()) {
          if (!savedRoles[level]) savedRoles[level] = {};
          savedRoles[level][col] = cell.textContent.trim();
        }
      }

      tableContainer.innerHTML = tableGenerator.generate(tree);

      // Restore saved role values
      if (Object.keys(savedRoles).length > 0) {
        window.setRoles(savedRoles);
      }
    }
  }

  btn.addEventListener('click', () => {
    isTableView = !isTableView;

    if (isTableView) {
      canvasWrapper.style.display = 'none';
      tableContainer.style.display = 'block';
      paletteBar.style.display = 'none';
      roleBar.style.display = 'flex';
      btn.textContent = 'Tree View';
      btn.style.background = '#333';
      btn.style.color = 'white';
      // Swap export buttons: show table, hide tree
      copyTree.style.display = 'none';
      downloadTree.style.display = 'none';
      copyTable.style.display = 'inline-block';
      downloadTable.style.display = 'inline-block';
      refreshTable();
    } else {
      canvasWrapper.style.display = '';
      tableContainer.style.display = 'none';
      paletteBar.style.display = '';
      roleBar.style.display = 'none';
      btn.textContent = 'Table View';
      btn.style.background = '';
      btn.style.color = '';
      // Swap export buttons: show tree, hide table
      copyTree.style.display = 'inline-block';
      downloadTree.style.display = 'inline-block';
      copyTable.style.display = 'none';
      downloadTable.style.display = 'none';
      // Refresh canvas after re-showing
      setTimeout(() => canvasManager.canvas.requestRenderAll(), 50);
    }
  });

  // Regenerate table when tree changes (debounced)
  tree.addEventListener((event, data) => {
    if (isTableView) {
      clearTimeout(refreshTimeout);
      refreshTimeout = setTimeout(refreshTable, 150);
    }
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
      const dataURL = await canvasManager.exportPNG(4);
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
        const dataURL = await canvasManager.exportPNG(4);
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
      const dataURL = await canvasManager.exportPNG(4);

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

/**
 * Export table as PNG via html2canvas
 * @param {number} scale - Resolution multiplier (default 4)
 * @returns {Promise<string>} data URL
 */
async function exportTablePNG(scale = 4) {
  const tableContainer = document.getElementById('table-container');
  const table = tableContainer.querySelector('.labeling-table');
  if (!table) throw new Error('No table to export');

  const canvas = await html2canvas(table, {
    scale: scale,
    backgroundColor: '#ffffff',
    logging: false,
  });
  return canvas.toDataURL('image/png');
}

/**
 * Setup table export buttons (copy + download)
 */
function setupTableExportButtons() {
  const statusEl = document.getElementById('export-status');
  const setStatus = (msg) => { statusEl.textContent = msg || ''; };

  const flashSuccess = () => {
    const container = document.getElementById('table-container');
    container.style.transition = 'box-shadow 0.2s ease';
    container.style.boxShadow = '0 0 20px 5px rgba(0, 200, 100, 0.5)';
    setTimeout(() => { container.style.boxShadow = ''; }, 300);
  };

  // Copy table as PNG to clipboard
  document.getElementById('copy-table').addEventListener('click', async () => {
    try {
      setStatus('Copying table...');
      const dataURL = await exportTablePNG(4);
      const res = await fetch(dataURL);
      const blob = await res.blob();

      await navigator.clipboard.write([
        new ClipboardItem({ 'image/png': blob })
      ]);

      flashSuccess();
      setStatus('Table copied!');
    } catch (err) {
      console.error('Table copy failed:', err);
      try {
        const dataURL = await exportTablePNG(4);
        window.open(dataURL, '_blank');
        setStatus('Opened in new tab');
      } catch (e2) {
        setStatus('Copy failed');
      }
    }
    setTimeout(() => setStatus(''), 2500);
  });

  // Download table as PNG
  document.getElementById('download-table').addEventListener('click', async () => {
    try {
      setStatus('Preparing table...');
      const dataURL = await exportTablePNG(4);

      const a = document.createElement('a');
      a.href = dataURL;
      a.download = 'labeling-table.png';
      document.body.appendChild(a);
      a.click();
      a.remove();

      flashSuccess();
      setStatus('Table downloaded!');
    } catch (err) {
      console.error('Table download failed:', err);
      setStatus('Download failed');
    }
    setTimeout(() => setStatus(''), 2500);
  });
}

/**
 * Set role labels programmatically.
 * Called by Playwright or other automation to fill in role cells.
 * @param {Object} roles - { "1": { "0": "Subject", "1": "Predicate" }, "2": { "1": "Direct Object" } }
 *   Keys are level numbers (strings), values are objects mapping column index (string) to role label.
 */
window.setRoles = function(roles) {
  const cells = document.querySelectorAll('#table-container td.role[contenteditable="true"]');
  for (const cell of cells) {
    const level = cell.getAttribute('data-level');
    const col = cell.getAttribute('data-col');
    if (roles[level] && roles[level][col]) {
      cell.textContent = roles[level][col];
    }
  }
};

// Expose table export for Playwright
window.exportTablePNG = exportTablePNG;
