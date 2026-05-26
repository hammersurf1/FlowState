"""
Google Docs Formatter (BETA).

Two-phase pipeline:
  1. Markdown → Tagged text   (INPUT: ambiguous, flexible)
  2. Tagged text → Instructions (INTERNAL: unambiguous, explicit)

Phase 1 handles ALL the ambiguity.  After conversion, every formatting
boundary is explicit — the typing backend never sees a bare `_` or `*`.

Only the CDP backend applies formatting (OS mode types literally).
"""

from __future__ import annotations

import re

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
    LiteralLine,
    NumberedItem,
    TableEnd,
    TableRow,
    TableStart,
    Text,
    UnderlineOff,
    UnderlineOn,
)

# ═══════════════════════════════════════════════════════════════════
#  PHASE 1: Markdown → Tagged text
# ═══════════════════════════════════════════════════════════════════

# Inline patterns (processed per-line)
_BOLD_ASTERISK = re.compile(r"\*\*([^*]+?)\*\*")    # **text**
_BOLD_UNDERSCORE = re.compile(r"(?<!\w)__([^_]+?)__(?!\w)")  # __text__
_ITALIC_ASTERISK = re.compile(r"(?<!\*)\*([^*]+?)\*(?!\*)")   # *text*
_ITALIC_UNDERSCORE = re.compile(r"(?<!\w)_([^_]+?)_(?!\w)")   # _text_

# Block-level patterns
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_TABLE_SEP_RE = re.compile(r"^\|[\s\-:|]+\|$")
_TABLE_ROW_RE = re.compile(r"^\|(.+?)\|$")
_HR_RE = re.compile(r"^[-*]{3,}\s*$")
_BULLET_RE = re.compile(r"^[-*]\s+(.+)$")
_NUMBERED_RE = re.compile(r"^(\d+)\.\s+(.+)$")
_BLANK_RE = re.compile(r"^\s*$")


def _markdown_to_tagged(text: str) -> str:
    """Convert markdown to tagged format.  This is the ONLY place
    markdown syntax is interpreted.  Output uses explicit <b>, <i>,
    <h2>, <table>, <li>, <ol>, <hr>, <br> tags."""
    lines = text.split("\n")
    result: list[str] = []
    in_table = False
    ol_depth = 0

    for line in lines:
        stripped = line.strip()

        # ── blank line ──
        if not stripped:
            if in_table:
                result.append("</table>")
                in_table = False
            if ol_depth:
                result.append("</ol>")
                ol_depth = 0
            result.append("<br>")
            continue

        # ── heading ──
        hm = _HEADING_RE.match(line)
        if hm:
            if in_table:
                result.append("</table>")
                in_table = False
            content = _inline_convert(hm.group(2))
            result.append(f"<h2>{content}</h2>")
            continue

        # ── horizontal rule ──
        if _HR_RE.match(stripped):
            if in_table:
                result.append("</table>")
                in_table = False
            result.append("<hr>")
            continue

        # ── table row ──
        if _TABLE_ROW_RE.match(stripped):
            if _TABLE_SEP_RE.match(stripped):
                continue  # separator row → skip
            if not in_table:
                result.append("<table>")
                in_table = True
            # Strip leading/trailing | and split
            inner = stripped.strip("|")
            cells = [c.strip() for c in inner.split("|")]
            cell_html = "".join(f"<td>{_inline_convert(c)}</td>" for c in cells)
            result.append(f"<tr>{cell_html}</tr>")
            continue

        # ── close table if we were in one ──
        if in_table:
            result.append("</table>")
            in_table = False

        # ── numbered list ──
        nm = _NUMBERED_RE.match(line)
        if nm:
            if not ol_depth:
                result.append("<ol>")
            content = _inline_convert(nm.group(2))
            result.append(f"<li>{content}</li>")
            ol_depth += 1
            continue

        # ── close ol if we were in one ──
        if ol_depth:
            result.append("</ol>")
            ol_depth = 0

        # ── bullet item ──
        bm = _BULLET_RE.match(line)
        if bm:
            content = _inline_convert(bm.group(1))
            result.append(f"<li>{content}</li>")
            continue

        # ── regular line ──
        result.append(_inline_convert(line))

    # Close any open blocks
    if in_table:
        result.append("</table>")
    if ol_depth:
        result.append("</ol>")

    return "\n".join(result)


def _inline_convert(text: str) -> str:
    """Convert bold and italic markdown in a single line to tagged format.

    Process bold first (avoids ** being confused with *), then italic.
    Underscore patterns use word-boundary assertions: _ only triggers
    italic when it touches a word character on the inside and word
    boundary / whitespace / line edge on the outside.

    Anything not matched is left as literal text — this includes:
      - Fill-in lines:  _______________________________
      - Inline underscores:  my_var, PrPᶜ
      - Leading/trailing underscores that don't form a pair
    """
    out = text

    # Bold via **  (safe — ** never appears in normal text)
    out = _BOLD_ASTERISK.sub(r"<b>\1</b>", out)

    # Bold via __  (must touch word boundaries — avoids matching
    #               ___ fill-in lines)
    out = _BOLD_UNDERSCORE.sub(r"<b>\1</b>", out)

    # Italic via *  (single *, not part of **)
    out = _ITALIC_ASTERISK.sub(r"<i>\1</i>", out)

    # Italic via _  (word-boundary guarded)
    out = _ITALIC_UNDERSCORE.sub(r"<i>\1</i>", out)

    return out


# ═══════════════════════════════════════════════════════════════════
#  PHASE 2: Tagged text → Instructions
# ═══════════════════════════════════════════════════════════════════

_TAG_RE = re.compile(
    r"<(b|i|u|h2|table|tr|td|li|ol|hr|br)\s*/?>"
    r"|"
    r"</(b|i|u|h2|table|tr|td|li|ol)>"
)


def _parse_tagged(text: str) -> list[Instruction]:
    """Parse tagged text into instruction stream.  NO markdown happens
    here — every character is literal unless it's inside a tag."""
    instructions: list[Instruction] = []
    pos = 0
    stack: list[str] = []
    table_buffer: list[TableRow] = []
    current_cells: list[str] = []
    cell_buf: list[str] = []          # accumulates text inside a <td>
    in_table = False
    in_tr = False
    in_td = False
    in_ol = False
    ol_counter = 0

    def _flush_cell():
        nonlocal cell_buf
        if cell_buf:
            current_cells.append("".join(cell_buf))
            cell_buf = []

    def _emit_text(t: str):
        """Emit literal text — either to cell buffer or to instructions."""
        nonlocal cell_buf
        if in_td:
            cell_buf.append(t)
        else:
            instructions.append(Text(t))

    while pos < len(text):
        m = _TAG_RE.search(text, pos)
        if not m:
            remaining = text[pos:]
            if remaining and not _is_whitespace_only(remaining):
                _emit_text(remaining)
            break

        # Text before this tag
        if m.start() > pos:
            chunk = text[pos : m.start()]
            if chunk and not _is_whitespace_only(chunk):
                _emit_text(chunk)

        raw = m.group().lower()
        is_closing = raw.startswith("</")

        if is_closing:
            tag_name = m.group(2)
            if tag_name == "b":
                _pop_stack(stack, "b")
                instructions.append(BoldOff())
            elif tag_name == "i":
                _pop_stack(stack, "i")
                instructions.append(ItalicOff())
            elif tag_name == "u":
                _pop_stack(stack, "u")
                instructions.append(UnderlineOff())
            elif tag_name == "h2":
                instructions.append(BoldOff())
            elif tag_name == "table":
                if table_buffer:
                    instructions.append(TableStart())
                    for row in table_buffer:
                        instructions.append(row)
                    instructions.append(TableEnd())
                    instructions.append(Enter())
                    table_buffer = []
                in_table = False
            elif tag_name == "tr":
                _flush_cell()
                if current_cells:
                    table_buffer.append(TableRow(cells=list(current_cells)))
                    current_cells = []
                in_tr = False
            elif tag_name == "td":
                _flush_cell()
                in_td = False
            elif tag_name == "li":
                instructions.append(Enter())
            elif tag_name == "ol":
                in_ol = False
                ol_counter = 0
        else:
            tag_name = raw.strip("<>").strip("/")
            if tag_name == "b":
                instructions.append(BoldOn())
                stack.append("b")
            elif tag_name == "i":
                instructions.append(ItalicOn())
                stack.append("i")
            elif tag_name == "u":
                instructions.append(UnderlineOn())
                stack.append("u")
            elif tag_name == "h2":
                instructions.append(BoldOn())
            elif tag_name == "hr":
                instructions.append(HorizontalRule())
            elif tag_name == "table":
                in_table = True
                table_buffer = []
            elif tag_name == "tr":
                in_tr = True
                current_cells = []
            elif tag_name == "td":
                in_td = True
                cell_buf = []
            elif tag_name == "li":
                if in_ol:
                    ol_counter += 1
                    instructions.append(Text(f"{ol_counter}. "))
                else:
                    instructions.append(Text("- "))
            elif tag_name == "ol":
                in_ol = True
                ol_counter = 0
            elif tag_name == "br":
                instructions.append(Enter())

        pos = m.end()

    # Close any unclosed formatting tags
    for tag in reversed(stack):
        _pop_stack(stack, tag)
        if tag == "b":
            instructions.append(BoldOff())
        elif tag == "i":
            instructions.append(ItalicOff())
        elif tag == "u":
            instructions.append(UnderlineOff())

    # Flush remaining table
    if table_buffer:
        instructions.append(TableStart())
        for row in table_buffer:
            instructions.append(row)
        instructions.append(TableEnd())
        instructions.append(Enter())

    return instructions


def _pop_stack(stack: list[str], expected: str) -> None:
    """Remove the expected tag from the stack (may be buried if tags
    are improperly nested — just remove it wherever it is)."""
    if expected in stack:
        stack.remove(expected)


def _is_whitespace_only(s: str) -> bool:
    return not s or s.isspace()


# ═══════════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════════


def format_for_google_docs(text: str) -> list[Instruction]:
    """Parse markdown clipboard text into a keystroke instruction stream.

    Pipeline: markdown → tagged → instructions
    """
    if not text or not text.strip():
        return [Text(text)] if text else []

    tagged = _markdown_to_tagged(text)
    instructions = _parse_tagged(tagged)
    return instructions


def audit_characters(original: str, instructions: list[Instruction]) -> int:
    """Return original_len - rendered_len (should be >= 0)."""
    rendered = 0
    for instr in instructions:
        if isinstance(instr, (TableStart, TableEnd, HorizontalRule)):
            continue
        rendered += len(instr.text_content())
    return len(original) - rendered
