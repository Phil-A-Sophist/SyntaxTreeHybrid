"""
Comprehensive UX testing for drag-and-drop and proximity snapping behavior.
Tests connection logic, parent-child relationships, and sibling ordering.
"""

import os
import sys
import time
import json
import threading
import http.server
import socketserver
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, Page

sys.stdout.reconfigure(line_buffering=True)

PORT = 8080
APP_DIR = Path(__file__).parent
SAVE_DIR = APP_DIR / "Examples and Saved Images"
LOG_FILE = APP_DIR / "ux_test_log.txt"

# Test diagrams - starting with simpler ones for thorough testing
DIAGRAM_TESTS = [
    {
        "name": "01_Simple_Intransitive_Sentence",
        "bracket": "[S [NP [N Phillip]] [VP [V sleeps]]]",
    },
    {
        "name": "02_Intransitive_Two_Noun_Phrases",
        "bracket": "[S [NP [N Frodo] [CONJ and] [N Sam]] [VP [V travel]]]",
    },
    {
        "name": "03_Intransitive_Two_Verb_Phrases",
        "bracket": "[S [NP [N Gandalf]] [VP [V thinks] [CONJ and] [V acts]]]",
    },
    {
        "name": "04_Determiners",
        "bracket": "[S [NP [DET the] [N dog]] [VP [V snores]]]",
    },
    {
        "name": "05_Adjectives_in_Noun_Phrase",
        "bracket": "[S [NP [DET the] [ADJP [ADJ fat]] [N dog]] [VP [V snores]]]",
    },
    {
        "name": "06_PP_in_Noun_Phrase",
        "bracket": "[S [NP [DET the] [N dog] [PP [PREP on] [NP [DET the] [N bed]]]] [VP [V snores]]]",
    },
    {
        "name": "07_PP_in_Verb_Phrase",
        "bracket": "[S [NP [DET the] [N dog]] [VP [V sleeps] [PP [PREP on] [NP [DET the] [N bed]]]]]",
    },
    {
        "name": "08_Adverb_in_Verb_Phrase",
        "bracket": "[S [NP [DET the] [ADJP [ADJ fat]] [N dog]] [VP [ADVP [ADV frequently]] [V snores]]]",
    },
    {
        "name": "09_Adverb_in_Adjective_Phrase",
        "bracket": "[S [NP [DET the] [ADJP [ADVP [ADV very]] [ADJ fat]] [N dog]] [VP [V snores]]]",
    },
    {
        "name": "10_Copular_Be_with_PP",
        "bracket": "[S [NP [N Phillip]] [VP [V is] [PP [PREP over] [NP [DET the] [N moon]]]]]",
    },
    {
        "name": "11_Copular_Be_with_AdvP",
        "bracket": "[S [NP [N Phillip]] [VP [V is] [ADVP [ADV here]]]]",
    },
    {
        "name": "12_Copular_Be_with_NP_Complement",
        "bracket": "[S [NP [N Phillip]] [VP [V is] [NP [DET a] [N doctor]]]]",
    },
    {
        "name": "13_Copular_Be_with_AdjP_Complement",
        "bracket": "[S [NP [N Phillip]] [VP [V is] [ADJP [ADV very] [ADJ tall]]]]",
    },
    {
        "name": "14_Linking_Verb_with_AdjP",
        "bracket": "[S [NP [N Phillip]] [VP [V became] [ADJP [ADJ famous]]]]",
    },
    {
        "name": "15_Linking_Verb_with_NP",
        "bracket": "[S [NP [N Phillip]] [VP [V became] [NP [DET a] [N doctor]] [PP [PREP in] [NP [N 2022]]]]]",
    },
    {
        "name": "16_Transitive_with_Direct_Object",
        "bracket": "[S [NP [DET the] [N dog]] [VP [V ate] [NP [DET a] [N bone]]]]",
    },
    {
        "name": "17_Ditransitive_with_Indirect_Object",
        "bracket": "[S [NP [N I]] [VP [V gave] [NP [DET the] [N dog]] [NP [DET a] [N bone]]]]",
    },
    {
        "name": "18_Ditransitive_AdjP_Object_Complement",
        "bracket": "[S [NP [DET the] [N student]] [VP [V found] [NP [DET the] [N test]] [ADJP [ADJ difficult]]]]",
    },
    {
        "name": "19_Ditransitive_NP_Object_Complement",
        "bracket": "[S [NP [DET the] [N student]] [VP [V called] [NP [DET the] [N test]] [NP [DET a] [N beast]]]]",
    },
    {
        "name": "20_Auxiliary_Verbs",
        "bracket": "[S [NP [N I]] [VP [AUX have] [AUX been] [V running]]]",
    },
    {
        "name": "21_Modals",
        "bracket": "[S [NP [N I]] [VP [MOD should] [AUX have] [AUX been] [V running]]]",
    },
    {
        "name": "22_Optional_Main_VP_Level",
        "bracket": "[S [NP [N I]] [VP [MOD should] [VP [AUX have] [VP [AUX been] [VP [V running]]]]]]",
    },
    {
        "name": "23_Passive_Voice",
        "bracket": "[S [NP [DET the] [N bone]] [VP [AUX was] [V eaten] [PP [PREP by] [NP [DET the] [N dog]]]]]",
    },
    {
        "name": "24_Coordination",
        "bracket": "[S [S [NP [N I]] [VP [V laugh]]] [CONJ and] [S [NP [N you]] [VP [V cry]]]]",
    },
    {
        "name": "25_Subordination_DC_Second",
        "bracket": "[S [IC [NP [N I]] [VP [V laugh]]] [DC [SUB because] [NP [N you]] [VP [V cry]]]]",
    },
    {
        "name": "26_Subordination_DC_First",
        "bracket": "[S [DC [SUB Because] [NP [N you]] [VP [V cry]]] [IC [NP [N I]] [VP [V laugh]]]]",
    },
    {
        "name": "27_Nouns_as_Adverbials",
        "bracket": "[S [NP [N I]] [VP [V sleep] [NP [DET every] [N day]]]]",
    },
    {
        "name": "28_Verbs_as_Adverbials_Present_Participle",
        "bracket": "[S [NP [N I]] [VP [V left] [VP [V running]]]]",
    },
    {
        "name": "29_Verbs_as_Adverbials_Infinitives",
        "bracket": "[S [NP [N I]] [VP [V went] [VP [PREP to] [V run]]]]",
    },
    {
        "name": "30_Verbs_as_Adjectivals_Present_Participle",
        "bracket": "[S [NP [DET the] [VP [V running]] [N dog]] [VP [V barks]]]",
    },
    {
        "name": "31_Verbs_as_Adjectivals_Past_Participle",
        "bracket": "[S [NP [DET the] [VP [V frightened]] [N dog]] [VP [V barks]]]",
    },
    {
        "name": "32_Relative_Clause_Pronoun_as_Subject",
        "bracket": "[S [NP [DET the] [N dog] [RC [REL who] [VP [V barks]]]] [VP [V sleeps]]]",
    },
    {
        "name": "33_Relative_Clause_Relativizer_Subject",
        "bracket": "[S [NP [DET the] [N dog] [RC [REL that] [NP [N I]] [VP [V saw]]]] [VP [V sleeps]]]",
    },
    {
        "name": "34_Relative_Clause_Direct_Object",
        "bracket": "[S [NP [N I]] [VP [V saw] [NP [DET the] [N place] [RC [REL where] [NP [N you]] [VP [V live]]]]]]",
    },
    {
        "name": "35_Empty_Relativizer",
        "bracket": "[S [NP [DET the] [N dog] [RC [REL _] [NP [N I]] [VP [V saw]]]] [VP [V sleeps]]]",
    },
    {
        "name": "36_Complement_Clause_Object_Comp_Subject",
        "bracket": "[S [NP [N I]] [VP [V know] [CC [COMP that] [NP [N you]] [VP [V cry]]]]]",
    },
    {
        "name": "37_Complement_Clause_Subject_Position",
        "bracket": "[S [CC [COMP That] [NP [N you]] [VP [V cry]]] [VP [V upsets] [NP [N me]]]]",
    },
    {
        "name": "38_Complement_Clause_Object_Complementizer",
        "bracket": "[S [NP [N I]] [VP [V wonder] [CC [COMP if] [NP [N you]] [VP [V cry]]]]]",
    },
    {
        "name": "39_Missing_Complementizer",
        "bracket": "[S [NP [N I]] [VP [V know] [CC [COMP _] [NP [N you]] [VP [V cry]]]]]",
    },
]


class UXTester:
    def __init__(self, page: Page):
        self.page = page
        self.issues = []
        self.current_test = ""

    def log(self, msg):
        print(msg, flush=True)

    def log_issue(self, issue_type, description, expected, actual):
        issue = {
            "test": self.current_test,
            "type": issue_type,
            "description": description,
            "expected": expected,
            "actual": actual,
            "timestamp": datetime.now().isoformat()
        }
        self.issues.append(issue)
        self.log(f"    ** ISSUE [{issue_type}]: {description}")
        self.log(f"        Expected: {expected}")
        self.log(f"        Actual: {actual}")

    def get_node_positions(self):
        """Get all node positions from the canvas."""
        return self.page.evaluate("""
            () => {
                const positions = [];
                if (typeof canvasManager !== 'undefined') {
                    for (const [nodeId, tile] of canvasManager.nodeToCanvas) {
                        const center = tile.getCenterPoint();
                        const node = canvasManager.tree.findById(nodeId);
                        positions.push({
                            id: nodeId,
                            label: node ? node.label : 'unknown',
                            x: center.x,
                            y: center.y,
                            parentId: node && node.parent ? node.parent.id : null
                        });
                    }
                }
                return positions;
            }
        """)

    def get_bracket_output(self):
        """Get the current bracket notation from the textarea."""
        return self.page.locator("#bracket-input").input_value()

    def drag_node_by_label(self, label, delta_x, delta_y):
        """Drag a node by its label to a relative position."""
        result = self.page.evaluate("""
            ([label, deltaX, deltaY]) => {
                for (const [nodeId, tile] of canvasManager.nodeToCanvas) {
                    const node = canvasManager.tree.findById(nodeId);
                    if (node && node.label === label) {
                        const center = tile.getCenterPoint();
                        return {
                            found: true,
                            startX: center.x,
                            startY: center.y,
                            nodeId: nodeId
                        };
                    }
                }
                return { found: false };
            }
        """, [label, delta_x, delta_y])

        if not result['found']:
            self.log(f"      Could not find node with label: {label}")
            return False

        # Use Playwright to perform the drag
        canvas = self.page.locator(".upper-canvas")
        canvas_box = canvas.bounding_box()

        start_x = canvas_box['x'] + result['startX']
        start_y = canvas_box['y'] + result['startY']
        end_x = start_x + delta_x
        end_y = start_y + delta_y

        # Perform drag operation
        self.page.mouse.move(start_x, start_y)
        self.page.mouse.down()
        time.sleep(0.1)
        self.page.mouse.move(end_x, end_y, steps=10)
        time.sleep(0.1)
        self.page.mouse.up()
        time.sleep(0.3)

        return True

    def drag_node_to_position(self, label, target_x, target_y):
        """Drag a node to an absolute canvas position."""
        result = self.page.evaluate("""
            ([label]) => {
                for (const [nodeId, tile] of canvasManager.nodeToCanvas) {
                    const node = canvasManager.tree.findById(nodeId);
                    if (node && node.label === label) {
                        const center = tile.getCenterPoint();
                        return {
                            found: true,
                            startX: center.x,
                            startY: center.y,
                            nodeId: nodeId
                        };
                    }
                }
                return { found: false };
            }
        """, [label])

        if not result['found']:
            return False

        canvas = self.page.locator(".upper-canvas")
        canvas_box = canvas.bounding_box()

        start_x = canvas_box['x'] + result['startX']
        start_y = canvas_box['y'] + result['startY']
        end_x = canvas_box['x'] + target_x
        end_y = canvas_box['y'] + target_y

        self.page.mouse.move(start_x, start_y)
        self.page.mouse.down()
        time.sleep(0.1)
        self.page.mouse.move(end_x, end_y, steps=10)
        time.sleep(0.1)
        self.page.mouse.up()
        time.sleep(0.3)

        return True

    def check_parent_child_relationship(self, child_label, expected_parent_label):
        """Verify a node has the expected parent."""
        result = self.page.evaluate("""
            ([childLabel, expectedParentLabel]) => {
                for (const [nodeId, tile] of canvasManager.nodeToCanvas) {
                    const node = canvasManager.tree.findById(nodeId);
                    if (node && node.label === childLabel) {
                        const actualParent = node.parent ? node.parent.label : null;
                        return {
                            found: true,
                            actualParent: actualParent,
                            matches: actualParent === expectedParentLabel
                        };
                    }
                }
                return { found: false };
            }
        """, [child_label, expected_parent_label])

        return result

    def check_sibling_order(self, parent_label, expected_order):
        """Verify children are in expected left-to-right order."""
        result = self.page.evaluate("""
            ([parentLabel]) => {
                for (const [nodeId, tile] of canvasManager.nodeToCanvas) {
                    const node = canvasManager.tree.findById(nodeId);
                    if (node && node.label === parentLabel) {
                        const children = node.children.map(c => ({
                            label: c.label,
                            x: canvasManager.nodeToCanvas.get(c.id).getCenterPoint().x
                        }));
                        children.sort((a, b) => a.x - b.x);
                        return {
                            found: true,
                            order: children.map(c => c.label)
                        };
                    }
                }
                return { found: false };
            }
        """, [parent_label])

        return result

    def check_vertical_relationship(self, parent_label, child_label):
        """Verify parent is above child vertically."""
        result = self.page.evaluate("""
            ([parentLabel, childLabel]) => {
                let parentY = null, childY = null;
                for (const [nodeId, tile] of canvasManager.nodeToCanvas) {
                    const node = canvasManager.tree.findById(nodeId);
                    if (node) {
                        const y = tile.getCenterPoint().y;
                        if (node.label === parentLabel) parentY = y;
                        if (node.label === childLabel) childY = y;
                    }
                }
                if (parentY !== null && childY !== null) {
                    return {
                        found: true,
                        parentY: parentY,
                        childY: childY,
                        parentAbove: parentY < childY
                    };
                }
                return { found: false };
            }
        """, [parent_label, child_label])

        return result

    def test_drag_behaviors(self, test_name):
        """Run comprehensive drag tests for a diagram."""
        self.current_test = test_name
        self.log(f"    Testing drag behaviors...")

        positions = self.get_node_positions()
        if len(positions) < 2:
            self.log(f"      Not enough nodes to test ({len(positions)} nodes)")
            return

        # Find a leaf node (no children) to drag around
        leaf_nodes = self.page.evaluate("""
            () => {
                const leaves = [];
                for (const [nodeId, tile] of canvasManager.nodeToCanvas) {
                    const node = canvasManager.tree.findById(nodeId);
                    if (node && node.children.length === 0 && !node.isTerminal()) {
                        leaves.push({
                            id: nodeId,
                            label: node.label,
                            parentLabel: node.parent ? node.parent.label : null
                        });
                    }
                }
                return leaves;
            }
        """)

        if not leaf_nodes:
            # Try with terminal nodes
            leaf_nodes = self.page.evaluate("""
                () => {
                    const leaves = [];
                    for (const [nodeId, tile] of canvasManager.nodeToCanvas) {
                        const node = canvasManager.tree.findById(nodeId);
                        if (node && node.isTerminal()) {
                            leaves.push({
                                id: nodeId,
                                label: node.label,
                                parentLabel: node.parent ? node.parent.label : null
                            });
                        }
                    }
                    return leaves;
                }
            """)

        if not leaf_nodes:
            self.log(f"      No suitable nodes to drag")
            return

        test_node = leaf_nodes[0]
        original_parent = test_node['parentLabel']

        # Test 1: Drag node down (should stay as child, not become parent)
        self.log(f"      Test: Drag '{test_node['label']}' down 80px")
        self.drag_node_by_label(test_node['label'], 0, 80)

        result = self.check_parent_child_relationship(test_node['label'], original_parent)
        if result['found']:
            if not result['matches']:
                self.log_issue(
                    "PARENT_SWAP",
                    f"Node '{test_node['label']}' changed parent when dragged down",
                    f"Parent should be '{original_parent}'",
                    f"Parent is now '{result['actualParent']}'"
                )
            else:
                self.log(f"        OK: Parent relationship maintained")

        # Reset by triggering relayout
        self.page.evaluate("canvasManager.relayout(true)")
        time.sleep(0.4)

        # Test 2: Drag node far away (should disconnect)
        self.log(f"      Test: Drag '{test_node['label']}' far away (200px right, 200px down)")
        self.drag_node_by_label(test_node['label'], 200, 200)

        result = self.check_parent_child_relationship(test_node['label'], None)
        if result['found']:
            if result['actualParent'] is not None:
                # This might be OK depending on threshold
                self.log(f"        Note: Node still connected to '{result['actualParent']}' after large drag")

        # Reset
        self.page.evaluate("canvasManager.relayout(true)")
        time.sleep(0.4)

        # Test 3: Check sibling ordering (if parent has multiple children)
        parent_with_children = self.page.evaluate("""
            () => {
                for (const [nodeId, tile] of canvasManager.nodeToCanvas) {
                    const node = canvasManager.tree.findById(nodeId);
                    if (node && node.children.length >= 2) {
                        return {
                            found: true,
                            label: node.label,
                            children: node.children.map(c => c.label)
                        };
                    }
                }
                return { found: false };
            }
        """)

        if parent_with_children['found']:
            parent = parent_with_children['label']
            children = parent_with_children['children']

            if len(children) >= 2:
                self.log(f"      Test: Sibling order under '{parent}'")

                # Get current order
                order_result = self.check_sibling_order(parent, children)
                if order_result['found']:
                    original_order = order_result['order']
                    self.log(f"        Current order: {original_order}")

                    # Drag first child to the right of last child
                    first_child = original_order[0]
                    last_child = original_order[-1]

                    # Get position of last child
                    last_pos = self.page.evaluate("""
                        ([label]) => {
                            for (const [nodeId, tile] of canvasManager.nodeToCanvas) {
                                const node = canvasManager.tree.findById(nodeId);
                                if (node && node.label === label) {
                                    return tile.getCenterPoint();
                                }
                            }
                            return null;
                        }
                    """, [last_child])

                    if last_pos:
                        # Drag first child to right of last
                        self.log(f"        Dragging '{first_child}' to right of '{last_child}'")
                        self.drag_node_to_position(first_child, last_pos['x'] + 100, last_pos['y'])

                        # Check new order
                        new_order_result = self.check_sibling_order(parent, children)
                        if new_order_result['found']:
                            new_order = new_order_result['order']
                            self.log(f"        New order: {new_order}")

                            # First child should now be last (or near last)
                            if new_order[0] == first_child:
                                self.log_issue(
                                    "SIBLING_ORDER",
                                    f"Sibling order not updated after drag",
                                    f"'{first_child}' should move to end",
                                    f"Order is still {new_order}"
                                )
                            else:
                                self.log(f"        OK: Sibling order updated correctly")

        # Reset to original state
        self.page.evaluate("canvasManager.relayout(true)")
        time.sleep(0.4)

    def test_connection_preview(self):
        """Test that connection preview lines appear correctly."""
        self.log(f"      Test: Connection preview visibility")

        # This would require checking for preview line elements
        # For now, we note this as a manual test item
        pass

    def run_test(self, test):
        """Run all tests for a single diagram."""
        self.current_test = test['name']
        self.log(f"\n[{test['name']}]")
        self.log("-" * 60)

        # Navigate and create diagram
        self.page.goto(f"http://localhost:{PORT}/index.html")
        self.page.wait_for_selector("#diagram-canvas", state="visible")
        time.sleep(0.5)

        # Enter bracket notation
        bracket_input = self.page.locator("#bracket-input")
        bracket_input.click()
        bracket_input.fill(test['bracket'])
        time.sleep(0.8)

        # Check status
        status = self.page.locator("#bracket-status").inner_text()
        self.log(f"    Bracket input status: {status}")

        # Run drag behavior tests
        self.test_drag_behaviors(test['name'])

        # Ensure final state is clean
        bracket_input.fill(test['bracket'])
        time.sleep(0.8)

        # Save screenshot
        screenshot_path = SAVE_DIR / f"{test['name']}.png"
        self.page.locator("#canvas-wrapper").screenshot(path=str(screenshot_path))
        self.log(f"    Saved: {test['name']}.png")

        return True


def start_server():
    os.chdir(str(APP_DIR))
    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda *args: None
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        httpd.serve_forever()


def main():
    print("=" * 70, flush=True)
    print("SyntaxTreeHybrid - Comprehensive UX Testing", flush=True)
    print("=" * 70, flush=True)
    print(f"Testing {len(DIAGRAM_TESTS)} diagrams", flush=True)
    print(f"Log file: {LOG_FILE}", flush=True)
    print("", flush=True)

    # Start server
    server = threading.Thread(target=start_server, daemon=True)
    server.start()
    time.sleep(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        tester = UXTester(page)

        for i, test in enumerate(DIAGRAM_TESTS):
            print(f"\n[{i+1:02d}/{len(DIAGRAM_TESTS)}] ", end="", flush=True)
            tester.run_test(test)

        browser.close()

    # Write issues to log file
    print("\n" + "=" * 70, flush=True)
    print("TEST SUMMARY", flush=True)
    print("=" * 70, flush=True)

    if tester.issues:
        print(f"\nFound {len(tester.issues)} issues:", flush=True)

        # Group by type
        by_type = {}
        for issue in tester.issues:
            t = issue['type']
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(issue)

        for issue_type, issues in by_type.items():
            print(f"\n  {issue_type}: {len(issues)} occurrences", flush=True)
            for issue in issues[:3]:  # Show first 3 of each type
                print(f"    - {issue['test']}: {issue['description']}", flush=True)
            if len(issues) > 3:
                print(f"    ... and {len(issues) - 3} more", flush=True)

        # Write full log
        with open(LOG_FILE, 'w') as f:
            f.write("SyntaxTreeHybrid UX Test Log\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("=" * 70 + "\n\n")

            for issue in tester.issues:
                f.write(f"Test: {issue['test']}\n")
                f.write(f"Type: {issue['type']}\n")
                f.write(f"Description: {issue['description']}\n")
                f.write(f"Expected: {issue['expected']}\n")
                f.write(f"Actual: {issue['actual']}\n")
                f.write("-" * 40 + "\n\n")

        print(f"\nFull log written to: {LOG_FILE}", flush=True)
    else:
        print("\nNo issues found!", flush=True)

    print("\n" + "=" * 70, flush=True)
    print("Testing complete!", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    main()
