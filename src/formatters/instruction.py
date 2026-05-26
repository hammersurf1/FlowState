"""
Instruction types for the Google Docs formatter.

Each instruction represents an action the output backend must perform.
The stream is verified to ensure no characters are lost.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Instruction:
    """Base instruction.  All subclasses are frozen."""

    def text_content(self) -> str:
        """Return the literal text this instruction would produce
        if rendered as plain text (for character-preservation audit)."""
        return ""


@dataclass
class Text(Instruction):
    """Type literal text, character by character."""

    content: str

    def text_content(self) -> str:
        return self.content


@dataclass
class BoldOn(Instruction):
    """Enable bold formatting (Ctrl+B)."""
    pass


@dataclass
class BoldOff(Instruction):
    """Disable bold formatting (Ctrl+B)."""
    pass


@dataclass
class ItalicOn(Instruction):
    """Enable italic formatting (Ctrl+I)."""
    pass


@dataclass
class ItalicOff(Instruction):
    """Disable italic formatting (Ctrl+I)."""
    pass


@dataclass
class UnderlineOn(Instruction):
    """Enable underline formatting (Ctrl+U)."""
    pass


@dataclass
class UnderlineOff(Instruction):
    """Disable underline formatting (Ctrl+U)."""
    pass


@dataclass
class Heading2(Instruction):
    """Apply Heading 2 style to the following text."""

    content: str

    def text_content(self) -> str:
        return self.content


@dataclass
class BulletItem(Instruction):
    """Insert a bullet-list item."""

    content: str

    def text_content(self) -> str:
        return self.content


@dataclass
class NumberedItem(Instruction):
    """Insert a numbered-list item."""

    content: str
    number: int

    def text_content(self) -> str:
        return self.content


@dataclass
class TableStart(Instruction):
    """Inject a native Google Docs table (multi-row via HTML)."""
    pass


@dataclass
class TableRow(Instruction):
    """A single row in an HTML table (rendered via inject_html)."""

    cells: list[str] = field(default_factory=list)

    def text_content(self) -> str:
        return " | ".join(self.cells)


@dataclass
class TableEnd(Instruction):
    """Close the table block."""
    pass


@dataclass
class HorizontalRule(Instruction):
    """Insert a native Google Docs horizontal line."""
    pass


@dataclass
class Enter(Instruction):
    """Line break."""
    pass


@dataclass
class LiteralLine(Instruction):
    """A plain line with optional inline formatting markers.

    This is used for lines that don't match any block-level pattern.
    The inline formatter processes the content for bold/italic.
    """

    content: str

    def text_content(self) -> str:
        return self.content
