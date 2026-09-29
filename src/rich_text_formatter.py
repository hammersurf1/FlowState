"""
FlowState — Rich Text Formatter
Parses Markdown-flavoured clipboard text into a sequence of TypeActions and
KeyActions that the TypingEngine executes to produce bold, italic, underline,
strikethrough, bullet lists, numbered lists, nested sub-items, and headings
in the target browser app.

Supported syntax:
  **text** or __text__        → Bold       (Ctrl/Cmd+B)
  *text*   or _text_          → Italic     (Ctrl/Cmd+I)
  ___text___                  → Underline  (Ctrl/Cmd+U)  [triple underscore]
  ~~text~~                    → Strikethrough (Alt+Shift+5) [Google Docs]
  - item  / * item            → Unordered bullet
  1. item                     → Ordered list item
  # / ## / ### ...            → Heading 1–6 (Ctrl/Cmd+Alt+1–6)
  Leading \\t or 2/4 spaces   → Sub-level indent (Tab after Enter)
  \\n                         → Enter (always hard Enter for list items)

Design notes:
- Parse line-by-line to detect list context, then inline-parse each line for
  bold/italic/underline/strikethrough spans.
- Formatting shortcuts are toggled before and after each span (open/close).
- The formatter is stateless; it returns an immutable list of actions per call.
- Platform ('win' or 'mac') determines the modifier key (Ctrl vs Cmd).
- Typos only fire on TypeAction text; KeyActions are never mis-typed.
"""

import re
import sys
from dataclasses import dataclass
from typing import List

# Maximum list nesting depth (matches Google Docs / Notion behaviour)
MAX_INDENT_DEPTH = 4


@dataclass
class TypeAction:
    """Instruct the engine to type a string with normal human rhythm."""
    text: str


@dataclass
class KeyAction:
    """Instruct the engine to press a keyboard shortcut immediately."""
    shortcut: str   # e.g. "ctrl+b", "tab", "enter"


Action = TypeAction | KeyAction


def _keymap(mod: str, profile: str) -> dict:
    """Formatting role -> key shortcut, or "exec:<command>[:<value>]" which the engine
    runs as document.execCommand in the focused editor.

    "docs": Google Docs shortcuts (its editor is not a real contenteditable, so
            execCommand does nothing there).
    "exec": anything else with a real contenteditable, e.g. Canvas's TinyMCE editor
            (inside an iframe), Gmail, Outlook web. Ctrl+B/I/U are universal;
            the rest goes through execCommand because TinyMCE's own shortcuts vary.
    """
    k = {"bold": f"{mod}+b", "italic": f"{mod}+i", "underline": f"{mod}+u"}
    if profile == "docs":
        k.update(strike="Alt+Shift+5", ul=f"{mod}+Shift+8", ol=f"{mod}+Shift+7")
        k.update({f"h{n}": f"{mod}+Alt+{n}" for n in range(1, 7)})
    else:
        k.update(strike="exec:strikeThrough", ul="exec:insertUnorderedList", ol="exec:insertOrderedList")
        k.update({f"h{n}": f"exec:formatBlock:<h{n}>" for n in range(1, 7)})
    return k


def profile_for_url(url: str) -> str:
    return "docs" if "docs.google.com" in url else "exec"


class RichTextFormatter:
    """
    Converts Markdown-flavoured plain text into an ordered list of Actions.

    Usage:
        formatter = RichTextFormatter(platform='win')  # or 'mac'
        actions = formatter.parse(clipboard_text)
        # actions is a list of TypeAction / KeyAction objects
    """

    def __init__(self, platform: str = "win", profile: str = "docs"):
        # Normalise platform string
        if platform == "darwin" or platform == "mac":
            self._mod = "Meta"      # Playwright key name for Cmd on macOS
        else:
            self._mod = "Control"   # Playwright key name for Ctrl on Windows/Linux
        self._k = _keymap(self._mod, profile)

        # Regex to detect list-item lines (unordered or ordered)
        self._unordered_re = re.compile(r'^(\s*)[-*]\s+(.*)', re.DOTALL)
        self._ordered_re   = re.compile(r'^(\s*)(\d{1,2})\.\s+(.*)', re.DOTALL)  # 1-2 digits: "2024. Text" is prose

    # ─── Public API ──────────────────────────────────────────────────────────

    def parse(self, text: str) -> List[Action]:
        """
        Parse *text* and return a flat list of TypeAction / KeyAction objects.

        The caller should iterate the list sequentially:
          - TypeAction  → run through the normal keystroke engine (typos, rhythm)
          - KeyAction   → press immediately with a small human-like pre/post delay
        """
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = text.split("\n")

        actions: List[Action] = []
        list_state: str | None = None   # "ul" | "ol" | None
        list_depth = 0                  # nesting level the cursor is currently at
        prev_header = False
        is_first_line = True

        for line_idx, raw_line in enumerate(lines):
            # Peek at the next non-empty line to decide list continuation
            next_line = lines[line_idx + 1] if line_idx + 1 < len(lines) else ""

            # ── Block-level: Header ──────────────────────────────────────
            header_match = re.match(r'^(#{1,6})\s+(.*)', raw_line)
            if header_match:
                level = len(header_match.group(1))
                content = header_match.group(2)
                if list_state is not None:
                    actions.extend([KeyAction("Enter"), KeyAction("Enter")])  # leave the list
                elif not is_first_line:
                    # Hard Enter: heading style applies to the whole paragraph, so
                    # a Shift+Enter line break would restyle the previous line too.
                    actions.append(KeyAction("Enter"))
                # Activate heading style (Ctrl/Cmd+Alt+1..6)
                actions.append(KeyAction(self._k[f"h{level}"]))
                actions.extend(self._parse_inline(content))
                list_state = None  # headers break any ongoing list
                list_depth = 0
                is_first_line = False
                prev_header = True
                continue

            ul_match = self._unordered_re.match(raw_line)
            ol_match = self._ordered_re.match(raw_line)

            if ul_match or ol_match:
                # ── List item ────────────────────────────────────────────────
                match = ul_match or ol_match
                indent_str = match.group(1)
                content    = match.group(3) if ol_match else match.group(2)
                depth      = self._indent_depth(indent_str)

                if not is_first_line:
                    # Between list items always use a hard Enter
                    actions.append(KeyAction("Enter"))

                # Activate the correct list mode on the first item of each block
                if ul_match and list_state != "ul":
                    # Ctrl/Cmd+Shift+8 → unordered list in Google Docs / Notion
                    actions.append(KeyAction(self._k["ul"]))
                    list_state = "ul"
                elif ol_match and list_state != "ol":
                    # Ctrl/Cmd+Shift+7 → ordered list in Google Docs / Notion
                    actions.append(KeyAction(self._k["ol"]))
                    list_state = "ol"

                # Move from the current nesting level to the wanted one
                # (Enter keeps the previous item's level).
                effective_depth = min(depth, MAX_INDENT_DEPTH)
                step = "Tab" if effective_depth > list_depth else "Shift+Tab"
                for _ in range(abs(effective_depth - list_depth)):
                    actions.append(KeyAction(step))
                list_depth = effective_depth

                # Type the list item content with inline formatting
                actions.extend(self._parse_inline(content))

            else:
                # ── Plain / paragraph line ───────────────────────────────────
                exited_list = False
                if list_state is not None:
                    # Exit list mode. In most rich-text editors, pressing Enter on
                    # the last list item creates an empty bullet; pressing Enter
                    # again exits the list and creates a new paragraph.
                    actions.append(KeyAction("Enter"))
                    actions.append(KeyAction("Enter"))
                    list_state = None
                    list_depth = 0
                    exited_list = True

                if not is_first_line and not exited_list:
                    # Newline between lines, blank lines included (they are paragraph spacing).
                    # After a heading use a hard Enter so the next line is not a heading.
                    actions.append(KeyAction("Enter" if prev_header else "\n"))  # engine maps \n → Enter/Shift+Enter

                # Type the line content with inline formatting
                actions.extend(self._parse_inline(raw_line))

            is_first_line = False
            prev_header = False

        return actions

    # ─── Private Helpers ─────────────────────────────────────────────────────

    def _indent_depth(self, indent_str: str) -> int:
        """
        Convert a leading-whitespace string to a 0-based nesting depth.
        Tab counts as one level; every 2 spaces count as one level.
        """
        tabs   = indent_str.count("\t")
        spaces = indent_str.count(" ")
        return tabs + (spaces // 2)

    def _parse_inline(self, text: str) -> List[Action]:
        """
        Parse inline Markdown (bold, italic, underline, strikethrough) within a
        single line of text and return a sequence of TypeActions / KeyActions.

        Precedence (parsed in order, highest first):
          1. ___text___   → underline  (triple underscore, checked before double)
          2. ~~text~~     → strikethrough (Alt+Shift+5 — Google Docs specific)
          3. **text**     → bold
          4. __text__     → bold  (double underscore)
          5. *text*       → italic
          6. _text_       → italic (single underscore, checked last)
        """
        actions: List[Action] = []
        # Build a single regex that matches all inline markers.
        # Named groups let us identify which marker was matched.
        # Italic markers use lookarounds so they don't match * or _ that
        # are part of **bold** or __bold__ pairs.
        pattern = re.compile(
            r'(?P<underline>(?<!\w)___(?!\s)(?P<u_text>.+?)(?<!\s)___(?!\w))'
            r'|(?P<strikethrough>~~(?!\s)(?P<s_text>.+?)(?<!\s)~~)'
            r'|(?P<bold_star>\*\*(?!\s)(?P<bs_text>.+?)(?<!\s)\*\*)'
            r'|(?P<bold_us>(?<!\w)__(?!\s)(?P<bu_text>.+?)(?<!\s)__(?!\w))'
            r'|(?P<italic_star>(?<![\w*])\*(?![\s*])(?P<is_text>.+?)(?<![\s*])\*(?![\w*]))'
            r'|(?P<italic_us>(?<![\w_])_(?![\s_])(?P<iu_text>.+?)(?<![\s_])_(?![\w_]))',
            re.DOTALL
        )

        pos = 0
        for m in pattern.finditer(text):
            start, end = m.span()

            # Emit any plain text before this match
            if pos < start:
                actions.append(TypeAction(text[pos:start]))

            if m.group("underline"):
                inner = m.group("u_text")
                actions.append(KeyAction(self._k["underline"]))
                actions.extend(self._parse_inline(inner))
                actions.append(KeyAction(self._k["underline"]))

            elif m.group("strikethrough"):
                inner = m.group("s_text")
                actions.append(KeyAction(self._k["strike"]))
                actions.extend(self._parse_inline(inner))
                actions.append(KeyAction(self._k["strike"]))

            elif m.group("bold_star") or m.group("bold_us"):
                inner = m.group("bs_text") or m.group("bu_text")
                actions.append(KeyAction(self._k["bold"]))
                actions.extend(self._parse_inline(inner))
                actions.append(KeyAction(self._k["bold"]))

            elif m.group("italic_star") or m.group("italic_us"):
                inner = m.group("is_text") or m.group("iu_text")
                actions.append(KeyAction(self._k["italic"]))
                actions.extend(self._parse_inline(inner))
                actions.append(KeyAction(self._k["italic"]))

            pos = end

        # Emit any trailing plain text
        if pos < len(text):
            actions.append(TypeAction(text[pos:]))

        return actions


def _platform_string() -> str:
    """Return a short platform identifier for the current OS."""
    return "mac" if sys.platform == "darwin" else "win"
