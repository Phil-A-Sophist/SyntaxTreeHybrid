"""
Regenerate all syntax tree diagrams for the grammar textbook.
Uses the built-in PNG export function for high-quality output.
"""

import os
import sys
import time
import base64
import threading
import http.server
import socketserver
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(line_buffering=True)

PORT = 8080
APP_DIR = Path(__file__).parent
OUTPUT_DIR = Path(r"C:\Users\irphy\Documents\concise-guide-english-grammar\assets\diagrams\new")
BRACKET_FILE = OUTPUT_DIR / "bracket_notations.txt"

def log(msg):
    print(msg, flush=True)

def parse_bracket_notations(filepath):
    """Parse the bracket_notations.txt file to extract diagram definitions."""
    diagrams = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            # Parse: filename | bracket_notation
            if '|' in line:
                parts = line.split('|', 1)
                if len(parts) == 2:
                    filename = parts[0].strip()
                    bracket = parts[1].strip()
                    diagrams.append({
                        'name': filename,
                        'bracket': bracket
                    })
    return diagrams

def start_server():
    """Start a simple HTTP server to serve the app."""
    os.chdir(str(APP_DIR))
    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda *args: None  # Suppress server logs
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        httpd.serve_forever()

def regenerate_diagrams():
    """Main function to regenerate all diagrams."""
    # Parse bracket notations
    if not BRACKET_FILE.exists():
        log(f"Error: Bracket notations file not found: {BRACKET_FILE}")
        return

    diagrams = parse_bracket_notations(BRACKET_FILE)
    log(f"Found {len(diagrams)} diagrams to generate")
    log(f"Output directory: {OUTPUT_DIR}")
    log("")

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Start server
    log("Starting HTTP server...")
    server = threading.Thread(target=start_server, daemon=True)
    server.start()
    time.sleep(1)

    results = {'success': 0, 'failed': 0, 'errors': []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        for i, diagram in enumerate(diagrams):
            name = diagram['name']
            bracket = diagram['bracket']

            log(f"\n[{i+1:02d}/{len(diagrams)}] {name}")
            log(f"  Bracket: {bracket[:60]}{'...' if len(bracket) > 60 else ''}")

            try:
                # Navigate to app
                page.goto(f"http://localhost:{PORT}/index.html")
                page.wait_for_selector("#diagram-canvas", state="visible")
                time.sleep(0.5)

                # Enter bracket notation
                bracket_input = page.locator("#bracket-input")
                bracket_input.click()
                bracket_input.fill(bracket)
                time.sleep(0.8)

                # Check status
                status = page.locator("#bracket-status").inner_text()

                if "error" in status.lower():
                    log(f"  ERROR: {status}")
                    results['failed'] += 1
                    results['errors'].append(f"{name}: {status}")
                    continue

                # Fit to view for consistent output
                page.click("#zoom-fit")
                time.sleep(0.3)

                # Export using built-in PNG function (high quality with 4x multiplier)
                data_url = page.evaluate("""
                    async () => {
                        return await window.canvasManager.exportPNG(4);
                    }
                """)

                # Save the PNG file
                if data_url and data_url.startswith('data:image/png;base64,'):
                    # Extract base64 data
                    base64_data = data_url.split(',', 1)[1]
                    png_data = base64.b64decode(base64_data)

                    output_path = OUTPUT_DIR / f"{name}.png"
                    with open(output_path, 'wb') as f:
                        f.write(png_data)

                    log(f"  Saved: {name}.png ({len(png_data):,} bytes)")
                    results['success'] += 1
                else:
                    log(f"  ERROR: Failed to get PNG data")
                    results['failed'] += 1
                    results['errors'].append(f"{name}: No PNG data returned")

            except Exception as e:
                log(f"  EXCEPTION: {str(e)}")
                results['failed'] += 1
                results['errors'].append(f"{name}: {str(e)}")

            time.sleep(0.2)

        browser.close()

    # Summary
    log("\n" + "=" * 70)
    log("GENERATION SUMMARY")
    log("=" * 70)
    log(f"Successful: {results['success']}/{len(diagrams)}")
    log(f"Failed: {results['failed']}/{len(diagrams)}")

    if results['errors']:
        log("\nErrors:")
        for err in results['errors']:
            log(f"  - {err}")

    log("\n" + "=" * 70)
    log("Done!")
    log("=" * 70)

    return results

if __name__ == "__main__":
    regenerate_diagrams()
