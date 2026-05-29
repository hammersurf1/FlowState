"""
FlowState — Settings GUI (Enhanced)
A tabbed settings window using tkinter, launchable from the system tray.
Uses native system theme. Supports press-to-record hotkey capture,
live typing preview, one-click presets, tooltips, and import/export.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
import random
import shutil


# ─── Tooltip Helper ──────────────────────────────────────────────────────

class _Tooltip:
    """Simple hover tooltip for any widget."""

    def __init__(self, widget, text, delay=400):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._tip = None
        self._id = None
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)
        widget.bind("<ButtonPress>", self._on_leave)

    def _on_enter(self, _event=None):
        self._id = self.widget.after(self.delay, self._show)

    def _on_leave(self, _event=None):
        if self._id:
            self.widget.after_cancel(self._id)
            self._id = None
        self._hide()

    def _show(self):
        if self._tip:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self._tip = tk.Toplevel(self.widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(
            self._tip, text=self.text, justify="left",
            background="#ffffe0", foreground="#333333",
            relief="solid", borderwidth=1,
            font=("Segoe UI", 9), padx=8, pady=4,
            wraplength=380
        )
        lbl.pack()

    def _hide(self):
        if self._tip:
            self._tip.destroy()
            self._tip = None


def add_tooltip(widget, text):
    """Attach a tooltip to a widget."""
    _Tooltip(widget, text)


# ─── Hotkey Recorder ─────────────────────────────────────────────────────

class HotkeyRecorder:
    """
    A widget that captures a keyboard shortcut via press-to-record.
    Click 'Record', press the key combo, it gets captured and displayed.
    """

    def __init__(self, parent, label_text, initial_value, row):
        self.value = initial_value
        self._recording = False
        self._pressed_keys = set()
        self._combo_parts = []

        frame = ttk.Frame(parent)
        frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=4)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text=label_text).grid(
            row=0, column=0, sticky="w", padx=(0, 10)
        )

        self.display_var = tk.StringVar(value=initial_value)
        self.display_entry = ttk.Entry(
            frame, textvariable=self.display_var, state="readonly", width=24
        )
        self.display_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        self.record_btn = ttk.Button(
            frame, text="Record", width=8, command=self._toggle_recording
        )
        self.record_btn.grid(row=0, column=2)

    def _toggle_recording(self):
        if self._recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        self._recording = True
        self._pressed_keys = set()
        self._combo_parts = []
        self.record_btn.configure(text="Stop")
        self.display_var.set("Press keys...")

        top = self.record_btn.winfo_toplevel()
        top.bind("<KeyPress>", self._on_key_press)
        top.bind("<KeyRelease>", self._on_key_release)
        top.focus_force()

    def _stop_recording(self):
        self._recording = False
        self.record_btn.configure(text="Record")

        top = self.record_btn.winfo_toplevel()
        top.unbind("<KeyPress>")
        top.unbind("<KeyRelease>")

        if self._combo_parts:
            self.value = "+".join(self._combo_parts)
            self.display_var.set(self.value)
        else:
            self.display_var.set(self.value)

    def _on_key_press(self, event):
        if not self._recording:
            return
        key_name = self._normalize_key(event)
        if key_name and key_name not in self._pressed_keys:
            self._pressed_keys.add(key_name)
            self._combo_parts.append(key_name)
            self.display_var.set("+".join(self._combo_parts))

    def _on_key_release(self, event):
        if not self._recording:
            return
        if self._combo_parts:
            self._stop_recording()

    @staticmethod
    def _normalize_key(event):
        """Convert a tkinter key event into a human-readable key name
        compatible with the keyboard (Windows) / pynput (macOS) libraries."""
        modifiers = {
            "Control_L": "ctrl", "Control_R": "ctrl",
            "Alt_L": "alt", "Alt_R": "alt",
            "Shift_L": "shift", "Shift_R": "shift",
            "Meta_L": "cmd", "Meta_R": "cmd",
            "Super_L": "cmd", "Super_R": "cmd",
        }
        if event.keysym in modifiers:
            return modifiers[event.keysym]

        named = {
            "Escape": "esc", "Return": "enter", "space": "space",
            "Tab": "tab", "BackSpace": "backspace", "Delete": "delete",
            "Up": "up", "Down": "down", "Left": "left", "Right": "right",
            "F1": "f1", "F2": "f2", "F3": "f3", "F4": "f4",
            "F5": "f5", "F6": "f6", "F7": "f7", "F8": "f8",
            "F9": "f9", "F10": "f10", "F11": "f11", "F12": "f12",
        }
        if event.keysym in named:
            return named[event.keysym]

        if len(event.keysym) == 1:
            return event.keysym.lower()

        char = event.char
        if char and char.isprintable():
            return char.lower()

        return event.keysym.lower()


# ─── Typing Preview Engine ───────────────────────────────────────────────

class TypingPreview:
    """
    Simulates typing into a tkinter Text widget using the current settings.
    This is a *visual* preview only — no actual keystrokes are sent.
    """

    def __init__(self, text_widget, settings, on_done=None):
        self.widget = text_widget
        self.settings = settings
        self.on_done = on_done
        self._after_id = None
        self._cancelled = False

    def start(self, text):
        self.widget.delete("1.0", tk.END)
        self._cancelled = False
        self._type_char(text, 0)

    def stop(self):
        self._cancelled = True
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _gaussian(self, mean, stddev):
        val = int(random.gauss(mean, stddev))
        return max(10, val)

    def _type_char(self, text, idx):
        if self._cancelled or idx >= len(text):
            if self.on_done:
                self.on_done()
            return

        char = text[idx]
        self.widget.insert(tk.END, char)
        self.widget.see(tk.END)

        # Calculate delay based on settings
        mean = self.settings.get("UserMeanDelay", 35)
        variance = self.settings.get("UserVariance", 45)

        # Sentence-end pause
        next_char = text[idx + 1] if idx + 1 < len(text) else ""
        if char in ".!?" and next_char in " \n":
            delay = random.randint(
                self.settings.get("SentencePauseMs", 1200),
                self.settings.get("SentencePauseMs", 1200) + 400
            )
        # Comma/semicolon pause
        elif char in ",;":
            delay = random.randint(300, 600)
        # Newline
        elif char == "\n":
            delay = random.randint(
                self.settings.get("ParagraphPauseMs", 2000),
                self.settings.get("ParagraphPauseMs", 2000) + 1000
            )
        else:
            delay = self._gaussian(mean, variance)
            # Common bigram speedup
            bigram = (char + next_char).lower()
            if bigram in ["th", "he", "in", "er", "an", "re", "on", "at", "en",
                          "nd", "ti", "es", "or", "te", "of", "ed", "is", "it",
                          "al", "ar", "st", "to", "nt"]:
                delay -= 10
            delay = max(10, min(delay, 250))

        self._after_id = self.widget.after(delay, self._type_char, text, idx + 1)


# ─── Settings Window ─────────────────────────────────────────────────────

class SettingsWindow:
    """
    Full settings GUI for FlowState. Takes an engine reference and an
    optional callback for when hotkeys change.
    """

    _instance_open = False

    # One-click presets: name -> {setting_key: value}
    PRESETS = {
        "Fast & Clean": {
            "UserMeanDelay": 15, "UserVariance": 20,
            "TypoChance": 0, "TypoDelay": 80, "RevisionChance": 0,
            "SentencePauseMs": 600, "ParagraphPauseMs": 1200,
            "BrainstormFrequency": 200, "EmojiPauseMs": 1000,
            "EnableTypos": 0, "EnableRevisions": 0,
            "EnableBrainstormPauses": 0, "EnableSmartRevisions": 0,
            "EnableFrequencyTypos": 0, "EnableDeferredCorrections": 0,
            "EnableFingerPenalty": 1, "EnableFluencyStates": 0,
            "EnableNumberSymbolCare": 1, "EnableCapsRunRealism": 1,
            "EnableSemanticSpeed": 1, "EnableClausePauses": 1,
            "EnableChunkBurst": 1, "EnableEntityCare": 1,
        },
        "Balanced": {
            "UserMeanDelay": 35, "UserVariance": 45,
            "TypoChance": 3, "TypoDelay": 125, "RevisionChance": 5,
            "SentencePauseMs": 1200, "ParagraphPauseMs": 2000,
            "BrainstormFrequency": 60, "EmojiPauseMs": 1800,
            "EnableTypos": 1, "EnableRevisions": 1,
            "EnableBrainstormPauses": 1, "EnableSmartRevisions": 1,
            "EnableFrequencyTypos": 1, "EnableDeferredCorrections": 1,
            "EnableFingerPenalty": 1, "EnableFluencyStates": 1,
            "EnableNumberSymbolCare": 1, "EnableCapsRunRealism": 1,
            "EnableSemanticSpeed": 1, "EnableClausePauses": 1,
            "EnableChunkBurst": 1, "EnableEntityCare": 1,
        },
        "Slow & Careful": {
            "UserMeanDelay": 80, "UserVariance": 70,
            "TypoChance": 5, "TypoDelay": 150, "RevisionChance": 8,
            "SentencePauseMs": 1800, "ParagraphPauseMs": 3000,
            "BrainstormFrequency": 40, "EmojiPauseMs": 2500,
            "EnableTypos": 1, "EnableRevisions": 1,
            "EnableBrainstormPauses": 1, "EnableSmartRevisions": 1,
            "EnableFrequencyTypos": 1, "EnableDeferredCorrections": 1,
            "EnableFingerPenalty": 1, "EnableFluencyStates": 1,
            "EnableNumberSymbolCare": 1, "EnableCapsRunRealism": 1,
            "EnableSemanticSpeed": 1, "EnableClausePauses": 1,
            "EnableChunkBurst": 1, "EnableEntityCare": 1,
        },
        "Maximum Realism": {
            "UserMeanDelay": 55, "UserVariance": 60,
            "TypoChance": 7, "TypoDelay": 180, "RevisionChance": 10,
            "SentencePauseMs": 1500, "ParagraphPauseMs": 2500,
            "BrainstormFrequency": 30, "EmojiPauseMs": 2200,
            "EnableTypos": 1, "EnableRevisions": 1,
            "EnableBrainstormPauses": 1, "EnableSmartRevisions": 1,
            "EnableFrequencyTypos": 1, "EnableDeferredCorrections": 1,
            "EnableFingerPenalty": 1, "EnableFluencyStates": 1,
            "EnableNumberSymbolCare": 1, "EnableCapsRunRealism": 1,
            "EnableSemanticSpeed": 1, "EnableClausePauses": 1,
            "EnableChunkBurst": 1, "EnableEntityCare": 1,
            "EnableCompositionPauses": 0,
            "CompositionPauseMinMs": 300, "CompositionPauseMaxMs": 6000,
            "ParagraphPlanningMinMs": 2000, "ParagraphPlanningMaxMs": 8000,
            "CompositionSensitivity": 50,
        },
        "Essay Drafting": {
            "UserMeanDelay": 95, "UserVariance": 55,
            "TypoChance": 4, "TypoDelay": 140, "RevisionChance": 8,
            "SentencePauseMs": 1800, "ParagraphPauseMs": 3500,
            "BrainstormFrequency": 60, "EmojiPauseMs": 2200,
            "EnableTypos": 1, "EnableRevisions": 1,
            "EnableBrainstormPauses": 0, "EnableSmartRevisions": 1,
            "EnableFrequencyTypos": 1, "EnableDeferredCorrections": 1,
            "EnableFingerPenalty": 1, "EnableFluencyStates": 1,
            "EnableNumberSymbolCare": 1, "EnableCapsRunRealism": 1,
            "EnableSemanticSpeed": 1, "EnableClausePauses": 1,
            "EnableChunkBurst": 1, "EnableEntityCare": 1,
            "EnableCompositionPauses": 1,
            "CompositionPauseMinMs": 400, "CompositionPauseMaxMs": 8000,
            "ParagraphPlanningMinMs": 3000, "ParagraphPlanningMaxMs": 9000,
            "CompositionSensitivity": 65,
        },
    }

    def __init__(self, engine, on_hotkey_change=None):
        if SettingsWindow._instance_open:
            return
        SettingsWindow._instance_open = True

        self.engine = engine
        self.on_hotkey_change = on_hotkey_change

        self.root = tk.Tk()
        self.root.title("FlowState Settings")
        self.root.geometry("640x700")
        self.root.minsize(520, 500)
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Keyboard shortcuts
        self.root.bind("<Control-s>", lambda _e: self._save())
        self.root.bind("<Escape>", lambda _e: self._on_close())

        # Native theme
        style = ttk.Style()
        if sys.platform == "win32":
            try:
                style.theme_use("vista")
            except tk.TclError:
                style.theme_use("clam")
        elif sys.platform == "darwin":
            try:
                style.theme_use("aqua")
            except tk.TclError:
                style.theme_use("clam")
        else:
            style.theme_use("clam")

        style.configure("Header.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Title.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("Value.TLabel", font=("Segoe UI", 9, "bold"), foreground="#0066cc")
        style.configure("Desc.TLabel", font=("Segoe UI", 8), foreground="#666666")
        style.configure("Status.TLabel", font=("Segoe UI", 9), foreground="#006600")

        self.vars = {}
        self.hotkey_recorders = {}
        self._preview_engine = None

        # ── Top bar: Presets + Status ──
        top_bar = ttk.Frame(self.root, padding=(12, 8))
        top_bar.pack(fill="x")
        top_bar.columnconfigure(1, weight=1)

        ttk.Label(top_bar, text="Preset:", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        self._preset_var = tk.StringVar(value="Custom")
        preset_combo = ttk.Combobox(
            top_bar, textvariable=self._preset_var,
            values=["Custom"] + list(self.PRESETS.keys()),
            state="readonly", width=20
        )
        preset_combo.grid(row=0, column=1, sticky="w", padx=(6, 0))
        preset_combo.bind("<<ComboboxSelected>>", self._on_preset_change)
        add_tooltip(preset_combo, "Apply a one-click preset configuration.\n"
                    "This updates all sliders and toggles to match the preset.")

        # Active profile indicator
        self._status_var = tk.StringVar(value="")
        self._status_lbl = ttk.Label(top_bar, textvariable=self._status_var, style="Status.TLabel")
        self._status_lbl.grid(row=0, column=2, sticky="e")
        self._update_status()

        # ── Notebook (Tabs) ──
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=12, pady=(0, 0))

        tab_typing = ttk.Frame(notebook, padding=16)
        notebook.add(tab_typing, text="  Typing  ")
        self._build_typing_tab(tab_typing)

        tab_behavior = ttk.Frame(notebook, padding=16)
        notebook.add(tab_behavior, text="  Behavior  ")
        self._build_behavior_tab(tab_behavior)

        tab_hotkeys = ttk.Frame(notebook, padding=16)
        notebook.add(tab_hotkeys, text="  Hotkeys  ")
        self._build_hotkeys_tab(tab_hotkeys)

        tab_profiles = ttk.Frame(notebook, padding=16)
        notebook.add(tab_profiles, text="  Profiles  ")
        self._build_profiles_tab(tab_profiles)

        tab_preview = ttk.Frame(notebook, padding=16)
        notebook.add(tab_preview, text="  Preview  ")
        self._build_preview_tab(tab_preview)

        # ── Footer Buttons ──
        btn_frame = ttk.Frame(self.root, padding=(12, 10))
        btn_frame.pack(side="bottom", fill="x")

        ttk.Button(
            btn_frame, text="Import...", command=self._import_settings
        ).pack(side="left", padx=(0, 4))
        ttk.Button(
            btn_frame, text="Export...", command=self._export_settings
        ).pack(side="left")

        ttk.Button(
            btn_frame, text="Reset to Defaults", command=self._reset_defaults
        ).pack(side="left", padx=(16, 0))

        ttk.Button(btn_frame, text="Save  (Ctrl+S)", command=self._save).pack(
            side="right", padx=(8, 0)
        )
        ttk.Button(btn_frame, text="Cancel  (Esc)", command=self._on_close).pack(
            side="right"
        )

        self.root.mainloop()

    # ─── Tab Builders ──────────────────────────────────────────────

    def _build_typing_tab(self, parent):
        self._add_section(parent, "Typing Speed & Variance")
        self._add_slider(
            parent, "UserMeanDelay", "Typing Speed (Lower = Faster)",
            5, 200, "Average delay in ms between keystrokes.\n"
                    "Humans average 30–60 ms; bots often sit at 0–10 ms."
        )
        self._add_slider(
            parent, "UserVariance", "Variance (Randomness)",
            0, 150, "Standard deviation of keystroke timing.\n"
                    "Higher = more erratic, human-like rhythm."
        )

        self._add_section(parent, "Errors & Corrections")
        self._add_slider(
            parent, "TypoChance", "Typo Chance (%)",
            0, 30, "Probability of a spatial/transposition typo per keystroke."
        )
        self._add_slider(
            parent, "TypoDelay", "Correction Speed (ms)",
            50, 500, "Pause before correcting a typo with backspace."
        )
        self._add_slider(
            parent, "RevisionChance", "Word Revision Chance (%)",
            0, 30, "Probability of mistyping a common word, then correcting it."
        )

    def _build_behavior_tab(self, parent):
        self._add_section(parent, "Human-like Pauses")
        self._add_slider(
            parent, "SentencePauseMs", "Sentence Pause (ms)",
            200, 4000, "Pause after sentence-ending punctuation (. ? !)"
        )
        self._add_slider(
            parent, "ParagraphPauseMs", "Paragraph Pause (ms)",
            500, 6000, "Pause at line breaks / new paragraphs"
        )
        self._add_slider(
            parent, "EmojiPauseMs", "Emoji / Symbol Pause (ms)",
            200, 4000, "Pause before pasting emoji or special characters"
        )
        self._add_slider(
            parent, "BrainstormFrequency", "Random Pause Frequency",
            10, 200, "Average words between random 'thinking' pauses"
        )
        self._add_slider(
            parent, "CompositionPauseMinMs", "Composition Pause Min (ms)",
            0, 2000, "Minimum content-aware hesitation before a word or phrase"
        )
        self._add_slider(
            parent, "CompositionPauseMaxMs", "Composition Pause Max (ms)",
            1000, 10000, "Maximum pre-typing composition pause"
        )
        self._add_slider(
            parent, "ParagraphPlanningMinMs", "Paragraph Planning Min (ms)",
            500, 6000, "Minimum pause before starting a new paragraph"
        )
        self._add_slider(
            parent, "ParagraphPlanningMaxMs", "Paragraph Planning Max (ms)",
            2000, 15000, "Maximum pause before starting a new paragraph"
        )
        self._add_slider(
            parent, "CompositionSensitivity", "Composition Sensitivity",
            0, 100, "Scale for content-aware pauses (50 = normal)"
        )

        self._add_section(parent, "Behavior Toggles")
        self._add_checkbox(
            parent, "EnableTypos",
            "Enable typos (spatial, transposition, omission, doubling)"
        )
        self._add_checkbox(
            parent, "EnableRevisions",
            "Enable word-level revisions (legacy — use Smart Revisions below)"
        )
        self._add_checkbox(
            parent, "EnableBrainstormPauses",
            "Enable random 'brainstorm' pauses"
        )
        self._add_checkbox(
            parent, "EnableCompositionPauses",
            "Composition pauses — content-aware drafting hesitation (replaces random brainstorm)"
        )
        self._add_checkbox(
            parent, "UseEnterOnly",
            "Use plain Enter instead of Shift+Enter for new lines"
        )
        self._add_checkbox(
            parent, "EnableRichText",
            "Enable rich-text formatting (bold, italic, lists, headings, etc.)"
        )

        self._add_section(parent, "Semantic Humanization")
        self._add_checkbox(
            parent, "EnableSmartRevisions",
            "Smart revisions — type a WordNet synonym, backspace, then correct"
        )
        self._add_checkbox(
            parent, "EnableSemanticSpeed",
            "Semantic speed — rare words slower, common words faster"
        )
        self._add_checkbox(
            parent, "EnableEntityCare",
            "Entity care — fewer typos on named entities (people, places, orgs)"
        )
        self._add_checkbox(
            parent, "EnableClausePauses",
            "Clause pauses — micro-pauses at subordinate clause boundaries"
        )
        self._add_checkbox(
            parent, "EnableChunkBurst",
            "Chunk burst — type noun phrases as single cognitive bursts"
        )
        self._add_checkbox(
            parent, "EnableFrequencyTypos",
            "Frequency-based typos — common words have fewer typos"
        )
        self._add_checkbox(
            parent, "EnableDeferredCorrections",
            "Deferred corrections — finish word before backspacing a typo"
        )

        self._add_section(parent, "Motor Realism")
        self._add_checkbox(
            parent, "EnableFingerPenalty",
            "Same-finger penalty — slower when same finger types two chars"
        )
        self._add_checkbox(
            parent, "EnableFluencyStates",
            "Fluency states — alternate between fluent and disfluent periods"
        )
        self._add_checkbox(
            parent, "EnableNumberSymbolCare",
            "Number / symbol care — slower, fewer typos on digits and symbols"
        )
        self._add_checkbox(
            parent, "EnableCapsRunRealism",
            "Caps Lock realism — delay on first capital only in a run"
        )

    def _build_profiles_tab(self, parent):
        """Build the per-app profiles configuration tab."""
        self._add_section(parent, "App Profiles")

        desc = ttk.Label(parent, text=(
            "Profiles override typing settings for specific applications.\n"
            "Match by substring in the active window title (case-insensitive)."
        ), style="Desc.TLabel", wraplength=560, justify="left")
        desc.pack(anchor="w", pady=(0, 12))

        # Listbox of existing profiles
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill="x", pady=6)

        self._profile_listbox = tk.Listbox(list_frame, height=5)
        self._profile_listbox.pack(side="left", fill="both", expand=True)
        self._profile_listbox.bind("<<ListboxSelect>>", self._on_profile_select)

        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(side="right", padx=(8, 0))

        ttk.Button(btn_frame, text="Add", command=self._add_profile, width=7).pack(pady=2)
        ttk.Button(btn_frame, text="Delete", command=self._delete_profile, width=7).pack(pady=2)

        # Profile editor fields
        self._prof_vars = {}
        self._prof_pattern_var = tk.StringVar()

        ttk.Label(parent, text="Window Pattern (substring):").pack(anchor="w", pady=(12, 2))
        ttk.Entry(parent, textvariable=self._prof_pattern_var, width=50).pack(fill="x")

        prof_fields = [
            ("UserMeanDelay", "Typing Speed"),
            ("UserVariance", "Variance"),
            ("TypoChance", "Typo Chance (%)"),
            ("TypoDelay", "Correction Speed (ms)"),
            ("RevisionChance", "Revision Chance (%)"),
        ]
        for key, label in prof_fields:
            f = ttk.Frame(parent)
            f.pack(fill="x", pady=2)
            ttk.Label(f, text=label, width=22).pack(side="left")
            self._prof_vars[key] = tk.IntVar(value=self.engine.settings.get(key, 0))
            s = ttk.Scale(f, from_={"UserMeanDelay": (5, 200), "UserVariance": (0, 150),
                                     "TypoChance": (0, 30), "TypoDelay": (50, 500),
                                     "RevisionChance": (0, 30)}[key][0],
                          to={"UserMeanDelay": (5, 200), "UserVariance": (0, 150),
                              "TypoChance": (0, 30), "TypoDelay": (50, 500),
                              "RevisionChance": (0, 30)}[key][1],
                          variable=self._prof_vars[key])
            s.pack(side="left", fill="x", expand=True)

        ttk.Button(parent, text="Save Profile", command=self._save_profile).pack(pady=12)

        # Populate listbox
        self._refresh_profile_listbox()

    def _build_preview_tab(self, parent):
        """Build the live typing preview tab."""
        self._add_section(parent, "Live Typing Preview")

        desc = ttk.Label(parent, text=(
            "Paste text below and click Preview to see how your current settings\n"
            "will feel. This is a visual simulation — no real keystrokes are sent."
        ), style="Desc.TLabel", wraplength=560, justify="left")
        desc.pack(anchor="w", pady=(0, 12))

        # Source text
        src_frame = ttk.LabelFrame(parent, text="Source Text", padding=6)
        src_frame.pack(fill="x", pady=(0, 8))
        self._preview_src = tk.Text(src_frame, height=4, wrap="word", font=("Segoe UI", 10))
        self._preview_src.pack(fill="both", expand=True)
        self._preview_src.insert("1.0", "The quarterly results were excellent because Alice worked hard.")

        # Controls
        ctrl_frame = ttk.Frame(parent)
        ctrl_frame.pack(fill="x", pady=(0, 8))

        self._preview_btn = ttk.Button(
            ctrl_frame, text="▶  Preview", command=self._start_preview
        )
        self._preview_btn.pack(side="left", padx=(0, 8))

        self._preview_stop_btn = ttk.Button(
            ctrl_frame, text="⏹  Stop", command=self._stop_preview, state="disabled"
        )
        self._preview_stop_btn.pack(side="left")

        ttk.Label(ctrl_frame, text="Speed multiplier:").pack(side="left", padx=(20, 4))
        self._preview_speed_var = tk.DoubleVar(value=1.0)
        ttk.Spinbox(ctrl_frame, from_=0.1, to=5.0, increment=0.1,
                    textvariable=self._preview_speed_var, width=5).pack(side="left")

        # Output text
        out_frame = ttk.LabelFrame(parent, text="Preview Output", padding=6)
        out_frame.pack(fill="both", expand=True)
        self._preview_out = tk.Text(out_frame, height=8, wrap="word", font=("Consolas", 11),
                                    state="normal", bg="#f8f8f8")
        self._preview_out.pack(fill="both", expand=True)
        self._preview_out.insert("1.0", "Preview output will appear here...")
        self._preview_out.config(state="disabled")

    def _build_hotkeys_tab(self, parent):
        self._add_section(parent, "Hotkey Configuration")

        is_mac = sys.platform == "darwin"
        trigger_desc = "Cmd+Option+V" if is_mac else "Ctrl+Alt+V"
        pause_desc = "Esc"

        desc = ttk.Label(parent, text=(
            "Click 'Record', then press your desired key combination.\n"
            "The hotkey will be captured when you release a key."
        ), style="Desc.TLabel", wraplength=560, justify="left")
        desc.pack(anchor="w", pady=(0, 12))

        hotkey_frame = ttk.Frame(parent)
        hotkey_frame.pack(fill="x")
        hotkey_frame.columnconfigure(1, weight=1)

        self.hotkey_recorders["TriggerHotkey"] = HotkeyRecorder(
            hotkey_frame,
            f"Trigger Typing (default: {trigger_desc}):",
            self.engine.hotkeys.get("TriggerHotkey", "ctrl+alt+v"),
            row=0
        )

        self.hotkey_recorders["PauseKey"] = HotkeyRecorder(
            hotkey_frame,
            f"Pause / Abort (default: {pause_desc}):",
            self.engine.hotkeys.get("PauseKey", "esc"),
            row=1
        )

        note = ttk.Label(parent, text=(
            "Note: Hotkey changes take effect immediately after saving.\n"
            "If you set an invalid combination, the previous hotkey "
            "will be restored."
        ), style="Desc.TLabel", wraplength=560, justify="left")
        note.pack(anchor="w", pady=(20, 0))

    # ─── Widget Helpers ────────────────────────────────────────────

    def _add_section(self, parent, title):
        lbl = ttk.Label(parent, text=title, style="Header.TLabel")
        lbl.pack(anchor="w", pady=(14, 2))
        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=(0, 8))

    def _add_slider(self, parent, key, label, min_val, max_val, tooltip=""):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=(0, 4))

        current_val = self.engine.settings.get(key, 0)
        self.vars[key] = tk.IntVar(value=current_val)

        # Two-column layout: label left, value right
        top_frame = ttk.Frame(frame)
        top_frame.pack(fill="x")
        ttk.Label(top_frame, text=label).pack(side="left")
        val_lbl = ttk.Label(
            top_frame, text=str(current_val), style="Value.TLabel"
        )
        val_lbl.pack(side="right")

        def update_lbl(v):
            val_lbl.config(text=str(int(float(v))))

        s = ttk.Scale(
            frame, from_=min_val, to=max_val, variable=self.vars[key],
            orient="horizontal", command=update_lbl
        )
        s.pack(fill="x", pady=(2, 0))

        if tooltip:
            add_tooltip(s, tooltip)
            add_tooltip(frame, tooltip)

    def _add_checkbox(self, parent, key, label):
        current_val = self.engine.settings.get(key, 0)
        self.vars[key] = tk.BooleanVar(value=bool(current_val))
        cb = ttk.Checkbutton(parent, text=label, variable=self.vars[key])
        cb.pack(anchor="w", pady=3)

    # ─── Preview Actions ───────────────────────────────────────────

    def _start_preview(self):
        text = self._preview_src.get("1.0", tk.END).rstrip("\n")
        if not text:
            return

        self._preview_out.config(state="normal")
        self._preview_out.delete("1.0", tk.END)
        self._preview_out.config(state="disabled")

        self._preview_btn.config(state="disabled")
        self._preview_stop_btn.config(state="normal")

        # Build a temporary settings dict scaled by speed multiplier
        speed_mult = self._preview_speed_var.get()
        preview_settings = {}
        for k, v in self.engine.settings.items():
            if isinstance(v, int) and "Delay" in k or "Pause" in k or "Ms" in k:
                preview_settings[k] = max(1, int(v / speed_mult))
            else:
                preview_settings[k] = v
        # Always keep these
        preview_settings["UserMeanDelay"] = max(1, int(self.engine.settings.get("UserMeanDelay", 35) / speed_mult))
        preview_settings["UserVariance"] = max(1, int(self.engine.settings.get("UserVariance", 45) / speed_mult))

        self._preview_out.config(state="normal")
        self._preview_engine = TypingPreview(
            self._preview_out, preview_settings,
            on_done=self._on_preview_done
        )
        self._preview_engine.start(text)

    def _stop_preview(self):
        if self._preview_engine:
            self._preview_engine.stop()
        self._on_preview_done()

    def _on_preview_done(self):
        self._preview_btn.config(state="normal")
        self._preview_stop_btn.config(state="disabled")
        self._preview_engine = None

    # ─── Presets ───────────────────────────────────────────────────

    def _on_preset_change(self, _event=None):
        name = self._preset_var.get()
        if name == "Custom" or name not in self.PRESETS:
            return

        preset = self.PRESETS[name]
        for key, val in preset.items():
            if key in self.vars:
                var = self.vars[key]
                if isinstance(var, tk.BooleanVar):
                    var.set(bool(val))
                elif isinstance(var, tk.IntVar):
                    var.set(val)

    # ─── Profile Actions ───────────────────────────────────────────

    def _refresh_profile_listbox(self):
        """Populate the profile listbox from engine's profile manager."""
        self._profile_listbox.delete(0, tk.END)
        for name in self.engine.profile_manager.profiles:
            self._profile_listbox.insert(tk.END, name)

    def _on_profile_select(self, _event=None):
        """Load selected profile values into the editor."""
        sel = self._profile_listbox.curselection()
        if not sel:
            return
        name = self._profile_listbox.get(sel[0])
        prof = self.engine.profile_manager.profiles.get(name, {})
        self._prof_pattern_var.set(prof.get("windowpattern", ""))
        for key, var in self._prof_vars.items():
            var.set(int(prof.get(key, self.engine.defaults.get(key, 0))))

    def _add_profile(self):
        """Add a blank profile entry."""
        from tkinter import simpledialog
        name = simpledialog.askstring("Profile Name", "Enter a name for this profile:",
                                      parent=self.root)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        # Ensure section header format
        self._refresh_profile_listbox()
        self._prof_pattern_var.set("")
        for key, var in self._prof_vars.items():
            var.set(self.engine.settings.get(key, 0))

    def _delete_profile(self):
        """Remove the selected profile."""
        sel = self._profile_listbox.curselection()
        if not sel:
            return
        name = self._profile_listbox.get(sel[0])
        self.engine.profile_manager.profiles.pop(name, None)
        # Also remove from config
        section = f"Profile:{name}"
        self.engine.config.remove_section(section)
        self._refresh_profile_listbox()

    def _save_profile(self):
        """Save the current profile editor values."""
        sel = self._profile_listbox.curselection()
        name = sel[0] if sel else None
        if name is None:
            from tkinter import simpledialog
            name = simpledialog.askstring("Profile Name", "Enter profile name:",
                                          parent=self.root)
            if not name:
                return
            name = name.strip()
            if not name:
                return
        else:
            name = self._profile_listbox.get(name)

        profile = {"windowpattern": self._prof_pattern_var.get().strip()}
        for key, var in self._prof_vars.items():
            profile[key] = str(var.get())

        self.engine.profile_manager.profiles[name] = profile
        section = f"Profile:{name}"
        if not self.engine.config.has_section(section):
            self.engine.config.add_section(section)
        for k, v in profile.items():
            self.engine.config.set(section, k, v)

        self._refresh_profile_listbox()

    # ─── Import / Export ───────────────────────────────────────────

    def _import_settings(self):
        path = filedialog.askopenfilename(
            title="Import Settings",
            filetypes=[("INI files", "*.ini"), ("All files", "*.*")],
            parent=self.root
        )
        if not path:
            return
        try:
            shutil.copy(path, self.engine.ini_file)
            self.engine.load_settings()
            # Refresh all UI vars
            for key, var in self.vars.items():
                val = self.engine.settings.get(key, 0)
                if isinstance(var, tk.BooleanVar):
                    var.set(bool(val))
                else:
                    var.set(val)
            for key, recorder in self.hotkey_recorders.items():
                recorder.value = self.engine.hotkeys.get(key, recorder.value)
                recorder.display_var.set(recorder.value)
            self._refresh_profile_listbox()
            messagebox.showinfo("Import Successful", f"Settings imported from:\n{path}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Import Failed", str(e), parent=self.root)

    def _export_settings(self):
        path = filedialog.asksaveasfilename(
            title="Export Settings",
            defaultextension=".ini",
            filetypes=[("INI files", "*.ini"), ("All files", "*.*")],
            parent=self.root
        )
        if not path:
            return
        try:
            shutil.copy(self.engine.ini_file, path)
            messagebox.showinfo("Export Successful", f"Settings saved to:\n{path}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Export Failed", str(e), parent=self.root)

    # ─── Status ────────────────────────────────────────────────────

    def _update_status(self):
        """Show active profile info in the top bar."""
        profiles = self.engine.profile_manager.profiles
        if profiles:
            count = len(profiles)
            self._status_var.set(f"{count} profile{'s' if count != 1 else ''} configured")
        else:
            self._status_var.set("No profiles configured")

    # ─── Actions ───────────────────────────────────────────────────

    def _save(self):
        hotkeys_changed = False

        for key, var in self.vars.items():
            if isinstance(var, tk.BooleanVar):
                self.engine.settings[key] = 1 if var.get() else 0
            else:
                self.engine.settings[key] = var.get()

        for key, recorder in self.hotkey_recorders.items():
            new_val = recorder.value
            if new_val != self.engine.hotkeys.get(key, ""):
                hotkeys_changed = True
            self.engine.hotkeys[key] = new_val

        self.engine.save_settings()

        # Persist profiles to the config file
        for name, prof in self.engine.profile_manager.profiles.items():
            section = f"Profile:{name}"
            if not self.engine.config.has_section(section):
                self.engine.config.add_section(section)
            for k, v in prof.items():
                self.engine.config.set(section, k, v)
        # Remove stale profile sections
        for section in self.engine.config.sections():
            if section.startswith("Profile:"):
                prof_name = section[8:]
                if prof_name not in self.engine.profile_manager.profiles:
                    self.engine.config.remove_section(section)
        with open(self.engine.ini_file, "w") as cf:
            self.engine.config.write(cf)

        if self.engine.ui_update_callback:
            self.engine.ui_update_callback()

        if hotkeys_changed and self.on_hotkey_change:
            try:
                self.on_hotkey_change()
            except Exception as e:
                messagebox.showwarning(
                    "Hotkey Error",
                    f"Could not register new hotkeys:\n{e}\n\n"
                    "Previous hotkeys will be restored.",
                    parent=self.root
                )

        self._on_close()

    def _reset_defaults(self):
        confirm = messagebox.askyesno(
            "Reset to Defaults",
            "Reset all settings to their default values?\n\n"
            "Click 'Save' afterward to persist the changes.",
            parent=self.root
        )
        if not confirm:
            return

        for key, default_val in self.engine.defaults.items():
            if key in self.vars:
                var = self.vars[key]
                if isinstance(var, tk.BooleanVar):
                    var.set(bool(default_val))
                else:
                    var.set(default_val)

        for key, default_val in self.engine.default_hotkeys.items():
            if key in self.hotkey_recorders:
                self.hotkey_recorders[key].value = default_val
                self.hotkey_recorders[key].display_var.set(default_val)

        self._preset_var.set("Custom")

    def _on_close(self):
        if self._preview_engine:
            self._preview_engine.stop()
        SettingsWindow._instance_open = False
        self.root.destroy()
