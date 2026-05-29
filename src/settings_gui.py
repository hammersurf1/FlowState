"""
FlowState — Settings GUI (CustomTkinter)
Sidebar navigation, scrollable panels, Apply/Save, hotkey capture, and live preview.
"""

from __future__ import annotations

import random
import shutil
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from iki_timing import sample_inter_key_delay_ms

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

SECTION_IDS = ("typing", "pauses", "behavior", "hotkeys", "profiles", "preview")
SECTION_LABELS = {
    "typing": "Typing",
    "pauses": "Pauses",
    "behavior": "Behavior",
    "hotkeys": "Hotkeys",
    "profiles": "Profiles",
    "preview": "Preview",
}

PROFILE_SLIDER_RANGES = {
    "UserMeanDelay": (5, 200),
    "UserVariance": (0, 150),
    "TypoChance": (0, 30),
    "TypoDelay": (50, 500),
    "RevisionChance": (0, 30),
}


def _is_timing_setting_key(key: str, value) -> bool:
    if not isinstance(value, int):
        return False
    return "Delay" in key or "Pause" in key or key.endswith("Ms")


# ─── Hotkey Recorder ─────────────────────────────────────────────────────


class HotkeyRecorder:
    """Press-to-record hotkey widget for CustomTkinter."""

    def __init__(self, parent, label_text: str, initial_value: str):
        self.value = initial_value
        self._recording = False
        self._pressed_keys: set[str] = set()
        self._combo_parts: list[str] = []

        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(self.frame, text=label_text, anchor="w").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 6)
        )

        self.display_var = tk.StringVar(value=initial_value)
        self.display_entry = ctk.CTkEntry(
            self.frame, textvariable=self.display_var, state="readonly", width=280
        )
        self.display_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8))

        self.record_btn = ctk.CTkButton(
            self.frame, text="Record", width=90, command=self._toggle_recording
        )
        self.record_btn.grid(row=1, column=1)

    def pack(self, **kwargs):
        kwargs.setdefault("fill", "x")
        kwargs.setdefault("pady", 8)
        self.frame.pack(**kwargs)

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
    """Visual typing simulation into a text widget (no real keystrokes)."""

    def __init__(self, text_widget, settings, on_done=None, after_widget=None):
        self.widget = text_widget
        self.settings = settings
        self.on_done = on_done
        self._after_widget = after_widget or text_widget
        self._after_id = None
        self._cancelled = False

    def start(self, text):
        self.widget.configure(state="normal")
        self.widget.delete("1.0", "end")
        self._cancelled = False
        self._type_char(text, 0)

    def stop(self):
        self._cancelled = True
        if self._after_id:
            self._after_widget.after_cancel(self._after_id)
            self._after_id = None

    def _type_char(self, text, idx):
        if self._cancelled or idx >= len(text):
            if self.on_done:
                self.on_done()
            return

        char = text[idx]
        self.widget.insert("end", char)
        self.widget.see("end")

        mean = self.settings.get("UserMeanDelay", 35)
        variance = self.settings.get("UserVariance", 45)
        next_char = text[idx + 1] if idx + 1 < len(text) else ""

        if char in ".!?" and next_char in " \n":
            base = self.settings.get("SentencePauseMs", 1200)
            delay = random.randint(base, base + 400)
        elif char in ",;":
            delay = random.randint(300, 600)
        elif char == "\n":
            base = self.settings.get("ParagraphPauseMs", 2000)
            delay = random.randint(base, base + 1000)
        else:
            calc_mean = mean
            bigram = (char + next_char).lower()
            if bigram in (
                "th", "he", "in", "er", "an", "re", "on", "at", "en",
                "nd", "ti", "es", "or", "te", "of", "ed", "is", "it",
                "al", "ar", "st", "to", "nt",
            ):
                calc_mean -= 10
            delay = int(sample_inter_key_delay_ms(calc_mean, variance))

        self._after_id = self._after_widget.after(delay, self._type_char, text, idx + 1)


# ─── Settings Window ─────────────────────────────────────────────────────


class SettingsWindow:
    """Full settings GUI for FlowState."""

    _instance_open = False

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
            "UserMeanDelay": 115, "UserVariance": 55,
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
            "CompositionPauseMinMs": 1500, "CompositionPauseMaxMs": 22000,
            "ParagraphPlanningMinMs": 12000, "ParagraphPlanningMaxMs": 45000,
            "CompositionSensitivity": 65,
        },
    }

    def __init__(self, engine, on_hotkey_change=None):
        if SettingsWindow._instance_open:
            return
        SettingsWindow._instance_open = True

        self.engine = engine
        self.on_hotkey_change = on_hotkey_change

        self.vars: dict[str, tk.Variable] = {}
        self._value_labels: dict[str, ctk.CTkLabel] = {}
        self.hotkey_recorders: dict[str, HotkeyRecorder] = {}
        self._preview_engine = None
        self._panels: dict[str, ctk.CTkScrollableFrame] = {}
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._active_section = "typing"
        self._snapshot_settings: dict = {}
        self._snapshot_hotkeys: dict = {}
        self._apply_status_after: str | None = None

        self.root = ctk.CTk()
        self.root.title("FlowState Settings")
        self.root.geometry("900x720")
        self.root.minsize(640, 520)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Control-s>", lambda _e: self._save(close=True))
        self.root.bind("<Escape>", lambda _e: self._on_close())

        self._build_top_bar()
        self._build_main_area()
        self._build_footer()

        self._show_section("typing")
        self._take_snapshot()
        self._update_dirty_state()

        self.root.mainloop()

    # ─── Layout ────────────────────────────────────────────────────

    def _build_top_bar(self):
        top = ctk.CTkFrame(self.root, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(14, 8))
        top.columnconfigure(2, weight=1)

        ctk.CTkLabel(top, text="Preset", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        self._preset_var = tk.StringVar(value="Custom")
        preset_menu = ctk.CTkOptionMenu(
            top,
            variable=self._preset_var,
            values=["Custom"] + list(self.PRESETS.keys()),
            command=self._on_preset_change,
            width=200,
        )
        preset_menu.grid(row=0, column=1, sticky="w", padx=(8, 0))

        self._status_var = tk.StringVar(value="")
        ctk.CTkLabel(top, textvariable=self._status_var, text_color="#2fa572").grid(
            row=0, column=2, sticky="e"
        )
        self._apply_feedback_var = tk.StringVar(value="")
        ctk.CTkLabel(top, textvariable=self._apply_feedback_var, text_color="#888888").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(4, 0)
        )
        self._update_status()

        self._stay_on_top_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            top,
            text="Stay on top",
            variable=self._stay_on_top_var,
            command=self._toggle_stay_on_top,
            width=120,
        ).grid(row=0, column=3, padx=(12, 0))

    def _build_main_area(self):
        body = ctk.CTkFrame(self.root, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(body, width=180, corner_radius=8)
        sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        sidebar.grid_propagate(False)

        for sid in SECTION_IDS:
            btn = ctk.CTkButton(
                sidebar,
                text=SECTION_LABELS[sid],
                anchor="w",
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray75", "gray25"),
                command=lambda s=sid: self._show_section(s),
            )
            btn.pack(fill="x", padx=8, pady=4)
            self._nav_buttons[sid] = btn

        content_host = ctk.CTkFrame(body, fg_color="transparent")
        content_host.grid(row=0, column=1, sticky="nsew")
        content_host.rowconfigure(0, weight=1)
        content_host.columnconfigure(0, weight=1)

        for sid in SECTION_IDS:
            panel = ctk.CTkScrollableFrame(content_host, label_text=SECTION_LABELS[sid])
            panel.grid(row=0, column=0, sticky="nsew")
            self._panels[sid] = panel
            builder = getattr(self, f"_build_{sid}_section")
            builder(panel)

    def _build_footer(self):
        footer = ctk.CTkFrame(self.root, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=16, pady=(0, 14))

        left = ctk.CTkFrame(footer, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkButton(left, text="Import…", width=90, command=self._import_settings).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkButton(left, text="Export…", width=90, command=self._export_settings).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkButton(
            left, text="Reset to Defaults", width=140, command=self._reset_defaults,
            fg_color="transparent", border_width=1,
        ).pack(side="left", padx=(12, 0))

        right = ctk.CTkFrame(footer, fg_color="transparent")
        right.pack(side="right")
        self._cancel_btn = ctk.CTkButton(
            right, text="Cancel  (Esc)", width=110, command=self._on_close,
            fg_color="transparent", border_width=1,
        )
        self._cancel_btn.pack(side="right", padx=(6, 0))
        self._save_btn = ctk.CTkButton(
            right, text="Save & Close  (Ctrl+S)", width=160, command=lambda: self._save(close=True)
        )
        self._save_btn.pack(side="right", padx=(6, 0))
        self._apply_btn = ctk.CTkButton(
            right, text="Apply", width=90, command=lambda: self._apply(close=False)
        )
        self._apply_btn.pack(side="right", padx=(6, 0))

    def _show_section(self, section_id: str):
        self._active_section = section_id
        for sid, panel in self._panels.items():
            if sid == section_id:
                panel.grid()
            else:
                panel.grid_remove()
        for sid, btn in self._nav_buttons.items():
            if sid == section_id:
                btn.configure(fg_color=("gray75", "gray30"))
            else:
                btn.configure(fg_color="transparent")

    def _toggle_stay_on_top(self):
        self.root.attributes("-topmost", self._stay_on_top_var.get())

    # ─── Section builders ──────────────────────────────────────────

    def _build_typing_section(self, parent):
        self._add_section(parent, "Typing Speed & Variance")
        self._add_slider(
            parent, "UserMeanDelay", "Typing Speed (Lower = Faster)",
            5, 200,
            "Average delay in ms between keystrokes.",
        )
        self._add_slider(
            parent, "UserVariance", "Variance (Randomness)",
            0, 150, "Standard deviation of keystroke timing.",
        )
        self._add_section(parent, "Errors & Corrections")
        self._add_slider(parent, "TypoChance", "Typo Chance (%)", 0, 30, "")
        self._add_slider(parent, "TypoDelay", "Correction Speed (ms)", 50, 500, "")
        self._add_slider(parent, "RevisionChance", "Word Revision Chance (%)", 0, 30, "")

    def _build_pauses_section(self, parent):
        self._add_section(parent, "Human-like Pauses")
        self._add_slider(parent, "SentencePauseMs", "Sentence Pause (ms)", 200, 4000, "")
        self._add_slider(parent, "ParagraphPauseMs", "Paragraph Pause (ms)", 500, 6000, "")
        self._add_slider(parent, "EmojiPauseMs", "Emoji / Symbol Pause (ms)", 200, 4000, "")
        self._add_slider(parent, "BrainstormFrequency", "Random Pause Frequency", 10, 200, "")
        self._add_section(parent, "Composition Pauses")
        self._add_slider(parent, "CompositionPauseMinMs", "Composition Pause Min (ms)", 0, 5000, "")
        self._add_slider(parent, "CompositionPauseMaxMs", "Composition Pause Max (ms)", 5000, 30000, "")
        self._add_slider(parent, "ParagraphPlanningMinMs", "Paragraph Planning Min (ms)", 2000, 30000, "")
        self._add_slider(parent, "ParagraphPlanningMaxMs", "Paragraph Planning Max (ms)", 5000, 60000, "")
        self._add_slider(parent, "CompositionSensitivity", "Composition Sensitivity", 0, 100, "")

    def _build_behavior_section(self, parent):
        self._add_section(parent, "Core Behavior")
        self._add_checkbox(parent, "EnableTypos", "Enable typos (spatial, transposition, omission, doubling)")
        self._add_checkbox(parent, "EnableRevisions", "Enable word-level revisions (legacy)")
        self._add_checkbox(parent, "EnableBrainstormPauses", "Enable random brainstorm pauses")
        self._add_checkbox(
            parent, "EnableCompositionPauses",
            "Composition pauses — content-aware drafting hesitation",
        )
        self._add_checkbox(parent, "UseEnterOnly", "Use plain Enter instead of Shift+Enter for new lines")
        self._add_checkbox(parent, "EnableRichText", "Enable rich-text formatting (bold, italic, lists, headings)")

        self._add_section(parent, "Semantic Humanization")
        self._add_checkbox(parent, "EnableSmartRevisions", "Smart revisions — synonym then correct")
        self._add_checkbox(parent, "EnableSemanticSpeed", "Semantic speed — rare words slower")
        self._add_checkbox(parent, "EnableEntityCare", "Entity care — fewer typos on named entities")
        self._add_checkbox(parent, "EnableClausePauses", "Clause pauses at subordinate boundaries")
        self._add_checkbox(parent, "EnableChunkBurst", "Chunk burst — noun phrases as cognitive bursts")
        self._add_checkbox(parent, "EnableFrequencyTypos", "Frequency-based typos")
        self._add_checkbox(parent, "EnableDeferredCorrections", "Deferred corrections — finish word before backspace")

        self._add_section(parent, "Motor Realism")
        self._add_checkbox(parent, "EnableFingerPenalty", "Same-finger penalty")
        self._add_checkbox(parent, "EnableFluencyStates", "Fluency states — fluent / disfluent periods")
        self._add_checkbox(parent, "EnableNumberSymbolCare", "Number / symbol care")
        self._add_checkbox(parent, "EnableCapsRunRealism", "Caps Lock realism — delay on first capital in run")

    def _build_hotkeys_section(self, parent):
        is_mac = sys.platform == "darwin"
        trigger_desc = "Cmd+Option+V" if is_mac else "Ctrl+Alt+V"
        ctk.CTkLabel(
            parent,
            text="Click Record, then press your key combination. Release to finish.",
            text_color="gray60",
            wraplength=520,
            justify="left",
        ).pack(anchor="w", pady=(0, 12))

        self.hotkey_recorders["TriggerHotkey"] = HotkeyRecorder(
            parent,
            f"Trigger Typing (default: {trigger_desc})",
            self.engine.hotkeys.get("TriggerHotkey", "ctrl+alt+v"),
        )
        self.hotkey_recorders["TriggerHotkey"].pack()

        self.hotkey_recorders["PauseKey"] = HotkeyRecorder(
            parent,
            "Pause / Abort (default: Esc)",
            self.engine.hotkeys.get("PauseKey", "esc"),
        )
        self.hotkey_recorders["PauseKey"].pack()

        ctk.CTkLabel(
            parent,
            text="Hotkey changes take effect when you Apply or Save.",
            text_color="gray60",
            wraplength=520,
            justify="left",
        ).pack(anchor="w", pady=(16, 0))

    def _build_profiles_section(self, parent):
        ctk.CTkLabel(
            parent,
            text="Profiles override typing settings per application (window title substring match).",
            text_color="gray60",
            wraplength=520,
            justify="left",
        ).pack(anchor="w", pady=(0, 12))

        list_row = ctk.CTkFrame(parent, fg_color="transparent")
        list_row.pack(fill="x", pady=6)
        list_row.columnconfigure(0, weight=1)

        list_container = ctk.CTkFrame(list_row)
        list_container.grid(row=0, column=0, sticky="nsew")
        self._profile_listbox = tk.Listbox(
            list_container, height=6, exportselection=False,
            font=("Segoe UI", 11), relief="flat", borderwidth=0,
        )
        self._profile_listbox.pack(fill="both", expand=True, padx=4, pady=4)
        self._profile_listbox.bind("<<ListboxSelect>>", self._on_profile_select)

        btn_col = ctk.CTkFrame(list_row, fg_color="transparent")
        btn_col.grid(row=0, column=1, padx=(8, 0))
        ctk.CTkButton(btn_col, text="Add", width=80, command=self._add_profile).pack(pady=3)
        ctk.CTkButton(btn_col, text="Delete", width=80, command=self._delete_profile).pack(pady=3)

        self._prof_vars: dict[str, tk.IntVar] = {}
        self._prof_pattern_var = tk.StringVar()
        ctk.CTkLabel(parent, text="Window pattern (substring)", anchor="w").pack(
            anchor="w", pady=(12, 4)
        )
        ctk.CTkEntry(parent, textvariable=self._prof_pattern_var).pack(fill="x", pady=(0, 8))

        for key, label in (
            ("UserMeanDelay", "Typing Speed"),
            ("UserVariance", "Variance"),
            ("TypoChance", "Typo Chance (%)"),
            ("TypoDelay", "Correction Speed (ms)"),
            ("RevisionChance", "Revision Chance (%)"),
        ):
            lo, hi = PROFILE_SLIDER_RANGES[key]
            self._add_slider(parent, key, label, lo, hi, "", prof=True)

        ctk.CTkButton(parent, text="Save Profile", command=self._save_profile).pack(pady=16)
        self._refresh_profile_listbox()

    def _build_preview_section(self, parent):
        ctk.CTkLabel(
            parent,
            text="Simulate typing with current slider/checkbox values (including unsaved changes).",
            text_color="gray60",
            wraplength=520,
            justify="left",
        ).pack(anchor="w", pady=(0, 12))

        ctk.CTkLabel(parent, text="Source text", anchor="w", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w"
        )
        self._preview_src = ctk.CTkTextbox(parent, height=100, wrap="word")
        self._preview_src.pack(fill="x", pady=(4, 12))
        self._preview_src.insert(
            "1.0", "The quarterly results were excellent because Alice worked hard."
        )

        ctrl = ctk.CTkFrame(parent, fg_color="transparent")
        ctrl.pack(fill="x", pady=(0, 12))
        self._preview_btn = ctk.CTkButton(ctrl, text="Preview", width=100, command=self._start_preview)
        self._preview_btn.pack(side="left", padx=(0, 8))
        self._preview_stop_btn = ctk.CTkButton(
            ctrl, text="Stop", width=80, command=self._stop_preview, state="disabled"
        )
        self._preview_stop_btn.pack(side="left")
        ctk.CTkLabel(ctrl, text="Speed multiplier").pack(side="left", padx=(20, 6))
        self._preview_speed_var = tk.DoubleVar(value=1.0)
        ctk.CTkEntry(ctrl, textvariable=self._preview_speed_var, width=60).pack(side="left")

        ctk.CTkLabel(parent, text="Preview output", anchor="w", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w"
        )
        self._preview_out = ctk.CTkTextbox(parent, height=200, wrap="word")
        self._preview_out.pack(fill="both", expand=True, pady=(4, 0))
        self._preview_out.insert("1.0", "Preview output will appear here…")
        self._preview_out.configure(state="disabled")

    # ─── Widget helpers ────────────────────────────────────────────

    def _add_section(self, parent, title: str):
        ctk.CTkLabel(
            parent, text=title, font=ctk.CTkFont(size=14, weight="bold"), anchor="w"
        ).pack(anchor="w", pady=(16, 8))

    def _add_slider(self, parent, key, label, min_val, max_val, tooltip="", prof=False):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=6)

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x")
        ctk.CTkLabel(header, text=label, anchor="w").pack(side="left")

        if prof:
            current_val = int(self.engine.settings.get(key, 0))
            var = tk.IntVar(value=current_val)
            self._prof_vars[key] = var
        else:
            current_val = int(self.engine.settings.get(key, 0))
            var = tk.IntVar(value=current_val)
            self.vars[key] = var
            var.trace_add("write", lambda *_: self._update_dirty_state())

        val_lbl = ctk.CTkLabel(header, text=str(current_val), width=48, anchor="e")
        val_lbl.pack(side="right")
        if not prof:
            self._value_labels[key] = val_lbl

        def on_slide(v):
            val_lbl.configure(text=str(int(float(v))))
            if not prof:
                self._update_dirty_state()

        slider = ctk.CTkSlider(
            frame, from_=min_val, to=max_val, variable=var, command=on_slide, number_of_steps=max(max_val - min_val, 1),
        )
        slider.pack(fill="x", pady=(4, 0))

        if tooltip:
            ctk.CTkLabel(frame, text=tooltip, text_color="gray60", font=ctk.CTkFont(size=11)).pack(
                anchor="w", pady=(2, 0)
            )

    def _add_checkbox(self, parent, key, label):
        current_val = bool(self.engine.settings.get(key, 0))
        var = tk.BooleanVar(value=current_val)
        self.vars[key] = var
        var.trace_add("write", lambda *_: self._update_dirty_state())
        ctk.CTkCheckBox(parent, text=label, variable=var).pack(anchor="w", pady=4)

    # ─── Gather / apply / persist ──────────────────────────────────

    def _gather_settings_from_ui(self) -> tuple[dict, dict, bool]:
        settings = {}
        for key, var in self.vars.items():
            if isinstance(var, tk.BooleanVar):
                settings[key] = 1 if var.get() else 0
            else:
                settings[key] = int(var.get())

        hotkeys = {}
        hotkeys_changed = False
        for key, recorder in self.hotkey_recorders.items():
            hotkeys[key] = recorder.value
            if hotkeys[key] != self.engine.hotkeys.get(key, ""):
                hotkeys_changed = True
        return settings, hotkeys, hotkeys_changed

    def _persist_profiles_to_config(self):
        for name, prof in self.engine.profile_manager.profiles.items():
            section = f"Profile:{name}"
            if not self.engine.config.has_section(section):
                self.engine.config.add_section(section)
            for k, v in prof.items():
                self.engine.config.set(section, k, str(v))
        for section in list(self.engine.config.sections()):
            if section.startswith("Profile:"):
                prof_name = section[8:]
                if prof_name not in self.engine.profile_manager.profiles:
                    self.engine.config.remove_section(section)

    def _write_ini(self):
        self.engine.save_settings()
        self._persist_profiles_to_config()
        with open(self.engine.ini_file, "w", encoding="utf-8") as cf:
            self.engine.config.write(cf)

    def _apply_to_engine(self, *, close: bool = False) -> bool:
        settings, hotkeys, hotkeys_changed = self._gather_settings_from_ui()
        self.engine.settings.update(settings)
        self.engine.hotkeys.update(hotkeys)

        try:
            self._write_ini()
        except Exception as e:
            messagebox.showerror("Save Failed", str(e), parent=self.root)
            return False

        if self.engine.ui_update_callback:
            self.engine.ui_update_callback()

        if hotkeys_changed and self.on_hotkey_change:
            try:
                self.on_hotkey_change()
            except Exception as e:
                messagebox.showwarning(
                    "Hotkey Error",
                    f"Could not register new hotkeys:\n{e}\n\n"
                    "Previous hotkeys may still be active.",
                    parent=self.root,
                )

        self._take_snapshot()
        self._update_dirty_state()
        self._show_apply_feedback("Settings applied")
        self._update_status()

        if close:
            self._on_close(force=True)
        return True

    def _apply(self, close: bool = False):
        self._apply_to_engine(close=close)

    def _save(self, close: bool = True):
        self._apply(close=close)

    def _take_snapshot(self):
        self._snapshot_settings, self._snapshot_hotkeys, _ = self._gather_settings_from_ui()

    def _is_dirty(self) -> bool:
        current_settings, current_hotkeys, _ = self._gather_settings_from_ui()
        return current_settings != self._snapshot_settings or current_hotkeys != self._snapshot_hotkeys

    def _update_dirty_state(self):
        dirty = self._is_dirty()
        state = "normal" if dirty else "disabled"
        self._apply_btn.configure(state=state)

    def _show_apply_feedback(self, message: str):
        self._apply_feedback_var.set(message)
        if self._apply_status_after:
            self.root.after_cancel(self._apply_status_after)
        self._apply_status_after = self.root.after(2500, lambda: self._apply_feedback_var.set(""))

    # ─── Preview ───────────────────────────────────────────────────

    def _preview_settings_dict(self) -> dict:
        settings, _, _ = self._gather_settings_from_ui()
        merged = self.engine.settings.copy()
        merged.update(settings)
        speed_mult = max(0.1, float(self._preview_speed_var.get()))
        preview = {}
        for k, v in merged.items():
            if _is_timing_setting_key(k, v):
                preview[k] = max(1, int(v / speed_mult))
            else:
                preview[k] = v
        preview["UserMeanDelay"] = max(1, int(merged.get("UserMeanDelay", 35) / speed_mult))
        preview["UserVariance"] = max(1, int(merged.get("UserVariance", 45) / speed_mult))
        return preview

    def _start_preview(self):
        text = self._preview_src.get("1.0", "end").rstrip("\n")
        if not text:
            return

        self._preview_out.configure(state="normal")
        self._preview_out.delete("1.0", "end")
        self._preview_btn.configure(state="disabled")
        self._preview_stop_btn.configure(state="normal")

        self._preview_engine = TypingPreview(
            self._preview_out,
            self._preview_settings_dict(),
            on_done=self._on_preview_done,
            after_widget=self.root,
        )
        self._preview_engine.start(text)

    def _stop_preview(self):
        if self._preview_engine:
            self._preview_engine.stop()
        self._on_preview_done()

    def _on_preview_done(self):
        self._preview_btn.configure(state="normal")
        self._preview_stop_btn.configure(state="disabled")
        self._preview_out.configure(state="disabled")
        self._preview_engine = None

    # ─── Presets ───────────────────────────────────────────────────

    def _on_preset_change(self, choice=None):
        name = choice or self._preset_var.get()
        if name == "Custom" or name not in self.PRESETS:
            return
        for key, val in self.PRESETS[name].items():
            if key not in self.vars:
                continue
            var = self.vars[key]
            if isinstance(var, tk.BooleanVar):
                var.set(bool(val))
            else:
                var.set(val)
            if key in self._value_labels:
                self._value_labels[key].configure(text=str(val))
        self._update_dirty_state()

    # ─── Profiles ──────────────────────────────────────────────────

    def _refresh_profile_listbox(self):
        self._profile_listbox.delete(0, tk.END)
        for name in sorted(self.engine.profile_manager.profiles):
            self._profile_listbox.insert(tk.END, name)

    def _on_profile_select(self, _event=None):
        sel = self._profile_listbox.curselection()
        if not sel:
            return
        name = self._profile_listbox.get(sel[0])
        prof = self.engine.profile_manager.profiles.get(name, {})
        self._prof_pattern_var.set(prof.get("windowpattern", ""))
        for key, var in self._prof_vars.items():
            var.set(int(prof.get(key, self.engine.defaults.get(key, 0))))

    def _add_profile(self):
        dialog = ctk.CTkInputDialog(text="Enter a name for this profile:", title="Profile Name")
        name = dialog.get_input()
        if not name:
            return
        name = name.strip()
        if not name:
            return
        if name in self.engine.profile_manager.profiles:
            messagebox.showwarning("Profile", f"Profile '{name}' already exists.", parent=self.root)
            return

        profile = {"windowpattern": ""}
        for key, var in self._prof_vars.items():
            profile[key] = str(self.engine.settings.get(key, 0))
        self.engine.profile_manager.profiles[name] = profile
        self._write_ini()
        self._refresh_profile_listbox()
        names = list(self.engine.profile_manager.profiles.keys())
        idx = names.index(name)
        self._profile_listbox.selection_clear(0, tk.END)
        self._profile_listbox.selection_set(idx)
        self._profile_listbox.see(idx)
        self._on_profile_select()
        self._update_status()

    def _delete_profile(self):
        sel = self._profile_listbox.curselection()
        if not sel:
            return
        name = self._profile_listbox.get(sel[0])
        if not messagebox.askyesno("Delete Profile", f"Delete profile '{name}'?", parent=self.root):
            return
        self.engine.profile_manager.profiles.pop(name, None)
        section = f"Profile:{name}"
        if self.engine.config.has_section(section):
            self.engine.config.remove_section(section)
        self._write_ini()
        self._refresh_profile_listbox()
        self._prof_pattern_var.set("")
        self._update_status()

    def _save_profile(self):
        sel = self._profile_listbox.curselection()
        if sel:
            name = self._profile_listbox.get(sel[0])
        else:
            dialog = ctk.CTkInputDialog(text="Enter profile name:", title="Profile Name")
            name = dialog.get_input()
            if not name:
                return
            name = name.strip()
            if not name:
                return

        profile = {"windowpattern": self._prof_pattern_var.get().strip()}
        for key, var in self._prof_vars.items():
            profile[key] = str(int(var.get()))

        self.engine.profile_manager.profiles[name] = profile
        self._write_ini()
        self._refresh_profile_listbox()
        names = sorted(self.engine.profile_manager.profiles)
        if name in names:
            idx = names.index(name)
            self._profile_listbox.selection_clear(0, tk.END)
            self._profile_listbox.selection_set(idx)
        self._update_status()
        self._show_apply_feedback(f"Profile '{name}' saved")

    # ─── Import / export ───────────────────────────────────────────

    def _import_settings(self):
        path = filedialog.askopenfilename(
            title="Import Settings",
            filetypes=[("INI files", "*.ini"), ("All files", "*.*")],
            parent=self.root,
        )
        if not path:
            return
        try:
            shutil.copy(path, self.engine.ini_file)
            self.engine.load_settings()
            self.engine.profile_manager.load(self.engine.config)
            self._reload_ui_from_engine()
            self._take_snapshot()
            self._update_dirty_state()
            messagebox.showinfo("Import Successful", f"Settings imported from:\n{path}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Import Failed", str(e), parent=self.root)

    def _export_settings(self):
        if self._is_dirty():
            if messagebox.askyesno(
                "Unsaved Changes",
                "Apply unsaved changes before exporting?",
                parent=self.root,
            ):
                if not self._apply_to_engine(close=False):
                    return
        path = filedialog.asksaveasfilename(
            title="Export Settings",
            defaultextension=".ini",
            filetypes=[("INI files", "*.ini"), ("All files", "*.*")],
            parent=self.root,
        )
        if not path:
            return
        try:
            shutil.copy(self.engine.ini_file, path)
            messagebox.showinfo("Export Successful", f"Settings saved to:\n{path}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Export Failed", str(e), parent=self.root)

    def _reload_ui_from_engine(self):
        for key, var in self.vars.items():
            val = self.engine.settings.get(key, 0)
            if isinstance(var, tk.BooleanVar):
                var.set(bool(val))
            else:
                var.set(int(val))
            if key in self._value_labels:
                self._value_labels[key].configure(text=str(int(val)))
        for key, recorder in self.hotkey_recorders.items():
            recorder.value = self.engine.hotkeys.get(key, recorder.value)
            recorder.display_var.set(recorder.value)
        self._refresh_profile_listbox()
        self._update_status()

    # ─── Status / close ────────────────────────────────────────────

    def _update_status(self):
        profiles = self.engine.profile_manager.profiles
        if profiles:
            count = len(profiles)
            self._status_var.set(f"{count} profile{'s' if count != 1 else ''} configured")
        else:
            self._status_var.set("No profiles configured")

    def _reset_defaults(self):
        if not messagebox.askyesno(
            "Reset to Defaults",
            "Reset all settings to their default values?\n\n"
            "Use Apply or Save & Close to persist.",
            parent=self.root,
        ):
            return
        for key, default_val in self.engine.defaults.items():
            if key not in self.vars:
                continue
            var = self.vars[key]
            if isinstance(var, tk.BooleanVar):
                var.set(bool(default_val))
            else:
                var.set(int(default_val))
            if key in self._value_labels:
                self._value_labels[key].configure(text=str(int(default_val)))
        for key, default_val in self.engine.default_hotkeys.items():
            if key in self.hotkey_recorders:
                self.hotkey_recorders[key].value = default_val
                self.hotkey_recorders[key].display_var.set(default_val)
        self._preset_var.set("Custom")
        self._update_dirty_state()

    def _on_close(self, force: bool = False):
        if not force and self._is_dirty():
            answer = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Save before closing?",
                parent=self.root,
            )
            if answer is None:
                return
            if answer:
                if not self._apply_to_engine(close=True):
                    return
                return

        if self._preview_engine:
            self._preview_engine.stop()
        SettingsWindow._instance_open = False
        self.root.destroy()
