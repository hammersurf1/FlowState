#!/usr/bin/env python3
"""Run the Test_Text.docx formatting test suite without manual steps.

Usage:
    uv run format-test              # headless, exits with status code
    uv run format-test --headed     # visible browser, still non-interactive
    uv run python scripts/run_formatting_test_editor.py [--headed]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from playwright.sync_api import sync_playwright

from formatting_harness import (
    EditorTestDriver,
    open_editor_page,
    run_formatting_test,
)
from fixtures.test_text_fixture import (
    load_expected_blocks,
    load_expected_plain_text,
    load_test_text_elements,
    load_test_text_via_html_clipboard,
)


def _run(headless: bool, hold: bool = False, hold_seconds: int = 0) -> int:
    expected_plain = load_expected_plain_text()
    expected_blocks = load_expected_blocks()
    failures: list[str] = []

    with sync_playwright() as playwright:
        browser, page = open_editor_page(playwright, headless=headless)
        driver = EditorTestDriver(page)

        for label, elements in (
            ("docx elements", load_test_text_elements()),
            ("html clipboard", load_test_text_via_html_clipboard()),
        ):
            result = run_formatting_test(
                driver,
                elements,
                expected_plain=expected_plain,
                expected_blocks=expected_blocks,
            )
            if result.passed:
                print(f"{label}: PASS")
            else:
                print(f"{label}: FAIL")
                failures.extend(result.plain_errors)
                failures.extend(result.format_errors)

        if not headless and (hold or hold_seconds > 0):
            if hold:
                print("\nBrowser open for inspection. Press Enter to close.")
                try:
                    input()
                except EOFError:
                    wait = hold_seconds or 120
                    print(f"No interactive terminal — keeping browser open for {wait}s.")
                    time.sleep(wait)
            else:
                print(f"\nBrowser open for inspection ({hold_seconds}s).")
                time.sleep(hold_seconds)
        browser.close()

    if failures:
        print("\nFailures:")
        for err in failures:
            print(f"  - {err}")
        return 1

    print("\nAll formatting checks passed (text identical to Test_Text.docx).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run FlowState formatting tests.")
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the browser window.",
    )
    parser.add_argument(
        "--hold",
        action="store_true",
        help="Keep the browser open until you press Enter (requires --headed).",
    )
    parser.add_argument(
        "--hold-seconds",
        type=int,
        default=0,
        metavar="N",
        help="Keep the browser open for N seconds after the test (requires --headed).",
    )
    args = parser.parse_args(argv)
    return _run(
        headless=not args.headed,
        hold=args.hold,
        hold_seconds=args.hold_seconds,
    )


if __name__ == "__main__":
    raise SystemExit(main())
