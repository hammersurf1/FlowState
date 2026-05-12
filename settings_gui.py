import tkinter as tk
from tkinter import ttk, messagebox

class SettingsWindow:
    def __init__(self, engine):
        self.engine = engine
        self.root = tk.Tk()
        self.root.title("AutoTyper Settings")
        self.root.geometry("480x650")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        # Style configuration
        style = ttk.Style()
        style.configure("TFrame", background="#f0f0f0")
        style.configure("Header.TLabel", font=('Segoe UI', 10, 'bold'), background="#f0f0f0")

        # Main Scrollable Area (optional, here we use fixed frame as it fits)
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill="both", expand=True)

        self.vars = {}

        # --- Section: Typing Speed ---
        self._add_section(main_frame, "Typing Speed & Variance")
        self._add_slider(main_frame, "UserMeanDelay", "Typing Speed (Lower is Faster)", 5, 200)
        self._add_slider(main_frame, "UserVariance", "Variance (Randomness)", 0, 150)
        
        # --- Section: Typos & Revisions ---
        self._add_section(main_frame, "Errors & Corrections")
        self._add_slider(main_frame, "TypoChance", "Typo Chance (%)", 0, 30)
        self._add_slider(main_frame, "TypoDelay", "Correction Speed (Delay ms)", 50, 500)
        self._add_slider(main_frame, "RevisionChance", "Word Revision Chance (%)", 0, 30)

        # --- Section: Human Stealth ---
        self._add_section(main_frame, "Human Pauses (Stealth)")
        self._add_slider(main_frame, "SentencePauseMs", "Sentence Pause (ms)", 200, 4000)
        self._add_slider(main_frame, "ParagraphPauseMs", "Paragraph Pause (ms)", 500, 6000)
        self._add_slider(main_frame, "EmojiPauseMs", "Emoji/Symbol Pause (ms)", 200, 4000)
        self._add_slider(main_frame, "BrainstormFrequency", "Random Pause (Every X Words)", 10, 200)

        # --- Section: Behavior ---
        self._add_section(main_frame, "Keyboard Behavior")
        self.vars["UseEnterOnly"] = tk.BooleanVar(value=int(self.engine.settings.get("UseEnterOnly", 0)) == 1)
        ttk.Checkbutton(main_frame, text="Use 'Enter' instead of 'Shift+Enter' for new lines", variable=self.vars["UseEnterOnly"]).pack(anchor="w", pady=5)

        # Buttons
        btn_frame = ttk.Frame(main_frame, padding="10")
        btn_frame.pack(side="bottom", fill="x", pady=(20, 0))
        
        ttk.Button(btn_frame, text="Save Settings", command=self.save).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.root.destroy).pack(side="right")

        self.root.mainloop()

    def _add_section(self, parent, title):
        lbl = ttk.Label(parent, text=title, style="Header.TLabel")
        lbl.pack(anchor="w", pady=(15, 2))
        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=(0, 10))

    def _add_slider(self, parent, key, label, min_val, max_val):
        frame = ttk.Frame(parent)
        frame.pack(fill="x")
        
        current_val = self.engine.settings.get(key, 0)
        self.vars[key] = tk.IntVar(value=current_val)
        
        ttk.Label(frame, text=label, font=('Segoe UI', 9)).pack(side="left")
        val_lbl = ttk.Label(frame, text=str(current_val), font=('Segoe UI', 9, 'bold'))
        val_lbl.pack(side="right")
        
        def update_lbl(v):
            val_lbl.config(text=str(int(float(v))))

        s = ttk.Scale(parent, from_=min_val, to=max_val, variable=self.vars[key], orient="horizontal", command=update_lbl)
        s.pack(fill="x", pady=(0, 10))

    def save(self):
        for key, var in self.vars.items():
            if key == "UseEnterOnly":
                self.engine.settings[key] = 1 if var.get() else 0
            else:
                self.engine.settings[key] = var.get()
        
        self.engine.save_settings()
        if self.engine.ui_update_callback:
            self.engine.ui_update_callback()
        self.root.destroy()