"""Ground-truth fixture loader for tests/Test_Text.docx.

All formatting tests must source copied text exclusively from Test_Text.docx.
"""

from __future__ import annotations

import json
from pathlib import Path

from clipboard_reader import (
    DocElement,
    StyledRun,
    TableCell,
    TableRow,
    parse_clipboard_html,
)
from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

FIXTURES_DIR = Path(__file__).parent
TEST_TEXT_DOCX = FIXTURES_DIR.parent / "Test_Text.docx"
EXPECTED_PLAIN_PATH = FIXTURES_DIR / "test_text_expected_plain.txt"
EXPECTED_BLOCKS_PATH = FIXTURES_DIR / "test_text_expected_blocks.json"


def _run_from_docx(run) -> StyledRun:
    bold = bool(run.bold) if run.bold is not None else False
    italic = bool(run.italic) if run.italic is not None else False
    underline = False
    r_pr = run._element.find(qn("w:rPr"))
    if r_pr is not None:
        u_el = r_pr.find(qn("w:u"))
        if u_el is not None and u_el.get(qn("w:val"), "single") not in (
            "none",
            "0",
            "false",
        ):
            underline = True
    return StyledRun(
        text=run.text,
        bold=bold,
        italic=italic,
        underline=underline,
    )


def _paragraph_to_element(p: Paragraph) -> DocElement | None:
    style = p.style.name if p.style else "Normal"
    runs = [_run_from_docx(r) for r in p.runs if r.text]
    if not p.text.strip():
        return DocElement(kind="blank")
    if style.startswith("Heading"):
        try:
            level = int(style.split()[-1])
        except ValueError:
            level = 1
        return DocElement(kind="heading", level=level, runs=runs)
    return DocElement(kind="paragraph", runs=runs)


def _table_to_element(table: Table) -> DocElement:
    rows: list[TableRow] = []
    for row_idx, row in enumerate(table.rows):
        cells: list[TableCell] = []
        for cell in row.cells:
            runs: list[StyledRun] = []
            for para in cell.paragraphs:
                for run in para.runs:
                    if run.text:
                        runs.append(_run_from_docx(run))
            cells.append(TableCell(runs=runs))
        rows.append(TableRow(cells=cells, is_header=row_idx == 0))
    return DocElement(kind="table", rows=rows)


def load_test_text_elements() -> list[DocElement]:
    """Parse Test_Text.docx into clipboard_reader DocElement objects."""
    doc = Document(TEST_TEXT_DOCX)
    elements: list[DocElement] = []
    for child in doc.element.body:
        tag = child.tag.split("}")[-1]
        if tag == "p":
            el = _paragraph_to_element(Paragraph(child, doc))
            if el is not None:
                elements.append(el)
        elif tag == "tbl":
            elements.append(_table_to_element(Table(child, doc)))
    return elements


def load_expected_plain_text() -> str:
    return EXPECTED_PLAIN_PATH.read_text(encoding="utf-8")


def load_expected_blocks() -> list[dict]:
    return json.loads(EXPECTED_BLOCKS_PATH.read_text(encoding="utf-8"))


def docx_plain_text() -> str:
    """Recompute plain text directly from Test_Text.docx (runtime check)."""
    return blocks_to_plain_text(elements_to_blocks(load_test_text_elements()))


def elements_to_blocks(elements: list[DocElement]) -> list[dict]:
    """Serialize DocElements to the block dict shape used by test fixtures."""
    blocks: list[dict] = []
    for el in elements:
        if el.kind == "heading":
            blocks.append(
                {
                    "kind": "heading",
                    "level": el.level,
                    "runs": [
                        {
                            "text": r.text,
                            "bold": r.bold,
                            "italic": r.italic,
                            "underline": r.underline,
                        }
                        for r in el.runs
                    ],
                    "rows": [],
                }
            )
        elif el.kind == "paragraph":
            blocks.append(
                {
                    "kind": "paragraph",
                    "level": 0,
                    "runs": [
                        {
                            "text": r.text,
                            "bold": r.bold,
                            "italic": r.italic,
                            "underline": r.underline,
                        }
                        for r in el.runs
                    ],
                    "rows": [],
                }
            )
        elif el.kind == "blank":
            blocks.append({"kind": "blank", "level": 0, "runs": [], "rows": []})
        elif el.kind == "table":
            rows = []
            for row in el.rows:
                cells = []
                for cell in row.cells:
                    cells.append(
                        {
                            "runs": [
                                {
                                    "text": r.text,
                                    "bold": r.bold,
                                    "italic": r.italic,
                                    "underline": r.underline,
                                }
                                for r in cell.runs
                            ]
                        }
                    )
                rows.append({"is_header": row.is_header, "cells": cells})
            blocks.append({"kind": "table", "level": 0, "runs": [], "rows": rows})
    return blocks


def blocks_to_plain_text(blocks: list[dict]) -> str:
    """Join block content the same way the test editor exports plain text."""
    parts: list[str] = []
    for block in blocks:
        kind = block.get("kind")
        if kind == "blank":
            parts.append("")
        elif kind == "heading":
            parts.append("".join(r["text"] for r in block.get("runs", [])))
        elif kind == "paragraph":
            parts.append("".join(r["text"] for r in block.get("runs", [])))
        elif kind == "table":
            row_texts = []
            for row in block.get("rows", []):
                row_texts.append(
                    "\t".join(
                        "".join(r["text"] for r in cell.get("runs", []))
                        for cell in row.get("cells", [])
                    )
                )
            parts.append("\n".join(row_texts))
    return "\n".join(parts)


def regenerate_expected_fixtures() -> None:
    """Rebuild golden files from Test_Text.docx."""
    elements = load_test_text_elements()
    blocks = elements_to_blocks(elements)
    plain = blocks_to_plain_text(blocks)
    EXPECTED_PLAIN_PATH.write_text(plain, encoding="utf-8")
    EXPECTED_BLOCKS_PATH.write_text(
        json.dumps(blocks, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def docx_to_gdocs_html() -> str:
    """Convert Test_Text.docx to Google Docs-style clipboard HTML."""
    elements = load_test_text_elements()
    parts: list[str] = ['<b style="font-weight:normal" id="docs-internal-guid-test">']

    def _runs_html(runs: list[StyledRun]) -> str:
        chunks: list[str] = []
        for run in runs:
            if not run.text:
                continue
            text = (
                run.text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            styles: list[str] = []
            if run.bold:
                styles.append("font-weight:700")
            if run.italic:
                styles.append("font-style:italic")
            if run.underline:
                styles.append("text-decoration:underline")
            if styles:
                chunks.append(f'<span style="{";".join(styles)}">{text}</span>')
            else:
                chunks.append(f"<span>{text}</span>")
        return "".join(chunks)

    for el in elements:
        if el.kind == "heading":
            parts.append(f"<h{el.level}>{_runs_html(el.runs)}</h{el.level}>")
        elif el.kind == "paragraph":
            parts.append(f"<p>{_runs_html(el.runs)}</p>")
        elif el.kind == "blank":
            parts.append("<p></p>")
        elif el.kind == "table":
            parts.append("<table><tbody>")
            for row in el.rows:
                parts.append("<tr>")
                for cell in row.cells:
                    tag = "th" if row.is_header else "td"
                    parts.append(f"<{tag}>{_runs_html(cell.runs)}</{tag}>")
                parts.append("</tr>")
            parts.append("</tbody></table>")
    parts.append("</b>")
    return "".join(parts)


def load_test_text_via_html_clipboard() -> list[DocElement]:
    """Simulate copying Test_Text.docx via Google Docs HTML clipboard."""
    return parse_clipboard_html(docx_to_gdocs_html())
