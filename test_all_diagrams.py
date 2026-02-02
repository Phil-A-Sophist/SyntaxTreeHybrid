"""
Full automated testing for SyntaxTreeHybrid - All diagram patterns
Tests bracket input method and documents results.
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

# All diagram test cases based on the reference document
DIAGRAM_TESTS = [
    {
        "name": "01_Simple_Intransitive_Sentence",
        "description": "Simple Intransitive Sentence",
        "bracket": "[S [NP [N Phillip]] [VP [V sleeps]]]",
    },
    {
        "name": "02_Intransitive_Two_Noun_Phrases",
        "description": "Intransitive Sentence with Two Noun Phrases",
        "bracket": "[S [NP [N Frodo] [CONJ and] [N Sam]] [VP [V travel]]]",
    },
    {
        "name": "03_Intransitive_Two_Verb_Phrases",
        "description": "Intransitive Sentence with Two Verb Phrases",
        "bracket": "[S [NP [N Gandalf]] [VP [V thinks] [CONJ and] [V acts]]]",
    },
    {
        "name": "04_Determiners",
        "description": "Determiners",
        "bracket": "[S [NP [DET the] [N dog]] [VP [V snores]]]",
    },
    {
        "name": "05_Adjectives_in_Noun_Phrase",
        "description": "Adjectives in a Noun Phrase",
        "bracket": "[S [NP [DET the] [ADJP [ADJ fat]] [N dog]] [VP [V snores]]]",
    },
    {
        "name": "06_PP_in_Noun_Phrase",
        "description": "Prepositional Phrase in a Noun Phrase",
        "bracket": "[S [NP [DET the] [N dog] [PP [PREP on] [NP [DET the] [N bed]]]] [VP [V snores]]]",
    },
    {
        "name": "07_PP_in_Verb_Phrase",
        "description": "Prepositional Phrase in a Verb Phrase",
        "bracket": "[S [NP [DET the] [N dog]] [VP [V sleeps] [PP [PREP on] [NP [DET the] [N bed]]]]]",
    },
    {
        "name": "08_Adverb_in_Verb_Phrase",
        "description": "Adverb in a Verb Phrase",
        "bracket": "[S [NP [DET the] [ADJP [ADJ fat]] [N dog]] [VP [ADVP [ADV frequently]] [V snores]]]",
    },
    {
        "name": "09_Adverb_in_Adjective_Phrase",
        "description": "Adverb in an Adjective Phrase",
        "bracket": "[S [NP [DET the] [ADJP [ADVP [ADV very]] [ADJ fat]] [N dog]] [VP [V snores]]]",
    },
    {
        "name": "10_Copular_Be_with_PP",
        "description": "Copular Be Sentence with a Prepositional Phrase as an Adverbial",
        "bracket": "[S [NP [N Phillip]] [VP [V is] [PP [PREP over] [NP [DET the] [N moon]]]]]",
    },
    {
        "name": "11_Copular_Be_with_AdvP",
        "description": "Copular Be Sentence with an Adverb Phrase as an Adverbial",
        "bracket": "[S [NP [N Phillip]] [VP [V is] [ADVP [ADV here]]]]",
    },
    {
        "name": "12_Copular_Be_with_NP_Complement",
        "description": "Copular Be Sentence with a Noun Phrase as a Subject Complement",
        "bracket": "[S [NP [N Phillip]] [VP [V is] [NP [DET a] [N doctor]]]]",
    },
    {
        "name": "13_Copular_Be_with_AdjP_Complement",
        "description": "Copular Be Sentence with an Adjective Phrase as Subject Complement",
        "bracket": "[S [NP [N Phillip]] [VP [V is] [ADJP [ADV very] [ADJ tall]]]]",
    },
    {
        "name": "14_Linking_Verb_with_AdjP",
        "description": "Linking Verb with an Adjective Phrase as a Subject Complement",
        "bracket": "[S [NP [N Phillip]] [VP [V became] [ADJP [ADJ famous]]]]",
    },
    {
        "name": "15_Linking_Verb_with_NP",
        "description": "Linking Verb with a Noun Phrase as a Subject Complement",
        "bracket": "[S [NP [N Phillip]] [VP [V became] [NP [DET a] [N doctor]] [PP [PREP in] [NP [N 2022]]]]]",
    },
    {
        "name": "16_Transitive_with_Direct_Object",
        "description": "Transitive Verb with a Direct Object",
        "bracket": "[S [NP [DET the] [N dog]] [VP [V ate] [NP [DET a] [N bone]]]]",
    },
    {
        "name": "17_Ditransitive_with_Indirect_Object",
        "description": "Transitive (ditransitive) verb with Direct Object and Indirect Object",
        "bracket": "[S [NP [N I]] [VP [V gave] [NP [DET the] [N dog]] [NP [DET a] [N bone]]]]",
    },
    {
        "name": "18_Ditransitive_AdjP_Object_Complement",
        "description": "Transitive verb with Direct Object and Adjective Phrase as Object Complement",
        "bracket": "[S [NP [DET the] [N student]] [VP [V found] [NP [DET the] [N test]] [ADJP [ADJ difficult]]]]",
    },
    {
        "name": "19_Ditransitive_NP_Object_Complement",
        "description": "Transitive verb with Direct Object and Noun Phrase as Object Complement",
        "bracket": "[S [NP [DET the] [N student]] [VP [V called] [NP [DET the] [N test]] [NP [DET a] [N beast]]]]",
    },
    {
        "name": "20_Auxiliary_Verbs",
        "description": "Auxiliary Verbs",
        "bracket": "[S [NP [N I]] [VP [AUX have] [AUX been] [V running]]]",
    },
    {
        "name": "21_Modals",
        "description": "Modals",
        "bracket": "[S [NP [N I]] [VP [MOD should] [AUX have] [AUX been] [V running]]]",
    },
    {
        "name": "22_Optional_Main_VP_Level",
        "description": "Optional Main Verb Phrase Level",
        "bracket": "[S [NP [N I]] [VP [MOD should] [VP [AUX have] [VP [AUX been] [VP [V running]]]]]]",
    },
    {
        "name": "23_Passive_Voice",
        "description": "Passive Voice",
        "bracket": "[S [NP [DET the] [N bone]] [VP [AUX was] [V eaten] [PP [PREP by] [NP [DET the] [N dog]]]]]",
    },
    {
        "name": "24_Coordination",
        "description": "Coordination (coordinating conjunction)",
        "bracket": "[S [S [NP [N I]] [VP [V laugh]]] [CONJ and] [S [NP [N you]] [VP [V cry]]]]",
    },
    {
        "name": "25_Subordination_DC_Second",
        "description": "Subordination (dependent clause second)",
        "bracket": "[S [IC [NP [N I]] [VP [V laugh]]] [DC [SUB because] [NP [N you]] [VP [V cry]]]]",
    },
    {
        "name": "26_Subordination_DC_First",
        "description": "Subordination (dependent clause first)",
        "bracket": "[S [DC [SUB Because] [NP [N you]] [VP [V cry]]] [IC [NP [N I]] [VP [V laugh]]]]",
    },
    {
        "name": "27_Nouns_as_Adverbials",
        "description": "Nouns as Adverbials",
        "bracket": "[S [NP [N I]] [VP [V sleep] [NP [DET every] [N day]]]]",
    },
    {
        "name": "28_Verbs_as_Adverbials_Present_Participle",
        "description": "Verbs as Adverbials (Present Participles)",
        "bracket": "[S [NP [N I]] [VP [V left] [VP [V running]]]]",
    },
    {
        "name": "29_Verbs_as_Adverbials_Infinitives",
        "description": "Verbs as Adverbials (Infinitives)",
        "bracket": "[S [NP [N I]] [VP [V went] [VP [PREP to] [V run]]]]",
    },
    {
        "name": "30_Verbs_as_Adjectivals_Present_Participle",
        "description": "Verbs as Adjectivals (Present Participle)",
        "bracket": "[S [NP [DET the] [VP [V running]] [N dog]] [VP [V barks]]]",
    },
    {
        "name": "31_Verbs_as_Adjectivals_Past_Participle",
        "description": "Verbs as Adjectivals (Past Participle)",
        "bracket": "[S [NP [DET the] [VP [V frightened]] [N dog]] [VP [V barks]]]",
    },
    {
        "name": "32_Relative_Clause_Pronoun_as_Subject",
        "description": "Relative Clauses with Relative Pronouns (Relative Pronoun as Subject)",
        "bracket": "[S [NP [DET the] [N dog] [RC [REL who] [VP [V barks]]]] [VP [V sleeps]]]",
    },
    {
        "name": "33_Relative_Clause_Relativizer_Subject",
        "description": "Relative Clauses (Relative Pronoun as Relativizer - Subject of RC)",
        "bracket": "[S [NP [DET the] [N dog] [RC [REL that] [NP [N I]] [VP [V saw]]]] [VP [V sleeps]]]",
    },
    {
        "name": "34_Relative_Clause_Direct_Object",
        "description": "Relative Clause modifying a Direct Object (Relative Adverb as Relativizer)",
        "bracket": "[S [NP [N I]] [VP [V saw] [NP [DET the] [N place] [RC [REL where] [NP [N you]] [VP [V live]]]]]]",
    },
    {
        "name": "35_Empty_Relativizer",
        "description": "Empty Relativizer - Relative Clause Modifying a Subject",
        "bracket": "[S [NP [DET the] [N dog] [RC [REL _] [NP [N I]] [VP [V saw]]]] [VP [V sleeps]]]",
    },
    {
        "name": "36_Complement_Clause_Object_Comp_Subject",
        "description": "Complement/Nominal Clause in Object Position (Complementizer as Subject)",
        "bracket": "[S [NP [N I]] [VP [V know] [CC [COMP that] [NP [N you]] [VP [V cry]]]]]",
    },
    {
        "name": "37_Complement_Clause_Subject_Position",
        "description": "Complement/Nominal Clause in Subject Position",
        "bracket": "[S [CC [COMP That] [NP [N you]] [VP [V cry]]] [VP [V upsets] [NP [N me]]]]",
    },
    {
        "name": "38_Complement_Clause_Object_Complementizer",
        "description": "Complement/Nominal Clause in Object Position (Complementizer)",
        "bracket": "[S [NP [N I]] [VP [V wonder] [CC [COMP if] [NP [N you]] [VP [V cry]]]]]",
    },
    {
        "name": "39_Missing_Complementizer",
        "description": "Missing Complementizer: Complement/Nominal Clause in Object Position",
        "bracket": "[S [NP [N I]] [VP [V know] [CC [COMP _] [NP [N you]] [VP [V cry]]]]]",
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

def run_tests():
    log("=" * 70)
    log("SyntaxTreeHybrid - Full Diagram Testing")
    log("=" * 70)
    log(f"Testing {len(DIAGRAM_TESTS)} diagram patterns")
    log(f"Saving to: {SAVE_DIR}")
    log("")

    # Start server
    server = threading.Thread(target=start_server, daemon=True)
    server.start()
    time.sleep(1)

    results = []
    improvements = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        for i, test in enumerate(DIAGRAM_TESTS):
            log(f"\n[{i+1:02d}/{len(DIAGRAM_TESTS)}] {test['description']}")
            log("-" * 60)

            # Navigate to app
            page.goto(f"http://localhost:{PORT}/index.html")
            page.wait_for_selector("#diagram-canvas", state="visible")
            time.sleep(0.5)

            # Test bracket input
            bracket_input = page.locator("#bracket-input")
            bracket_input.click()
            bracket_input.fill(test["bracket"])
            time.sleep(0.8)

            # Check status
            status = page.locator("#bracket-status").inner_text()
            success = "error" not in status.lower() or "parse" not in status.lower()

            # Retry logic if needed
            attempts = 1
            while not success and attempts < 5:
                log(f"  Attempt {attempts} failed ({status}), retrying...")
                attempts += 1
                bracket_input.fill("")
                time.sleep(0.3)
                bracket_input.fill(test["bracket"])
                time.sleep(0.8)
                status = page.locator("#bracket-status").inner_text()
                success = "error" not in status.lower()

            if success:
                # Save screenshot
                screenshot_path = SAVE_DIR / f"{test['name']}.png"
                page.locator("#canvas-wrapper").screenshot(path=str(screenshot_path))
                log(f"  Status: {status}")
                log(f"  Saved: {test['name']}.png")
                results.append({"name": test["name"], "success": True, "status": status})

                # Assessment notes
                if "warning" in status.lower():
                    improvements.append(f"{test['name']}: Rendered with warning - {status}")
            else:
                log(f"  FAILED after {attempts} attempts: {status}")
                results.append({"name": test["name"], "success": False, "status": status})
                improvements.append(f"{test['name']}: FAILED - {status}")

            time.sleep(0.3)

        browser.close()

    # Summary
    log("\n" + "=" * 70)
    log("TEST SUMMARY")
    log("=" * 70)

    passed = sum(1 for r in results if r["success"])
    failed = len(results) - passed

    log(f"Passed: {passed}/{len(results)}")
    log(f"Failed: {failed}/{len(results)}")

    if failed > 0:
        log("\nFailed tests:")
        for r in results:
            if not r["success"]:
                log(f"  - {r['name']}: {r['status']}")

    if improvements:
        log("\nNotes for improvement:")
        for note in improvements:
            log(f"  - {note}")

    log("\n" + "=" * 70)
    log("Testing complete!")
    log("=" * 70)

    return results

if __name__ == "__main__":
    run_tests()
