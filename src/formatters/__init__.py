"""Formatter module (BETA — Google Docs CDP mode only).

Pipeline:
  markdown clipboard → tagged internal format → instruction stream → keystrokes

All formatting ambiguity is resolved in the markdown→tagged conversion.
The typing backend only sees explicit instructions, never bare markdown.
"""

from .backends.cdp_backend import execute as execute_cdp
from .backends.os_backend import execute as execute_os
from .google_docs_formatter import format_for_google_docs
from .instruction import (
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

__all__ = [
    "format_for_google_docs",
    "execute_cdp",
    "execute_os",
    "Instruction",
    "Text",
    "BoldOn",
    "BoldOff",
    "ItalicOn",
    "ItalicOff",
    "UnderlineOn",
    "UnderlineOff",
    "Heading2",
    "BulletItem",
    "NumberedItem",
    "TableStart",
    "TableRow",
    "TableEnd",
    "HorizontalRule",
    "Enter",
]
