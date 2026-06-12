"""Playwright harness for running FlowState rich formatting against a local editor."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from engine import TypingEngine
from rich_text_formatter import KeyAction, PasteHtmlAction, TypeAction

EDITOR_HTML = Path(__file__).parent / "fixtures" / "gdocs_editor.html"

# Minimum delays and disabled realism — used for all formatting test runs.
FAST_TEST_SETTINGS: dict[str, int] = {
    "UserMeanDelay": 0,
    "UserVariance": 0,
    "TypoChance": 0,
    "TypoDelay": 0,
    "RevisionChance": 0,
    "SentencePauseMs": 0,
    "ParagraphPauseMs": 0,
    "BrainstormFrequency": 0,
    "EmojiPauseMs": 0,
    "CompositionPauseMinMs": 0,
    "CompositionPauseMaxMs": 0,
    "ParagraphPlanningMinMs": 0,
    "ParagraphPlanningMaxMs": 0,
    "CompositionSensitivity": 0,
    "RetrospectiveLookbackChars": 0,
    "EnableTypos": 0,
    "EnableRevisions": 0,
    "EnableBrainstormPauses": 0,
    "EnableRichText": 1,
    "EnableSemanticSpeed": 0,
    "EnableClausePauses": 0,
    "EnableChunkBurst": 0,
    "EnableSmartRevisions": 0,
    "EnableEntityCare": 0,
    "EnableFingerPenalty": 0,
    "EnableFluencyStates": 0,
    "EnableNumberSymbolCare": 0,
    "EnableCapsRunRealism": 0,
    "EnableFrequencyTypos": 0,
    "EnableDeferredCorrections": 0,
    "EnableCompositionPauses": 0,
}


@dataclass
class FormattingTestResult:
    passed: bool
    plain_errors: list[str] = field(default_factory=list)
    format_errors: list[str] = field(default_factory=list)


class EditorTestDriver:
    """Minimal Playwright driver that targets the local formatting test editor."""

    def __init__(self, page):
        self.page = page

    def attach(self, window_title=None):
        pass

    def detach(self):
        pass

    def focus_page(self):
        self.page.bring_to_front()

    def focus_editor(self):
        self.page.evaluate("window.__flowstateEditor.focus()")

    def detect_layout(self):
        return "QWERTY"

    def get_clipboard(self):
        return ""

    def is_playwright_mode(self):
        return True

    def send_char(self, char, dwell_time_seconds=0.0):
        self.page.keyboard.insert_text(char)

    def send_backspace(self):
        self.page.keyboard.press("Backspace")

    def send_key(self, shortcut):
        self.page.keyboard.press(shortcut)

    def send_enter(self):
        self.page.keyboard.press("Enter")

    def send_shift_enter(self):
        self.page.keyboard.press("Shift+Enter")

    def send_tab(self):
        self.page.keyboard.press("Tab")

    def surgical_paste(self, text):
        self.insert_styled_text(text, {"bold": False, "italic": False, "underline": False})

    def insert_styled_text(self, text: str, style: dict) -> None:
        self.page.evaluate(
            """({ text, style }) => window.__flowstateEditor.insertStyledText(text, style)""",
            {"text": text, "style": style},
        )

    def paste_html(self, html):
        self.page.evaluate(
            """(html) => {
                const dt = new DataTransfer();
                const wrapped = '<html><body><!--StartFragment-->' + html + '<!--EndFragment--></body></html>';
                dt.setData('text/html', wrapped);
                const event = new ClipboardEvent('paste', {
                    clipboardData: dt,
                    bubbles: true,
                    cancelable: true,
                });
                document.getElementById('editor').dispatchEvent(event);
            }""",
            html,
        )
    def inject_html(self, html):
        self.paste_html(html)

    def clear_editor(self):
        self.page.evaluate("window.__flowstateEditor.clear()")

    def reload_editor(self):
        """Reload the editor page for a clean DOM between tests."""
        self.page.goto(EDITOR_HTML.resolve().as_uri())
        self.page.wait_for_function("window.__flowstateEditor !== undefined")

    def get_plain_text(self) -> str:
        return self.page.evaluate("window.__flowstateEditor.getPlainText()")

    def get_formatted_blocks(self) -> list[dict]:
        return self.page.evaluate("window.__flowstateEditor.getFormattedBlocks()")


def apply_fast_test_settings(engine: TypingEngine) -> None:
    """Apply minimum timing and disable realism features for fast test runs."""
    for key, value in FAST_TEST_SETTINGS.items():
        engine.settings[key] = value
    engine._sleep = lambda _duration: None  # noqa: SLF001 — test-only bypass


def make_test_engine(driver: EditorTestDriver) -> TypingEngine:
    """TypingEngine configured for deterministic, fast formatting tests."""
    engine = TypingEngine(driver)
    apply_fast_test_settings(engine)
    engine.is_running = True
    return engine


def execute_formatting_actions(driver: EditorTestDriver, actions: list) -> None:
    """Execute formatting actions deterministically in the local editor."""
    driver.focus_editor()
    inline = {"bold": False, "italic": False, "underline": False}

    for action in actions:
        if isinstance(action, PasteHtmlAction):
            driver.paste_html(action.html)
            continue
        if isinstance(action, KeyAction):
            shortcut = action.shortcut
            if shortcut.endswith("+b"):
                inline["bold"] = not inline["bold"]
                continue
            if shortcut.endswith("+i"):
                inline["italic"] = not inline["italic"]
                continue
            if shortcut.endswith("+u"):
                inline["underline"] = not inline["underline"]
                continue
            if shortcut == "\n":
                shortcut = "Enter"
            driver.send_key(shortcut)
            continue
        if isinstance(action, TypeAction):
            driver.insert_styled_text(action.text, inline)


def run_formatting_actions(
    engine: TypingEngine,
    driver: EditorTestDriver,
    actions: list,
) -> None:
    """Execute formatting actions without countdown or clipboard reads."""
    driver.clear_editor()
    execute_formatting_actions(driver, actions)


def build_actions_from_elements(
    engine: TypingEngine,
    elements: list,
    *,
    reset: bool = False,
) -> list:
    """Build formatting actions from parsed elements.

    Production typing prepends a Normal Text reset. Tests skip it because an
    empty editor does not need a style reset and the reset creates a spurious
    leading blank line in the test editor.
    """
    actions = engine._elements_to_actions(elements)
    if reset:
        mod = engine._formatter._mod
        actions = [KeyAction(f"{mod}+Alt+0")] + actions
    return actions


def block_kinds(blocks: list[dict]) -> list[str]:
    return [block.get("kind", "") for block in blocks]


def compare_block_structure(actual: list[dict], expected: list[dict]) -> list[str]:
    """Verify block order and kinds, including blank lines."""
    errors: list[str] = []
    actual_kinds = block_kinds(actual)
    expected_kinds = block_kinds(expected)
    if actual_kinds != expected_kinds:
        errors.append(
            f"Block structure mismatch: got {actual_kinds} expected {expected_kinds}"
        )
    if len(actual) != len(expected):
        errors.append(f"Block count mismatch: got {len(actual)} expected {len(expected)}")
    return errors


def normalize_runs(runs: list[dict]) -> list[dict]:
    out: list[dict] = []
    for run in runs:
        text = run.get("text", "")
        if not text:
            continue
        out.append(
            {
                "text": text,
                "bold": bool(run.get("bold")),
                "italic": bool(run.get("italic")),
                "underline": bool(run.get("underline")),
            }
        )
    return out


def normalize_blocks(blocks: list[dict]) -> list[dict]:
    """Drop empty structural blocks and normalize run formatting flags."""
    normalized: list[dict] = []
    for block in blocks:
        kind = block.get("kind")
        if kind == "blank":
            normalized.append({"kind": "blank", "level": 0, "runs": [], "rows": []})
            continue
        if kind == "heading":
            runs = normalize_runs(block.get("runs", []))
            if not any(r["text"].strip() for r in runs):
                continue
            normalized.append(
                {"kind": "heading", "level": block.get("level", 1), "runs": runs, "rows": []}
            )
            continue
        if kind == "paragraph":
            runs = normalize_runs(block.get("runs", []))
            if not any(r["text"].strip() for r in runs):
                continue
            normalized.append({"kind": "paragraph", "level": 0, "runs": runs, "rows": []})
            continue
        if kind == "list_item":
            runs = normalize_runs(block.get("runs", []))
            normalized.append(
                {
                    "kind": "list_item",
                    "level": 0,
                    "list_type": block.get("list_type", "ul"),
                    "runs": runs,
                    "rows": [],
                }
            )
            continue
        if kind == "table":
            rows = []
            for row in block.get("rows", []):
                cells = []
                for cell in row.get("cells", []):
                    cells.append({"runs": normalize_runs(cell.get("runs", []))})
                rows.append({"is_header": bool(row.get("is_header")), "cells": cells})
            normalized.append({"kind": "table", "level": 0, "runs": [], "rows": rows})
            continue
        if kind == "hr":
            normalized.append({"kind": "hr", "level": 0, "runs": [], "rows": []})
    return normalized


def compare_plain_text(actual: str, expected: str) -> list[str]:
    errors: list[str] = []
    if actual != expected:
        errors.append(
            f"Plain text mismatch (len {len(actual)} vs {len(expected)} expected)"
        )
        # Find first differing character for debugging
        for i, (a, e) in enumerate(zip(actual, expected)):
            if a != e:
                errors.append(
                    f"First diff at index {i}: got {a!r} expected {e!r}"
                )
                break
        if len(actual) != len(expected):
            errors.append(f"Length delta: {len(actual) - len(expected):+d} characters")
    return errors


def compare_formatted_blocks(actual: list[dict], expected: list[dict]) -> list[str]:
    errors: list[str] = []
    errors.extend(compare_block_structure(actual, expected))
    actual_n = normalize_blocks(actual)
    expected_n = normalize_blocks(expected)

    for idx, (act, exp) in enumerate(zip(actual_n, expected_n)):
        if act.get("kind") != exp.get("kind"):
            errors.append(
                f"Block {idx}: kind {act.get('kind')!r} != {exp.get('kind')!r}"
            )
            continue
        if act.get("kind") == "heading" and act.get("level") != exp.get("level"):
            errors.append(
                f"Block {idx}: heading level {act.get('level')} != {exp.get('level')}"
            )
        if act.get("kind") == "table":
            act_rows = act.get("rows", [])
            exp_rows = exp.get("rows", [])
            if len(act_rows) != len(exp_rows):
                errors.append(
                    f"Block {idx}: table rows {len(act_rows)} != {len(exp_rows)}"
                )
                continue
            for ridx, (arow, erow) in enumerate(zip(act_rows, exp_rows)):
                for cidx, (acell, ecell) in enumerate(
                    zip(arow.get("cells", []), erow.get("cells", []))
                ):
                    if normalize_runs(acell.get("runs", [])) != normalize_runs(
                        ecell.get("runs", [])
                    ):
                        errors.append(
                            f"Block {idx} table cell [{ridx},{cidx}] formatting mismatch"
                        )
            continue

        act_runs = normalize_runs(act.get("runs", []))
        exp_runs = normalize_runs(exp.get("runs", []))
        if act.get("kind") == "heading":
            # Heading tags carry visual weight; compare text only.
            act_text = "".join(r["text"] for r in act_runs)
            exp_text = "".join(r["text"] for r in exp_runs)
            if act_text != exp_text:
                errors.append(f"Block {idx}: heading text mismatch")
            continue
        if act_runs != exp_runs:
            errors.append(f"Block {idx}: inline formatting mismatch")
            act_text = "".join(r["text"] for r in act_runs)
            exp_text = "".join(r["text"] for r in exp_runs)
            if act_text != exp_text:
                errors.append(f"  text: {act_text[:80]!r} != {exp_text[:80]!r}")
    return errors


def open_editor_page(playwright, headless: bool = True):
    browser = playwright.chromium.launch(headless=headless)
    page = browser.new_page()
    page.goto(EDITOR_HTML.resolve().as_uri())
    page.wait_for_function("window.__flowstateEditor !== undefined")
    return browser, page


def run_formatting_test(
    driver: EditorTestDriver,
    elements: list,
    *,
    expected_plain: str,
    expected_blocks: list[dict],
) -> FormattingTestResult:
    """Run the formatting pipeline and compare against Test_Text.docx ground truth."""
    from fixtures.test_text_fixture import blocks_to_plain_text

    engine = make_test_engine(driver)
    actions = build_actions_from_elements(engine, elements, reset=False)
    run_formatting_actions(engine, driver, actions)

    actual_blocks = driver.get_formatted_blocks()
    actual_plain = driver.get_plain_text()
    expected_plain_from_blocks = blocks_to_plain_text(expected_blocks)
    if expected_plain != expected_plain_from_blocks:
        raise ValueError("Committed golden plain text does not match golden blocks")

    plain_errors = compare_plain_text(actual_plain, expected_plain)
    if not plain_errors:
        plain_errors = compare_plain_text(
            blocks_to_plain_text(actual_blocks),
            expected_plain_from_blocks,
        )
    format_errors = compare_formatted_blocks(actual_blocks, expected_blocks)
    return FormattingTestResult(
        passed=not plain_errors and not format_errors,
        plain_errors=plain_errors,
        format_errors=format_errors,
    )
