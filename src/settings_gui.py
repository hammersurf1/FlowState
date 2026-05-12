"""
FlowState — Settings GUI
A tabbed settings window using tkinter, launchable from the system tray.
Uses native system theme. Supports press-to-record hotkey capture.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys


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


class SettingsWindow:
    """
    Full settings GUI for FlowState. Takes an engine reference and an
    optional callback for when hotkeys change.
    """

    _instance_open = False

    def __init__(self, engine, on_hotkey_change=None):
        if SettingsWindow._instance_open:
            return
        SettingsWindow._instance_open = True

        self.engine = engine
        self.on_hotkey_change = on_hotkey_change

        self.root = tk.Tk()
        self.root.title("FlowState Settings")
        self.root.geometry("520x620")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Use native theme
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
        style.configure(
            "Desc.TLabel", font=("Segoe UI", 8), foreground="#666666"
        )

        self.vars = {}
        self.hotkey_recorders = {}

        # --- Notebook (Tabs) ---
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=12, pady=(12, 0))

        tab_typing = ttk.Frame(notebook, padding=16)
        notebook.add(tab_typing, text="  Typing  ")
        self._build_typing_tab(tab_typing)

        tab_behavior = ttk.Frame(notebook, padding=16)
        notebook.add(tab_behavior, text="  Behavior  ")
        self._build_behavior_tab(tab_behavior)

        tab_hotkeys = ttk.Frame(notebook, padding=16)
        notebook.add(tab_hotkeys, text="  Hotkeys  ")
        self._build_hotkeys_tab(tab_hotkeys)

        # --- Footer Buttons ---
        btn_frame = ttk.Frame(self.root, padding=(12, 10))
        btn_frame.pack(side="bottom", fill="x")

        ttk.Button(
            btn_frame, text="Reset to Defaults", command=self._reset_defaults
        ).pack(side="left")
        ttk.Button(btn_frame, text="Save", command=self._save).pack(
            side="right", padx=(8, 0)
        )
        ttk.Button(btn_frame, text="Cancel", command=self._on_close).pack(
            side="right"
        )

        self.root.mainloop()

    # ─── Tab Builders ──────────────────────────────────────────────

    def _build_typing_tab(self, parent):
        self._add_section(parent, "Typing Speed & Variance")
        self._add_slider(
            parent, "UserMeanDelay", "Typing Speed (Lower = Faster)",
            5, 200, "Average delay in ms between keystrokes"
        )
        self._add_slider(
            parent, "UserVariance", "Variance (Randomness)",
            0, 150, "Standard deviation of keystroke timing"
        )

        self._add_section(parent, "Errors & Corrections")
        self._add_slider(
            parent, "TypoChance", "Typo Chance (%)",
            0, 30, "Probability of a spatial/transposition typo per keystroke"
        )
        self._add_slider(
            parent, "TypoDelay", "Correction Speed (ms)",
            50, 500, "Pause before correcting a typo with backspace"
        )
        self._add_slider(
            parent, "RevisionChance", "Word Revision Chance (%)",
            0, 30, "Probability of mistyping a common word, then correcting"
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

        self._add_section(parent, "Behavior Toggles")
        self._add_checkbox(
            parent, "EnableTypos",
            "Enable typos (spatial, transposition, omission, doubling)"
        )
        self._add_checkbox(
            parent, "EnableRevisions",
            "Enable word-level revisions (common misspellings)"
        )
        self._add_checkbox(
            parent, "EnableBrainstormPauses",
            "Enable random 'brainstorm' pauses"
        )
        self._add_checkbox(
            parent, "UseEnterOnly",
            "Use plain Enter instead of Shift+Enter for new lines"
        )

    def _build_hotkeys_tab(self, parent):
        self._add_section(parent, "Hotkey Configuration")

        is_mac = sys.platform == "darwin"
        trigger_desc = "Cmd+Option+V" if is_mac else "Ctrl+Alt+V"
        pause_desc = "Esc"

        desc = ttk.Label(parent, text=(
            "Click 'Record', then press your desired key combination.\n"
            "The hotkey will be captured when you release a key."
        ), style="Desc.TLabel", wraplength=440, justify="left")
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
        ), style="Desc.TLabel", wraplength=440, justify="left")
        note.pack(anchor="w", pady=(20, 0))

    # ─── Widget Helpers ────────────────────────────────────────────

    def _add_section(self, parent, title):
        lbl = ttk.Label(parent, text=title, style="Header.TLabel")
        lbl.pack(anchor="w", pady=(14, 2))
        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=(0, 8))

    def _add_slider(self, parent, key, label, min_val, max_val, desc=""):
        frame = ttk.Frame(parent)
        frame.pack(fill="x")

        current_val = self.engine.settings.get(key, 0)
        self.vars[key] = tk.IntVar(value=current_val)

        label_frame = ttk.Frame(frame)
        label_frame.pack(fill="x")
        ttk.Label(label_frame, text=label).pack(side="left")
        val_lbl = ttk.Label(
            label_frame, text=str(current_val), font=("Segoe UI", 9, "bold")
        )
        val_lbl.pack(side="right")

        def update_lbl(v):
            val_lbl.config(text=str(int(float(v))))

        s = ttk.Scale(
            frame, from_=min_val, to=max_val, variable=self.vars[key],
            orient="horizontal", command=update_lbl
        )
        s.pack(fill="x", pady=(0, 2))

        if desc:
            ttk.Label(frame, text=desc, style="Desc.TLabel").pack(
                anchor="w", pady=(0, 6)
            )

    def _add_checkbox(self, parent, key, label):
        current_val = self.engine.settings.get(key, 0)
        self.vars[key] = tk.BooleanVar(value=bool(current_val))
        cb = ttk.Checkbutton(parent, text=label, variable=self.vars[key])
        cb.pack(anchor="w", pady=3)

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

    def _on_close(self):
        SettingsWindow._instance_open = False
        self.root.destroy()
