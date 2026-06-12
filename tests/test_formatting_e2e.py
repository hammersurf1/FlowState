"""End-to-end rich formatting tests using Test_Text.docx and a local editor.

Opens tests/fixtures/gdocs_editor.html via Playwright, runs the FlowState
formatting action pipeline, and verifies that output text and inline formatting
match the original Test_Text.docx content exactly.
"""

from __future__ import annotations

import pytest

from formatting_harness import run_formatting_test
from fixtures.test_text_fixture import (
    docx_plain_text,
    load_expected_blocks,
    load_expected_plain_text,
    load_test_text_elements,
    load_test_text_via_html_clipboard,
)

pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def expected_plain():
    return load_expected_plain_text()


@pytest.fixture(scope="session")
def expected_blocks():
    return load_expected_blocks()


@pytest.fixture(scope="session")
def docx_elements():
    return load_test_text_elements()


@pytest.fixture(scope="session")
def html_clipboard_elements():
    return load_test_text_via_html_clipboard()


def test_docx_fixture_matches_golden_plain():
    """Runtime docx read must match committed golden plain text."""
    assert docx_plain_text() == load_expected_plain_text()


def test_html_clipboard_elements_match_docx_elements(docx_elements, html_clipboard_elements):
    """Both input paths must parse Test_Text.docx into the same structure."""
    assert [el.kind for el in docx_elements] == [el.kind for el in html_clipboard_elements]


def test_docx_elements_preserve_plain_text(docx_elements):
    """Parsed DocElements must contain every character from Test_Text.docx."""
    parts: list[str] = []
    for el in docx_elements:
        if el.kind == "heading":
            parts.append("".join(r.text for r in el.runs))
        elif el.kind == "paragraph":
            parts.append("".join(r.text for r in el.runs))
        elif el.kind == "blank":
            parts.append("")
        elif el.kind == "table":
            row_texts = []
            for row in el.rows:
                row_texts.append(
                    "\t".join("".join(r.text for r in cell.runs) for cell in row.cells)
                )
            parts.append("\n".join(row_texts))
    assert "\n".join(parts) == load_expected_plain_text()


def test_formatting_from_docx_elements(
    formatting_editor, docx_elements, expected_plain, expected_blocks
):
    """Run _elements_to_actions against the local editor; text and formatting must match."""
    result = run_formatting_test(
        formatting_editor,
        docx_elements,
        expected_plain=expected_plain,
        expected_blocks=expected_blocks,
    )
    assert result.passed, "\n".join(result.plain_errors + result.format_errors)


def test_formatting_from_html_clipboard_path(
    formatting_editor, html_clipboard_elements, expected_plain, expected_blocks
):
    """HTML clipboard parse path (Google Docs style) must also reproduce Test_Text.docx."""
    result = run_formatting_test(
        formatting_editor,
        html_clipboard_elements,
        expected_plain=expected_plain,
        expected_blocks=expected_blocks,
    )
    assert result.passed, "\n".join(result.plain_errors + result.format_errors)
