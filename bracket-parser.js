/**
 * Bracket Parser - Converts bracket notation to tree model
 * Ported and adapted from Syntree
 */

class BracketParser {
  constructor() {
    this.lastError = null;
  }

  /**
   * Parse bracket notation string into a SyntaxTree
   * @param {string} str - Bracket notation string like "[S [NP the cat] [VP ran]]"
   * @param {SyntaxTree} tree - Optional existing tree to populate (clears it first)
   * @returns {SyntaxTree} - The populated syntax tree
   */
  parse(str, tree = null) {
    this.lastError = null;

    if (!tree) {
      tree = new SyntaxTree();
    } else {
      tree.clear();
    }

    // Clean up the string
    str = str.trim();

    if (!str) {
      return tree;
    }

    // Balance brackets
    str = this.balanceBrackets(str);

    try {
      tree.beginBatch();

      // Parse may return multiple roots if there are multiple top-level brackets
      const roots = this.parseMultipleRoots(str);

      for (const root of roots) {
        tree.addRoot(root);
      }

      tree.endBatch();
    } catch (e) {
      this.lastError = e.message;
      tree.endBatch();
    }

    return tree;
  }

  /**
   * Balance unmatched brackets
   */
  balanceBrackets(str) {
    let open = 0;
    for (let i = 0; i < str.length; i++) {
      if (str[i] === '[') open++;
      if (str[i] === ']') open--;
    }

    // Add missing closing brackets
    while (open > 0) {
      str = str + ']';
      open--;
    }

    // Add missing opening brackets
    while (open < 0) {
      str = '[' + str;
      open++;
    }

    return str;
  }

  /**
   * Parse string that may contain multiple root-level brackets
   */
  parseMultipleRoots(str) {
    const roots = [];
    let i = 0;

    while (i < str.length) {
      // Skip whitespace
      while (i < str.length && /\s/.test(str[i])) i++;

      if (i >= str.length) break;

      if (str[i] === '[') {
        // Find matching closing bracket
        const start = i;
        let level = 0;
        let end = i;

        for (let j = i; j < str.length; j++) {
          if (str[j] === '[') level++;
          if (str[j] === ']') level--;
          if (level === 0) {
            end = j;
            break;
          }
        }

        const substring = str.substring(start, end + 1);
        const node = this.parseNode(substring);
        if (node) {
          roots.push(node);
        }

        i = end + 1;
      } else {
        // Bare text at root level - treat as terminal
        let end = i;
        while (end < str.length && str[end] !== '[' && str[end] !== ']') {
          end++;
        }

        const text = str.substring(i, end).trim();
        if (text) {
          const node = this.parseTerminal(text);
          if (node) {
            roots.push(node);
          }
        }

        i = end;
      }
    }

    return roots;
  }

  /**
   * Parse a single node (recursive)
   */
  parseNode(str) {
    str = str.trim();

    if (!str) return null;

    // Not a bracketed node - treat as terminal
    if (str[0] !== '[') {
      return this.parseTerminal(str);
    }

    // Extract label (text between [ and first space/bracket)
    let i = 1;
    while (i < str.length && str[i] !== ' ' && str[i] !== '[' && str[i] !== ']') {
      i++;
    }

    let label = str.substring(1, i);
    let node = new TreeNode(label);

    // Parse special markers in label
    this.parseSpecialMarkers(node);

    // Skip whitespace after label
    while (i < str.length && str[i] === ' ') i++;

    // If we hit ], no children
    if (str[i] === ']') {
      return node;
    }

    // Parse children
    let level = 1;
    let childStart = i;

    for (; i < str.length && level > 0; i++) {
      const prevLevel = level;

      if (str[i] === '[') level++;
      if (str[i] === ']') level--;

      // Found a child boundary
      if ((prevLevel === 1 && level === 2) || (prevLevel === 1 && level === 0)) {
        // Text child (terminal)
        const childText = str.substring(childStart, i).trim();
        if (childText && /\S/.test(childText)) {
          const terminal = this.parseTerminal(childText);
          if (terminal) {
            node.addChild(terminal);
          }
        }
        childStart = i;
      }

      if (prevLevel === 2 && level === 1) {
        // Bracketed child
        const childStr = str.substring(childStart, i + 1);
        const childNode = this.parseNode(childStr);
        if (childNode) {
          node.addChild(childNode);
        }
        childStart = i + 1;
      }
    }

    return node;
  }

  /**
   * Parse a terminal (leaf) node
   */
  parseTerminal(str) {
    str = str.trim();
    if (!str) return null;

    const node = new TreeNode(str, NodeType.TERMINAL);

    // Check for movement tail: <label>
    const tailMatch = str.match(/\s*<(\w+)>\s*/);
    if (tailMatch) {
      node.movementTail = tailMatch[1];
      node.label = str.replace(/\s*<\w+>\s*/, ' ').trim();
    }

    return node;
  }

  /**
   * Parse special markers from label (starred, movement labels)
   */
  parseSpecialMarkers(node) {
    let label = node.label;

    // Check for starred (^)
    if (label.includes('^')) {
      node.isStarred = true;
      label = label.replace('^', '');
    }

    // Check for movement label (_label or _number)
    const labelMatch = label.match(/_(\w+)$/);
    if (labelMatch) {
      node.movementLabel = labelMatch[1];
      // If it's a number, we'll display it as subscript (handled in rendering)
      label = label.replace(/_\w+$/, '');
    }

    node.label = label;

    // Update node type based on cleaned label
    if (node.nodeType !== NodeType.TERMINAL) {
      node.nodeType = getNodeTypeFromLabel(label);
    }
  }

  /**
   * Validate bracket notation without parsing
   * Returns { valid: boolean, error: string|null, position: number|null }
   */
  validate(str) {
    if (!str || !str.trim()) {
      return { valid: true, error: null, position: null };
    }

    let depth = 0;
    let maxDepth = 0;

    for (let i = 0; i < str.length; i++) {
      if (str[i] === '[') {
        depth++;
        maxDepth = Math.max(maxDepth, depth);
      } else if (str[i] === ']') {
        depth--;
        if (depth < 0) {
          return {
            valid: false,
            error: 'Unexpected closing bracket',
            position: i
          };
        }
      }
    }

    if (depth > 0) {
      return {
        valid: false,
        error: `Missing ${depth} closing bracket${depth > 1 ? 's' : ''}`,
        position: str.length
      };
    }

    return { valid: true, error: null, position: null };
  }

  /**
   * Get error from last parse attempt
   */
  getLastError() {
    return this.lastError;
  }

  /**
   * Convert subscript numbers for display
   */
  static subscriptify(str) {
    const subscripts = {
      '0': '\u2080', '1': '\u2081', '2': '\u2082', '3': '\u2083', '4': '\u2084',
      '5': '\u2085', '6': '\u2086', '7': '\u2087', '8': '\u2088', '9': '\u2089'
    };

    let result = '';
    for (const char of str) {
      result += subscripts[char] || char;
    }
    return result;
  }

  /**
   * Get display label for a node (with subscript movement labels)
   */
  static getDisplayLabel(node) {
    let label = node.label;

    if (node.movementLabel && /^\d+$/.test(node.movementLabel)) {
      label += BracketParser.subscriptify(node.movementLabel);
    } else if (node.movementLabel) {
      label += '_' + node.movementLabel;
    }

    return label;
  }
}

// Export for use in other modules
window.BracketParser = BracketParser;
