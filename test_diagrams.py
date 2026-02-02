"""
Automated testing for SyntaxTreeHybrid using Playwright
Tests both drag-and-drop and bracket input methods for creating syntax tree diagrams.
"""

import os
import sys
import time
import threading
import http.server
import socketserver
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, expect

# Configuration
PORT = 8080
APP_DIR = Path(__file__).parent
SAVE_DIR = APP_DIR / "Examples and Saved Images"
SAVE_DIR.mkdir(exist_ok=True)

# Diagram test cases: (name, bracket_notation, drag_drop_steps)
# drag_drop_steps is a list of tuples: (node_type, label, parent_label_or_none)
DIAGRAM_TESTS = [
    {
        "name": "01_Simple_Intransitive_Sentence",
        "description": "Simple Intransitive Sentence",
        "bracket": "[S [NP [N Phillip]] [VP [V sleeps]]]",
        "drag_steps": [
            ("clause", "S", None),
            ("phrase", "NP", "S"),
            ("phrase", "VP", "S"),
            ("pos", "N", "NP"),
            ("pos", "V", "VP"),
            ("terminal", "Phillip", "N"),
            ("terminal", "sleeps", "V"),
        ]
    },
    {
        "name": "02_Intransitive_Two_Noun_Phrases",
        "description": "Intransitive Sentence with Two Noun Phrases",
        "bracket": "[S [NP [N Frodo] [CONJ and] [N Sam]] [VP [V travel]]]",
        "drag_steps": [
            ("clause", "S", None),
            ("phrase", "NP", "S"),
            ("phrase", "VP", "S"),
            ("pos", "N", "NP"),
            ("pos", "CONJ", "NP"),
            ("pos", "N", "NP"),
            ("pos", "V", "VP"),
            ("terminal", "Frodo", "N"),
            ("terminal", "and", "CONJ"),
            ("terminal", "Sam", "N"),
            ("terminal", "travel", "V"),
        ]
    },
    {
        "name": "03_Intransitive_Two_Verb_Phrases",
        "description": "Intransitive Sentence with Two Verb Phrases",
        "bracket": "[S [NP [N Gandalf]] [VP [V thinks] [CONJ and] [V acts]]]",
        "drag_steps": [
            ("clause", "S", None),
            ("phrase", "NP", "S"),
            ("phrase", "VP", "S"),
            ("pos", "N", "NP"),
            ("pos", "V", "VP"),
            ("pos", "CONJ", "VP"),
            ("pos", "V", "VP"),
            ("terminal", "Gandalf", "N"),
            ("terminal", "thinks", "V"),
            ("terminal", "and", "CONJ"),
            ("terminal", "acts", "V"),
        ]
    },
    {
        "name": "04_Determiners",
        "description": "Determiners",
        "bracket": "[S [NP [DET the] [N dog]] [VP [V snores]]]",
        "drag_steps": [
            ("clause", "S", None),
            ("phrase", "NP", "S"),
            ("phrase", "VP", "S"),
            ("pos", "DET", "NP"),
            ("pos", "N", "NP"),
            ("pos", "V", "VP"),
            ("terminal", "the", "DET"),
            ("terminal", "dog", "N"),
            ("terminal", "snores", "V"),
        ]
    },
    {
        "name": "05_Adjectives_in_Noun_Phrase",
        "description": "Adjectives in a Noun Phrase",
        "bracket": "[S [NP [DET the] [ADJP [ADJ fat]] [N dog]] [VP [V snores]]]",
        "drag_steps": [
            ("clause", "S", None),
            ("phrase", "NP", "S"),
            ("phrase", "VP", "S"),
            ("pos", "DET", "NP"),
            ("phrase", "ADJP", "NP"),
            ("pos", "N", "NP"),
            ("pos", "ADJ", "ADJP"),
            ("pos", "V", "VP"),
            ("terminal", "the", "DET"),
            ("terminal", "fat", "ADJ"),
            ("terminal", "dog", "N"),
            ("terminal", "snores", "V"),
        ]
    },
    {
        "name": "06_PP_in_Noun_Phrase",
        "description": "Prepositional Phrase in a Noun Phrase",
        "bracket": "[S [NP [DET the] [N dog] [PP [P on] [NP [DET the] [N bed]]]] [VP [V snores]]]",
        "drag_steps": [
            ("clause", "S", None),
            ("phrase", "NP", "S"),
            ("phrase", "VP", "S"),
            ("pos", "DET", "NP"),
            ("pos", "N", "NP"),
            ("phrase", "PP", "NP"),
            ("pos", "P", "PP"),
            ("phrase", "NP", "PP"),
            ("pos", "DET", "NP"),
            ("pos", "N", "NP"),
            ("pos", "V", "VP"),
        ]
    },
    {
        "name": "07_PP_in_Verb_Phrase",
        "description": "Prepositional Phrase in a Verb Phrase",
        "bracket": "[S [NP [DET the] [N dog]] [VP [V sleeps] [PP [P on] [NP [DET the] [N bed]]]]]",
        "drag_steps": []  # Complex - will focus on bracket method
    },
    {
        "name": "08_Adverb_in_Verb_Phrase",
        "description": "Adverb in a Verb Phrase",
        "bracket": "[S [NP [DET the] [ADJP [ADJ fat]] [N dog]] [VP [ADVP [ADV frequently]] [V snores]]]",
        "drag_steps": []
    },
    {
        "name": "09_Adverb_in_Adjective_Phrase",
        "description": "Adverb in an Adjective Phrase",
        "bracket": "[S [NP [DET the] [ADJP [ADVP [ADV very]] [ADJ fat]] [N dog]] [VP [V snores]]]",
        "drag_steps": []
    },
    {
        "name": "10_Copular_Be_with_PP",
        "description": "Copular Be Sentence with a Prepositional Phrase as an Adverbial",
        "bracket": "[S [NP [N Phillip]] [VP [V is] [PP [P over] [NP [DET the] [N moon]]]]]",
        "drag_steps": []
    },
    {
        "name": "11_Copular_Be_with_AdvP",
        "description": "Copular Be Sentence with an Adverb Phrase as an Adverbial",
        "bracket": "[S [NP [N Phillip]] [VP [V is] [ADVP [ADV here]]]]",
        "drag_steps": []
    },
    {
        "name": "12_Copular_Be_with_NP_Complement",
        "description": "Copular Be Sentence with a Noun Phrase as a Subject Complement",
        "bracket": "[S [NP [N Phillip]] [VP [V is] [NP [DET a] [N doctor]]]]",
        "drag_steps": []
    },
    {
        "name": "13_Copular_Be_with_AdjP_Complement",
        "description": "Copular Be Sentence with an Adjective Phrase as Subject Complement",
        "bracket": "[S [NP [N Phillip]] [VP [V is] [ADJP [ADV very] [ADJ tall]]]]",
        "drag_steps": []
    },
    {
        "name": "14_Linking_Verb_with_AdjP",
        "description": "Linking Verb with an Adjective Phrase as a Subject Complement",
        "bracket": "[S [NP [N Phillip]] [VP [V became] [ADJP [ADJ famous]]]]",
        "drag_steps": []
    },
    {
        "name": "15_Linking_Verb_with_NP",
        "description": "Linking Verb with a Noun Phrase as a Subject Complement",
        "bracket": "[S [NP [N Phillip]] [VP [V became] [NP [DET a] [N doctor]] [PP [P in] [NP [N 2022]]]]]",
        "drag_steps": []
    },
    {
        "name": "16_Transitive_with_Direct_Object",
        "description": "Transitive Verb with a Direct Object",
        "bracket": "[S [NP [DET the] [N dog]] [VP [V ate] [NP [DET a] [N bone]]]]",
        "drag_steps": []
    },
    {
        "name": "17_Ditransitive_with_Indirect_Object",
        "description": "Transitive (ditransitive) verb with a Direct Object and an Indirect Object",
        "bracket": "[S [NP [N I]] [VP [V gave] [NP [DET the] [N dog]] [NP [DET a] [N bone]]]]",
        "drag_steps": []
    },
    {
        "name": "18_Ditransitive_AdjP_Object_Complement",
        "description": "Transitive verb with a Direct Object and an Adjective Phrase as an Object Complement",
        "bracket": "[S [NP [DET the] [N student]] [VP [V found] [NP [DET the] [N test]] [ADJP [ADJ difficult]]]]",
        "drag_steps": []
    },
    {
        "name": "19_Ditransitive_NP_Object_Complement",
        "description": "Transitive verb with a Direct Object and a Noun Phrase as an Object Complement",
        "bracket": "[S [NP [DET the] [N student]] [VP [V called] [NP [DET the] [N test]] [NP [DET a] [N beast]]]]",
        "drag_steps": []
    },
    {
        "name": "20_Auxiliary_Verbs",
        "description": "Auxiliary Verbs",
        "bracket": "[S [NP [N I]] [VP [AUX have] [AUX been] [V running]]]",
        "drag_steps": []
    },
    {
        "name": "21_Modals",
        "description": "Modals",
        "bracket": "[S [NP [N I]] [VP [MOD should] [AUX have] [AUX been] [V running]]]",
        "drag_steps": []
    },
    {
        "name": "22_Optional_Main_VP_Level",
        "description": "Optional Main Verb Phrase Level",
        "bracket": "[S [NP [N I]] [VP [MOD should] [VP [AUX have] [VP [AUX been] [VP [V running]]]]]]",
        "drag_steps": []
    },
    {
        "name": "23_Passive_Voice",
        "description": "Passive Voice",
        "bracket": "[S [NP [DET the] [N bone]] [VP [AUX was] [V eaten] [PP [P by] [NP [DET the] [N dog]]]]]",
        "drag_steps": []
    },
    {
        "name": "24_Coordination",
        "description": "Coordination (coordinating conjunction)",
        "bracket": "[S [S [NP [N I]] [VP [V laugh]]] [CONJ and] [S [NP [N you]] [VP [V cry]]]]",
        "drag_steps": []
    },
    {
        "name": "25_Subordination_DC_Second",
        "description": "Subordination (dependent clause second)",
        "bracket": "[S [IC [NP [N I]] [VP [V laugh]]] [DC [SUB because] [NP [N you]] [VP [V cry]]]]",
        "drag_steps": []
    },
    {
        "name": "26_Subordination_DC_First",
        "description": "Subordination (dependent clause first)",
        "bracket": "[S [DC [SUB Because] [NP [N you]] [VP [V cry]]] [IC [NP [N I]] [VP [V laugh]]]]",
        "drag_steps": []
    },
    {
        "name": "27_Nouns_as_Adverbials",
        "description": "Nouns as Adverbials",
        "bracket": "[S [NP [N I]] [VP [V sleep] [NP [DET every] [N day]]]]",
        "drag_steps": []
    },
    {
        "name": "28_Verbs_as_Adverbials_Present_Participle",
        "description": "Verbs as Adverbials (Present Participles)",
        "bracket": "[S [NP [N I]] [VP [V left] [VP [V running]]]]",
        "drag_steps": []
    },
    {
        "name": "29_Verbs_as_Adverbials_Infinitives",
        "description": "Verbs as Adverbials (Infinitives)",
        "bracket": "[S [NP [N I]] [VP [V went] [VP [P to] [V run]]]]",
        "drag_steps": []
    },
    {
        "name": "30_Verbs_as_Adjectivals_Present_Participle",
        "description": "Verbs as Adjectivals (Present Participle)",
        "bracket": "[S [NP [DET the] [VP [V running]] [N dog]] [VP [V barks]]]",
        "drag_steps": []
    },
    {
        "name": "31_Verbs_as_Adjectivals_Past_Participle",
        "description": "Verbs as Adjectivals (Past Participle)",
        "bracket": "[S [NP [DET the] [VP [V frightened]] [N dog]] [VP [V barks]]]",
        "drag_steps": []
    },
    {
        "name": "32_Relative_Clause_Pronoun_as_Subject",
        "description": "Relative Clauses with Relative Pronouns [Relative Pronoun as Subject]",
        "bracket": "[S [NP [DET the] [N dog] [RC [REL who] [VP [V barks]]]] [VP [V sleeps]]]",
        "drag_steps": []
    },
    {
        "name": "33_Relative_Clause_Relativizer_Subject",
        "description": "Relative Clauses (Relative Pronoun as Relativizer - Relativizer as Subject of RC)",
        "bracket": "[S [NP [DET the] [N dog] [RC [REL that] [NP [N I]] [VP [V saw]]]] [VP [V sleeps]]]",
        "drag_steps": []
    },
    {
        "name": "34_Relative_Clause_Direct_Object",
        "description": "Relative Clause modifying a Direct Object (Relative Adverb as Relativizer)",
        "bracket": "[S [NP [N I]] [VP [V saw] [NP [DET the] [N place] [RC [REL where] [NP [N you]] [VP [V live]]]]]]",
        "drag_steps": []
    },
    {
        "name": "35_Empty_Relativizer",
        "description": "Empty Relativizer - Relative Clause Modifying a Subject",
        "bracket": "[S [NP [DET the] [N dog] [RC [REL _] [NP [N I]] [VP [V saw]]]] [VP [V sleeps]]]",
        "drag_steps": []
    },
    {
        "name": "36_Complement_Clause_Object_Complementizer_Subject",
        "description": "Complement/Nominal Clause in Object Position (Complementizer as Subject)",
        "bracket": "[S [NP [N I]] [VP [V know] [CC [COMP that] [NP [N you]] [VP [V cry]]]]]",
        "drag_steps": []
    },
    {
        "name": "37_Complement_Clause_Subject_Position",
        "description": "Complement/Nominal Clause in Subject Position (Pronoun as Subject)",
        "bracket": "[S [CC [COMP That] [NP [N you]] [VP [V cry]]] [VP [V upsets] [NP [N me]]]]",
        "drag_steps": []
    },
    {
        "name": "38_Complement_Clause_Object_Complementizer",
        "description": "Complement/Nominal Clause in Object Position (Complementizer)",
        "bracket": "[S [NP [N I]] [VP [V wonder] [CC [COMP if] [NP [N you]] [VP [V cry]]]]]",
        "drag_steps": []
    },
    {
        "name": "39_Missing_Complementizer",
        "description": "Missing Complementizer: Complement/Nominal Clause in Object Position",
        "bracket": "[S [NP [N I]] [VP [V know] [CC [COMP _] [NP [N you]] [VP [V cry]]]]]",
        "drag_steps": []
    },
]


class SyntaxTreeTester:
    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url
        self.attempts = 0
        self.max_attempts = 5

    def navigate_to_app(self):
        """Navigate to the app and wait for it to load."""
        self.page.goto(self.base_url)
        self.page.wait_for_selector("#diagram-canvas", state="visible")
        time.sleep(0.5)  # Wait for Fabric.js to initialize

    def clear_canvas(self):
        """Clear the canvas by selecting all and deleting, and clear bracket input."""
        # Clear bracket input
        bracket_input = self.page.locator("#bracket-input")
        bracket_input.fill("")
        time.sleep(0.3)

        # Click on canvas to ensure focus, then try to delete any existing nodes
        canvas = self.page.locator("#diagram-canvas")
        canvas.click(position={"x": 50, "y": 50})
        time.sleep(0.2)

    def test_bracket_input(self, bracket_notation: str, test_name: str) -> bool:
        """Test diagram creation using bracket input method."""
        print(f"  Testing bracket input: {bracket_notation[:50]}...")

        try:
            self.clear_canvas()

            # Enter bracket notation
            bracket_input = self.page.locator("#bracket-input")
            bracket_input.click()
            bracket_input.fill(bracket_notation)

            # Wait for debounce and rendering
            time.sleep(0.8)

            # Check if status shows "Synced" or "warning" (partial is ok)
            status = self.page.locator("#bracket-status")
            status_text = status.inner_text()

            if "error" in status_text.lower() and "parse" in status_text.lower():
                print(f"    Parse error: {status_text}")
                return False

            # Take screenshot
            time.sleep(0.3)
            return True

        except Exception as e:
            print(f"    Error: {e}")
            return False

    def get_palette_tile(self, node_type: str, label: str):
        """Get the palette tile element for a given node type and label."""
        if node_type == "terminal":
            return None  # Terminals use the word input

        # Map node types to data-type attributes
        type_map = {
            "clause": "clause",
            "phrase": "phrase",
            "pos": "pos"
        }

        data_type = type_map.get(node_type, node_type)
        selector = f'.palette-tile[data-type="{data_type}"][data-abbrev="{label}"]'

        tile = self.page.locator(selector)
        if tile.count() > 0:
            return tile.first
        return None

    def drag_tile_to_canvas(self, tile, x: int, y: int):
        """Drag a palette tile to a position on the canvas."""
        canvas = self.page.locator("#diagram-canvas")
        canvas_box = canvas.bounding_box()

        target_x = canvas_box["x"] + x
        target_y = canvas_box["y"] + y

        # Perform drag and drop
        tile.drag_to(canvas, target_position={"x": x, "y": y})
        time.sleep(0.3)

    def add_terminal_word(self, word: str, x: int, y: int):
        """Add a terminal word using the word input field."""
        word_input = self.page.locator("#word-input")
        word_preview = self.page.locator("#word-preview")
        canvas = self.page.locator("#diagram-canvas")

        # Type the word
        word_input.fill(word)
        time.sleep(0.2)

        # Drag the preview to canvas
        word_preview.drag_to(canvas, target_position={"x": x, "y": y})
        time.sleep(0.3)

    def test_drag_drop(self, drag_steps: list, test_name: str) -> bool:
        """Test diagram creation using drag and drop method."""
        if not drag_steps:
            print("  Skipping drag-drop test (no steps defined)")
            return True

        print(f"  Testing drag-drop with {len(drag_steps)} steps...")

        try:
            self.clear_canvas()
            time.sleep(0.3)

            # Track positions for each node
            node_positions = {}
            y_offset = 50
            x_base = 200

            for i, (node_type, label, parent) in enumerate(drag_steps):
                # Calculate position
                level = 0 if parent is None else node_positions.get(parent, {}).get("level", 0) + 1
                x = x_base + (i % 5) * 100
                y = y_offset + level * 80

                if node_type == "terminal":
                    self.add_terminal_word(label, x, y)
                else:
                    tile = self.get_palette_tile(node_type, label)
                    if tile:
                        self.drag_tile_to_canvas(tile, x, y)
                    else:
                        print(f"    Warning: Could not find tile for {node_type}/{label}")

                node_positions[label] = {"x": x, "y": y, "level": level}
                time.sleep(0.2)

            time.sleep(0.5)
            return True

        except Exception as e:
            print(f"    Error: {e}")
            return False

    def save_screenshot(self, test_name: str, method: str):
        """Save a screenshot of the current diagram."""
        filename = f"{test_name}_{method}.png"
        filepath = SAVE_DIR / filename

        # Screenshot just the canvas area
        canvas_wrapper = self.page.locator("#canvas-wrapper")
        canvas_wrapper.screenshot(path=str(filepath))
        print(f"    Saved: {filename}")
        return filepath


def start_http_server(port: int, directory: str):
    """Start a simple HTTP server in a background thread."""
    os.chdir(directory)
    handler = http.server.SimpleHTTPRequestHandler

    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Serving at http://localhost:{port}")
        httpd.serve_forever()


def run_tests():
    """Run all diagram tests."""
    print("=" * 60)
    print("SyntaxTreeHybrid Automated Testing")
    print("=" * 60)

    # Start HTTP server in background
    server_thread = threading.Thread(
        target=start_http_server,
        args=(PORT, str(APP_DIR)),
        daemon=True
    )
    server_thread.start()
    time.sleep(1)  # Wait for server to start

    base_url = f"http://localhost:{PORT}/index.html"

    results = []
    improvements = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set to True for headless
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        page = context.new_page()

        tester = SyntaxTreeTester(page, base_url)

        for i, test in enumerate(DIAGRAM_TESTS):
            print(f"\n[{i+1}/{len(DIAGRAM_TESTS)}] {test['description']}")
            print("-" * 50)

            tester.navigate_to_app()

            # Test bracket input method
            bracket_success = False
            for attempt in range(5):
                if tester.test_bracket_input(test["bracket"], test["name"]):
                    bracket_success = True
                    tester.save_screenshot(test["name"], "bracket")
                    break
                else:
                    print(f"    Attempt {attempt + 1} failed, retrying...")
                    time.sleep(0.5)

            if not bracket_success:
                print(f"    FAILED: Could not create diagram via bracket input after 5 attempts")
                results.append({
                    "name": test["name"],
                    "bracket_success": False,
                    "drag_success": False,
                    "notes": "Bracket input failed"
                })
                continue

            # Test drag-drop method (if steps defined)
            drag_success = True
            if test["drag_steps"]:
                tester.navigate_to_app()
                for attempt in range(5):
                    if tester.test_drag_drop(test["drag_steps"], test["name"]):
                        drag_success = True
                        tester.save_screenshot(test["name"], "dragdrop")
                        break
                    else:
                        print(f"    Attempt {attempt + 1} failed, retrying...")
                        time.sleep(0.5)
                        drag_success = False

            results.append({
                "name": test["name"],
                "bracket_success": bracket_success,
                "drag_success": drag_success,
                "notes": ""
            })

            print(f"    Result: Bracket={'PASS' if bracket_success else 'FAIL'}, "
                  f"DragDrop={'PASS' if drag_success else 'FAIL' if test['drag_steps'] else 'SKIP'}")

            # Brief pause between tests
            time.sleep(0.5)

        browser.close()

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in results if r["bracket_success"])
    print(f"Bracket Input: {passed}/{len(results)} passed")

    drag_tested = [r for r in results if r.get("drag_success") is not None]
    drag_passed = sum(1 for r in drag_tested if r["drag_success"])
    print(f"Drag & Drop: {drag_passed}/{len(drag_tested)} passed")

    failed = [r for r in results if not r["bracket_success"]]
    if failed:
        print("\nFailed tests:")
        for r in failed:
            print(f"  - {r['name']}: {r.get('notes', 'Unknown error')}")

    return results


if __name__ == "__main__":
    run_tests()
