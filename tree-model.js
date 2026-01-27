/**
 * Tree Model - Single source of truth for the syntax tree
 * Both the canvas view and bracket notation derive from this model
 */

// Node types
const NodeType = {
  CLAUSE: 'clause',
  PHRASE: 'phrase',
  POS: 'pos',
  TERMINAL: 'terminal'
};

// Color mappings for each category
const NodeColors = {
  // Clauses - white
  S: { bg: '#ffffff', text: '#000000', border: '#333333' },
  IC: { bg: '#ffffff', text: '#000000', border: '#333333' },
  DC: { bg: '#ffffff', text: '#000000', border: '#333333' },
  RC: { bg: '#ffffff', text: '#000000', border: '#333333' },
  CC: { bg: '#ffffff', text: '#000000', border: '#333333' },
  CP: { bg: '#ffffff', text: '#000000', border: '#333333' },
  IP: { bg: '#ffffff', text: '#000000', border: '#333333' },
  TP: { bg: '#ffffff', text: '#000000', border: '#333333' },

  // Phrases - colored
  NP: { bg: '#F1948A', text: '#000000', border: '#333333' },
  VP: { bg: '#58D68D', text: '#000000', border: '#333333' },
  PP: { bg: '#D7BDE2', text: '#000000', border: '#333333' },
  ADJP: { bg: '#F7DC6F', text: '#000000', border: '#333333' },
  ADVP: { bg: '#85C1E9', text: '#000000', border: '#333333' },
  DP: { bg: '#F5B7B1', text: '#000000', border: '#333333' },

  // POS - colored (full names)
  NOUN: { bg: '#E74C3C', text: '#000000', border: '#333333' },
  VERB: { bg: '#27AE60', text: '#000000', border: '#333333' },
  ADJ: { bg: '#F1C40F', text: '#000000', border: '#333333' },
  ADV: { bg: '#3498DB', text: '#000000', border: '#333333' },
  DET: { bg: '#F39C12', text: '#000000', border: '#333333' },
  PRON: { bg: '#E67E22', text: '#000000', border: '#333333' },
  PREP: { bg: '#7D3C98', text: '#000000', border: '#333333' },
  CONJ: { bg: '#95A5A6', text: '#000000', border: '#333333' },
  MOD: { bg: '#A3E4D7', text: '#000000', border: '#333333' },
  AUX: { bg: '#16A085', text: '#000000', border: '#333333' },
  SUB: { bg: '#D5DBDB', text: '#000000', border: '#333333' },
  REL: { bg: '#FCF3CF', text: '#000000', border: '#333333' },
  COMP: { bg: '#FADBD8', text: '#000000', border: '#333333' },

  // POS - common single-letter abbreviations (same colors as full names)
  N: { bg: '#E74C3C', text: '#000000', border: '#333333' },    // Noun
  V: { bg: '#27AE60', text: '#000000', border: '#333333' },    // Verb
  A: { bg: '#F1C40F', text: '#000000', border: '#333333' },    // Adjective
  P: { bg: '#7D3C98', text: '#000000', border: '#333333' },    // Preposition
  D: { bg: '#F39C12', text: '#000000', border: '#333333' },    // Determiner
  C: { bg: '#95A5A6', text: '#000000', border: '#333333' },    // Conjunction/Complementizer
  T: { bg: '#16A085', text: '#000000', border: '#333333' },    // Tense
  I: { bg: '#16A085', text: '#000000', border: '#333333' },    // Inflection

  // Penn Treebank style POS tags
  NN: { bg: '#E74C3C', text: '#000000', border: '#333333' },   // Noun
  NNS: { bg: '#E74C3C', text: '#000000', border: '#333333' },  // Noun plural
  NNP: { bg: '#E74C3C', text: '#000000', border: '#333333' },  // Proper noun
  NNPS: { bg: '#E74C3C', text: '#000000', border: '#333333' }, // Proper noun plural
  VB: { bg: '#27AE60', text: '#000000', border: '#333333' },   // Verb base
  VBD: { bg: '#27AE60', text: '#000000', border: '#333333' },  // Verb past tense
  VBG: { bg: '#27AE60', text: '#000000', border: '#333333' },  // Verb gerund
  VBN: { bg: '#27AE60', text: '#000000', border: '#333333' },  // Verb past participle
  VBP: { bg: '#27AE60', text: '#000000', border: '#333333' },  // Verb non-3rd person
  VBZ: { bg: '#27AE60', text: '#000000', border: '#333333' },  // Verb 3rd person singular
  JJ: { bg: '#F1C40F', text: '#000000', border: '#333333' },   // Adjective
  JJR: { bg: '#F1C40F', text: '#000000', border: '#333333' },  // Adjective comparative
  JJS: { bg: '#F1C40F', text: '#000000', border: '#333333' },  // Adjective superlative
  RB: { bg: '#3498DB', text: '#000000', border: '#333333' },   // Adverb
  RBR: { bg: '#3498DB', text: '#000000', border: '#333333' },  // Adverb comparative
  RBS: { bg: '#3498DB', text: '#000000', border: '#333333' },  // Adverb superlative
  IN: { bg: '#7D3C98', text: '#000000', border: '#333333' },   // Preposition/subordinating conj
  DT: { bg: '#F39C12', text: '#000000', border: '#333333' },   // Determiner
  PRP: { bg: '#E67E22', text: '#000000', border: '#333333' },  // Personal pronoun
  'PRP$': { bg: '#E67E22', text: '#000000', border: '#333333' }, // Possessive pronoun
  WP: { bg: '#E67E22', text: '#000000', border: '#333333' },   // Wh-pronoun
  WDT: { bg: '#F39C12', text: '#000000', border: '#333333' },  // Wh-determiner
  WRB: { bg: '#3498DB', text: '#000000', border: '#333333' },  // Wh-adverb
  MD: { bg: '#16A085', text: '#000000', border: '#333333' },   // Modal
  TO: { bg: '#7D3C98', text: '#000000', border: '#333333' },   // "to"

  // Terminal - white
  TERMINAL: { bg: '#ffffff', text: '#000000', border: '#999999' }
};

// Determine node type from label
function getNodeTypeFromLabel(label) {
  const upperLabel = label.toUpperCase();

  // Clauses
  if (['S', 'IC', 'DC', 'RC', 'CC', 'CP', 'IP', 'TP'].includes(upperLabel)) {
    return NodeType.CLAUSE;
  }

  // Phrases
  if (['NP', 'VP', 'PP', 'ADJP', 'ADVP', 'DP'].includes(upperLabel)) {
    return NodeType.PHRASE;
  }

  // POS - full names
  if (['NOUN', 'VERB', 'ADJ', 'ADV', 'DET', 'PRON', 'PREP', 'CONJ', 'MOD', 'AUX', 'SUB', 'REL', 'COMP'].includes(upperLabel)) {
    return NodeType.POS;
  }

  // POS - single letter abbreviations
  if (['N', 'V', 'A', 'P', 'D', 'C', 'T', 'I'].includes(upperLabel)) {
    return NodeType.POS;
  }

  // POS - Penn Treebank style tags
  if (['NN', 'NNS', 'NNP', 'NNPS', 'VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ',
       'JJ', 'JJR', 'JJS', 'RB', 'RBR', 'RBS', 'IN', 'DT', 'PRP', 'PRP$',
       'WP', 'WDT', 'WRB', 'MD', 'TO'].includes(upperLabel)) {
    return NodeType.POS;
  }

  return NodeType.CLAUSE; // Default for unknown labels
}

// Get color scheme for a node
function getNodeColors(label, nodeType) {
  if (nodeType === NodeType.TERMINAL) {
    return NodeColors.TERMINAL;
  }
  const upperLabel = label.toUpperCase();
  return NodeColors[upperLabel] || { bg: '#cccccc', text: '#000000', border: '#333333' };
}

/**
 * TreeNode - represents a single node in the syntax tree
 */
class TreeNode {
  constructor(label, nodeType = null) {
    this.id = TreeNode.nextId++;
    this.label = label;
    this.nodeType = nodeType || getNodeTypeFromLabel(label);
    this.children = [];
    this.parent = null;

    // Position on canvas (managed by canvas manager)
    this.x = 0;
    this.y = 0;

    // Movement notation
    this.movementLabel = null;  // e.g., "_1" in [NP_1 what]
    this.movementTail = null;   // e.g., "<1>" for trace
    this.isStarred = false;     // For triangle notation

    // Reference to canvas object (set by canvas manager)
    this.canvasObject = null;
  }

  // Add a child node
  addChild(child, index = null) {
    // Remove from previous parent if any
    if (child.parent) {
      child.parent.removeChild(child);
    }

    child.parent = this;

    if (index !== null && index >= 0 && index <= this.children.length) {
      this.children.splice(index, 0, child);
    } else {
      this.children.push(child);
    }

    return child;
  }

  // Remove a child node
  removeChild(child) {
    const index = this.children.indexOf(child);
    if (index > -1) {
      this.children.splice(index, 1);
      child.parent = null;
    }
    return child;
  }

  // Get all descendants (recursive)
  getDescendants() {
    let descendants = [];
    for (const child of this.children) {
      descendants.push(child);
      descendants = descendants.concat(child.getDescendants());
    }
    return descendants;
  }

  // Check if this node is an ancestor of another
  isAncestorOf(node) {
    let current = node.parent;
    while (current) {
      if (current === this) return true;
      current = current.parent;
    }
    return false;
  }

  // Find the lowest common ancestor with another node
  findLCA(other) {
    const ancestors = new Set();
    let current = this;
    while (current) {
      ancestors.add(current);
      current = current.parent;
    }

    current = other;
    while (current) {
      if (ancestors.has(current)) return current;
      current = current.parent;
    }
    return null;
  }

  // Check if this is a terminal node (leaf with no children)
  isTerminal() {
    return this.nodeType === NodeType.TERMINAL;
  }

  // Get siblings
  getSiblings() {
    if (!this.parent) return [];
    return this.parent.children.filter(c => c !== this);
  }

  // Get index among siblings
  getSiblingIndex() {
    if (!this.parent) return 0;
    return this.parent.children.indexOf(this);
  }

  // Reorder among siblings based on horizontal position
  reorderByPosition() {
    if (!this.parent) return;
    const parent = this.parent;
    parent.children.sort((a, b) => a.x - b.x);
  }

  // Clone this node (and optionally its subtree)
  clone(deep = false) {
    const cloned = new TreeNode(this.label, this.nodeType);
    cloned.movementLabel = this.movementLabel;
    cloned.movementTail = this.movementTail;
    cloned.isStarred = this.isStarred;
    cloned.x = this.x;
    cloned.y = this.y;

    if (deep) {
      for (const child of this.children) {
        cloned.addChild(child.clone(true));
      }
    }

    return cloned;
  }
}

// Static ID counter
TreeNode.nextId = 0;

/**
 * SyntaxTree - manages the entire tree structure
 */
class SyntaxTree {
  constructor() {
    this.roots = [];  // Support multiple root nodes (forest)
    this.listeners = [];
    this.batchMode = false;
    this.pendingEvents = [];
  }

  // Event system
  addEventListener(callback) {
    this.listeners.push(callback);
  }

  removeEventListener(callback) {
    const index = this.listeners.indexOf(callback);
    if (index > -1) {
      this.listeners.splice(index, 1);
    }
  }

  emit(event, data) {
    if (this.batchMode) {
      this.pendingEvents.push({ event, data });
    } else {
      for (const listener of this.listeners) {
        listener(event, data);
      }
    }
  }

  // Batch updates (prevent event spam during complex operations)
  beginBatch() {
    this.batchMode = true;
    this.pendingEvents = [];
  }

  endBatch() {
    this.batchMode = false;
    // Emit a single 'tree-changed' event instead of individual events
    if (this.pendingEvents.length > 0) {
      this.emit('tree-changed', { events: this.pendingEvents });
    }
    this.pendingEvents = [];
  }

  // Add a root node
  addRoot(node) {
    if (node.parent) {
      node.parent.removeChild(node);
    }
    this.roots.push(node);
    this.emit('root-added', { node });
    return node;
  }

  // Remove a root node
  removeRoot(node) {
    const index = this.roots.indexOf(node);
    if (index > -1) {
      this.roots.splice(index, 1);
      this.emit('root-removed', { node });
    }
  }

  // Create a new node and add it as a root
  createNode(label, nodeType = null) {
    const node = new TreeNode(label, nodeType);
    this.addRoot(node);
    return node;
  }

  // Create a terminal node with text
  createTerminal(text) {
    const node = new TreeNode(text, NodeType.TERMINAL);
    return node;
  }

  // Connect two nodes (child becomes child of parent)
  connect(parent, child) {
    // If child is a root, remove it from roots
    const rootIndex = this.roots.indexOf(child);
    if (rootIndex > -1) {
      this.roots.splice(rootIndex, 1);
    }

    parent.addChild(child);
    this.emit('nodes-connected', { parent, child });
  }

  // Disconnect a child from its parent (becomes a root)
  disconnect(child) {
    if (child.parent) {
      const parent = child.parent;
      parent.removeChild(child);
      this.addRoot(child);
      this.emit('nodes-disconnected', { parent, child });
    }
  }

  // Delete a node and all its descendants
  deleteNode(node) {
    // Remove from parent or roots
    if (node.parent) {
      node.parent.removeChild(node);
    } else {
      this.removeRoot(node);
    }

    // Recursively collect all deleted nodes for the event
    const deleted = [node, ...node.getDescendants()];
    this.emit('nodes-deleted', { nodes: deleted });
  }

  // Update a node's label
  updateLabel(node, newLabel) {
    const oldLabel = node.label;
    node.label = newLabel;

    // Update node type if it's not a terminal
    if (node.nodeType !== NodeType.TERMINAL) {
      node.nodeType = getNodeTypeFromLabel(newLabel);
    }

    this.emit('node-updated', { node, oldLabel, newLabel });
  }

  // Find a node by ID
  findById(id) {
    for (const root of this.roots) {
      if (root.id === id) return root;
      for (const desc of root.getDescendants()) {
        if (desc.id === id) return desc;
      }
    }
    return null;
  }

  // Find all nodes matching a predicate
  findAll(predicate) {
    const results = [];
    for (const root of this.roots) {
      if (predicate(root)) results.push(root);
      for (const desc of root.getDescendants()) {
        if (predicate(desc)) results.push(desc);
      }
    }
    return results;
  }

  // Get all nodes in the tree
  getAllNodes() {
    return this.findAll(() => true);
  }

  // Clear the entire tree
  clear() {
    const allNodes = this.getAllNodes();
    this.roots = [];
    this.emit('tree-cleared', { nodes: allNodes });
  }

  // Check if the tree is empty
  isEmpty() {
    return this.roots.length === 0;
  }

  // Find movement pairs (label <-> tail)
  findMovementPairs() {
    const pairs = [];
    const nodes = this.getAllNodes();

    // Find all nodes with movement labels
    const heads = nodes.filter(n => n.movementLabel);
    const tails = nodes.filter(n => n.movementTail);

    for (const tail of tails) {
      const head = heads.find(h => h.movementLabel === tail.movementTail);
      if (head) {
        pairs.push({ head, tail });
      }
    }

    return pairs;
  }
}

// Export for use in other modules
window.NodeType = NodeType;
window.NodeColors = NodeColors;
window.getNodeTypeFromLabel = getNodeTypeFromLabel;
window.getNodeColors = getNodeColors;
window.TreeNode = TreeNode;
window.SyntaxTree = SyntaxTree;
