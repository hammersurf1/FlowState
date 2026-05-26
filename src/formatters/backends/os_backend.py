"""
OS Backend — stub for OS-level mode.

OS mode does NOT apply special formatting (BETA scope: Google Docs CDP only).
All text is typed literally via driver.surgical_paste().
"""

from __future__ import annotations

from ..instruction import (
    Enter,
    Instruction,
    LiteralLine,
    Text,
)


def execute(driver, instructions: list[Instruction], dwell_time_seconds: float = 0.0) -> None:
    """Flat render: concatenate all visible text and type literally.

    Formatting instructions (BoldOn, Heading2, etc.) are silently ignored
    because OS mode is not in the beta formatting scope.
    """
    parts: list[str] = []

    for instr in instructions:
        tc = instr.text_content()
        if tc:
            parts.append(tc)
        elif isinstance(instr, Enter):
            parts.append("\n")

    flat = "".join(parts)
    if flat:
        driver.surgical_paste(flat)
