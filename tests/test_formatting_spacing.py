"""Unit tests for blank-line spacing in the formatting action pipeline."""

from __future__ import annotations

import pytest

from engine import TypingEngine
from formatting_harness import (
    EditorTestDriver,
    block_kinds,
    build_actions_from_elements,
    make_test_engine,
)
from fixtures.test_text_fixture import (
    elements_to_blocks,
    load_expected_blocks,
    load_test_text_elements,
)
from rich_text_formatter import KeyAction, PasteHtmlAction, TypeAction

pytestmark = pytest.mark.integration


class _NoopDriver:
    def attach(self, title=None):
        pass

    def detach(self):
        pass

    def is_playwright_mode(self):
        return True


@pytest.fixture
def engine():
    return make_test_engine(_NoopDriver())  # type: ignore[arg-type]


def test_test_text_block_structure_matches_docx():
    expected = load_expected_blocks()
    actual = elements_to_blocks(load_test_text_elements())
    assert block_kinds(actual) == block_kinds(expected)
    assert block_kinds(actual) == [
        "heading",
        "paragraph",
        "blank",
        "heading",
        "paragraph",
        "blank",
        "table",
        "blank",
        "blank",
        "blank",
        "paragraph",
    ]


def test_elements_to_actions_blank_line_enter_sequence(engine):
    elements = load_test_text_elements()
    actions = build_actions_from_elements(engine, elements, reset=False)
    enters = [a.shortcut for a in actions if isinstance(a, KeyAction) and a.shortcut == "Enter"]

    # Five blank elements, one extra Enter before the second heading, and two
    # structural heading Enters before body paragraphs.
    assert [i for i, a in enumerate(actions) if isinstance(a, KeyAction) and a.shortcut == "Enter"] == [
        2,
        4,
        5,
        8,
        18,
        21,
        22,
        23,
    ]

    assert not any(
        isinstance(a, KeyAction) and a.shortcut.endswith("+0")
        for a in actions[:3]
    )


def test_elements_to_actions_table_followed_by_three_blank_lines(engine):
    elements = load_test_text_elements()
    actions = build_actions_from_elements(engine, elements, reset=False)

    paste_idx = next(i for i, a in enumerate(actions) if isinstance(a, PasteHtmlAction))
    following = actions[paste_idx + 1 :]
    final_type_idx = next(
        i for i, a in enumerate(following) if isinstance(a, TypeAction)
    )
    blank_enters = [
        a
        for a in following[:final_type_idx]
        if isinstance(a, KeyAction) and a.shortcut == "Enter"
    ]
    assert len(blank_enters) == 3


def test_production_path_still_prepends_normal_text_reset():
    engine = TypingEngine(_NoopDriver())
    actions = build_actions_from_elements(engine, load_test_text_elements(), reset=True)
    assert isinstance(actions[0], KeyAction)
    assert actions[0].shortcut == "Control+Alt+0"
