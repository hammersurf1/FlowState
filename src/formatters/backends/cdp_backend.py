"""
CDP Backend — executes formatting instructions via Playwright keystrokes.

Converts instruction stream to Playwright keyboard calls.  No HTML
injection except for tables and horizontal rules (which can't be
produced reliably via keystrokes alone).
"""

from __future__ import annotations

import time

from ..instruction import (
    BoldOff,
    BoldOn,
    BulletItem,
    Enter,
    Heading2,
    HorizontalRule,
    Instruction,
    ItalicOff,
    ItalicOn,
    NumberedItem,
    TableEnd,
    TableRow,
    TableStart,
    Text,
    UnderlineOff,
    UnderlineOn,
)


def _build_table_html(rows: list[TableRow]) -> str:
    """Build a minimal HTML table."""
    if not rows:
        return ""
    cols = max(len(r.cells) for r in rows) if rows else 1
    html = '<table style="border-collapse:collapse;width:100%"><tbody>'
    for row in rows:
        cells = row.cells[:]
        while len(cells) < cols:
            cells.append("")
        html += "<tr>"
        for cell in cells:
            html += f"<td>{cell}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    return html


def execute(driver, instructions: list[Instruction], dwell_time_seconds: float = 0.0) -> None:
    """Execute instruction stream against a Playwright CDP driver.

    Args:
        driver: PlaywrightDriverWin/Mac (must be attached with active page).
        instructions: Instruction objects from format_for_google_docs().
        dwell_time_seconds: Unused — insert_text is atomic.
    """
    table_rows: list[TableRow] = []

    for instr in instructions:
        if isinstance(instr, Text):
            driver.surgical_paste(instr.content)

        elif isinstance(instr, BoldOn):
            driver.send_formatting_key("Control+b")

        elif isinstance(instr, BoldOff):
            driver.send_formatting_key("Control+b")

        elif isinstance(instr, ItalicOn):
            driver.send_formatting_key("Control+i")

        elif isinstance(instr, ItalicOff):
            driver.send_formatting_key("Control+i")

        elif isinstance(instr, UnderlineOn):
            driver.send_formatting_key("Control+u")

        elif isinstance(instr, UnderlineOff):
            driver.send_formatting_key("Control+u")

        elif isinstance(instr, Heading2):
            # Google Docs: Ctrl+Alt+2 applies Heading 2
            driver.send_formatting_key("Control+Alt+2")
            driver.surgical_paste(instr.content)
            time.sleep(0.05)
            # Don't reset to Normal Text here — Google Docs automatically
            # reverts to Normal when Enter is pressed after a heading.
            # Sending Ctrl+Alt+0 would revert the *current* line's heading.

        elif isinstance(instr, BulletItem):
            # Google Docs: Ctrl+Shift+8 toggles bullet list
            driver.send_formatting_key("Control+Shift+8")
            if instr.content:
                driver.surgical_paste(instr.content)

        elif isinstance(instr, NumberedItem):
            # Type "N. " to trigger Google Docs auto-numbering
            driver.surgical_paste(f"{instr.number}. {instr.content}" if instr.content else f"{instr.number}. ")

        elif isinstance(instr, TableStart):
            table_rows = []

        elif isinstance(instr, TableRow):
            table_rows.append(instr)

        elif isinstance(instr, TableEnd):
            html = _build_table_html(table_rows)
            if html:
                if hasattr(driver, 'paste_html'):
                    driver.paste_html(html)
                else:
                    driver.inject_html(html)
                time.sleep(0.05)

        elif isinstance(instr, HorizontalRule):
            if hasattr(driver, 'paste_html'):
                driver.paste_html("<hr>")
            else:
                driver.inject_html("<hr>")
            time.sleep(0.03)

        elif isinstance(instr, Enter):
            driver.send_enter()

        # Unknown instructions are silently skipped (safety)
