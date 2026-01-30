/**
 * Canvas Manager - Handles Fabric.js canvas rendering and interactions
 * Visual representation of the syntax tree
 */

class CanvasManager {
  constructor(canvasId, tree) {
    this.canvas = new fabric.Canvas(canvasId);
    this.tree = tree;

    // Tile dimensions
    this.TILE_WIDTH = 85;
    this.TILE_HEIGHT = 40;
    this.TERMINAL_WIDTH = 85;
    this.TERMINAL_HEIGHT = 34;

    // Layout settings
    this.UNIT_WIDTH = 145;      // Horizontal spacing for larger tiles
    this.LEVEL_HEIGHT = 105;    // Vertical spacing for larger tiles
    this.TOP_MARGIN = 40;       // Top margin
    this.ANIMATION_DURATION = 150;

    // Auto-connection settings
    this.CONNECTION_THRESHOLD = 360; // pixels - max distance to auto-connect
    this.DISCONNECT_THRESHOLD = 540; // pixels - distance to auto-disconnect (larger for hysteresis)
    this.MIN_VERTICAL_GAP = 25; // parent must be at least this many pixels above child
    this.HORIZONTAL_WEIGHT = 1.5; // penalize horizontal distance more than vertical

    // Preview line for potential connection
    this.potentialConnectionLine = null;
    this.potentialParent = null;

    // Preview for insertion between nodes
    this.potentialInsertion = null; // { parent, child } when inserting between
    this.insertionPreviewLines = []; // Two preview lines for insertion

    // State
    this.selectedTile = null;
    this.connectionPreviewLine = null;
    this.hoveredTile = null;
    this.isDraggingCanvas = false;

    // Map of node ID to canvas object
    this.nodeToCanvas = new Map();

    // Event callbacks
    this.onTreeChanged = null;

    this.setupCanvas();
    this.setupEventHandlers();
  }

  setupCanvas() {
    this.resizeCanvas();
    window.addEventListener('resize', () => this.resizeCanvas());
  }

  resizeCanvas() {
    const wrapper = document.getElementById('canvas-wrapper');
    if (!wrapper) return;

    const rect = wrapper.getBoundingClientRect();
    const newWidth = Math.max(400, Math.floor(rect.width));
    const newHeight = Math.max(200, Math.floor(rect.height));

    this.canvas.setWidth(newWidth);
    this.canvas.setHeight(newHeight);
    this.canvas.calcOffset();
    this.canvas.requestRenderAll();
  }

  setupEventHandlers() {
    // Zoom with mouse wheel
    this.canvas.on('mouse:wheel', (opt) => {
      const delta = opt.e.deltaY;
      let zoom = this.canvas.getZoom();
      zoom *= 0.999 ** delta;
      zoom = Math.max(0.1, Math.min(10, zoom));
      this.canvas.zoomToPoint({ x: opt.e.offsetX, y: opt.e.offsetY }, zoom);
      opt.e.preventDefault();
      opt.e.stopPropagation();
    });

    // Pan and click handling
    this.canvas.on('mouse:down', (opt) => {
      const evt = opt.e;

      // Ctrl+click to edit
      if ((evt.ctrlKey || evt.metaKey) && opt.target && opt.target.treeNodeId) {
        evt.preventDefault();
        evt.stopPropagation();
        this.editTile(opt.target);
        return;
      }

      // Click on empty space
      if (!opt.target) {
        if (this.selectedTile) {
          this.setTileSelected(this.selectedTile, false);
          this.selectedTile = null;
          this.removeConnectionPreview();
          this.clearHoveredTile();
        }
        this.isDraggingCanvas = true;
        this.canvas.selection = false;
        this.lastPosX = evt.clientX;
        this.lastPosY = evt.clientY;
      }
    });

    this.canvas.on('mouse:move', (opt) => {
      if (this.isDraggingCanvas) {
        const e = opt.e;
        const vpt = this.canvas.viewportTransform;
        vpt[4] += e.clientX - this.lastPosX;
        vpt[5] += e.clientY - this.lastPosY;
        this.canvas.requestRenderAll();
        this.lastPosX = e.clientX;
        this.lastPosY = e.clientY;
      }

      // Update connection preview
      if (this.selectedTile && !this.isDraggingCanvas) {
        const pointer = this.canvas.getPointer(opt.e);
        this.updateConnectionPreview(pointer.x, pointer.y);

        // Highlight potential target
        const target = opt.target;
        if (target && target.treeNodeId && target !== this.selectedTile) {
          if (this.hoveredTile && this.hoveredTile !== target) {
            this.highlightConnectionTarget(this.hoveredTile, false);
          }
          this.hoveredTile = target;
          this.highlightConnectionTarget(this.hoveredTile, true);
        } else {
          this.clearHoveredTile();
        }
      }
    });

    this.canvas.on('mouse:up', () => {
      this.canvas.setViewportTransform(this.canvas.viewportTransform);
      this.isDraggingCanvas = false;
      this.canvas.selection = true;
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (this.selectedTile && !this.isEditingText()) {
          const node = this.tree.findById(this.selectedTile.treeNodeId);
          if (node) {
            this.tree.deleteNode(node);
            this.selectedTile = null;
          }
        }
      }
      if (e.key === 'Escape') {
        if (this.selectedTile) {
          this.setTileSelected(this.selectedTile, false);
          this.selectedTile = null;
          this.removeConnectionPreview();
          this.clearHoveredTile();
        }
      }
    });
  }

  isEditingText() {
    return document.activeElement &&
           (document.activeElement.tagName === 'INPUT' ||
            document.activeElement.tagName === 'TEXTAREA');
  }

  // === Tile Creation ===

  createTileForNode(node) {
    const colors = getNodeColors(node.label, node.nodeType);
    let tile;

    if (node.isTerminal()) {
      tile = this.createTerminalTile(node.label, colors);
    } else {
      tile = this.createStandardTile(node.label, colors);
    }

    tile.treeNodeId = node.id;
    node.canvasObject = tile;
    this.nodeToCanvas.set(node.id, tile);

    this.setupTileEvents(tile, node);
    this.canvas.add(tile);

    return tile;
  }

  createStandardTile(label, colors) {
    const rect = new fabric.Rect({
      width: this.TILE_WIDTH,
      height: this.TILE_HEIGHT,
      fill: colors.bg,
      rx: 6,
      ry: 6,
      stroke: colors.border,
      strokeWidth: 1.5,
      originX: 'center',
      originY: 'center'
    });

    const text = new fabric.Text(label, {
      fontSize: 14,
      fontWeight: 'bold',
      fill: colors.text,
      textAlign: 'center',
      originX: 'center',
      originY: 'center',
      fontFamily: 'system-ui, sans-serif'
    });

    const group = new fabric.Group([rect, text], {
      hasControls: false,
      lockScalingX: true,
      lockScalingY: true
    });

    return group;
  }

  createTerminalTile(text, colors) {
    const isEmpty = !text || text === '...';

    const rect = new fabric.Rect({
      width: this.TERMINAL_WIDTH,
      height: this.TERMINAL_HEIGHT,
      fill: colors.bg,
      rx: 5,
      ry: 5,
      stroke: colors.border,
      strokeWidth: 1,
      originX: 'center',
      originY: 'center'
    });

    const label = new fabric.Text(text || '...', {
      fontSize: 16,
      fill: colors.text,
      textAlign: 'center',
      originX: 'center',
      originY: 'center',
      top: isEmpty ? -8 : 0,
      fontFamily: 'system-ui, sans-serif'
    });

    const hint = new fabric.Text('Ctrl+click to type', {
      fontSize: 10,
      fill: '#999',
      textAlign: 'center',
      originX: 'center',
      originY: 'center',
      top: 5,
      fontFamily: 'system-ui, sans-serif',
      visible: isEmpty
    });

    const group = new fabric.Group([rect, label, hint], {
      hasControls: false,
      lockScalingX: true,
      lockScalingY: true
    });

    group.isTerminalTile = true;

    return group;
  }

  setupTileEvents(tile, node) {
    let lastPosition = { x: 0, y: 0 };
    let isDragging = false;

    tile.on('moving', () => {
      isDragging = true;
      const currentPos = { x: tile.left, y: tile.top };
      const deltaX = currentPos.x - lastPosition.x;
      const deltaY = currentPos.y - lastPosition.y;

      // Move subtree (children follow parent)
      this.moveSubtree(node, deltaX, deltaY);
      lastPosition = currentPos;

      // Show preview of potential parent connection
      this.handleAutoConnectionPreview(node, tile);

      this.updateConnectionLines();
    });

    tile.on('mousedown', (e) => {
      lastPosition = { x: tile.left, y: tile.top };
      isDragging = false;
      e.e.stopPropagation();

      // Add lift effect
      tile.set({
        shadow: new fabric.Shadow({
          color: 'rgba(0,0,0,0.3)',
          blur: 12,
          offsetX: 4,
          offsetY: 4
        })
      });

      // Show preview immediately on mousedown
      this.handleAutoConnectionPreview(node, tile);

      this.canvas.requestRenderAll();
    });

    tile.on('mouseup', () => {
      // Remove lift effect
      if (this.selectedTile !== tile) {
        tile.set({ shadow: null });
        tile.item(0).set({ shadow: null });
      }

      if (isDragging) {
        // Capture drop position BEFORE finalizeAutoConnection (which may trigger relayout)
        const dropX = tile.left + this.TILE_WIDTH / 2;
        const dropY = tile.top + this.TILE_HEIGHT / 2;

        // Update node position first so reordering uses correct x coordinate
        node.x = dropX;
        node.y = dropY;

        // Finalize auto-connection based on final position
        this.finalizeAutoConnection(node, tile);

        // Reorder siblings based on horizontal position
        node.reorderByPosition();

        // Trigger relayout to apply proper spacing with new sibling order
        this.relayout(true);

        if (this.onTreeChanged) {
          this.onTreeChanged();
        }
      } else {
        // Clean up preview even if not dragging (e.g., click without drag)
        this.hidePotentialConnection();
        this.hideInsertionPreview();
        if (this._lastHighlightedTile) {
          this.highlightConnectionTarget(this._lastHighlightedTile, false);
          this._lastHighlightedTile = null;
        }
        if (this._lastHighlightedTile2) {
          this.highlightConnectionTarget(this._lastHighlightedTile2, false);
          this._lastHighlightedTile2 = null;
        }
      }

      isDragging = false;
      this.canvas.requestRenderAll();
    });

    tile.on('mousedblclick', (e) => {
      e.e.stopPropagation();
      this.handleTileDoubleClick(tile, node);
    });

    // Hover effects
    tile.on('mouseover', () => {
      if (this.selectedTile !== tile && !isDragging) {
        tile.set({
          scaleX: 1.03,
          scaleY: 1.03,
          shadow: new fabric.Shadow({
            color: 'rgba(0,0,0,0.15)',
            blur: 8,
            offsetX: 2,
            offsetY: 2
          })
        });
        this.canvas.requestRenderAll();
      }
    });

    tile.on('mouseout', () => {
      if (this.selectedTile !== tile && !isDragging) {
        tile.set({
          scaleX: 1,
          scaleY: 1,
          shadow: null
        });
        this.canvas.requestRenderAll();
      }
    });
  }

  handleTileDoubleClick(tile, node) {
    if (!this.selectedTile) {
      // First selection
      this.selectedTile = tile;
      this.setTileSelected(tile, true);
    } else if (this.selectedTile === tile) {
      // Deselect
      this.setTileSelected(tile, false);
      this.selectedTile = null;
      this.removeConnectionPreview();
      this.clearHoveredTile();
    } else {
      // Connect two tiles
      const selectedNode = this.tree.findById(this.selectedTile.treeNodeId);
      const targetNode = this.tree.findById(tile.treeNodeId);

      if (selectedNode && targetNode) {
        // Higher tile (smaller y) becomes parent
        const parent = (this.selectedTile.top < tile.top) ? selectedNode : targetNode;
        const child = (parent === selectedNode) ? targetNode : selectedNode;

        // Don't allow connecting a node to its own descendant
        if (!child.isAncestorOf(parent)) {
          this.tree.connect(parent, child);
        }
      }

      // Clean up
      this.removeConnectionPreview();
      this.clearHoveredTile();
      this.setTileSelected(this.selectedTile, false);
      this.selectedTile = null;
    }
  }

  setTileSelected(tile, isSelected) {
    const rect = tile.item(0);
    if (isSelected) {
      rect.set({
        stroke: '#0066ff',
        strokeWidth: 4,
        shadow: new fabric.Shadow({
          color: '#0066ff',
          blur: 10,
          offsetX: 0,
          offsetY: 0
        })
      });
    } else {
      const node = this.tree.findById(tile.treeNodeId);
      const colors = node ? getNodeColors(node.label, node.nodeType) : { border: '#333' };
      rect.set({
        stroke: colors.border,
        strokeWidth: node && node.isTerminal() ? 1.5 : 2,
        shadow: null
      });
    }
    this.canvas.requestRenderAll();
  }

  // === Connection Preview ===

  updateConnectionPreview(mouseX, mouseY) {
    if (!this.selectedTile) {
      this.removeConnectionPreview();
      return;
    }

    const center = this.selectedTile.getCenterPoint();

    if (!this.connectionPreviewLine) {
      this.connectionPreviewLine = new fabric.Line(
        [center.x, center.y, mouseX, mouseY],
        {
          stroke: '#0066ff',
          strokeWidth: 2,
          strokeDashArray: [8, 4],
          selectable: false,
          evented: false,
          opacity: 0.7
        }
      );
      this.canvas.add(this.connectionPreviewLine);
      this.canvas.sendToBack(this.connectionPreviewLine);
    } else {
      this.connectionPreviewLine.set({
        x1: center.x,
        y1: center.y,
        x2: mouseX,
        y2: mouseY
      });
    }

    this.canvas.requestRenderAll();
  }

  removeConnectionPreview() {
    if (this.connectionPreviewLine) {
      this.canvas.remove(this.connectionPreviewLine);
      this.connectionPreviewLine = null;
      this.canvas.requestRenderAll();
    }
  }

  highlightConnectionTarget(tile, highlight) {
    if (!tile || tile === this.selectedTile) return;

    const rect = tile.item(0);
    if (highlight) {
      rect.set({
        stroke: '#00cc44',
        strokeWidth: 3,
        shadow: new fabric.Shadow({
          color: '#00cc44',
          blur: 8,
          offsetX: 0,
          offsetY: 0
        })
      });
    } else {
      const node = this.tree.findById(tile.treeNodeId);
      const colors = node ? getNodeColors(node.label, node.nodeType) : { border: '#333' };
      rect.set({
        stroke: colors.border,
        strokeWidth: node && node.isTerminal() ? 1.5 : 2,
        shadow: null
      });
    }
    this.canvas.requestRenderAll();
  }

  clearHoveredTile() {
    if (this.hoveredTile) {
      this.highlightConnectionTarget(this.hoveredTile, false);
      this.hoveredTile = null;
    }
  }

  // === Editing ===

  editTile(tile) {
    const node = this.tree.findById(tile.treeNodeId);
    if (!node) return;

    const textObj = tile.item(1);
    const currentText = textObj.text;
    const inputText = currentText === '...' ? '' : currentText;

    // Create modal dialog
    const overlay = document.createElement('div');
    overlay.style.cssText = `
      position: fixed; inset: 0; background: rgba(0,0,0,0.5);
      display: flex; align-items: center; justify-content: center; z-index: 10000;
    `;

    const dialog = document.createElement('div');
    dialog.style.cssText = `
      background: white; padding: 20px; border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `;

    const label = document.createElement('div');
    label.textContent = node.isTerminal() ? 'Edit word:' : 'Edit label:';
    label.style.marginBottom = '10px';

    const input = document.createElement('input');
    input.type = 'text';
    input.value = inputText;
    input.style.cssText = `
      width: 240px; padding: 8px; border: 1px solid #ccc;
      border-radius: 4px; font-size: 14px;
    `;

    const buttonContainer = document.createElement('div');
    buttonContainer.style.cssText = 'margin-top: 10px; text-align: right;';

    const cancelBtn = document.createElement('button');
    cancelBtn.textContent = 'Cancel';
    cancelBtn.style.cssText = `
      margin-right: 10px; padding: 6px 12px; border: 1px solid #ccc;
      background: white; border-radius: 4px; cursor: pointer;
    `;

    const okBtn = document.createElement('button');
    okBtn.textContent = 'OK';
    okBtn.style.cssText = `
      padding: 6px 12px; border: 1px solid #007bff;
      background: #007bff; color: white; border-radius: 4px; cursor: pointer;
    `;

    buttonContainer.appendChild(cancelBtn);
    buttonContainer.appendChild(okBtn);
    dialog.appendChild(label);
    dialog.appendChild(input);
    dialog.appendChild(buttonContainer);
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    input.focus();
    input.select();

    const closeDialog = (save) => {
      document.body.removeChild(overlay);
      if (save) {
        const finalText = input.value.trim() || (node.isTerminal() ? '...' : node.label);
        this.tree.updateLabel(node, finalText);
      }
    };

    okBtn.addEventListener('click', () => closeDialog(true));
    cancelBtn.addEventListener('click', () => closeDialog(false));
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') closeDialog(true);
      else if (e.key === 'Escape') closeDialog(false);
    });
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeDialog(false);
    });
  }

  // === Tree Operations ===

  moveSubtree(node, deltaX, deltaY) {
    for (const child of node.children) {
      const childTile = this.nodeToCanvas.get(child.id);
      if (childTile) {
        childTile.set({
          left: childTile.left + deltaX,
          top: childTile.top + deltaY
        });
        childTile.setCoords();
        this.moveSubtree(child, deltaX, deltaY);
      }
    }
  }

  // === Auto-Connection Logic ===

  /**
   * Line insertion threshold - distance to a connection line to trigger insertion mode.
   */
  LINE_INSERTION_THRESHOLD = 40; // pixels

  /**
   * Find if a node is close to an existing connection line (for insertion between nodes).
   * Returns { parent, child, distance } or null if not near any line.
   */
  findNearestConnectionLine(node, tile) {
    const nodeCenter = tile.getCenterPoint();
    let bestMatch = null;
    let bestDistance = Infinity;

    for (const parentNode of this.tree.getAllNodes()) {
      // Skip if this is the node we're dragging
      if (parentNode === node) continue;

      for (const childNode of parentNode.children) {
        // Skip if this is the node we're dragging
        if (childNode === node) continue;

        // Skip if the dragged node is an ancestor of the parent (would create cycle)
        if (node.isAncestorOf(parentNode)) continue;

        // Skip if parent is a terminal (can't have children)
        if (parentNode.isTerminal()) continue;

        const parentTile = this.nodeToCanvas.get(parentNode.id);
        const childTile = this.nodeToCanvas.get(childNode.id);

        if (!parentTile || !childTile) continue;

        const parentCenter = parentTile.getCenterPoint();
        const childCenter = childTile.getCenterPoint();

        // Calculate distance from point to line segment
        const distance = this.pointToLineDistance(
          nodeCenter.x, nodeCenter.y,
          parentCenter.x, parentCenter.y,
          childCenter.x, childCenter.y
        );

        // Check if the dragged node's y position is between parent and child
        const minY = Math.min(parentCenter.y, childCenter.y);
        const maxY = Math.max(parentCenter.y, childCenter.y);
        const isVerticallyBetween = nodeCenter.y > minY + this.MIN_VERTICAL_GAP &&
                                    nodeCenter.y < maxY - this.MIN_VERTICAL_GAP;

        if (distance !== null && distance < this.LINE_INSERTION_THRESHOLD &&
            distance < bestDistance && isVerticallyBetween) {
          bestDistance = distance;
          bestMatch = { parent: parentNode, child: childNode, distance };
        }
      }
    }

    return bestMatch;
  }

  /**
   * Calculate the perpendicular distance from a point to a line segment.
   * Returns null if the perpendicular projection falls outside the segment.
   */
  pointToLineDistance(px, py, x1, y1, x2, y2) {
    const dx = x2 - x1;
    const dy = y2 - y1;
    const lengthSquared = dx * dx + dy * dy;

    if (lengthSquared === 0) {
      // Line segment is a point
      return Math.sqrt((px - x1) ** 2 + (py - y1) ** 2);
    }

    // Calculate projection parameter t
    let t = ((px - x1) * dx + (py - y1) * dy) / lengthSquared;

    // Clamp t to [0, 1] but allow small margin for near-endpoint cases
    if (t < 0.1 || t > 0.9) {
      // Too close to endpoints - prefer direct parent connection instead
      return null;
    }

    // Find closest point on line segment
    const closestX = x1 + t * dx;
    const closestY = y1 + t * dy;

    // Return distance to closest point
    return Math.sqrt((px - closestX) ** 2 + (py - closestY) ** 2);
  }

  /**
   * Find the best parent candidate for a node based on proximity.
   * Parent must be above the child (smaller y value).
   * Uses weighted distance that penalizes horizontal offset more.
   * Returns { node, distance, tile } or null if no suitable parent found.
   */
  findBestParentCandidate(childNode, childTile) {
    const childCenter = childTile.getCenterPoint();
    let bestCandidate = null;
    let bestScore = Infinity;
    let bestTile = null;

    for (const [nodeId, tile] of this.nodeToCanvas) {
      const node = this.tree.findById(nodeId);
      if (!node || node === childNode) continue;

      // Skip if this node is a descendant of the child (would create cycle)
      if (childNode.isAncestorOf(node)) continue;

      // Skip terminal nodes - they can't be parents
      if (node.isTerminal()) continue;

      const tileCenter = tile.getCenterPoint();

      // Parent must be above child (smaller y = higher on screen)
      if (tileCenter.y >= childCenter.y - this.MIN_VERTICAL_GAP) continue;

      // Calculate weighted distance (penalize horizontal more)
      const dx = Math.abs(tileCenter.x - childCenter.x);
      const dy = Math.abs(tileCenter.y - childCenter.y);

      // Score: horizontal distance weighted more heavily + vertical distance
      // This prefers parents that are more directly above
      const score = (dx * this.HORIZONTAL_WEIGHT) + dy;

      // Raw distance for threshold check
      const distance = Math.sqrt(dx * dx + dy * dy);

      // Check if within threshold and better score than current best
      if (distance < this.CONNECTION_THRESHOLD && score < bestScore) {
        bestCandidate = node;
        bestScore = score;
        bestTile = tile;
      }
    }

    return bestCandidate ? { node: bestCandidate, score: bestScore, tile: bestTile } : null;
  }

  /**
   * Show a preview line to potential parent during drag.
   */
  showPotentialConnection(childTile, parentTile) {
    const childCenter = childTile.getCenterPoint();
    const parentCenter = parentTile.getCenterPoint();

    if (!this.potentialConnectionLine) {
      this.potentialConnectionLine = new fabric.Line(
        [parentCenter.x, parentCenter.y, childCenter.x, childCenter.y],
        {
          stroke: '#00aa44',
          strokeWidth: 3,
          strokeDashArray: [8, 4],
          selectable: false,
          evented: false,
          opacity: 0.8
        }
      );
      this.canvas.add(this.potentialConnectionLine);
      this.canvas.sendToBack(this.potentialConnectionLine);
    } else {
      this.potentialConnectionLine.set({
        x1: parentCenter.x,
        y1: parentCenter.y,
        x2: childCenter.x,
        y2: childCenter.y
      });
    }
    this.canvas.requestRenderAll();
  }

  /**
   * Remove the potential connection preview line.
   */
  hidePotentialConnection() {
    if (this.potentialConnectionLine) {
      this.canvas.remove(this.potentialConnectionLine);
      this.potentialConnectionLine = null;
    }
    this.potentialParent = null;
  }

  /**
   * Show preview lines during drag-over from palette (before drop).
   * Creates a preview of where connections would be made if dropped at (x, y).
   */
  showDropPreview(x, y) {
    // First check for insertion between existing nodes
    const insertion = this.findNearestConnectionLineAtPoint(x, y);

    if (insertion) {
      // We're near a connection line - show insertion preview
      this.hidePotentialConnection();

      const parentTile = this.nodeToCanvas.get(insertion.parent.id);
      const childTile = this.nodeToCanvas.get(insertion.child.id);

      if (parentTile && childTile) {
        this.showInsertionPreviewAtPoint(x, y, parentTile, childTile);

        // Highlight both parent and child tiles in orange
        if (this._dropHighlightedTile && this._dropHighlightedTile !== parentTile) {
          this.highlightConnectionTarget(this._dropHighlightedTile, false);
        }
        if (this._dropHighlightedTile2 && this._dropHighlightedTile2 !== childTile) {
          this.highlightConnectionTarget(this._dropHighlightedTile2, false);
        }
        this.highlightInsertionTarget(parentTile, true);
        this.highlightInsertionTarget(childTile, true);
        this._dropHighlightedTile = parentTile;
        this._dropHighlightedTile2 = childTile;
      }
      return;
    }

    // Clear insertion preview if not in insertion mode
    this.hideInsertionPreview();
    if (this._dropHighlightedTile2) {
      this.highlightConnectionTarget(this._dropHighlightedTile2, false);
      this._dropHighlightedTile2 = null;
    }

    // Fall back to regular parent candidate logic
    const candidate = this.findBestParentCandidateAtPoint(x, y);

    if (candidate) {
      // Show preview line to potential parent
      this.showPotentialConnectionAtPoint(x, y, candidate.tile);

      // Highlight the potential parent tile
      if (this._dropHighlightedTile && this._dropHighlightedTile !== candidate.tile) {
        this.highlightConnectionTarget(this._dropHighlightedTile, false);
      }
      this.highlightConnectionTarget(candidate.tile, true);
      this._dropHighlightedTile = candidate.tile;
    } else {
      // No suitable parent found
      this.hidePotentialConnection();

      // Remove highlight from previous tile
      if (this._dropHighlightedTile) {
        this.highlightConnectionTarget(this._dropHighlightedTile, false);
        this._dropHighlightedTile = null;
      }
    }
  }

  /**
   * Hide preview lines shown during drag-over.
   */
  hideDropPreview() {
    this.hidePotentialConnection();
    this.hideInsertionPreview();

    if (this._dropHighlightedTile) {
      this.highlightConnectionTarget(this._dropHighlightedTile, false);
      this._dropHighlightedTile = null;
    }
    if (this._dropHighlightedTile2) {
      this.highlightConnectionTarget(this._dropHighlightedTile2, false);
      this._dropHighlightedTile2 = null;
    }
    this.canvas.requestRenderAll();
  }

  /**
   * Find the best parent candidate for a point (used during drag-over).
   */
  findBestParentCandidateAtPoint(x, y) {
    let bestCandidate = null;
    let bestScore = Infinity;
    let bestTile = null;

    for (const [nodeId, tile] of this.nodeToCanvas) {
      const node = this.tree.findById(nodeId);
      if (!node) continue;

      // Skip terminal nodes - they can't be parents
      if (node.isTerminal()) continue;

      const tileCenter = tile.getCenterPoint();

      // Parent must be above drop point (smaller y = higher on screen)
      if (tileCenter.y >= y - this.MIN_VERTICAL_GAP) continue;

      // Calculate weighted distance (penalize horizontal more)
      const dx = Math.abs(tileCenter.x - x);
      const dy = Math.abs(tileCenter.y - y);

      const score = (dx * this.HORIZONTAL_WEIGHT) + dy;
      const distance = Math.sqrt(dx * dx + dy * dy);

      if (distance < this.CONNECTION_THRESHOLD && score < bestScore) {
        bestCandidate = node;
        bestScore = score;
        bestTile = tile;
      }
    }

    return bestCandidate ? { node: bestCandidate, score: bestScore, tile: bestTile } : null;
  }

  /**
   * Find if a point is close to an existing connection line (for insertion).
   */
  findNearestConnectionLineAtPoint(x, y) {
    let bestMatch = null;
    let bestDistance = Infinity;

    for (const parentNode of this.tree.getAllNodes()) {
      for (const childNode of parentNode.children) {
        // Skip if parent is a terminal (can't have children)
        if (parentNode.isTerminal()) continue;

        const parentTile = this.nodeToCanvas.get(parentNode.id);
        const childTile = this.nodeToCanvas.get(childNode.id);

        if (!parentTile || !childTile) continue;

        const parentCenter = parentTile.getCenterPoint();
        const childCenter = childTile.getCenterPoint();

        const distance = this.pointToLineDistance(
          x, y,
          parentCenter.x, parentCenter.y,
          childCenter.x, childCenter.y
        );

        // Check if the point's y position is between parent and child
        const minY = Math.min(parentCenter.y, childCenter.y);
        const maxY = Math.max(parentCenter.y, childCenter.y);
        const isVerticallyBetween = y > minY + this.MIN_VERTICAL_GAP &&
                                    y < maxY - this.MIN_VERTICAL_GAP;

        if (distance !== null && distance < this.LINE_INSERTION_THRESHOLD &&
            distance < bestDistance && isVerticallyBetween) {
          bestDistance = distance;
          bestMatch = { parent: parentNode, child: childNode, distance };
        }
      }
    }

    return bestMatch;
  }

  /**
   * Show a preview line from a point to a potential parent tile.
   */
  showPotentialConnectionAtPoint(x, y, parentTile) {
    const parentCenter = parentTile.getCenterPoint();

    if (!this.potentialConnectionLine) {
      this.potentialConnectionLine = new fabric.Line(
        [parentCenter.x, parentCenter.y, x, y],
        {
          stroke: '#00aa44',
          strokeWidth: 3,
          strokeDashArray: [8, 4],
          selectable: false,
          evented: false,
          opacity: 0.8
        }
      );
      this.canvas.add(this.potentialConnectionLine);
      this.canvas.sendToBack(this.potentialConnectionLine);
    } else {
      this.potentialConnectionLine.set({
        x1: parentCenter.x,
        y1: parentCenter.y,
        x2: x,
        y2: y
      });
    }
    this.canvas.requestRenderAll();
  }

  /**
   * Show insertion preview lines at a point (during drag-over).
   */
  showInsertionPreviewAtPoint(x, y, parentTile, childTile) {
    const parentCenter = parentTile.getCenterPoint();
    const childCenter = childTile.getCenterPoint();

    // Clear existing preview lines
    this.hideInsertionPreview();

    // Line from parent to drop point
    const lineToParent = new fabric.Line(
      [parentCenter.x, parentCenter.y, x, y],
      {
        stroke: '#ff9900',
        strokeWidth: 3,
        strokeDashArray: [8, 4],
        selectable: false,
        evented: false,
        opacity: 0.9
      }
    );

    // Line from drop point to child
    const lineToChild = new fabric.Line(
      [x, y, childCenter.x, childCenter.y],
      {
        stroke: '#ff9900',
        strokeWidth: 3,
        strokeDashArray: [8, 4],
        selectable: false,
        evented: false,
        opacity: 0.9
      }
    );

    this.insertionPreviewLines = [lineToParent, lineToChild];
    this.canvas.add(lineToParent, lineToChild);
    this.canvas.sendToBack(lineToParent);
    this.canvas.sendToBack(lineToChild);
    this.canvas.requestRenderAll();
  }

  /**
   * Show preview lines for insertion between two nodes.
   * Shows two dashed lines: parent→newNode and newNode→child
   */
  showInsertionPreview(tile, parentTile, childTile) {
    const nodeCenter = tile.getCenterPoint();
    const parentCenter = parentTile.getCenterPoint();
    const childCenter = childTile.getCenterPoint();

    // Clear existing preview lines
    this.hideInsertionPreview();

    // Line from parent to new node (orange/yellow to indicate insertion)
    const lineToParent = new fabric.Line(
      [parentCenter.x, parentCenter.y, nodeCenter.x, nodeCenter.y],
      {
        stroke: '#ff9900',
        strokeWidth: 3,
        strokeDashArray: [8, 4],
        selectable: false,
        evented: false,
        opacity: 0.9
      }
    );

    // Line from new node to child
    const lineToChild = new fabric.Line(
      [nodeCenter.x, nodeCenter.y, childCenter.x, childCenter.y],
      {
        stroke: '#ff9900',
        strokeWidth: 3,
        strokeDashArray: [8, 4],
        selectable: false,
        evented: false,
        opacity: 0.9
      }
    );

    this.insertionPreviewLines = [lineToParent, lineToChild];
    this.canvas.add(lineToParent, lineToChild);
    this.canvas.sendToBack(lineToParent);
    this.canvas.sendToBack(lineToChild);
    this.canvas.requestRenderAll();
  }

  /**
   * Remove the insertion preview lines.
   */
  hideInsertionPreview() {
    for (const line of this.insertionPreviewLines) {
      this.canvas.remove(line);
    }
    this.insertionPreviewLines = [];
    this.potentialInsertion = null;
  }

  /**
   * Handle auto-connection preview during drag.
   * Checks for insertion between nodes first, then falls back to parent connection.
   * Only shows preview - actual connection happens on mouseup.
   */
  handleAutoConnectionPreview(node, tile) {
    // First, check if we're near a connection line (insertion mode)
    const insertion = this.findNearestConnectionLine(node, tile);

    if (insertion) {
      // We're near a connection line - show insertion preview
      this.potentialInsertion = insertion;
      this.potentialParent = null;

      // Hide regular connection preview
      this.hidePotentialConnection();

      const parentTile = this.nodeToCanvas.get(insertion.parent.id);
      const childTile = this.nodeToCanvas.get(insertion.child.id);

      if (parentTile && childTile) {
        this.showInsertionPreview(tile, parentTile, childTile);

        // Highlight both parent and child tiles in orange
        if (this._lastHighlightedTile) {
          this.highlightConnectionTarget(this._lastHighlightedTile, false);
        }
        if (this._lastHighlightedTile2) {
          this.highlightConnectionTarget(this._lastHighlightedTile2, false);
        }
        this.highlightInsertionTarget(parentTile, true);
        this.highlightInsertionTarget(childTile, true);
        this._lastHighlightedTile = parentTile;
        this._lastHighlightedTile2 = childTile;
      }
      return;
    }

    // Clear insertion preview if we're not in insertion mode
    this.hideInsertionPreview();
    if (this._lastHighlightedTile2) {
      this.highlightConnectionTarget(this._lastHighlightedTile2, false);
      this._lastHighlightedTile2 = null;
    }

    // Fall back to regular parent candidate logic
    const candidate = this.findBestParentCandidate(node, tile);

    if (candidate) {
      // Show preview line to potential parent
      this.showPotentialConnection(tile, candidate.tile);
      this.potentialParent = candidate.node;

      // Highlight the potential parent tile
      if (this._lastHighlightedTile && this._lastHighlightedTile !== candidate.tile) {
        this.highlightConnectionTarget(this._lastHighlightedTile, false);
      }
      this.highlightConnectionTarget(candidate.tile, true);
      this._lastHighlightedTile = candidate.tile;
    } else {
      // No suitable parent found
      this.hidePotentialConnection();

      // Remove highlight from previous tile
      if (this._lastHighlightedTile) {
        this.highlightConnectionTarget(this._lastHighlightedTile, false);
        this._lastHighlightedTile = null;
      }
    }
  }

  /**
   * Highlight a tile for insertion mode (orange).
   */
  highlightInsertionTarget(tile, highlight) {
    if (!tile) return;

    const rect = tile.item(0);
    if (highlight) {
      rect.set({
        stroke: '#ff9900',
        strokeWidth: 3,
        shadow: new fabric.Shadow({
          color: '#ff9900',
          blur: 8,
          offsetX: 0,
          offsetY: 0
        })
      });
    } else {
      const node = this.tree.findById(tile.treeNodeId);
      const colors = node ? getNodeColors(node.label, node.nodeType) : { border: '#333' };
      rect.set({
        stroke: colors.border,
        strokeWidth: node && node.isTerminal() ? 1.5 : 2,
        shadow: null
      });
    }
    this.canvas.requestRenderAll();
  }

  /**
   * Finalize auto-connection on mouseup.
   * Handles insertion between nodes, regular parent connection, or disconnection.
   */
  finalizeAutoConnection(node, tile) {
    // Clean up all previews
    this.hidePotentialConnection();
    this.hideInsertionPreview();
    if (this._lastHighlightedTile) {
      this.highlightConnectionTarget(this._lastHighlightedTile, false);
      this._lastHighlightedTile = null;
    }
    if (this._lastHighlightedTile2) {
      this.highlightConnectionTarget(this._lastHighlightedTile2, false);
      this._lastHighlightedTile2 = null;
    }

    // First, check for insertion between nodes
    const insertion = this.findNearestConnectionLine(node, tile);

    if (insertion) {
      // Insert this node between parent and child
      const { parent, child } = insertion;

      // Disconnect node from its current parent if any
      if (node.parent) {
        this.tree.disconnect(node);
      }

      // Disconnect the child from the parent
      this.tree.disconnect(child);

      // Connect: parent → new node → child
      this.tree.connect(parent, node);
      this.tree.connect(node, child);

      return;
    }

    // Fall back to regular parent candidate logic
    const candidate = this.findBestParentCandidate(node, tile);

    if (candidate) {
      // Found a suitable parent - connect if different from current
      if (node.parent !== candidate.node) {
        if (node.parent) {
          this.tree.disconnect(node);
        }
        this.tree.connect(candidate.node, node);
      }
    } else {
      // No suitable parent - check if we should disconnect
      if (node.parent) {
        const parentTile = this.nodeToCanvas.get(node.parent.id);
        if (parentTile) {
          const parentCenter = parentTile.getCenterPoint();
          const childCenter = tile.getCenterPoint();
          const dx = parentCenter.x - childCenter.x;
          const dy = parentCenter.y - childCenter.y;
          const distance = Math.sqrt(dx * dx + dy * dy);

          // Only disconnect if moved far enough away
          if (distance > this.DISCONNECT_THRESHOLD) {
            this.tree.disconnect(node);
          }
        }
      }
    }
  }

  // === Connection Lines ===

  updateConnectionLines() {
    // Remove old lines and movement arrows
    const lines = this.canvas.getObjects('line').filter(l => l.isConnectionLine);
    lines.forEach(line => this.canvas.remove(line));

    const arrows = this.canvas.getObjects().filter(o => o.isMovementArrow);
    arrows.forEach(arrow => this.canvas.remove(arrow));

    // Draw new lines
    for (const node of this.tree.getAllNodes()) {
      for (const child of node.children) {
        this.drawConnectionLine(node, child);
      }
    }

    // Draw movement arrows
    this.drawMovementArrows();

    this.canvas.requestRenderAll();
  }

  // === Movement Arrows ===

  drawMovementArrows() {
    const pairs = this.tree.findMovementPairs();

    for (const { head, tail } of pairs) {
      this.drawMovementArrow(head, tail);
    }
  }

  drawMovementArrow(head, tail) {
    const headTile = this.nodeToCanvas.get(head.id);
    const tailTile = this.nodeToCanvas.get(tail.id);

    if (!headTile || !tailTile) return;

    const headCenter = headTile.getCenterPoint();
    const tailCenter = tailTile.getCenterPoint();

    // Determine direction
    const leftwards = headCenter.x > tailCenter.x;

    // Calculate curve control point (below both nodes)
    const maxY = Math.max(
      headCenter.y + this.TILE_HEIGHT,
      tailCenter.y + this.TILE_HEIGHT
    );
    const curveY = maxY + 40;

    // Offset start/end points slightly based on direction
    const offsetX = leftwards ? -5 : 5;
    const startX = tailCenter.x + offsetX;
    const startY = tailCenter.y + this.TILE_HEIGHT / 2 + 5;
    const endX = headCenter.x - offsetX;
    const endY = headCenter.y + this.TILE_HEIGHT / 2 + 5;

    // Draw curved path using fabric.Path
    const midX = (startX + endX) / 2;
    const pathData = `M ${startX} ${startY} Q ${startX} ${curveY} ${midX} ${curveY} Q ${endX} ${curveY} ${endX} ${endY}`;

    const path = new fabric.Path(pathData, {
      fill: '',
      stroke: '#666',
      strokeWidth: 1.5,
      selectable: false,
      evented: false,
      isMovementArrow: true
    });

    this.canvas.add(path);
    this.canvas.sendToBack(path);

    // Draw arrowhead at the head (destination)
    const arrowSize = 8;
    const arrowhead = new fabric.Triangle({
      left: endX,
      top: endY - arrowSize / 2,
      width: arrowSize,
      height: arrowSize,
      fill: '#666',
      angle: 180, // Point upward
      originX: 'center',
      originY: 'center',
      selectable: false,
      evented: false,
      isMovementArrow: true
    });

    this.canvas.add(arrowhead);
  }

  drawConnectionLine(parent, child) {
    const parentTile = this.nodeToCanvas.get(parent.id);
    const childTile = this.nodeToCanvas.get(child.id);

    if (!parentTile || !childTile) return;

    const pCenter = parentTile.getCenterPoint();
    const cCenter = childTile.getCenterPoint();

    const line = new fabric.Line([pCenter.x, pCenter.y, cCenter.x, cCenter.y], {
      stroke: '#333',
      strokeWidth: 3,
      selectable: false,
      evented: true,
      isConnectionLine: true,
      hoverCursor: 'pointer',
      parentNodeId: parent.id,
      childNodeId: child.id,
      padding: 5
    });

    // Click to disconnect
    line.on('mousedown', (e) => {
      e.e.stopPropagation();
      this.tree.disconnect(child);
    });

    // Hover effect
    line.on('mouseover', () => {
      line.set({ stroke: '#cc0000', strokeWidth: 4 });
      this.canvas.requestRenderAll();
    });

    line.on('mouseout', () => {
      line.set({ stroke: '#333', strokeWidth: 3 });
      this.canvas.requestRenderAll();
    });

    this.canvas.add(line);
    this.canvas.sendToBack(line);
  }

  // === Auto-Layout ===

  relayout(animate = true) {
    // Skip if relayout is suppressed (e.g., during batch operations)
    if (this._suppressRelayout) {
      return;
    }

    if (this.tree.isEmpty()) {
      this.updateConnectionLines();
      return;
    }

    // Bottom-up layout: position leaves first, then center parents over children

    // Step 1: Calculate leaf count for each subtree (for width allocation)
    const leafCounts = new Map();
    const calculateLeafCount = (node) => {
      if (node.children.length === 0) {
        leafCounts.set(node.id, 1);
        return 1;
      }
      let sum = 0;
      for (const child of node.children) {
        sum += calculateLeafCount(child);
      }
      leafCounts.set(node.id, sum);
      return sum;
    };

    for (const root of this.tree.roots) {
      calculateLeafCount(root);
    }

    // Step 2: Calculate depth for each node
    const depths = new Map();
    const calculateDepth = (node, depth) => {
      depths.set(node.id, depth);
      for (const child of node.children) {
        calculateDepth(child, depth + 1);
      }
    };

    for (const root of this.tree.roots) {
      calculateDepth(root, 0);
    }

    // Sort roots by current x position
    this.tree.roots.sort((a, b) => {
      const tileA = this.nodeToCanvas.get(a.id);
      const tileB = this.nodeToCanvas.get(b.id);
      if (!tileA || !tileB) return 0;
      return tileA.getCenterPoint().x - tileB.getCenterPoint().x;
    });

    // Step 3: Collect all leaves in left-to-right order
    const leaves = [];
    const collectLeaves = (node) => {
      if (node.children.length === 0) {
        leaves.push(node);
      } else {
        for (const child of node.children) {
          collectLeaves(child);
        }
      }
    };

    for (const root of this.tree.roots) {
      collectLeaves(root);
    }

    // Step 4: Determine starting X position (anchor to first root)
    const totalLeaves = leaves.length;
    const totalPx = totalLeaves * this.UNIT_WIDTH;

    let startX;
    const firstRoot = this.tree.roots[0];
    const firstRootTile = this.nodeToCanvas.get(firstRoot.id);
    if (firstRootTile) {
      const currentCenterX = firstRootTile.getCenterPoint().x;
      const firstRootLeafCount = leafCounts.get(firstRoot.id) || 1;
      const firstRootCenterOffset = (firstRootLeafCount * this.UNIT_WIDTH) / 2;
      startX = currentCenterX - firstRootCenterOffset;
      startX = Math.max(60, startX);
    } else {
      startX = Math.max(60, (this.canvas.getWidth() - totalPx) / 2);
    }

    // Step 5: Position leaves with fixed spacing
    const targets = new Map();

    for (let i = 0; i < leaves.length; i++) {
      const leaf = leaves[i];
      const tile = this.nodeToCanvas.get(leaf.id);
      if (tile) {
        const centerX = startX + (i + 0.5) * this.UNIT_WIDTH;
        const depth = depths.get(leaf.id);
        const y = this.TOP_MARGIN + depth * this.LEVEL_HEIGHT;
        const width = tile.item(0).width || this.TILE_WIDTH;
        targets.set(leaf.id, {
          left: centerX - width / 2,
          top: y,
          centerX: centerX
        });
      }
    }

    // Step 6: Position parents bottom-up, centered over their children
    const positionParent = (node) => {
      if (node.children.length === 0) {
        return; // Already positioned
      }

      // First position all children
      for (const child of node.children) {
        positionParent(child);
      }

      // Find leftmost and rightmost child centers
      let minX = Infinity, maxX = -Infinity;
      for (const child of node.children) {
        const childTarget = targets.get(child.id);
        if (childTarget) {
          minX = Math.min(minX, childTarget.centerX);
          maxX = Math.max(maxX, childTarget.centerX);
        }
      }

      // Center this node over its children
      const centerX = (minX + maxX) / 2;
      const depth = depths.get(node.id);
      const y = this.TOP_MARGIN + depth * this.LEVEL_HEIGHT;
      const tile = this.nodeToCanvas.get(node.id);
      if (tile) {
        const width = tile.item(0).width || this.TILE_WIDTH;
        targets.set(node.id, {
          left: centerX - width / 2,
          top: y,
          centerX: centerX
        });
      }
    };

    for (const root of this.tree.roots) {
      positionParent(root);
    }

    // Animate to targets
    if (animate) {
      this.animateToTargets(targets);
    } else {
      for (const [nodeId, target] of targets) {
        const tile = this.nodeToCanvas.get(nodeId);
        if (tile) {
          tile.set({ left: target.left, top: target.top });
          tile.setCoords();
        }
      }
      this.updateConnectionLines();
      this.canvas.requestRenderAll();
    }
  }

  animateToTargets(targets) {
    const startTime = performance.now();
    const duration = this.ANIMATION_DURATION;
    const startPositions = new Map();

    // Store start positions
    for (const [nodeId, target] of targets) {
      const tile = this.nodeToCanvas.get(nodeId);
      if (tile) {
        startPositions.set(nodeId, { left: tile.left, top: tile.top });
      }
    }

    const animate = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // Ease-out cubic

      for (const [nodeId, target] of targets) {
        const tile = this.nodeToCanvas.get(nodeId);
        const start = startPositions.get(nodeId);
        if (tile && start) {
          tile.set({
            left: start.left + (target.left - start.left) * eased,
            top: start.top + (target.top - start.top) * eased
          });
          tile.setCoords();
        }
      }

      this.updateConnectionLines();
      this.canvas.requestRenderAll();

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }

  // === Sync with Tree Model ===

  syncFromTree() {
    // Remove all existing objects
    this.canvas.clear();
    this.nodeToCanvas.clear();

    // Create tiles for all nodes
    for (const node of this.tree.getAllNodes()) {
      this.createTileForNode(node);
    }

    // Position tiles
    this.relayout(false);
  }

  updateTileLabel(node) {
    const tile = this.nodeToCanvas.get(node.id);
    if (tile) {
      const textObj = tile.item(1);
      const displayLabel = BracketParser.getDisplayLabel(node);
      textObj.set({ text: displayLabel });

      // Update colors if needed
      const colors = getNodeColors(node.label, node.nodeType);
      tile.item(0).set({ fill: colors.bg, stroke: colors.border });
      textObj.set({ fill: colors.text });

      // For terminal tiles, show/hide hint based on whether text is empty
      if (tile.isTerminalTile && tile.item(2)) {
        const isEmpty = !displayLabel || displayLabel === '...';
        tile.item(2).set({ visible: isEmpty });
        textObj.set({ top: isEmpty ? -5 : 0 });
      }

      this.canvas.requestRenderAll();
    }
  }

  removeTileForNode(node) {
    const tile = this.nodeToCanvas.get(node.id);
    if (tile) {
      this.canvas.remove(tile);
      this.nodeToCanvas.delete(node.id);
    }
  }

  // === Drag & Drop from Palette ===

  handleDrop(dropData, x, y) {
    const { type, value } = dropData;

    if (type === 'terminal') {
      // Word dragged from palette input
      const terminal = this.tree.createNode(value, NodeType.TERMINAL);
      const tile = this.createTileForNode(terminal);
      this.positionTileAtDropImmediate(tile, x, y);

      // Auto-connect to nearest parent or insert between nodes
      this.finalizeAutoConnectionForDrop(terminal, tile);
      this.updateConnectionLines();

      // Animate the drop after positioning
      this.animateTileDrop(tile, y);

      // Smart auto-zoom if element is outside viewport
      this.ensureVisible(x, y, this.TERMINAL_WIDTH, this.TERMINAL_HEIGHT);

      if (this.onTreeChanged) {
        this.onTreeChanged();
      }

      return terminal;
    }

    // Create the main node
    const nodeType = type === 'pos' ? NodeType.POS :
                     type === 'phrase' ? NodeType.PHRASE :
                     NodeType.CLAUSE;
    const node = this.tree.createNode(value, nodeType);
    const tile = this.createTileForNode(node);
    this.positionTileAtDropImmediate(tile, x, y);

    // Auto-connect to nearest parent or insert between nodes
    this.finalizeAutoConnectionForDrop(node, tile);

    // For POS nodes, auto-create a terminal child
    let lowestY = y;
    if (type === 'pos') {
      // Suppress automatic relayout during this operation
      this._suppressRelayout = true;

      const terminal = new TreeNode('...', NodeType.TERMINAL);
      this.tree.connect(node, terminal);
      const terminalTile = this.createTileForNode(terminal);

      // Position terminal directly below parent using parent's actual center
      const parentCenter = tile.getCenterPoint();
      const terminalY = parentCenter.y + this.LEVEL_HEIGHT;
      this.positionTileAtDropImmediate(terminalTile, parentCenter.x, terminalY);
      this.animateTileDrop(terminalTile, terminalY);

      lowestY = terminalY;

      // Re-enable relayout
      this._suppressRelayout = false;
    }

    this.updateConnectionLines();

    // Now trigger a single relayout with all tiles present
    this.relayout(true);

    // Smart auto-zoom if element is outside viewport
    this.ensureVisible(x, lowestY, this.TILE_WIDTH, this.TILE_HEIGHT);

    if (this.onTreeChanged) {
      this.onTreeChanged();
    }

    return node;
  }

  /**
   * Similar to finalizeAutoConnection but for newly dropped nodes.
   * Checks for insertion between nodes first.
   */
  finalizeAutoConnectionForDrop(node, tile) {
    // First, check for insertion between nodes
    const insertion = this.findNearestConnectionLine(node, tile);

    if (insertion) {
      // Insert this node between parent and child
      const { parent, child } = insertion;

      // Disconnect the child from the parent
      this.tree.disconnect(child);

      // Connect: parent → new node → child
      this.tree.connect(parent, node);
      this.tree.connect(node, child);

      return;
    }

    // Fall back to regular parent candidate logic
    const candidate = this.findBestParentCandidate(node, tile);

    if (candidate) {
      this.tree.connect(candidate.node, node);
    }
  }

  /**
   * Position tile immediately at drop location (for connection detection).
   * Centers the tile at the given (x, y) coordinates.
   */
  positionTileAtDropImmediate(tile, x, y) {
    // First, set a rough position and call setCoords to calculate actual dimensions
    tile.set({ left: x, top: y, opacity: 1 });
    tile.setCoords();

    // Now use the actual calculated dimensions to center properly
    const actualWidth = tile.width;
    const actualHeight = tile.height;

    tile.set({
      left: x - actualWidth / 2,
      top: y - actualHeight / 2
    });
    tile.setCoords();
  }

  /**
   * Animate a tile dropping into place.
   */
  animateTileDrop(tile, targetY) {
    const groupHeight = tile.height || (tile.isTerminalTile ? this.TERMINAL_HEIGHT : this.TILE_HEIGHT);
    const targetTop = targetY - groupHeight / 2;
    const startTop = targetTop - 20;

    tile.set({
      top: startTop,
      opacity: 0.3
    });
    tile.setCoords();

    const startTime = performance.now();

    const animateDrop = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / 120, 1);
      const eased = 1 - Math.pow(1 - progress, 2);

      tile.set({
        top: startTop + 20 * eased,
        opacity: 0.3 + 0.7 * eased
      });
      tile.setCoords();
      this.updateConnectionLines();
      this.canvas.requestRenderAll();

      if (progress < 1) {
        requestAnimationFrame(animateDrop);
      }
    };

    requestAnimationFrame(animateDrop);
  }

  positionTileAtDrop(tile, x, y) {
    const groupWidth = tile.width || (tile.isTerminalTile ? this.TERMINAL_WIDTH : this.TILE_WIDTH);
    const groupHeight = tile.height || (tile.isTerminalTile ? this.TERMINAL_HEIGHT : this.TILE_HEIGHT);
    const targetTop = y - groupHeight / 2;
    const startTop = targetTop - 20;

    // Animate drop
    tile.set({
      left: x - groupWidth / 2,
      top: startTop,
      opacity: 0.3
    });
    tile.setCoords();

    const startTime = performance.now();

    const animateDrop = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / 120, 1);
      const eased = 1 - Math.pow(1 - progress, 2);

      tile.set({
        top: startTop + 20 * eased,
        opacity: 0.3 + 0.7 * eased
      });
      tile.setCoords();
      this.canvas.requestRenderAll();

      if (progress < 1) {
        requestAnimationFrame(animateDrop);
      }
    };

    requestAnimationFrame(animateDrop);
  }

  // === View Management ===

  /**
   * Get the visible viewport bounds in canvas coordinates.
   */
  getVisibleBounds() {
    const vpt = this.canvas.viewportTransform;
    const zoom = this.canvas.getZoom();
    const width = this.canvas.getWidth();
    const height = this.canvas.getHeight();

    return {
      left: -vpt[4] / zoom,
      top: -vpt[5] / zoom,
      right: (-vpt[4] + width) / zoom,
      bottom: (-vpt[5] + height) / zoom,
      width: width / zoom,
      height: height / zoom
    };
  }

  /**
   * Check if a point is within the visible viewport.
   */
  isPointVisible(x, y, margin = 50) {
    const bounds = this.getVisibleBounds();
    return x >= bounds.left + margin &&
           x <= bounds.right - margin &&
           y >= bounds.top + margin &&
           y <= bounds.bottom - margin;
  }

  /**
   * Fit the entire tree into the viewport with padding.
   */
  fitToView(animate = true) {
    const treeBounds = this.getTreeBounds();
    if (!treeBounds) return;

    const canvasWidth = this.canvas.getWidth();
    const canvasHeight = this.canvas.getHeight();
    const padding = 40;

    // Calculate zoom to fit
    const scaleX = (canvasWidth - padding * 2) / treeBounds.width;
    const scaleY = (canvasHeight - padding * 2) / treeBounds.height;
    const targetZoom = Math.min(scaleX, scaleY, 2); // Cap at 2x zoom

    // Calculate center offset
    const treeCenterX = treeBounds.left + treeBounds.width / 2;
    const treeCenterY = treeBounds.top + treeBounds.height / 2;

    const targetVptX = canvasWidth / 2 - treeCenterX * targetZoom;
    const targetVptY = canvasHeight / 2 - treeCenterY * targetZoom;

    if (animate) {
      this.animateViewport(targetZoom, targetVptX, targetVptY);
    } else {
      this.canvas.setZoom(targetZoom);
      this.canvas.setViewportTransform([targetZoom, 0, 0, targetZoom, targetVptX, targetVptY]);
      this.canvas.requestRenderAll();
    }
  }

  /**
   * Get the bounding box of all tree nodes.
   */
  getTreeBounds() {
    const tiles = Array.from(this.nodeToCanvas.values());
    if (tiles.length === 0) return null;

    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;

    for (const tile of tiles) {
      tile.setCoords();
      const bounds = tile.getBoundingRect(true);
      minX = Math.min(minX, bounds.left);
      minY = Math.min(minY, bounds.top);
      maxX = Math.max(maxX, bounds.left + bounds.width);
      maxY = Math.max(maxY, bounds.top + bounds.height);
    }

    return {
      left: minX,
      top: minY,
      width: maxX - minX,
      height: maxY - minY,
      right: maxX,
      bottom: maxY
    };
  }

  /**
   * Smart auto-zoom: if a new element is outside the viewport, zoom out to show it.
   * Otherwise, keep the current view to avoid jarring motion.
   */
  ensureVisible(x, y, nodeWidth = this.TILE_WIDTH, nodeHeight = this.TILE_HEIGHT) {
    const visibleBounds = this.getVisibleBounds();
    const margin = 30;

    // Check if the new element is within the visible area
    const isVisible = x - nodeWidth / 2 >= visibleBounds.left + margin &&
                      x + nodeWidth / 2 <= visibleBounds.right - margin &&
                      y - nodeHeight / 2 >= visibleBounds.top + margin &&
                      y + nodeHeight / 2 <= visibleBounds.bottom - margin;

    if (isVisible) {
      // Element is visible, no need to adjust view
      return;
    }

    // Element is outside viewport - zoom out to show it
    const treeBounds = this.getTreeBounds();
    if (!treeBounds) return;

    const canvasWidth = this.canvas.getWidth();
    const canvasHeight = this.canvas.getHeight();
    const padding = 50;

    // Calculate zoom needed to fit all content including new element
    const scaleX = (canvasWidth - padding * 2) / treeBounds.width;
    const scaleY = (canvasHeight - padding * 2) / treeBounds.height;
    let targetZoom = Math.min(scaleX, scaleY, this.canvas.getZoom()); // Don't zoom in, only out

    // Ensure minimum zoom
    targetZoom = Math.max(targetZoom, 0.3);

    // Calculate viewport to center on point biased toward the new element
    const treeCenterX = treeBounds.left + treeBounds.width / 2;
    const treeCenterY = treeBounds.top + treeBounds.height / 2;

    // Bias center toward the new element (30% toward new element, 70% toward tree center)
    const biasFactor = 0.3;
    const adjustedCenterX = treeCenterX + (x - treeCenterX) * biasFactor;
    const adjustedCenterY = treeCenterY + (y - treeCenterY) * biasFactor;

    const targetVptX = canvasWidth / 2 - adjustedCenterX * targetZoom;
    const targetVptY = canvasHeight / 2 - adjustedCenterY * targetZoom;

    this.animateViewport(targetZoom, targetVptX, targetVptY, 200);
  }

  /**
   * Animate viewport transform smoothly.
   */
  animateViewport(targetZoom, targetVptX, targetVptY, duration = 300) {
    const startZoom = this.canvas.getZoom();
    const startVpt = this.canvas.viewportTransform.slice();
    const startTime = performance.now();

    const animate = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // Ease-out cubic

      const currentZoom = startZoom + (targetZoom - startZoom) * eased;
      const currentVptX = startVpt[4] + (targetVptX - startVpt[4]) * eased;
      const currentVptY = startVpt[5] + (targetVptY - startVpt[5]) * eased;

      this.canvas.setZoom(currentZoom);
      this.canvas.setViewportTransform([currentZoom, 0, 0, currentZoom, currentVptX, currentVptY]);
      this.canvas.requestRenderAll();

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }

  // === Export ===

  getTightBounds() {
    const objs = this.canvas.getObjects().filter(o =>
      o.visible && (o.type === 'group' || o.isConnectionLine)
    );

    if (objs.length === 0) {
      return { left: 0, top: 0, width: this.canvas.getWidth(), height: this.canvas.getHeight() };
    }

    objs.forEach(o => o.setCoords());

    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;

    objs.forEach(o => {
      const ac = o.aCoords || o.calcCoords();
      const xs = [ac.tl.x, ac.tr.x, ac.bl.x, ac.br.x];
      const ys = [ac.tl.y, ac.tr.y, ac.bl.y, ac.br.y];
      minX = Math.min(minX, ...xs);
      maxX = Math.max(maxX, ...xs);
      minY = Math.min(minY, ...ys);
      maxY = Math.max(maxY, ...ys);
    });

    const width = Math.max(1, maxX - minX);
    const height = Math.max(1, maxY - minY);
    const padX = Math.max(30, width * 0.10);
    const padY = Math.max(30, height * 0.10);

    return {
      left: Math.max(0, Math.floor(minX - padX)),
      top: Math.max(0, Math.floor(minY - padY)),
      width: Math.ceil(width + padX * 2),
      height: Math.ceil(height + padY * 2)
    };
  }

  async exportPNG(multiplier = 3) {
    const prevBg = this.canvas.backgroundColor;
    this.canvas.backgroundColor = '#ffffff';
    this.canvas.requestRenderAll();

    const bounds = this.getTightBounds();
    const dataURL = this.canvas.toDataURL({
      format: 'png',
      left: bounds.left,
      top: bounds.top,
      width: bounds.width,
      height: bounds.height,
      multiplier
    });

    this.canvas.backgroundColor = prevBg || null;
    this.canvas.requestRenderAll();

    return dataURL;
  }
}

// Export for use in other modules
window.CanvasManager = CanvasManager;
