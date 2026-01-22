/**
 * Bracket Serializer - Converts tree model to bracket notation
 */

class BracketSerializer {
  constructor(options = {}) {
    this.options = {
      prettyPrint: false,
      indentSize: 2,
      includeMovement: true,
      ...options
    };
  }

  /**
   * Serialize a SyntaxTree to bracket notation
   * @param {SyntaxTree} tree - The tree to serialize
   * @returns {string} - Bracket notation string
   */
  serialize(tree) {
    if (!tree || tree.isEmpty()) {
      return '';
    }

    const parts = [];
    for (const root of tree.roots) {
      parts.push(this.serializeNode(root, 0));
    }

    if (this.options.prettyPrint) {
      return parts.join('\n\n');
    } else {
      return parts.join(' ');
    }
  }

  /**
   * Serialize a single node (recursive)
   * @param {TreeNode} node - The node to serialize
   * @param {number} depth - Current depth for indentation
   * @returns {string} - Bracket notation for this subtree
   */
  serializeNode(node, depth = 0) {
    const indent = this.options.prettyPrint ? ' '.repeat(depth * this.options.indentSize) : '';
    const newline = this.options.prettyPrint ? '\n' : '';

    // Terminal nodes are just their label (possibly with movement tail)
    if (node.isTerminal()) {
      let text = node.label;
      if (this.options.includeMovement && node.movementTail) {
        text += `<${node.movementTail}>`;
      }
      return text;
    }

    // Build the label with special markers
    let label = node.label;

    if (node.isStarred) {
      label += '^';
    }

    if (this.options.includeMovement && node.movementLabel) {
      label += `_${node.movementLabel}`;
    }

    // No children - just return the label in brackets
    if (node.children.length === 0) {
      return `[${label}]`;
    }

    // Serialize children
    const childStrings = node.children.map(child => this.serializeNode(child, depth + 1));

    if (this.options.prettyPrint) {
      // Pretty print with indentation
      const childIndent = ' '.repeat((depth + 1) * this.options.indentSize);
      const formattedChildren = childStrings.map(s => childIndent + s).join(newline);
      return `[${label}${newline}${formattedChildren}]`;
    } else {
      // Compact format
      return `[${label} ${childStrings.join(' ')}]`;
    }
  }

  /**
   * Serialize with pretty printing enabled
   */
  serializePretty(tree) {
    const oldPrettyPrint = this.options.prettyPrint;
    this.options.prettyPrint = true;
    const result = this.serialize(tree);
    this.options.prettyPrint = oldPrettyPrint;
    return result;
  }

  /**
   * Serialize in compact format
   */
  serializeCompact(tree) {
    const oldPrettyPrint = this.options.prettyPrint;
    this.options.prettyPrint = false;
    const result = this.serialize(tree);
    this.options.prettyPrint = oldPrettyPrint;
    return result;
  }

  /**
   * Serialize a single node and its subtree
   */
  serializeSubtree(node) {
    return this.serializeNode(node, 0);
  }

  /**
   * Create a URL-safe encoded version
   */
  serializeForURL(tree) {
    const compact = this.serializeCompact(tree);
    return encodeURIComponent(compact);
  }

  /**
   * Generate bracket text with node ID markers (for cursor mapping)
   * Returns { text: string, positions: Map<nodeId, { start, end }> }
   */
  serializeWithPositions(tree) {
    if (!tree || tree.isEmpty()) {
      return { text: '', positions: new Map() };
    }

    const positions = new Map();
    let offset = 0;

    const serializeNodeWithPos = (node) => {
      const start = offset;

      if (node.isTerminal()) {
        let text = node.label;
        if (this.options.includeMovement && node.movementTail) {
          text += `<${node.movementTail}>`;
        }
        offset += text.length;
        positions.set(node.id, { start, end: offset, text });
        return text;
      }

      // Build label
      let label = node.label;
      if (node.isStarred) label += '^';
      if (this.options.includeMovement && node.movementLabel) {
        label += `_${node.movementLabel}`;
      }

      // Opening bracket and label
      let result = '[' + label;
      offset += result.length;

      // Children
      if (node.children.length > 0) {
        result += ' ';
        offset += 1;

        for (let i = 0; i < node.children.length; i++) {
          if (i > 0) {
            result += ' ';
            offset += 1;
          }
          result += serializeNodeWithPos(node.children[i]);
        }
      }

      // Closing bracket
      result += ']';
      offset += 1;

      positions.set(node.id, { start, end: offset, label });
      return result;
    };

    const parts = [];
    for (let i = 0; i < tree.roots.length; i++) {
      if (i > 0) {
        parts.push(' ');
        offset += 1;
      }
      parts.push(serializeNodeWithPos(tree.roots[i]));
    }

    return {
      text: parts.join(''),
      positions
    };
  }

  /**
   * Find which node corresponds to a cursor position in the bracket text
   * @param {number} cursorPos - Cursor position in text
   * @param {Map} positions - Position map from serializeWithPositions
   * @returns {number|null} - Node ID at cursor, or null
   */
  findNodeAtPosition(cursorPos, positions) {
    let bestMatch = null;
    let smallestRange = Infinity;

    for (const [nodeId, pos] of positions) {
      if (cursorPos >= pos.start && cursorPos <= pos.end) {
        const range = pos.end - pos.start;
        if (range < smallestRange) {
          smallestRange = range;
          bestMatch = nodeId;
        }
      }
    }

    return bestMatch;
  }
}

// Export for use in other modules
window.BracketSerializer = BracketSerializer;
