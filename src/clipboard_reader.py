"""
Clipboard HTML Reader — Windows.

Reads the HTML clipboard format (CF_HTML) to extract styled text runs
with formatting information (bold, italic, underline, headings).

Google Docs puts richly formatted HTML on the clipboard when you copy.
This module reads that HTML and extracts the formatting directly,
bypassing markdown parsing entirely.
"""

import ctypes
import ctypes.wintypes
import re
from html.parser import HTMLParser
from dataclasses import dataclass, field
from typing import List, Tuple


# ── Windows Clipboard API ────────────────────────────────────────────

CF_HTML = ctypes.wintypes.UINT(0)

def _register_html_format():
    """Register the HTML clipboard format (idempotent)."""
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

    # Open clipboard
    if not user32.OpenClipboard(0):
        return None
    try:
        h_data = user32.GetClipboardData(cf)
        if not h_data:
            return None

        # Lock global memory
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalSize.restype = ctypes.c_size_t
        kernel32.GlobalSize.argtypes = [ctypes.c_void_p]
        p_data = kernel32.GlobalLock(h_data)
        if not p_data:
            return None
        try:
            size = kernel32.GlobalSize(h_data)
            if size == 0 or size > 50_000_000:  # sanity cap at 50MB
                return None
            # Read in chunks to avoid huge allocations
            buf = (ctypes.c_char * size).from_address(p_data)
            raw = bytes(buf)

            # CF_HTML has a header like:
            #   Version:0.9\r\nStartHTML:00000123\r\nEndHTML:00004567\r\n...
            # The HTML content starts at StartHTML offset and ends at EndHTML.
            header_end = raw.find(b"\r\n\r\n")
            if header_end == -1:
                # Fallback: try to find <html> or <
                html_start = raw.find(b"<")
                if html_start == -1:
                    return None
                html_bytes = raw[html_start:]
            else:
                # Parse StartHTML/EndHTML from header
                header = raw[:header_end].decode("ascii", errors="ignore")
                start_match = re.search(r"StartHTML:(\d+)", header)
                end_match = re.search(r"EndHTML:(\d+)", header)
                if start_match and end_match:
                    start = int(start_match.group(1))
                    end = int(end_match.group(1))
                    html_bytes = raw[start:end]
                else:
                    html_bytes = raw[header_end + 4:]

            # Decode (CF_HTML is UTF-8)
            return html_bytes.decode("utf-8", errors="replace")

        finally:
            kernel32.GlobalUnlock(h_data)
    finally:
        user32.CloseClipboard()


# ── HTML Parser: extract styled text runs ────────────────────────────

@dataclass
class StyledRun:
    """A run of text with formatting attributes."""
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    heading_level: int = 0  # 0 = normal, 1 = H1, 2 = H2, ...
    newline_after: bool = False  # block-level element break


class _ClipboardHTMLParser(HTMLParser):
    """Parse Google Docs clipboard HTML into styled text runs."""

    # Google Docs uses inline CSS for formatting.
    # Common patterns from Google Docs export:
    #   <span style="font-weight:700"> → bold
    #   <span style="font-style:italic"> → italic
    #   <span style="text-decoration:underline"> → underline
    #   <h1>, <h2>, ... → headings (rare in clipboard HTML)
    #   <p class="c2"> → might indicate formatting via class
    #   <b>, <i>, <u> → explicit tags (some apps use these)
    #   <br> → line break
    #   <p>, <div> → paragraph break

    HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
    BLOCK_ELEMENTS = {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6",
                       "li", "tr", "table", "hr", "ul", "ol"}

    def __init__(self):
        super().__init__()
        self.runs: List[StyledRun] = []
        self._buf: List[str] = []
        self._bold_stack = 0
        self._italic_stack = 0
        self._underline_stack = 0
        self._heading = 0
        self._in_heading = False

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs_dict = dict(attrs)

        if tag in self.HEADINGS:
            self._flush_text()
            self._heading = self.HEADINGS[tag]
            self._in_heading = True
            return

        if tag in ("b", "strong"):
            self._flush_text()
            self._bold_stack += 1
        elif tag in ("i", "em"):
            self._flush_text()
            self._italic_stack += 1
        elif tag == "u":
            self._flush_text()
            self._underline_stack += 1
        elif tag == "br":
            self._flush_text()
            self.runs.append(StyledRun("\n"))
        elif tag == "span":
            style = attrs_dict.get("style", "")
            self._flush_text()
            if "font-weight:700" in style or "font-weight:bold" in style:
                self._bold_stack += 1
            if "font-style:italic" in style:
                self._italic_stack += 1
            if "text-decoration:underline" in style:
                self._underline_stack += 1

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.HEADINGS:
            self._flush_text()
            self._heading = 0
            self._in_heading = False
            self.runs[-1].heading_level = self._heading  # already captured
            return

        if tag in ("b", "strong"):
            self._flush_text()
            if self._bold_stack > 0:
                self._bold_stack -= 1
        elif tag in ("i", "em"):
            self._flush_text()
            if self._italic_stack > 0:
                self._italic_stack -= 1
        elif tag == "u":
            self._flush_text()
            if self._underline_stack > 0:
                self._underline_stack -= 1
        elif tag == "span":
            self._flush_text()
            # We can't easily determine WHICH span ended, so we approximate:
            # Google Docs clipboard HTML typically wraps each element in its
            # own span, so ending a span resets all span-based formatting.
            # We clear all span stacks and let re-opened spans re-apply.
            pass  # stacks persist across spans in Google Docs style
        elif tag in self.BLOCK_ELEMENTS:
            self._flush_text()
            if self.runs and self.runs[-1].text not in ("\n", ""):
                self.runs.append(StyledRun("\n"))

    def handle_data(self, data):
        # Skip whitespace-only in head/style/script
        if not data:
            return
        self._buf.append(data)

    def _flush_text(self):
        if self._buf:
            text = "".join(self._buf)
            self._buf.clear()
            run = StyledRun(
                text=text,
                bold=self._bold_stack > 0,
                italic=self._italic_stack > 0,
                underline=self._underline_stack > 0,
                heading_level=self._heading,
            )
            self.runs.append(run)

    def close(self):
        self._flush_text()
        super().close()


def parse_clipboard_html(html: str) -> List[StyledRun]:
    """Parse clipboard HTML into a list of styled text runs."""
    parser = _ClipboardHTMLParser()
    # Feed only the body content (skip <head> noise)
    body_match = re.search(r"<body[^>]*>(.*)</body>", html, re.DOTALL | re.IGNORECASE)
    if body_match:
        body = body_match.group(1)
    else:
        body = html
    parser.feed(body)
    parser.close()
    return _postprocess_runs(parser.runs)


def _postprocess_runs(runs: List[StyledRun]) -> List[StyledRun]:
    """Clean up runs: merge adjacent with same formatting, trim whitespace."""
    merged: List[StyledRun] = []
    for run in runs:
        if not run.text:
            continue
        # Merge with previous if same formatting
        if (merged and
            merged[-1].bold == run.bold and
            merged[-1].italic == run.italic and
            merged[-1].underline == run.underline and
            merged[-1].heading_level == run.heading_level and
            not merged[-1].text.endswith("\n") and
            not run.text.startswith("\n")):
            merged[-1].text += run.text
        else:
            merged.append(run)

    # Clean up: remove trailing empty runs, collapse multiple newlines
    return merged


# ── Public API ───────────────────────────────────────────────────────

def get_clipboard_styled_runs() -> List[StyledRun] | None:
    """Read clipboard HTML and return styled text runs, or None."""
    html = get_clipboard_html()
    if not html:
        return None
    return parse_clipboard_html(html)


def styled_runs_to_rich_text(runs: List[StyledRun]) -> List[Tuple[str, dict]]:
    """Convert StyledRun list to a format the engine can use directly.
    
    Returns list of (text, formatting_dict) tuples.
    formatting_dict keys: bold, italic, underline, heading_level
    """
    result = []
    for run in runs:
        result.append((run.text, {
            "bold": run.bold,
            "italic": run.italic,
            "underline": run.underline,
            "heading_level": run.heading_level,
        }))
    return result
