const { test, expect } = require('@playwright/test');
const path = require('path');

test.describe('Word Box Positioning Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Load the local HTML file
    const filePath = path.join(__dirname, '..', 'index.html');
    await page.goto(`file://${filePath}`);

    // Wait for the canvas to be ready
    await page.waitForSelector('#diagram-canvas');
    await page.waitForTimeout(500); // Give Fabric.js time to initialize
  });

  test('Terminal child should be vertically aligned below POS parent', async ({ page }) => {
    // Get the canvas element
    const canvas = page.locator('#canvas-wrapper');
    const canvasBox = await canvas.boundingBox();

    // Find the NOUN tile in the bottom palette
    const nounTile = page.locator('.palette-tile[data-value="NOUN"]');
    await expect(nounTile).toBeVisible();

    // Get the position of the NOUN tile
    const nounBox = await nounTile.boundingBox();

    // Calculate drop position (center of canvas)
    const dropX = canvasBox.x + canvasBox.width / 2;
    const dropY = canvasBox.y + canvasBox.height / 3;

    // Perform drag and drop
    await nounTile.hover();
    await page.mouse.down();
    await page.mouse.move(dropX, dropY, { steps: 10 });
    await page.mouse.up();

    // Wait for the tiles to be created
    await page.waitForTimeout(500);

    // Get console logs for debugging
    const logs = [];
    page.on('console', msg => logs.push(msg.text()));

    // Execute script to get tile positions from Fabric.js canvas
    const positions = await page.evaluate(() => {
      const cm = window.canvasManager;
      if (!cm) return { error: 'canvasManager not found' };

      const tiles = [];
      cm.nodeToCanvas.forEach((tile, nodeId) => {
        const node = cm.tree.findById(nodeId);
        tiles.push({
          nodeId,
          label: node ? node.label : 'unknown',
          isTerminal: tile.isTerminalTile || false,
          left: tile.left,
          top: tile.top,
          width: tile.width,
          height: tile.height,
          centerX: tile.left + tile.width / 2,
          centerY: tile.top + tile.height / 2
        });
      });

      return { tiles, tileCount: tiles.length };
    });

    console.log('Tile positions:', JSON.stringify(positions, null, 2));

    // We should have 2 tiles: the POS node and its terminal child
    expect(positions.tileCount).toBe(2);

    // Find parent (non-terminal) and child (terminal)
    const parent = positions.tiles.find(t => !t.isTerminal);
    const child = positions.tiles.find(t => t.isTerminal);

    expect(parent).toBeTruthy();
    expect(child).toBeTruthy();

    console.log('Parent:', parent);
    console.log('Child:', child);

    // Calculate center X positions
    const parentCenterX = parent.centerX;
    const childCenterX = child.centerX;

    console.log(`Parent center X: ${parentCenterX}`);
    console.log(`Child center X: ${childCenterX}`);
    console.log(`Difference: ${Math.abs(parentCenterX - childCenterX)}px`);

    // The child's center X should be within 2 pixels of the parent's center X
    const tolerance = 2;
    const xDifference = Math.abs(parentCenterX - childCenterX);

    expect(xDifference).toBeLessThanOrEqual(tolerance);
  });
});
