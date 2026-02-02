"""
Quick test to verify improved spacing
"""

import os
import sys
import time
import threading
import http.server
import socketserver
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(line_buffering=True)

PORT = 8080
APP_DIR = Path(__file__).parent
SAVE_DIR = APP_DIR / "Examples and Saved Images"

# Test cases that benefit from improved spacing
TEST_CASES = [
    {
        "name": "spacing_test_01_coordination",
        "bracket": "[S [S [NP [N I]] [VP [V laugh]]] [CONJ and] [S [NP [N you]] [VP [V cry]]]]",
    },
    {
        "name": "spacing_test_02_complex_pp",
        "bracket": "[S [NP [DET the] [N dog] [PP [PREP on] [NP [DET the] [N bed]]]] [VP [V snores]]]",
    },
    {
        "name": "spacing_test_03_relative_clause",
        "bracket": "[S [NP [DET the] [N dog] [RC [REL that] [NP [N I]] [VP [V saw]]]] [VP [V sleeps]]]",
    },
]

def log(msg):
    print(msg, flush=True)

def start_server():
    os.chdir(str(APP_DIR))
    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda *args: None
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        httpd.serve_forever()

def main():
    log("Testing improved spacing...")

    server = threading.Thread(target=start_server, daemon=True)
    server.start()
    time.sleep(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        for test in TEST_CASES:
            log(f"\nTesting: {test['name']}")

            page.goto(f"http://localhost:{PORT}/index.html")
            page.wait_for_selector("#diagram-canvas", state="visible")
            time.sleep(0.5)

            bracket_input = page.locator("#bracket-input")
            bracket_input.click()
            bracket_input.fill(test["bracket"])
            time.sleep(0.8)

            screenshot_path = SAVE_DIR / f"{test['name']}.png"
            page.locator("#canvas-wrapper").screenshot(path=str(screenshot_path))
            log(f"  Saved: {screenshot_path}")

        time.sleep(2)
        browser.close()

    log("\nSpacing test complete!")

if __name__ == "__main__":
    main()
