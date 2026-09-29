"""Tier 1: a fake driver that behaves like a text editor (append-only cursor).
Records every action so a wrong output can be traced to the keystroke."""


class SimEditorDriver:
    def __init__(self, clipboard=""):
        self.buf = []
        self.log = []          # (kind, arg, len(buf) after)
        self.clipboard = clipboard

    @property
    def text(self):
        return "".join(self.buf)

    def _rec(self, kind, arg=""):
        self.log.append((kind, arg, len(self.buf)))

    # --- driver interface used by TypingEngine ---
    def send_char(self, c, dwell=0.0):
        self.buf.extend(c)                 # keyboard.type("\n") == Enter in a browser
        self._rec("char", c)

    def send_backspace(self):
        if self.buf:
            self.buf.pop()
        self._rec("backspace")

    def send_enter(self):
        self.buf.append("\n"); self._rec("key", "Enter")

    def send_shift_enter(self):
        self.buf.append("\n"); self._rec("key", "Shift+Enter")

    def send_tab(self):
        self.buf.append("\t"); self._rec("key", "Tab")

    def send_key(self, k):
        kl = k.lower()
        if kl == "enter" or kl == "shift+enter":
            self.buf.append("\n")
        elif kl == "tab":
            self.buf.append("\t")
        # formatting shortcuts (Ctrl+B, Ctrl+Alt+1, ...) don't change text
        self._rec("key", k)

    def surgical_paste(self, text):
        self.buf.extend(text); self._rec("paste", text)

    def focused_kind(self): return "rich"
    def page_url(self): return ""
    def exec_command(self, cmd, value=None): self._rec("exec", cmd)

    def attach(self, title=None): pass
    def detach(self): pass
    def get_clipboard(self): return self.clipboard
    def detect_layout(self): return "QWERTY"

    def context(self, char_pos, n=25):
        """Actions around the first action whose buffer length reaches char_pos."""
        idx = next((i for i, (_, _, ln) in enumerate(self.log) if ln > char_pos), len(self.log) - 1)
        lo = max(0, idx - n)
        return [(i,) + a for i, a in enumerate(self.log[lo: idx + 5], lo)]
