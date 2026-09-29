"""Read the HTML flavour of the clipboard (what Word, Google Docs and web pages put
there) and convert it to the Markdown dialect RichTextFormatter understands, so
copying formatted text is enough: no need to write Markdown by hand.

Everything here fails soft: no HTML on the clipboard -> None -> the caller types the
plain text exactly as before.
"""
import re
import subprocess
import sys
from html.parser import HTMLParser

# ─── Reading the clipboard ───────────────────────────────────────────────────


def get_clipboard_html():
    try:
        if sys.platform == "win32":
            return _win_html()
        if sys.platform == "darwin":
            return _mac_html()
        return _linux_html()
    except Exception:
        return None


def _cf_html_fragment(raw: bytes) -> str:
    """Windows 'HTML Format' = ASCII header with byte offsets + UTF-8 HTML."""
    m1, m2 = re.search(rb"StartFragment:(\d+)", raw), re.search(rb"EndFragment:(\d+)", raw)
    if m1 and m2:
        raw = raw[int(m1.group(1)):int(m2.group(1))]
    return raw.rstrip(b"\0").decode("utf-8", "replace")


def _win_html():
    import ctypes
    u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
    u32.GetClipboardData.restype = ctypes.c_void_p
    u32.GetClipboardData.argtypes = [ctypes.c_uint]
    k32.GlobalLock.restype = ctypes.c_void_p
    k32.GlobalLock.argtypes = [ctypes.c_void_p]
    k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    k32.GlobalSize.restype = ctypes.c_size_t
    k32.GlobalSize.argtypes = [ctypes.c_void_p]
    fmt = u32.RegisterClipboardFormatW("HTML Format")
    if not u32.OpenClipboard(None):
        return None
    try:
        h = u32.GetClipboardData(fmt)
        if not h:
            return None
        ptr = k32.GlobalLock(h)
        try:
            raw = ctypes.string_at(ptr, k32.GlobalSize(h))
        finally:
            k32.GlobalUnlock(h)
    finally:
        u32.CloseClipboard()
    return _cf_html_fragment(raw)


def _mac_html():
    out = subprocess.run(["osascript", "-e", "the clipboard as «class HTML»"],
                         capture_output=True, text=True, timeout=5).stdout
    m = re.search(r"«data HTML([0-9A-Fa-f]+)»", out)
    return bytes.fromhex(m.group(1)).decode("utf-8", "replace") if m else None


def _linux_html():
    for cmd in (["xclip", "-selection", "clipboard", "-t", "text/html", "-o"],
                ["wl-paste", "-t", "text/html"]):
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.decode("utf-8", "replace")
    return None


# ─── HTML -> Markdown ────────────────────────────────────────────────────────

_VOID = {"br", "meta", "link", "img", "hr", "input", "col", "wbr"}
_SKIP = {"script", "style", "head", "title"}
_HEADING = {f"h{n}" for n in range(1, 7)}


def _style_flags(tag, style):
    """(turned_on, turned_off) formatting for one element, from its tag and inline
    style. Google Docs wraps everything in <b style="font-weight:normal">, so the
    style must be able to switch a tag's default OFF."""
    on, off = set(), set()
    if tag in ("b", "strong"): on.add("bold")
    if tag in ("i", "em"): on.add("italic")
    if tag in ("u", "ins"): on.add("underline")
    if tag in ("s", "strike", "del"): on.add("strike")
    m = re.search(r"font-weight\s*:\s*(\w+)", style)
    if m:
        w = m.group(1)
        (on if w in ("bold", "bolder") or (w.isdigit() and int(w) >= 600) else off).add("bold")
    m = re.search(r"font-style\s*:\s*(\w+)", style)
    if m:
        (on if m.group(1) in ("italic", "oblique") else off).add("italic")
    m = re.search(r"text-decoration(?:-line)?\s*:\s*([^;]+)", style)
    if m:
        deco = m.group(1)
        if "underline" in deco and tag != "a": on.add("underline")
        if "line-through" in deco: on.add("strike")
        if deco.strip() == "none": off.update(("underline", "strike"))
    return on, off


def _mark(flags, core):
    # Nesting chosen so every level survives RichTextFormatter's regexes;
    # ponytail: underline+italic+bold on the same run is not representable.
    if "bold" in flags: core = f"**{core}**"
    if "italic" in flags: core = f"*{core}*" if "underline" in flags else f"_{core}_"
    if "underline" in flags: core = f"___{core}___"
    if "strike" in flags: core = f"~~{core}~~"
    return core


def _wrap(flags, text):
    """Wrap each line of a run separately, keeping edge spaces OUTSIDE the markers
    (the formatter ignores `** bold**`)."""
    out = []
    for piece in text.split("\n"):
        core = piece.strip(" ")
        if not core or not flags:
            out.append(piece)
        else:
            lead = piece[:len(piece) - len(piece.lstrip(" "))]
            out.append(lead + _mark(flags, core) + piece[len(piece.rstrip(" ")):])
    return "\n".join(out)


class _MD(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []            # (kind, line): kind in p | h | li
        self.runs = []              # [(flags, text)] of the block being built
        self.kind, self.prefix = "p", ""
        self.stack = []             # (tag, flags_before, special)
        self.flags = frozenset()
        self.lists = []
        self.li = 0
        self.skip = 0               # inside <style>/<script>/<head>...
        self.formatted = False      # anything beyond plain paragraphs seen?

    def _flush(self):
        merged = []
        for f, t in self.runs:
            if self.kind == "h":
                f = f - {"bold"}                    # heading style already implies it
            if merged and merged[-1][1].endswith((" ", "\n")) and t.startswith(" "):
                t = t.lstrip(" ")                   # HTML collapses spaces across elements
            if not t:
                continue
            if merged and merged[-1][0] == f:
                merged[-1][1] += t
            else:
                merged.append([f, t])
        if merged:
            merged[0][1] = merged[0][1].lstrip(" ")
            merged[-1][1] = merged[-1][1].rstrip(" ")
        line = re.sub(r" *\n *", "\n", "".join(_wrap(f, t) for f, t in merged)).strip("\n")
        if line.strip():
            self.blocks.append((self.kind, self.prefix + line))
        self.runs, self.kind, self.prefix = [], "p", ""

    def handle_starttag(self, tag, attrs):
        style = re.sub(r"\s+", "", dict(attrs).get("style") or "").lower()
        if tag == "br":
            self.runs.append((self.flags, "\n" if self.kind == "p" else " "))
            return
        if tag in _VOID:
            return
        special = None
        if tag in _SKIP:
            self.skip += 1; special = "skip"
        elif "mso-list:ignore" in style:            # Word's fake bullet glyph
            self.skip += 1; special = "skip"
        if tag in ("ul", "ol"):
            self._flush(); self.lists.append(tag)
        elif tag == "li":
            self._flush()
            self.kind = "li"
            self.prefix = "  " * max(len(self.lists) - 1, 0) + ("1. " if self.lists[-1:] == ["ol"] else "- ")
            self.li += 1; self.formatted = True
        elif tag in _HEADING:
            self._flush()
            self.kind, self.prefix = "h", "#" * int(tag[1]) + " "
            self.formatted = True
        elif tag in ("p", "div", "tr", "blockquote", "pre") and not (self.li and tag in ("p", "div")):
            self._flush()
        on, off = _style_flags(tag, style)
        self.stack.append((tag, self.flags, special))
        self.flags = frozenset((self.flags | on) - off)

    def handle_endtag(self, tag):
        idx = next((i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i][0] == tag), None)
        if idx is None:
            return
        self.flags = self.stack[idx][1]
        self.skip -= sum(sp == "skip" for _, _, sp in self.stack[idx:])
        del self.stack[idx:]
        if tag in ("ul", "ol"):
            self._flush()
            if self.lists: self.lists.pop()
        elif tag == "li":
            self._flush(); self.li = max(self.li - 1, 0)
        elif tag in _HEADING or (tag in ("p", "div", "tr", "blockquote", "pre") and not self.li):
            self._flush()
        elif tag in ("td", "th"):
            self.runs.append((self.flags, " "))

    def handle_data(self, data):
        if self.skip:
            return
        data = re.sub(r"[ \t\r\n\f\xa0]+", " ", data)
        if data:
            self.runs.append((self.flags, data))
            if self.flags:
                self.formatted = True

    def result(self):
        self._flush()
        out = ""
        for i, (kind, line) in enumerate(self.blocks):
            if i:  # blank line between plain paragraphs; headings/lists sit flush
                out += "\n\n" if kind == "p" and self.blocks[i - 1][0] == "p" else "\n"
            out += line
        return out


def html_to_markdown(html):
    """Markdown for the formatter, or None if the HTML has no formatting worth
    converting (then plain text is the more faithful thing to type: it keeps
    indentation and spacing that HTML collapses)."""
    p = _MD()
    p.feed(html)
    p.close()
    return p.result() if p.formatted and p.blocks else None
