/**
 * Table Generator - Generates hierarchical labeling tables from the syntax tree.
 * Read-only view derived from tree/bracket notation.
 * Role cells are editable for student interaction.
 */

class TableGenerator {

  /**
   * Generate an HTML table from the current syntax tree.
   * @param {SyntaxTree} syntaxTree
   * @returns {string} HTML string
   */
  generate(syntaxTree) {
    if (!syntaxTree || syntaxTree.isEmpty()) {
      return '<p class="table-empty">Enter bracket notation or build a tree to see the table view.</p>';
    }

    const startNodes = this._getStartNodes(syntaxTree);
    if (startNodes.length === 0) {
      return '<p class="table-empty">No structure to display.</p>';
    }

    // Collect terminals left-to-right
    const terminals = [];
    this._collectTerminals(startNodes, terminals);
    if (terminals.length === 0) {
      return '<p class="table-empty">No words in tree.</p>';
    }

    const numCols = terminals.length;

    // Map each terminal to its column index
    const terminalIndex = new Map();
    terminals.forEach((t, i) => terminalIndex.set(t, i));

    // Assign depth and compute column spans for each phrase/clause node
    const nodeInfo = new Map();
    this._processNodes(startNodes, 1, terminalIndex, nodeInfo);

    // Find max depth
    let maxDepth = 0;
    for (const info of nodeInfo.values()) {
      if (info.depth > maxDepth) maxDepth = info.depth;
    }

    // Collect POS labels (one per terminal)
    const posLabels = terminals.map(t => {
      if (t.parent && t.parent.nodeType === NodeType.POS) {
        return t.parent.label;
      }
      return '';
    });

    return this._renderTable(terminals, nodeInfo, posLabels, maxDepth, numCols);
  }

  /**
   * Get starting nodes for table generation.
   * If single root is a clause (S, IC, etc.), skip it and use its children.
   */
  _getStartNodes(syntaxTree) {
    const roots = syntaxTree.roots.filter(r => r.children.length > 0 || r.nodeType === NodeType.TERMINAL);
    if (roots.length === 1 && roots[0].nodeType === NodeType.CLAUSE && roots[0].children.length > 0) {
      return roots[0].children;
    }
    return roots;
  }

  /**
   * Collect terminal nodes in left-to-right order.
   */
  _collectTerminals(nodes, result) {
    for (const node of nodes) {
      if (node.nodeType === NodeType.TERMINAL) {
        result.push(node);
      } else {
        this._collectTerminals(node.children, result);
      }
    }
  }

  /**
   * Assign depth levels and compute column spans for phrase/clause nodes.
   * POS and terminal nodes are skipped (they have dedicated rows).
   */
  _processNodes(nodes, depth, terminalIndex, nodeInfo) {
    for (const node of nodes) {
      if (node.nodeType === NodeType.TERMINAL || node.nodeType === NodeType.POS) {
        continue;
      }

      // Compute span from terminal descendants
      const terms = [];
      this._collectTerminals([node], terms);
      if (terms.length === 0) continue;

      const startCol = terminalIndex.get(terms[0]);
      const endCol = terminalIndex.get(terms[terms.length - 1]) + 1; // exclusive

      if (startCol === undefined) continue;

      nodeInfo.set(node, { depth, startCol, endCol });

      // Recurse into children at next depth
      this._processNodes(node.children, depth + 1, terminalIndex, nodeInfo);
    }
  }

  /**
   * Render the complete HTML table.
   */
  _renderTable(terminals, nodeInfo, posLabels, maxDepth, numCols) {
    // Group nodes by depth level
    const levels = new Map();
    for (const [node, info] of nodeInfo) {
      if (!levels.has(info.depth)) levels.set(info.depth, []);
      levels.get(info.depth).push({ node, startCol: info.startCol, endCol: info.endCol });
    }

    const showNumbers = maxDepth > 1;
    let html = '<table class="labeling-table">\n';

    // Generate level rows (Role + Phrase/Clause pairs)
    for (let d = 1; d <= maxDepth; d++) {
      const entries = (levels.get(d) || []).sort((a, b) => a.startCol - b.startCol);

      // Determine if this level contains clauses
      const hasClauses = entries.some(e => e.node.nodeType === NodeType.CLAUSE);
      const typeLabel = hasClauses ? 'Clause' : 'Phrase';
      const numSuffix = showNumbers ? ' ' + d : '';

      // Role row (editable blanks where content exists, grey elsewhere)
      this._currentLevel = d;
      html += '  <tr>\n';
      html += `    <th class="lsh">Role${numSuffix}</th>\n`;
      html += this._renderCells(entries, numCols, 'role', true);
      html += '  </tr>\n';

      // Phrase/Clause row (auto-populated from tree)
      html += '  <tr>\n';
      html += `    <th>${typeLabel}${numSuffix}</th>\n`;
      html += this._renderCells(entries, numCols, null, false);
      html += '  </tr>\n';
    }

    // POS row
    html += '  <tr>\n';
    html += '    <th class="lsh">POS</th>\n';
    for (const label of posLabels) {
      html += `    <td class="pos">${this._esc(label)}</td>\n`;
    }
    html += '  </tr>\n';

    // Word row
    html += '  <tr>\n';
    html += '    <th class="lsh word-header">Word</th>\n';
    for (const t of terminals) {
      html += `    <td class="word">${this._esc(t.label)}</td>\n`;
    }
    html += '  </tr>\n';

    html += '</table>';
    return html;
  }

  /**
   * Render cells for a single row at a given depth level.
   * Fills gaps between nodes with grey (empty) merged cells.
   */
  _renderCells(entries, numCols, forcedClass, isEditable) {
    let html = '';
    let col = 0;

    for (const entry of entries) {
      // Grey gap before this node
      if (entry.startCol > col) {
        const gap = entry.startCol - col;
        html += `    <td class="empty"${gap > 1 ? ` colspan="${gap}"` : ''}></td>\n`;
      }

      // Determine cell class
      let cellClass;
      if (forcedClass) {
        cellClass = forcedClass;
      } else {
        cellClass = entry.node.nodeType === NodeType.CLAUSE ? 'clause' : 'phrase';
      }

      const span = entry.endCol - entry.startCol;
      const colspanAttr = span > 1 ? ` colspan="${span}"` : '';

      if (isEditable) {
        html += `    <td class="${cellClass}"${colspanAttr} contenteditable="true" data-level="${this._currentLevel}" data-col="${entry.startCol}"></td>\n`;
      } else {
        html += `    <td class="${cellClass}"${colspanAttr}>${this._esc(entry.node.label)}</td>\n`;
      }

      col = entry.endCol;
    }

    // Grey gap after last node
    if (col < numCols) {
      const gap = numCols - col;
      html += `    <td class="empty"${gap > 1 ? ` colspan="${gap}"` : ''}></td>\n`;
    }

    return html;
  }

  /** HTML-escape a string. */
  _esc(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
}

window.TableGenerator = TableGenerator;
