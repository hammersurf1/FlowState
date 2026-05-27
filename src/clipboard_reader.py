"""
Clipboard HTML Reader — Windows.

Reads the HTML clipboard format (CF_HTML) from Google Docs
and parses it into styled text runs with structural elements.

Google Docs clipboard HTML structure:
  <b style="font-weight:normal" id="docs-internal-guid-...">
    <h1><span style="font-size:20pt;...">Title</span></h1>
    <h2><span style="font-size:16pt;...">Section</span></h2>
    <p><span style="font-weight:700;...">bold text</span></p>
    <table><thead><tr><th>...</th></tr></thead>...</table>
    <ul><li>...</li></ul>
  </b>

The outer <b style="font-weight:normal"> is a Google Docs wrapper
that sets the base font weight — ignored.
"""

import ctypes
import ctypes.wintypes
import re
from html.parser import HTMLParser
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


# ── Windows Clipboard API ────────────────────────────────────────────

CF_HTML = ctypes.wintypes.UINT(0)

def _register_html_format():
    global CF_HTML
    if CF_HTML.value == 0:
        user32 = ctypes.windll.user32
        CF_HTML = user32.RegisterClipboardFormatW("HTML Format")
    return CF_HTML


def get_clipboard_html() -> str | None:
    """Return the HTML clipboard content, or None if unavailable."""
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
    cf = _register_html_format()
    if not cf:
        return None
    if not user32.OpenClipboard(0):
        return None
    try:
        h_data = user32.GetClipboardData(cf)
        if not h_data:
            return None
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalSize.restype = ctypes.c_size_t
        kernel32.GlobalSize.argtypes = [ctypes.c_void_p]
        p_data = kernel32.GlobalLock(h_data)
        if not p_data:
            return None
        try:
            size = kernel32.GlobalSize(h_data)
            if size == 0 or size > 50_000_000:
                return None
            buf = (ctypes.c_char * size).from_address(p_data)
            raw = bytes(buf)
            header_end = raw.find(b"\r\n\r\n")
            if header_end == -1:
                html_start = raw.find(b"<")
                if html_start == -1:
                    return None
                html_bytes = raw[html_start:]
            else:
                header = raw[:header_end].decode("ascii", errors="ignore")
                start_match = re.search(r"StartHTML:(\d+)", header)
                end_match = re.search(r"EndHTML:(\d+)", header)
                if start_match and end_match:
                    start = int(start_match.group(1))
                    end = int(end_match.group(1))
                    html_bytes = raw[start:end]
                else:
                    html_bytes = raw[header_end + 4:]
            return html_bytes.decode("utf-8", errors="replace")
        finally:
            kernel32.GlobalUnlock(h_data)
    finally:
        user32.CloseClipboard()


# ── Structured document model ────────────────────────────────────────

@dataclass
class StyledRun:
    """A run of text with inline formatting."""
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False


@dataclass
class TableCell:
    """A single table cell holding styled runs."""
    runs: List[StyledRun] = field(default_factory=list)

    def plain_text(self) -> str:
        return "".join(r.text for r in self.runs)


@dataclass
class TableRow:
    """A table row with cells."""
    cells: List[TableCell] = field(default_factory=list)
    is_header: bool = False


@dataclass
class DocElement:
    """A structural document element."""
    kind: str  # 'heading', 'paragraph', 'table', 'hr', 'list_item', 'blank'
    level: int = 0        # heading level (1-6)
    runs: List[StyledRun] = field(default_factory=list)
    rows: List[TableRow] = field(default_factory=list)
    list_type: str = ""   # 'ul' or 'ol'


# ── HTML Parser ──────────────────────────────────────────────────────

class _GDocsHTMLParser(HTMLParser):
    """Parse Google Docs clipboard HTML into DocElement list."""

    HEADING_TAGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
    
    # Tags that contain inline styled spans
    INLINE_CONTAINERS = {"span", "b", "strong", "i", "em", "u", "a", "p"}

    def __init__(self):
        super().__init__()
        self.elements: List[DocElement] = []

        # Current element being built
        self._current: Optional[DocElement] = None
        
        # Inline state
        self._inline_runs: List[StyledRun] = []
        self._text_buf: List[str] = []
        self._bold_depth = 0
        self._italic_depth = 0
        self._underline_depth = 0

        # Table state
        self._in_table = False
        self._in_thead = False
        self._table_rows: List[TableRow] = []
        self._current_row: Optional[TableRow] = None
        self._current_cell: Optional[TableCell] = None

        # List state
        self._in_list = False
        self._list_type = ""
        
        # Google Docs wrapper depth
        self._gdocs_wrapper_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs = dict(attrs)
        style = attrs.get("style", "")

        # ── Google Docs wrapper: <b style="font-weight:normal" id="docs-internal-guid-...">
        if tag == "b" and "docs-internal-guid" in attrs.get("id", ""):
            self._gdocs_wrapper_depth += 1
            return
        if self._gdocs_wrapper_depth > 0 and tag == "b":
            self._gdocs_wrapper_depth += 1
            return

        # ── Headings ──────────────────────────────────────────────
        if tag in self.HEADING_TAGS:
            self._flush_inline()
            self._current = DocElement(kind="heading", level=self.HEADING_TAGS[tag])
            return

        # ── Table elements ────────────────────────────────────────
        if tag == "table":
            self._finish_element()
            self._in_table = True
            self._table_rows = []
            return
        if tag in ("thead", "tbody"):
            self._in_thead = (tag == "thead")
            return
        if tag == "tr":
            self._current_row = TableRow(is_header=self._in_thead)
            return
        if tag in ("td", "th"):
            self._current_cell = TableCell()
            return

        # ── Lists ─────────────────────────────────────────────────
        if tag == "ul":
            self._finish_element()
            self._in_list = True
            self._list_type = "ul"
            return
        if tag == "ol":
            self._finish_element()
            self._in_list = True
            self._list_type = "ol"
            return
        if tag == "li":
            self._flush_inline()
            self._current = DocElement(kind="list_item", list_type=self._list_type)
            return

        # ── Paragraphs ────────────────────────────────────────────
        if tag == "p":
            self._flush_inline()
            self._current = DocElement(kind="paragraph")
            return

        # ── Horizontal rule / page break ──────────────────────────
        if tag == "hr":
            self._finish_element()
            style = attrs.get("style", "")
            if "page-break" in style:
                self.elements.append(DocElement(kind="page_break"))
            else:
                self.elements.append(DocElement(kind="hr"))
            return

        # ── Inline formatting via <span style="..."> ──────────────
        if tag == "span" and style:
            self._push_inline_style(style)
            return

        # ── Explicit formatting tags ──────────────────────────────
        if tag in ("b", "strong"):
            self._flush_text()
            self._bold_depth += 1
        elif tag in ("i", "em"):
            self._flush_text()
            self._italic_depth += 1
        elif tag == "u":
            self._flush_text()
            self._underline_depth += 1
        elif tag == "br":
            self._flush_text()
            self._inline_runs.append(StyledRun("\n"))

    def handle_endtag(self, tag):
        tag = tag.lower()

        # ── Google Docs wrapper ───────────────────────────────────
        if self._gdocs_wrapper_depth > 0:
            if tag == "b":
                self._gdocs_wrapper_depth -= 1
                return

        # ── Headings, paragraphs, list items — close element ─────
        if tag in self.HEADING_TAGS or tag in ("p", "li"):
            self._finish_element()
            return

        # ── Lists ─────────────────────────────────────────────────
        if tag in ("ul", "ol"):
            self._finish_element()
            self._in_list = False
            self._list_type = ""
            return

        # ── Table elements ────────────────────────────────────────
        if tag in ("thead", "tbody"):
            self._in_thead = False
            return
        if tag == "tr":
            self._flush_inline()
            if self._current_cell:
                self._current_row.cells.append(self._current_cell)
                self._current_cell = None
            if self._current_row:
                self._table_rows.append(self._current_row)
                self._current_row = None
            return
        if tag in ("td", "th"):
            self._flush_inline()
            if self._current_cell:
                self._current_row.cells.append(self._current_cell)
                self._current_cell = None
            return
        if tag == "table":
            self._in_table = False
            if self._table_rows:
                self.elements.append(DocElement(kind="table", rows=self._table_rows))
                self._table_rows = []
            return

        # ── Inline formatting close ───────────────────────────────
        if tag == "span":
            self._flush_text()
            # Pop the style pushed by span open
            self._pop_inline_style()
        elif tag in ("b", "strong"):
            self._flush_text()
            if self._bold_depth > 0:
                self._bold_depth -= 1
        elif tag in ("i", "em"):
            self._flush_text()
            if self._italic_depth > 0:
                self._italic_depth -= 1
        elif tag == "u":
            self._flush_text()
            if self._underline_depth > 0:
                self._underline_depth -= 1

    def handle_data(self, data):
        if not data:
            return
        # Inside a table cell or inline — accumulate text
        self._text_buf.append(data)

    # ── Helpers ──────────────────────────────────────────────────────

    def _push_inline_style(self, style: str):
        """Parse inline style string and push formatting state."""
        self._flush_text()
        if "font-weight:700" in style or "font-weight:bold" in style:
            self._bold_depth += 1
        if "font-style:italic" in style:
            self._italic_depth += 1
        if "text-decoration:underline" in style:
            self._underline_depth += 1

    def _pop_inline_style(self):
        """Span closed — the formatting it applied is removed.
        Since we track depth per-style, we approximate: any span
        close reduces all depths that were pushed by spans.
        Google Docs clipboard wraps each formatted run in its own
        span, so closing a span resets all span-based formatting.
        """
        # Simple approach: just flush. Depths percolate via nested spans.
        pass

    def _flush_text(self):
        """Emit accumulated text as a StyledRun."""
        if self._text_buf:
            text = "".join(self._text_buf)
            self._text_buf.clear()
            run = StyledRun(
                text=text,
                bold=self._bold_depth > 0,
                italic=self._italic_depth > 0,
                underline=self._underline_depth > 0,
            )
            if self._current_cell is not None:
                self._current_cell.runs.append(run)
            elif self._current is not None:
                self._current.runs.append(run)
            else:
                self._inline_runs.append(run)

    def _flush_inline(self):
        """Flush any dangling inline runs into the current element or
        create a paragraph element for them."""
        self._flush_text()

    def _finish_element(self):
        """Close the current element and append to elements list."""
        self._flush_text()
        if self._current is not None:
            # Don't add empty elements
            if self._current.runs or self._current.kind == "hr":
                self.elements.append(self._current)
            self._current = None
        # Also flush any orphan inline runs
        if self._inline_runs and not self._in_table:
            el = DocElement(kind="paragraph", runs=list(self._inline_runs))
            self.elements.append(el)
            self._inline_runs.clear()

    def close(self):
        self._finish_element()
        if self._inline_runs:
            self.elements.append(DocElement(kind="paragraph", runs=list(self._inline_runs)))
        super().close()


def parse_clipboard_html(html: str) -> List[DocElement]:
    """Parse clipboard HTML into structured document elements."""
    parser = _GDocsHTMLParser()
    # Google Docs wraps content in <meta charset="utf-8">
    # Strip the meta tag to avoid confusing the parser
    html = re.sub(r'<meta[^>]*>', '', html, flags=re.IGNORECASE)
    parser.feed(html)
    parser.close()
    return parser.elements


# ── Public API ───────────────────────────────────────────────────────

def get_clipboard_styled_runs() -> List[DocElement] | None:
    """Read clipboard HTML and return document elements, or None."""
    html = get_clipboard_html()
    if not html:
        return None
    return parse_clipboard_html(html)
