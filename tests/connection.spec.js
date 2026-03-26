const { test, expect } = require('@playwright/test');
const path = require('path');

/**
 * Connection logic test suite.
 * Tests auto-connect, disconnect guards, insertion between nodes,
 * and parent selection accuracy using bracket notation fixtures.
 */

const FIXTURES = {
  simple: '[S [NP [DET The] [N dog]] [VP [V barked]]]',
  complex: '[S [NP [DET The] [ADJP [ADJ young]] [N artist] [PP [PREP from] [NP [N Paris]]]] [VP [V painted] [NP [ADJP [ADJ beautiful]] [N landscapes]]]]',
  ditransitive: '[VP [V gave] [NP [PRON her]] [NP [DET a] [N present]]]',
  coordination: '[S [IC [NP [N dogs]] [VP [V bark]]] [CONJ and] [IC [NP [N cats]] [VP [V meow]]]]',
  deepNesting: '[S [NP [DET the] [N student]] [VP [V read] [NP [DET the] [N book] [PP [PREP about] [NP [DET the] [N history] [PP [PREP of] [NP [N Rome]]]]]]]]',
};

test.describe('Connection Logic Tests', () => {
  test.beforeEach(async ({ page }) => {
    const filePath = path.join(__dirname, '..', 'index.html');
    await page.goto(`file://${filePath}`);
    await page.waitForSelector('#diagram-canvas');
    await page.waitForTimeout(500);
  });

  /**
   * Helper: load a bracket notation fixture into the app.
   */
  async function loadFixture(page, bracket) {
    await page.evaluate((text) => {
      document.getElementById('bracket-input').value = text;
      window.syncEngine.forceTextToCanvas();
    }, bracket);
    await page.waitForTimeout(600); // Wait for relayout
  }

  /**
   * Helper: get all tile positions and tree structure from the canvas.
   */
  async function getTreeState(page) {
    return page.evaluate(() => {
      const cm = window.canvasManager;
      const tree = window.tree;
      const tiles = [];
      cm.nodeToCanvas.forEach((tile, nodeId) => {
        const node = tree.findById(nodeId);
        const center = tile.getCenterPoint();
        tiles.push({
          nodeId,
          label: node ? node.label : 'unknown',
          isTerminal: node ? node.isTerminal() : false,
          parentId: node && node.parent ? node.parent.id : null,
          childCount: node ? node.children.length : 0,
          centerX: center.x,
          centerY: center.y,
          left: tile.left,
          top: tile.top,
        });
      });
      return {
        tiles,
        rootCount: tree.roots.length,
        totalNodes: tree.getAllNodes().length,
      };
    });
  }

  // === FALSE DISCONNECT TESTS ===

  test('Small drag (< 50px) should NOT disconnect a connected node', async ({ page }) => {
    await loadFixture(page, FIXTURES.simple);

    const state = await getTreeState(page);
    const npTile = state.tiles.find(t => t.label === 'NP');
    expect(npTile).toBeTruthy();
    expect(npTile.parentId).not.toBeNull(); // NP is connected to S

    // Simulate a small drag (30px right) via evaluate
    const result = await page.evaluate((npId) => {
      const cm = window.canvasManager;
      const tree = window.tree;
      const node = tree.findById(npId);
      const tile = cm.nodeToCanvas.get(npId);

      // Simulate finalizeAutoConnection with small drag distance
      cm.finalizeAutoConnection(node, tile, 30, false);

      return {
        stillConnected: node.parent !== null,
        parentLabel: node.parent ? node.parent.label : null,
      };
    }, npTile.nodeId);

    expect(result.stillConnected).toBe(true);
    expect(result.parentLabel).toBe('S');
  });

  test('Shift+drag should allow disconnect even for small drags', async ({ page }) => {
    await loadFixture(page, FIXTURES.simple);

    const state = await getTreeState(page);
    const detTile = state.tiles.find(t => t.label === 'The');

    // Move DET very far away and use shift
    const result = await page.evaluate((detId) => {
      const cm = window.canvasManager;
      const tree = window.tree;
      const node = tree.findById(detId);
      const tile = cm.nodeToCanvas.get(detId);

      // Move tile far away from parent
      tile.set({ left: tile.left + 500, top: tile.top + 500 });
      tile.setCoords();

      cm.finalizeAutoConnection(node, tile, 30, true); // shift held, small drag

      return {
        disconnected: node.parent === null,
      };
    }, detTile.nodeId);

    expect(result.disconnected).toBe(true);
  });

  // === CORRECT PARENT SELECTION TESTS ===

  test('Orphan node near a parent should auto-connect to nearest valid parent', async ({ page }) => {
    await loadFixture(page, FIXTURES.simple);

    // Create an orphan node and position it near VP
    const result = await page.evaluate(() => {
      const cm = window.canvasManager;
      const tree = window.tree;

      // Get VP position
      const vpNode = tree.getAllNodes().find(n => n.label === 'VP');
      const vpTile = cm.nodeToCanvas.get(vpNode.id);
      const vpCenter = vpTile.getCenterPoint();

      // Create a new orphan ADVP
      const advp = tree.createNode('ADVP', 'phrase');
      const advpTile = cm.createTileForNode(advp);

      // Position it below and slightly right of VP
      advpTile.set({
        left: vpCenter.x + 30,
        top: vpCenter.y + cm.LEVEL_HEIGHT - 10,
      });
      advpTile.setCoords();

      cm.finalizeAutoConnection(advp, advpTile, 200, false);

      return {
        connected: advp.parent !== null,
        parentLabel: advp.parent ? advp.parent.label : null,
      };
    });

    expect(result.connected).toBe(true);
    expect(result.parentLabel).toBe('VP');
  });

  test('Current parent gets affinity bonus (stability)', async ({ page }) => {
    await loadFixture(page, FIXTURES.simple);

    // Move NP slightly — it should stay connected to S, not jump to a different parent
    const result = await page.evaluate(() => {
      const cm = window.canvasManager;
      const tree = window.tree;

      const npNode = tree.getAllNodes().find(n => n.label === 'NP');
      const npTile = cm.nodeToCanvas.get(npNode.id);

      // Move NP 60px to the right (medium drag, within connection range of S)
      npTile.set({ left: npTile.left + 60 });
      npTile.setCoords();

      cm.finalizeAutoConnection(npNode, npTile, 60, false);

      return {
        parentLabel: npNode.parent ? npNode.parent.label : null,
      };
    });

    expect(result.parentLabel).toBe('S');
  });

  // === LINE INSERTION TESTS ===

  test('Node dragged near a connection line should trigger insertion', async ({ page }) => {
    await loadFixture(page, FIXTURES.simple);

    const result = await page.evaluate(() => {
      const cm = window.canvasManager;
      const tree = window.tree;

      // Get S and NP positions
      const sNode = tree.getAllNodes().find(n => n.label === 'S');
      const npNode = tree.getAllNodes().find(n => n.label === 'NP');
      const sTile = cm.nodeToCanvas.get(sNode.id);
      const npTile = cm.nodeToCanvas.get(npNode.id);
      const sCenter = sTile.getCenterPoint();
      const npCenter = npTile.getCenterPoint();

      // Create a new CP node
      const cp = tree.createNode('CP', 'clause');
      const cpTile = cm.createTileForNode(cp);

      // Position it on the S→NP connection line (midpoint)
      const midX = (sCenter.x + npCenter.x) / 2;
      const midY = (sCenter.y + npCenter.y) / 2;
      cpTile.set({ left: midX - 36, top: midY - 16 });
      cpTile.setCoords();

      // Check if insertion is detected
      const insertion = cm.findNearestConnectionLine(cp, cpTile);

      return {
        insertionDetected: insertion !== null,
        parentLabel: insertion ? insertion.parent.label : null,
        childLabel: insertion ? insertion.child.label : null,
      };
    });

    expect(result.insertionDetected).toBe(true);
    expect(result.parentLabel).toBe('S');
    expect(result.childLabel).toBe('NP');
  });

  // === SIBLING INSERTION ZONE TESTS ===

  test('Node between two siblings horizontally should detect sibling insertion zone', async ({ page }) => {
    await loadFixture(page, FIXTURES.ditransitive);

    const result = await page.evaluate(() => {
      const cm = window.canvasManager;
      const tree = window.tree;

      // VP has 3 children: V, NP(her), NP(a present)
      const vpNode = tree.getAllNodes().find(n => n.label === 'VP');
      const children = vpNode.children;

      // Get positions of first and second NP children
      const child1Tile = cm.nodeToCanvas.get(children[1].id); // NP (her)
      const child2Tile = cm.nodeToCanvas.get(children[2].id); // NP (a present)
      const c1Center = child1Tile.getCenterPoint();
      const c2Center = child2Tile.getCenterPoint();

      // Create a new PP and position it between the two NPs
      const pp = tree.createNode('PP', 'phrase');
      const ppTile = cm.createTileForNode(pp);
      const midX = (c1Center.x + c2Center.x) / 2;
      ppTile.set({ left: midX - 36, top: c1Center.y - 16 });
      ppTile.setCoords();

      const zone = cm.findSiblingInsertionZone(pp, ppTile);

      return {
        zoneDetected: zone !== null,
        parentLabel: zone ? zone.parent.label : null,
        leftChildLabel: zone ? zone.leftChild.label : null,
        rightChildLabel: zone ? zone.rightChild.label : null,
      };
    });

    expect(result.zoneDetected).toBe(true);
    expect(result.parentLabel).toBe('VP');
  });

  // === PRESENTATION MODE TESTS ===

  test('Presentation mode toggles font sizes and layout', async ({ page }) => {
    await loadFixture(page, FIXTURES.simple);

    const before = await page.evaluate(() => {
      const cm = window.canvasManager;
      return {
        unitWidth: cm.UNIT_WIDTH,
        levelHeight: cm.LEVEL_HEIGHT,
        presentationMode: cm.presentationMode,
      };
    });

    expect(before.presentationMode).toBe(false);
    expect(before.unitWidth).toBe(155);

    // Toggle presentation mode
    await page.evaluate(() => {
      window.canvasManager.togglePresentationMode();
    });
    await page.waitForTimeout(300);

    const after = await page.evaluate(() => {
      const cm = window.canvasManager;
      return {
        unitWidth: cm.UNIT_WIDTH,
        levelHeight: cm.LEVEL_HEIGHT,
        presentationMode: cm.presentationMode,
      };
    });

    expect(after.presentationMode).toBe(true);
    expect(after.unitWidth).toBe(115);
    expect(after.levelHeight).toBe(85);
  });

  // === TREE INTEGRITY TESTS ===

  test('Complex tree loads correctly from bracket notation', async ({ page }) => {
    await loadFixture(page, FIXTURES.complex);

    const state = await getTreeState(page);

    // "The young artist from Paris painted beautiful landscapes" = 15 nodes total
    expect(state.rootCount).toBe(1);
    expect(state.totalNodes).toBeGreaterThanOrEqual(14);

    // All non-root nodes should be connected
    const disconnected = state.tiles.filter(t => t.parentId === null && t.label !== 'S');
    expect(disconnected.length).toBe(0);
  });

  test('Deep nesting renders without overlapping tiles', async ({ page }) => {
    await loadFixture(page, FIXTURES.deepNesting);

    const state = await getTreeState(page);

    // Check no two tiles at the same level overlap horizontally
    const byLevel = {};
    for (const tile of state.tiles) {
      const level = Math.round(tile.centerY / 85); // approximate level grouping
      if (!byLevel[level]) byLevel[level] = [];
      byLevel[level].push(tile);
    }

    for (const [level, tiles] of Object.entries(byLevel)) {
      tiles.sort((a, b) => a.centerX - b.centerX);
      for (let i = 1; i < tiles.length; i++) {
        const gap = tiles[i].centerX - tiles[i - 1].centerX;
        // Tiles should have at least 30px between centers
        expect(gap).toBeGreaterThan(30);
      }
    }
  });
});
