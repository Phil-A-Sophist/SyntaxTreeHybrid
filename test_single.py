"""
Single diagram test for SyntaxTreeHybrid - quick verification
"""

import os
import sys
import time
import threading
import http.server
import socketserver
from pathlib import Path
from playwright.sync_api import sync_playwright

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

PORT = 8080
APP_DIR = Path(__file__).parent
SAVE_DIR = APP_DIR / "Examples and Saved Images"

def log(msg):
    print(msg, flush=True)

def start_server():
    os.chdir(str(APP_DIR))
    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda *args: None  # Suppress server logs
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        httpd.serve_forever()

def simulate_drag_drop(page, source_selector, target_x, target_y):
    """
    Simulate HTML5 drag and drop using JavaScript.
    This bypasses Playwright's drag_to which doesn't work well with Fabric.js upper canvas.
    """
    page.evaluate("""
        ([sourceSelector, targetX, targetY]) => {
            const source = document.querySelector(sourceSelector);
            const canvas = document.querySelector('.upper-canvas');

            if (!source || !canvas) {
                console.error('Could not find elements:', sourceSelector, source, canvas);
                return false;
            }

            const canvasRect = canvas.getBoundingClientRect();
            const dropX = canvasRect.left + targetX;
            const dropY = canvasRect.top + targetY;

            // Create dataTransfer mock
            const dataTransfer = new DataTransfer();

            // Get data from the source element
            const data = {
                type: source.getAttribute('data-type'),
                value: source.getAttribute('data-abbrev') || source.getAttribute('data-value')
            };
            dataTransfer.setData('text/plain', JSON.stringify(data));

            // Dispatch dragstart on source
            source.dispatchEvent(new DragEvent('dragstart', {
                bubbles: true,
                cancelable: true,
                dataTransfer: dataTransfer
            }));

            // Dispatch dragover on canvas (required for drop to work)
            canvas.dispatchEvent(new DragEvent('dragover', {
                bubbles: true,
                cancelable: true,
                clientX: dropX,
                clientY: dropY,
                dataTransfer: dataTransfer
            }));

            // Dispatch drop on canvas
            canvas.dispatchEvent(new DragEvent('drop', {
                bubbles: true,
                cancelable: true,
                clientX: dropX,
                clientY: dropY,
                dataTransfer: dataTransfer
            }));

            // Dispatch dragend on source
            source.dispatchEvent(new DragEvent('dragend', {
                bubbles: true,
                cancelable: true,
                dataTransfer: dataTransfer
            }));

            return true;
        }
    """, [source_selector, target_x, target_y])

def simulate_word_drop(page, word, target_x, target_y):
    """
    Simulate dragging a word from the word input to the canvas.
    """
    page.evaluate("""
        ([word, targetX, targetY]) => {
            const wordInput = document.getElementById('word-input');
            const wordPreview = document.getElementById('word-preview');
            const canvas = document.querySelector('.upper-canvas');

            if (!wordInput || !wordPreview || !canvas) {
                console.error('Could not find elements');
                return false;
            }

            // Set the word in the input
            wordInput.value = word;
            wordInput.dispatchEvent(new Event('input', { bubbles: true }));

            const canvasRect = canvas.getBoundingClientRect();
            const dropX = canvasRect.left + targetX;
            const dropY = canvasRect.top + targetY;

            // Create dataTransfer mock
            const dataTransfer = new DataTransfer();
            const data = {
                type: 'terminal',
                value: word
            };
            dataTransfer.setData('text/plain', JSON.stringify(data));

            // Dispatch dragstart on preview
            wordPreview.dispatchEvent(new DragEvent('dragstart', {
                bubbles: true,
                cancelable: true,
                dataTransfer: dataTransfer
            }));

            // Dispatch dragover on canvas
            canvas.dispatchEvent(new DragEvent('dragover', {
                bubbles: true,
                cancelable: true,
                clientX: dropX,
                clientY: dropY,
                dataTransfer: dataTransfer
            }));

            // Dispatch drop on canvas
            canvas.dispatchEvent(new DragEvent('drop', {
                bubbles: true,
                cancelable: true,
                clientX: dropX,
                clientY: dropY,
                dataTransfer: dataTransfer
            }));

            // Dispatch dragend on preview
            wordPreview.dispatchEvent(new DragEvent('dragend', {
                bubbles: true,
                cancelable: true,
                dataTransfer: dataTransfer
            }));

            // Clear the input
            wordInput.value = '';
            wordInput.dispatchEvent(new Event('input', { bubbles: true }));

            return true;
        }
    """, [word, target_x, target_y])

def main():
    log("=" * 50)
    log("SyntaxTreeHybrid - Single Test")
    log("=" * 50)

    # Start server
    log("Starting HTTP server...")
    server = threading.Thread(target=start_server, daemon=True)
    server.start()
    time.sleep(1)

    log("Launching browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        log("Navigating to app...")
        page.goto(f"http://localhost:{PORT}/index.html")
        page.wait_for_selector("#diagram-canvas", state="visible")
        time.sleep(1)

        # Test 1: Simple bracket input
        log("\n--- Test 1: Bracket Input ---")
        bracket = "[S [NP [N Phillip]] [VP [V sleeps]]]"
        log(f"Entering: {bracket}")

        bracket_input = page.locator("#bracket-input")
        bracket_input.click()
        bracket_input.fill(bracket)
        time.sleep(1)

        # Check status
        status = page.locator("#bracket-status").inner_text()
        log(f"Status: {status}")

        # Save screenshot
        screenshot_path = SAVE_DIR / "test_01_bracket.png"
        page.locator("#canvas-wrapper").screenshot(path=str(screenshot_path))
        log(f"Saved: {screenshot_path}")

        # Test 2: Clear and try drag-drop
        log("\n--- Test 2: Drag and Drop ---")
        bracket_input.fill("")
        time.sleep(0.5)

        # Drag S (Sentence) to canvas
        log("Dragging S tile to canvas...")
        simulate_drag_drop(page, '.palette-tile[data-abbrev="S"]', 300, 50)
        time.sleep(0.5)

        # Drag NP below and left of S
        log("Dragging NP tile...")
        simulate_drag_drop(page, '.palette-tile[data-abbrev="NP"]', 200, 130)
        time.sleep(0.5)

        # Drag VP below and right of S
        log("Dragging VP tile...")
        simulate_drag_drop(page, '.palette-tile[data-abbrev="VP"]', 400, 130)
        time.sleep(0.5)

        # Drag NOUN under NP
        log("Dragging NOUN tile...")
        simulate_drag_drop(page, '.palette-tile[data-abbrev="NOUN"]', 200, 210)
        time.sleep(0.5)

        # Drag VERB under VP
        log("Dragging VERB tile...")
        simulate_drag_drop(page, '.palette-tile[data-abbrev="VERB"]', 400, 210)
        time.sleep(0.5)

        # Add terminal words
        log("Adding terminal 'Phillip'...")
        simulate_word_drop(page, "Phillip", 200, 290)
        time.sleep(0.5)

        log("Adding terminal 'sleeps'...")
        simulate_word_drop(page, "sleeps", 400, 290)
        time.sleep(0.5)

        # Save screenshot
        screenshot_path = SAVE_DIR / "test_01_dragdrop.png"
        page.locator("#canvas-wrapper").screenshot(path=str(screenshot_path))
        log(f"Saved: {screenshot_path}")

        # Check bracket output
        bracket_output = bracket_input.input_value()
        log(f"Generated bracket notation: {bracket_output}")

        log("\n" + "=" * 50)
        log("Test complete! Check the screenshots.")
        log("=" * 50)

        # Wait a moment then close
        time.sleep(3)
        browser.close()

if __name__ == "__main__":
    main()
