import time
import random
import configparser
import os
import json
import datetime
from pathlib import Path
import subprocess
import sys

from rich_text_formatter import RichTextFormatter, TypeAction, KeyAction, _platform_string
from semantic_analyzer import SemanticAnalyzer
from typing_planner import TypingPlanner
try:
    from clipboard_reader import get_clipboard_styled_runs, StyledRun
    _HAS_CLIPBOARD_HTML = True
except ImportError:
    _HAS_CLIPBOARD_HTML = False

class StopTypingException(Exception):
    pass

LAYOUTS = {
    "QWERTY": {
        "q":"wa", "w":"qase", "e":"wsdr", "r":"edft", "t":"rfgy", "y":"tghu", "u":"yhji", "i":"ujko", "o":"iklp", "p":"ol",
        "a":"qwsz", "s":"qweadzx", "d":"wersfcx", "f":"ertdgvc", "g":"rtyfhvb", "h":"tyugjbn", "j":"yuihkmn", "k":"uiojlm,", "l":"iopk;",
        "z":"asx", "x":"zsdc", "c":"xdfv", "v":"cfgb", "b":"vghn", "n":"bhjm", "m":"njk,",
        "1":"2", "2":"13", "3":"24", "4":"35", "5":"46", "6":"57", "7":"68", "8":"79", "9":"80", "0":"9-", "-":"0=", "=":"-", " ":" "
    },
    "QWERTZ": {
        "q":"wa", "w":"qase", "e":"wsdr", "r":"edft", "t":"rfgy", "z":"tghu", "u":"zhji", "i":"ujko", "o":"iklp", "p":"olü",
        "a":"qwsy", "s":"qweadzy", "d":"wersfcx", "f":"ertdgvc", "g":"rtyfhvb", "h":"tzugjbn", "j":"zuihkmn", "k":"uiojlm,", "l":"iopkö",
        "y":"asx", "x":"ysdc", "c":"xdfv", "v":"cfgb", "b":"vghn", "n":"bhjm", "m":"njk,",
        "1":"2", "2":"13", "3":"24", "4":"35", "5":"46", "6":"57", "7":"68", "8":"79", "9":"80", "0":"9ß", "ß":"0", " ":" "
    },
    "AZERTY": {
        "a":"zq", "z":"azse", "e":"zsdr", "r":"edft", "t":"rfgy", "y":"tghu", "u":"yhji", "i":"ujko", "o":"iklp", "p":"olm",
        "q":"awsw", "s":"aqzedxw", "d":"zersfcx", "f":"ertdgvc", "g":"rtyfhvb", "h":"tyugjbn", "j":"yuihk,n", "k":"uiojlm;", "l":"iopk:!",
        "w":"qsx", "x":"wsdc", "c":"xdfv", "v":"cfgb", "b":"vghn", "n":"bhj;",
        "1":"2", "2":"13", "3":"24", "4":"35", "5":"46", "6":"57", "7":"68", "8":"79", "9":"80", "0":"9", " ":" "
    }
}

# Finger IDs per layout: 0=LP, 1=LR, 2=LM, 3=LI, 4=RI, 5=RM, 6=RR, 7=RP, 8=thumb
FINGER_MAPS = {
    "QWERTY": {
        "q":0,"w":1,"e":2,"r":3,"t":3,"y":4,"u":4,"i":5,"o":6,"p":7,
        "a":0,"s":1,"d":2,"f":3,"g":3,"h":4,"j":4,"k":5,"l":6,
        "z":0,"x":1,"c":2,"v":3,"b":4,"n":4,"m":5,
        "1":0,"2":1,"3":2,"4":3,"5":3,"6":4,"7":4,"8":5,"9":6,"0":7,"-":7,"=":7," ":8
    },
    "QWERTZ": {
        "q":0,"w":1,"e":2,"r":3,"t":3,"z":4,"u":4,"i":5,"o":6,"p":7,"ü":7,
        "a":0,"s":1,"d":2,"f":3,"g":3,"h":4,"j":4,"k":5,"l":6,"ö":7,
        "y":0,"x":1,"c":2,"v":3,"b":4,"n":4,"m":5,
        "1":0,"2":1,"3":2,"4":3,"5":3,"6":4,"7":4,"8":5,"9":6,"0":7,"ß":7," ":8
    },
    "AZERTY": {
        "a":0,"z":1,"e":2,"r":3,"t":3,"y":4,"u":4,"i":5,"o":6,"p":7,"m":7,
        "q":0,"s":1,"d":2,"f":3,"g":3,"h":4,"j":4,"k":5,"l":6,";":6,":":6,
        "w":0,"x":1,"c":2,"v":3,"b":4,"n":4,
        "1":0,"2":1,"3":2,"4":3,"5":3,"6":4,"7":4,"8":5,"9":6,"0":7," ":8
    }
}

COMMON_TYPOS = {
    "the": ["teh"], "and": ["adn"], "that":["taht"], "because": ["becuase", "becaus"],
    "definitely": ["definately"], "separate": ["seperate"], "a lot":["alot"],
    "receive": ["recieve"], "their":["thier", "there"], "you're":["your"]
}

class ProfileManager:
    """Per-app profile manager — matches window titles to setting overrides."""

    def __init__(self):
        self.profiles: dict[str, dict[str, str]] = {}
        self._original_settings: dict[str, any] | None = None

    def load(self, config: configparser.ConfigParser):
        self.profiles.clear()
        for section in config.sections():
            if section.lower().startswith("profile:"):
                name = section[8:].strip()
                self.profiles[name] = dict(config.items(section))

    def match(self, window_title: str | None) -> dict[str, str] | None:
        if not window_title:
            return None
        wt_lower = window_title.lower()
        for prof in self.profiles.values():
            pattern = prof.get("windowpattern", "")
            if pattern and pattern.lower() in wt_lower:
                return prof
        return None

    def apply(self, engine: "TypingEngine", profile: dict[str, str]):
        self._original_settings = engine.settings.copy()
        for key, val in profile.items():
            key_lower = key.lower()
            if key_lower == "windowpattern":
                continue
            actual_key = next((k for k in engine.settings if k.lower() == key_lower), key)
            try:
                engine.settings[actual_key] = int(val)
            except ValueError:
                engine.settings[actual_key] = val

    def restore(self, engine: "TypingEngine"):
        if self._original_settings is not None:
            engine.settings.update(self._original_settings)
            self._original_settings = None


class TypingEngine:
    def __init__(self, driver):
        self.driver = driver
        
        config_dir = Path.home() / ".flowstate"
        config_dir.mkdir(exist_ok=True)
        self.ini_file = config_dir / "settings.ini"
        self.config = configparser.ConfigParser()
        
        self.defaults = {
            "UserMeanDelay": 35, "UserVariance": 45, "TypoChance": 3,
            "TypoDelay": 125, "RevisionChance": 5, "SentencePauseMs": 1200,
            "ParagraphPauseMs": 2000, "BrainstormFrequency": 60, "EmojiPauseMs": 1800,
            "UseEnterOnly": 0, "EnableTypos": 1, "EnableRevisions": 1,
            "EnableBrainstormPauses": 1, "EnableRichText": 1,
            "EnableSemanticSpeed": 1, "EnableClausePauses": 1,
            "EnableChunkBurst": 1, "EnableSmartRevisions": 1,
            "EnableEntityCare": 1,
            "EnableFingerPenalty": 1, "EnableFluencyStates": 1,
            "EnableNumberSymbolCare": 1, "EnableCapsRunRealism": 1,
            "EnableFrequencyTypos": 1, "EnableDeferredCorrections": 1,
        }
        self.default_hotkeys = {
            "TriggerHotkey": "ctrl+alt+v",
            "PauseKey": "esc",
        }
        
        self.settings = self.defaults.copy()
        self.hotkeys = self.default_hotkeys.copy()
        self.load_settings()

        # Rich text formatter — platform detected once at startup
        self._formatter = RichTextFormatter(platform=_platform_string())

        # Semantic layer (lazy-loaded so the app starts fast even if spaCy is heavy)
        self._analyzer: SemanticAnalyzer | None = None
        self._planner: TypingPlanner | None = None

        self.settings_list =["UserMeanDelay", "UserVariance", "TypoChance", "TypoDelay", "RevisionChance"]
        self.setting_names =["Typing Speed (Lower is Faster)", "Variance", "Typo Chance (%)", "Typo Correction Speed", "Base Revision Chance (%)"]
        self.current_setting_index = 0

        self.is_running = False
        self.is_paused = False
        self.current_momentum = 0
        self.last_esc_time = 0
        self.countdown = 0

        # Motor-model state machines
        self._fluent_state = True
        self._fluency_chars_remaining = 0
        self._caps_run_active = False
        self._caps_run_length = 0
        self._in_number_symbol_run = False
        self._layout_name = "QWERTY"
        self._finger_map = FINGER_MAPS["QWERTY"]

        # Per-app profiles
        self.profile_manager = ProfileManager()
        self.profile_manager.load(self.config)

        # Debug logging
        self._debug = False
        self._debug_log_path = Path.home() / ".flowstate" / "debug.log"
        self._debug_buffer = []

        # Log clipboard_reader availability
        if self._debug and not _HAS_CLIPBOARD_HTML:
            self._debug_log("WARNING: clipboard_reader import failed — no HTML clipboard support")
        elif self._debug:
            self._debug_log("clipboard_reader: available")

        self.ui_update_callback = None
        self.status_callback = None

    def _ensure_semantic_layer(self):
        if self._analyzer is None:
            self._analyzer = SemanticAnalyzer()
            self._planner = TypingPlanner(self._analyzer)

    def load_settings(self):
        if self.ini_file.exists():
            self.config.read(self.ini_file)
            for section in self.config.sections():
                for key, val in self.config.items(section):
                    # Match hotkey string settings
                    hotkey_key = next((k for k in self.hotkeys if k.lower() == key.lower()), None)
                    if hotkey_key:
                        self.hotkeys[hotkey_key] = val
                        continue
                    # Match numeric settings
                    actual_key = next((k for k in self.settings if k.lower() == key.lower()), key)
                    try:
                        self.settings[actual_key] = int(val)
                    except ValueError:
                        pass
        else:
            self.save_settings()

    def save_settings(self):
        self.config['Settings'] = {
            'UserMeanDelay': str(self.settings['UserMeanDelay']),
            'UserVariance': str(self.settings['UserVariance']),
            'TypoChance': str(self.settings['TypoChance']),
            'TypoDelay': str(self.settings['TypoDelay']),
            'RevisionChance': str(self.settings['RevisionChance'])
        }
        self.config['Advanced'] = {
            'SentencePauseMs': str(self.settings['SentencePauseMs']),
            'ParagraphPauseMs': str(self.settings['ParagraphPauseMs']),
            'BrainstormFrequency': str(self.settings['BrainstormFrequency']),
            'EmojiPauseMs': str(self.settings['EmojiPauseMs'])
        }
        self.config['Behavior'] = {
            'UseEnterOnly': str(self.settings['UseEnterOnly']),
            'EnableTypos': str(self.settings['EnableTypos']),
            'EnableRevisions': str(self.settings['EnableRevisions']),
            'EnableBrainstormPauses': str(self.settings['EnableBrainstormPauses']),
            'EnableRichText': str(self.settings['EnableRichText']),
            'EnableSemanticSpeed': str(self.settings['EnableSemanticSpeed']),
            'EnableClausePauses': str(self.settings['EnableClausePauses']),
            'EnableChunkBurst': str(self.settings['EnableChunkBurst']),
            'EnableSmartRevisions': str(self.settings['EnableSmartRevisions']),
            'EnableEntityCare': str(self.settings['EnableEntityCare']),
            'EnableFingerPenalty': str(self.settings['EnableFingerPenalty']),
            'EnableFluencyStates': str(self.settings['EnableFluencyStates']),
            'EnableNumberSymbolCare': str(self.settings['EnableNumberSymbolCare']),
            'EnableCapsRunRealism': str(self.settings['EnableCapsRunRealism']),
            'EnableFrequencyTypos': str(self.settings['EnableFrequencyTypos']),
            'EnableDeferredCorrections': str(self.settings['EnableDeferredCorrections']),
        }
        self.config['Hotkeys'] = {
            'TriggerHotkey': self.hotkeys['TriggerHotkey'],
            'PauseKey': self.hotkeys['PauseKey'],
        }
        with open(self.ini_file, 'w') as configfile:
            self.config.write(configfile)

    def cycle_hud(self, direction):
        self.current_setting_index = (self.current_setting_index + direction) % len(self.settings_list)
        val = self.settings[self.settings_list[self.current_setting_index]]
        
        if self.ui_update_callback:
            self.ui_update_callback()

    def adjust_hud(self, direction):
        var_name = self.settings_list[self.current_setting_index]
        step = 1 if var_name in ["TypoChance", "RevisionChance"] else (25 if var_name == "TypoDelay" else 5)
        
        self.settings[var_name] += (step * direction)
        if self.settings[var_name] < 0:
            self.settings[var_name] = 0
            
        self.save_settings()
        if self.ui_update_callback:
            self.ui_update_callback()

    def set_state(self, running=None, paused=None):
        if running is not None:
            self.is_running = running
        if paused is not None:
            self.is_paused = paused

        if self.status_callback:
            self.status_callback()

    def _sleep(self, duration):
        remaining = duration
        while True:
            if not self.is_running:
                raise StopTypingException()
            
            if self.is_paused:
                self.driver.detach()
                while self.is_paused and self.is_running:
                    time.sleep(0.05)
                if not self.is_running:
                    raise StopTypingException()
                self.driver.attach()
            
            if remaining <= 0:
                break
            chunk = min(0.05, remaining)
            time.sleep(chunk)
            remaining -= chunk

    def _debug_log(self, msg):
        """Write a debug message to the log file."""
        if not self._debug:
            return
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:12]
        self._debug_log_path.parent.mkdir(exist_ok=True)
        with open(self._debug_log_path, "a", encoding="utf-8") as f:
            f.write(f"{ts} {msg}\n")

    def _debug_char(self, char):
        """Record a typed character for audit trail."""
        self._debug_buffer.append(char)

    def _debug_flush_chars(self):
        """Flush buffered characters to the log."""
        if self._debug_buffer:
            batch = "".join(self._debug_buffer)
            self._debug_log(f"TYPED [{len(batch)} chars]: {repr(batch[:120])}")
            self._debug_buffer.clear()

    def enable_debug(self, enabled=True):
        """Enable/disable debug logging. Writes to ~/.flowstate/debug.log"""
        self._debug = enabled
        if enabled and hasattr(self, "driver") and hasattr(self.driver, "os_driver"):
            self.driver.os_driver._debug = True
        self._debug_log(f"DEBUG MODE: {'ON' if enabled else 'OFF'}")
        if enabled:
            self._debug_log(f"clipboard_reader: {'available' if _HAS_CLIPBOARD_HTML else 'UNAVAILABLE'}")

    def trigger_typing(self, window_title=None):
        if self.is_running:
            self.set_state(paused=not self.is_paused)
            return

        clipboard_text = self.driver.get_clipboard()
        if not clipboard_text:
            return

        original_text = clipboard_text
        self._debug_log(f"TRIGGER: {len(original_text)} chars")
        self._debug_log(f"CLIPBOARD: {repr(original_text[:200])}")

        clipboard_text = clipboard_text.replace("\r\n", "\n")
        
        # Attach and lock onto the correct tab using the window title
        self.driver.attach(window_title)
        mode = getattr(self.driver, "_mode", "unknown")
        self._debug_log(f"MODE: {mode}")

        # Apply per-app profile if matched
        active_profile = self.profile_manager.match(window_title)
        if active_profile:
            self.profile_manager.apply(self, active_profile)

        # Lock in running state
        self.set_state(running=True, paused=False)

        # Reset motor-model state machines
        self._fluent_state = True
        self._fluency_chars_remaining = 0
        self._caps_run_active = False
        self._caps_run_length = 0
        self._in_number_symbol_run = False

        try:
            # COUNTDOWN LOOP
            for i in range(3, 0, -1):
                if not self.is_running: raise StopTypingException()
                self.countdown = i
                if self.ui_update_callback: self.ui_update_callback()
                self._sleep(0.5)

            self.countdown = 0
            if self.ui_update_callback: self.ui_update_callback()
            
            if not self.is_running: raise StopTypingException()

            # Restore focus to the page after the OSD countdown finishes
            self.driver.focus_page()

            layout_name = self.driver.detect_layout()
            self._layout_name = layout_name
            self._finger_map = FINGER_MAPS.get(layout_name, FINGER_MAPS["QWERTY"])
            neighbor_map = LAYOUTS.get(layout_name, LAYOUTS["QWERTY"])

            if self.settings["EnableRichText"] and getattr(self.driver, "is_playwright_mode", lambda: False)():
                # Try HTML clipboard first (preserves formatting from Google Docs)
                actions = None
                if _HAS_CLIPBOARD_HTML:
                    try:
                        from clipboard_reader import get_clipboard_html
                        raw_html = get_clipboard_html()
                        if raw_html:
                            self._debug_log(f"CLIPBOARD HTML: {len(raw_html)} bytes")
                            self._debug_log(f"HTML PREVIEW: {repr(raw_html[:500])}")
                        runs = get_clipboard_styled_runs()
                        if runs:
                            self._debug_log(f"HTML: {len(runs)} styled runs from clipboard")
                            actions = self._styled_runs_to_actions(runs)
                    except Exception as e:
                        self._debug_log(f"HTML clipboard failed: {e}")
                
                if actions is None:
                    # Fall back to markdown parsing
                    actions = self._formatter.parse(clipboard_text)

                # Reset formatting state before typing (Google Docs may have
                # bold/italic/underline left over from previous edits).
                reset = [KeyAction(f"{self._formatter._mod}+Alt+0")]  # Normal Text
                actions = reset + actions
                
                self._execute_actions(actions, neighbor_map)
            else:
                self._type_plain_text(clipboard_text, neighbor_map)

        except StopTypingException:
            pass

        # Completely sever the Playwright connection when typing finishes
        self.driver.detach()
        self.set_state(running=False, paused=False)
        self._debug_flush_chars()
        self._debug_log("DETACH: session complete")
        self._debug_log(f"AUDIT: {len(original_text)} chars in clipboard")

        # Restore original settings if a profile was active
        self.profile_manager.restore(self)

    # ─── Action Dispatcher ───────────────────────────────────────────────────

    def _execute_actions(self, actions, neighbor_map):
        """Execute a pre-parsed list of TypeAction / KeyAction objects."""
        for action in actions:
            self._sleep(0)  # honour pause/stop between actions
            if isinstance(action, TypeAction):
                self._type_plain_text(action.text, neighbor_map)
            elif isinstance(action, KeyAction):
                shortcut = action.shortcut
                # Map the engine's newline sentinel to the correct key
                if shortcut == "\n":
                    if self.settings["UseEnterOnly"]:
                        shortcut = "Enter"
                    else:
                        shortcut = "Shift+Enter"
                # Small human-like pause before the shortcut
                self._sleep(random.randint(60, 130) / 1000.0)
                self._debug_log(f"KEY: {shortcut}")
                self._debug_flush_chars()
                self.driver.send_key(shortcut)
                # Small pause after the shortcut
                self._sleep(random.randint(60, 130) / 1000.0)
                self.current_momentum = 0

    # ─── Plain-text Typing Loop ──────────────────────────────────────────────

    def _styled_runs_to_actions(self, runs):
        """Convert clipboard HTML styled runs to TypeAction/KeyAction list."""
        mod = self._formatter._mod  # "Control" or "Meta"
        actions = []
        prev = {"bold": False, "italic": False, "underline": False, "heading": 0}
        
        for run in runs:
            text = run.text
            
            # Handle newlines
            if text == "\n":
                actions.append(KeyAction("\n"))
                prev = {"bold": False, "italic": False, "underline": False, "heading": 0}
                continue
            
            if not text.strip():
                actions.append(TypeAction(text))
                continue
            
            # Heading change
            if run.heading_level != prev["heading"]:
                if prev["heading"]:
                    # Reset to normal
                    actions.append(KeyAction(f"{mod}+Alt+0"))
                if run.heading_level:
                    actions.append(KeyAction(f"{mod}+Alt+{run.heading_level}"))
                prev["heading"] = run.heading_level
            
            # Bold toggle
            if run.bold != prev["bold"]:
                actions.append(KeyAction(f"{mod}+b"))
                prev["bold"] = run.bold
            
            # Italic toggle
            if run.italic != prev["italic"]:
                actions.append(KeyAction(f"{mod}+i"))
                prev["italic"] = run.italic
            
            # Underline toggle
            if run.underline != prev["underline"]:
                actions.append(KeyAction(f"{mod}+u"))
                prev["underline"] = run.underline
            
            actions.append(TypeAction(text))
        
        # Close any open formatting
        if prev["bold"]:
            actions.append(KeyAction(f"{mod}+b"))
        if prev["italic"]:
            actions.append(KeyAction(f"{mod}+i"))
        if prev["underline"]:
            actions.append(KeyAction(f"{mod}+u"))
        if prev["heading"]:
            actions.append(KeyAction(f"{mod}+Alt+0"))
        
        return actions

    def _type_plain_text(self, clipboard_text, neighbor_map):
        """Entry point. Chooses semantic path or legacy path."""
        semantic_active = any([
            self.settings["EnableSemanticSpeed"],
            self.settings["EnableClausePauses"],
            self.settings["EnableChunkBurst"],
            self.settings["EnableSmartRevisions"],
            self.settings["EnableEntityCare"],
        ])

        if semantic_active:
            self._ensure_semantic_layer()
            assert self._planner is not None
            directives = self._planner.plan(
                text=clipboard_text,
                mean_delay=self.settings["UserMeanDelay"],
                variance=self.settings["UserVariance"],
            )
            self._execute_directives(directives, neighbor_map)
        else:
            self._legacy_type_plain_text(clipboard_text, neighbor_map)

    def _execute_directives(self, directives, neighbor_map):
        """Typed-loop over directives instead of raw characters."""
        for directive in directives:
            self._sleep(0)

            # --- SMART REVISION: type similar word, pause, backspace, type real word ---
            if (self.settings["EnableSmartRevisions"]
                    and directive.revision_candidate
                    and random.randint(1, 100) <= self.settings["RevisionChance"]):
                self._simulate_revision(directive, neighbor_map)
                continue

            # --- CHUNK BURST: lower variance inside noun chunks ---
            effective_variance = (
                self.settings["UserVariance"] // 2
                if (self.settings["EnableChunkBurst"] and directive.chunk_burst)
                else self.settings["UserVariance"]
            )

            # --- ENTITY CARE + FREQUENCY TYPO MODULATION ---
            effective_typo_chance = self.settings["TypoChance"]
            if self.settings["EnableEntityCare"] and directive.is_entity:
                effective_typo_chance = max(0, effective_typo_chance - 2)
            if self.settings["EnableFrequencyTypos"]:
                effective_typo_chance = max(0, effective_typo_chance + directive.typo_chance_adjustment)

            # --- FLUENCY STATE ---
            if self.settings["EnableFluencyStates"]:
                self._update_fluency_state()
                effective_variance, effective_typo_chance = self._apply_fluency(effective_variance, effective_typo_chance)

            # --- SPEED MODULATION: apply rank-based multiplier ---
            mean = self.settings["UserMeanDelay"]
            if self.settings["EnableSemanticSpeed"]:
                mean = mean * directive.delay_multiplier
            mean = max(10, mean)

            # Emit characters in this directive
            for idx, char in enumerate(directive.text):
                self._sleep(0)

                # Emoji / surrogate pair fast-path
                char_code = ord(char)
                if 0xD800 <= char_code <= 0xDBFF or char_code > 0xFFFF:
                    self._sleep(random.randint(self.settings["EmojiPauseMs"], self.settings["EmojiPauseMs"] + 500) / 1000.0)
                    self.driver.surgical_paste(char)
                    self._sleep(self.settings["UserMeanDelay"] / 1000.0)
                    self.current_momentum = 0
                    self._in_number_symbol_run = False
                    continue

                # --- NUMBER / SYMBOL HANDLING ---
                if self.settings["EnableNumberSymbolCare"]:
                    if self._is_digit_or_symbol(char):
                        if not self._in_number_symbol_run:
                            self._in_number_symbol_run = True
                    else:
                        self._in_number_symbol_run = False

                # Intra-directive typo logic — suppress typos on number/symbol runs
                local_typo_chance = effective_typo_chance
                if self.settings["EnableNumberSymbolCare"] and self._in_number_symbol_run:
                    local_typo_chance = max(0, local_typo_chance - 5)

                if (self.settings["EnableTypos"]
                        and local_typo_chance > 0
                        and char_code < 128
                        and char not in [" ", "\n", "\t"]
                        and random.randint(1, 100) <= local_typo_chance):
                    consumed = self._inject_typo(char, directive.text[idx + 1:], neighbor_map)
                    if consumed:
                        # Skip consumed chars (retyped inside _inject_typo)
                        for _skip in range(consumed - 1):
                            idx += 1
                        continue

                # Normal keystroke
                self._human_keystroke(char)

                # Momentum
                if directive.momentum_boost and self.current_momentum < 15:
                    self.current_momentum += 0.5

                # Delay calculation
                calc_mean = mean - self.current_momentum
                next_char = directive.text[idx + 1] if idx + 1 < len(directive.text) else ""
                bigram = (char + next_char).lower()
                if bigram in ["th", "he", "in", "er", "an", "re", "on", "at", "en",
                              "nd", "ti", "es", "or", "te", "of", "ed", "is", "it",
                              "al", "ar", "st", "to", "nt"]:
                    calc_mean -= 10

                # Same-finger bigram penalty / alternating-hand bonus
                if self.settings["EnableFingerPenalty"]:
                    calc_mean += self._same_finger_penalty_ms(char, next_char)

                # Number / symbol run delay multiplier
                if self.settings["EnableNumberSymbolCare"] and self._in_number_symbol_run:
                    calc_mean = int(calc_mean * 1.35)

                delay = self._gaussian(calc_mean, effective_variance)
                delay = max(10, min(delay, 250))
                self._sleep(delay / 1000.0)

            # --- Pause after directive (clause boundaries, etc.) ---
            if self.settings["EnableClausePauses"] and directive.pause_after_ms:
                self._sleep(directive.pause_after_ms / 1000.0)
                self.current_momentum = max(0, self.current_momentum - 3)

            # --- Sentence / paragraph boundary pauses ---
            stripped = directive.text.rstrip()
            if stripped and stripped[-1] in [".", "?", "!"]:
                self._sleep(random.randint(self.settings["SentencePauseMs"], self.settings["SentencePauseMs"] + 400) / 1000.0)
                self.current_momentum = 0
                self._in_number_symbol_run = False
            elif stripped and stripped[-1] in [",", ";"]:
                self._sleep(random.randint(300, 600) / 1000.0)
                self.current_momentum = max(0, self.current_momentum - 5)
            elif stripped and stripped[-1] == "\n":
                if self.settings["UseEnterOnly"]:
                    self.driver.send_enter()
                else:
                    self.driver.send_shift_enter()
                self._sleep(random.randint(self.settings["ParagraphPauseMs"], self.settings["ParagraphPauseMs"] + 1000) / 1000.0)
                self.current_momentum = 0
                self._in_number_symbol_run = False

    def _simulate_revision(self, directive, neighbor_map):
        """Type the similar candidate, hesitate, backspace, then type the real text."""
        wrong = directive.revision_candidate
        right = directive.text.strip()

        # Type wrong word
        for c in wrong:
            self._human_keystroke(c)
            self._sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)

        # Hesitation (the 'reconsideration' moment)
        self._sleep(random.randint(500, 1100) / 1000.0)

        # Backspace wrong word
        for _ in range(len(wrong)):
            self.driver.send_backspace()
            self._sleep(random.randint(40, 70) / 1000.0)

        # Pause before choosing correct word
        self._sleep(random.randint(600, 1200) / 1000.0)
        self.current_momentum = 0

        # Type correct word with slightly more care (higher delay multiplier)
        for c in right:
            self._human_keystroke(c)
            calc_mean = self.settings["UserMeanDelay"] * 1.15
            delay = self._gaussian(calc_mean, self.settings["UserVariance"])
            self._sleep(max(10, delay) / 1000.0)

        # Re-inject trailing whitespace if directive had it
        trailing_ws = directive.text[len(directive.text.rstrip()):]
        for c in trailing_ws:
            self._human_keystroke(c)
            self._sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)

    def _inject_typo(self, char, remaining_text, neighbor_map):
        """Attempt a single-character typo. Returns chars consumed (0 = no typo)."""
        next_char = remaining_text[0] if remaining_text else ""
        weights = self._get_typo_weights(char, next_char, self.current_momentum, neighbor_map)
        choices = ["spatial", "transposition", "omission", "doubling"]
        typo_type = random.choices(choices, weights=weights, k=1)[0]

        typo_chars = ""
        chars_consumed = 1

        if typo_type == "spatial":
            neighbor = self._get_neighbor(char, neighbor_map)
            typo_chars = neighbor if neighbor else char
        elif typo_type == "transposition":
            typo_chars = next_char + char
            chars_consumed = 2
            self._sleep(max(10, self.settings["UserMeanDelay"] - 15) / 1000.0)
        elif typo_type == "omission":
            typo_chars = ""
        elif typo_type == "doubling":
            typo_chars = char + char

        for c in typo_chars:
            self._human_keystroke(c)
            self._sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)

        realization = random.randint(0, 3)
        buf = remaining_text[:realization]
        for c in buf:
            self._human_keystroke(c)
            self._sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)

        # --- DEFERRED vs IMMEDIATE correction strategy ---
        deferred = False
        if self.settings["EnableDeferredCorrections"] and random.random() < 0.5:
            deferred = True
            # Finish typing the current word before backspacing
            deferred_chars = ""
            lookahead = remaining_text[realization:]
            for lc in lookahead:
                if lc in [" ", "\n", "\t", ".", ",", ";", ":", "!", "?"]:
                    break
                deferred_chars += lc
                self._human_keystroke(lc)
                self._sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)

            # Now backspace the whole mess
            self._sleep(random.randint(self.settings["TypoDelay"] * 2, self.settings["TypoDelay"] * 4) / 1000.0)
            back_count = len(typo_chars) + len(buf) + len(deferred_chars)
        else:
            self._sleep(random.randint(self.settings["TypoDelay"] * 2, self.settings["TypoDelay"] * 4) / 1000.0)
            back_count = len(typo_chars) + len(buf)

        for _ in range(back_count):
            self.driver.send_backspace()
            self._sleep(random.randint(30, 60) / 1000.0)

        self._sleep(random.randint(100, 200) / 1000.0)
        self.current_momentum = 0

        # ── RETYPE the correct character(s) after correction ──────
        if chars_consumed == 2:  # transposition: retype both in correct order
            self._human_keystroke(char)
            self._sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)
            self._human_keystroke(next_char)
            self._sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)
        else:
            self._human_keystroke(char)
            self._sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)

        return chars_consumed

    def _legacy_type_plain_text(self, clipboard_text, neighbor_map):
        """The original character-by-character typing loop with full typo/rhythm
        logic. Used when all semantic toggles are disabled."""
        total_len = len(clipboard_text)
        self.current_momentum = 0
        words_typed_in_sentence = 0
        current_word_buffer = ""
        just_corrected_word = False

        i = 0
        while i < total_len:
                self._sleep(0)

                char = clipboard_text[i]
                char_code = ord(char)
                next_char = clipboard_text[i+1] if i + 1 < total_len else ""

                # --- COGNITIVE TYPO LOGIC ---
                if self.settings["EnableRevisions"] and (i == 0 or clipboard_text[i-1] in[" ", "\n", "\t"]) and char.isalpha() and not just_corrected_word:
                    word_end = i
                    while word_end < total_len and clipboard_text[word_end].isalpha():
                        word_end += 1
                    upcoming_word = clipboard_text[i:word_end]

                    if upcoming_word.lower() in COMMON_TYPOS and random.randint(1, 100) <= self.settings["RevisionChance"]:
                        wrong_word = random.choice(COMMON_TYPOS[upcoming_word.lower()])

                        if upcoming_word.istitle():
                            wrong_word = wrong_word.capitalize()

                        for c in wrong_word:
                            self._human_keystroke(c)
                            self._sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)

                        self._sleep(random.randint(400, 800) / 1000.0)

                        for _ in range(len(wrong_word)):
                            self.driver.send_backspace()
                            self._sleep(random.randint(40, 70) / 1000.0)

                        self._sleep(random.randint(600, 1200) / 1000.0)
                        self.current_momentum = 0

                        just_corrected_word = True
                        continue

                if not char.isalpha() or (i > 0 and clipboard_text[i-1] not in[" ", "\n", "\t"]):
                    just_corrected_word = False

                # --- INTELLIGENT TYPO LOGIC ---
                if self.settings["EnableTypos"] and char_code < 128 and char not in[" ", "\n", "\t"] and random.randint(1, 100) <= self.settings["TypoChance"]:

                    weights = self._get_typo_weights(char, next_char, self.current_momentum, neighbor_map)
                    choices =["spatial", "transposition", "omission", "doubling"]

                    typo_type = random.choices(choices, weights=weights, k=1)[0]

                    typo_chars = ""
                    chars_consumed = 1

                    if typo_type == "spatial":
                        neighbor = self._get_neighbor(char, neighbor_map)
                        typo_chars = neighbor if neighbor else char

                    elif typo_type == "transposition":
                        typo_chars = next_char + char
                        chars_consumed = 2
                        self._sleep(max(10, self.settings["UserMeanDelay"] - 15) / 1000.0)

                    elif typo_type == "omission":
                        typo_chars = ""

                    elif typo_type == "doubling":
                        typo_chars = char + char

                    for c in typo_chars:
                        self._human_keystroke(c)
                        current_word_buffer += c
                        self._sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)

                    realization_delay = random.randint(0, 3)
                    if i + chars_consumed + realization_delay >= total_len:
                        realization_delay = 0

                    for step in range(realization_delay):
                        buf_char = clipboard_text[i + chars_consumed + step]
                        self._human_keystroke(buf_char)
                        current_word_buffer += buf_char
                        self._sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)

                    self._sleep(random.randint(self.settings["TypoDelay"] * 2, self.settings["TypoDelay"] * 4) / 1000.0)

                    backspace_count = len(typo_chars) + realization_delay
                    for _ in range(backspace_count):
                        self.driver.send_backspace()
                        current_word_buffer = current_word_buffer[:-1]
                        self._sleep(random.randint(30, 60) / 1000.0)

                    self._sleep(random.randint(100, 200) / 1000.0)
                    self.current_momentum = 0

                    # ── RETYPE the correct character(s) after correction ──
                    if chars_consumed == 2:
                        self._human_keystroke(char)
                        self._sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)
                        self._human_keystroke(next_char)
                        self._sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)
                        i += 2  # skip both chars since we retyped them
                    else:
                        self._human_keystroke(char)
                        self._sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)
                        i += 1  # advance past retyped char
                    continue

                # --- NORMAL TYPING EXECUTION ---
                if 0xD800 <= char_code <= 0xDBFF or char_code > 0xFFFF:
                    self._sleep(random.randint(self.settings["EmojiPauseMs"], self.settings["EmojiPauseMs"] + 500) / 1000.0)
                    self.driver.surgical_paste(char)
                    self._sleep(self.settings["UserMeanDelay"] / 1000.0)
                    self.current_momentum = 0
                    current_word_buffer = ""
                    self._in_number_symbol_run = False
                    i += 1
                    continue

                is_separator = char in[" ", ".", ",", "!", "?", "\n", "\t", ";", ":"]

                if is_separator:
                    if char == " ":
                        words_typed_in_sentence += 1
                    current_word_buffer = ""
                else:
                    current_word_buffer += char

                if char in [".", "?", "!"] and next_char in [" ", "\n"]:
                    self._human_keystroke(char)
                    self._sleep(random.randint(self.settings["SentencePauseMs"], self.settings["SentencePauseMs"] + 400) / 1000.0)
                    self.current_momentum = 0
                    self._in_number_symbol_run = False
                    words_typed_in_sentence = 0
                    i += 1
                    continue

                if char in [",", ";"]:
                    self._human_keystroke(char)
                    self._sleep(random.randint(300, 600) / 1000.0)
                    self.current_momentum = max(0, self.current_momentum - 5)
                    self._in_number_symbol_run = False
                    i += 1
                    continue

                if self.settings["EnableBrainstormPauses"] and char == " " and random.randint(1, self.settings["BrainstormFrequency"]) == 1:
                    self._sleep(random.randint(1500, 4000) / 1000.0)
                    self.current_momentum = 0

                if char == "\n":
                    if self.settings["UseEnterOnly"]:
                        self.driver.send_enter()
                    else:
                        self.driver.send_shift_enter()
                    self._sleep(random.randint(self.settings["ParagraphPauseMs"], self.settings["ParagraphPauseMs"] + 1000) / 1000.0)
                    self.current_momentum = 0
                    self._in_number_symbol_run = False
                    words_typed_in_sentence = 0
                elif char == "\t":
                    self.driver.send_tab()
                    self._sleep(random.randint(50, 100) / 1000.0)
                else:
                    self._human_keystroke(char)
                    if self.current_momentum < 15:
                        self.current_momentum += 0.5

                calc_mean = self.settings["UserMeanDelay"] - self.current_momentum
                bigram = (char + next_char).lower()
                if bigram in["th", "he", "in", "er", "an", "re", "on", "at", "en", "nd", "ti", "es", "or", "te", "of", "ed", "is", "it", "al", "ar", "st", "to", "nt"]:
                    calc_mean -= 10

                # Same-finger bigram penalty
                if self.settings["EnableFingerPenalty"]:
                    calc_mean += self._same_finger_penalty_ms(char, next_char)

                # Number / symbol run handling
                if self.settings["EnableNumberSymbolCare"]:
                    if self._is_digit_or_symbol(char):
                        if not self._in_number_symbol_run:
                            self._in_number_symbol_run = True
                    else:
                        self._in_number_symbol_run = False
                    if self._in_number_symbol_run:
                        calc_mean = int(calc_mean * 1.35)

                # Fluency state
                effective_variance = self.settings["UserVariance"]
                if self.settings["EnableFluencyStates"]:
                    self._update_fluency_state()
                    if not self._fluent_state:
                        effective_variance = int(effective_variance * 1.7)

                final_delay = self._gaussian(calc_mean, effective_variance)
                final_delay = max(10, min(final_delay, 250))
                self._sleep(final_delay / 1000.0)

                i += 1

        # (StopTypingException propagates up to trigger_typing)

    def handle_esc(self):
        current_time = time.time()
        if self.is_running:
            if current_time - self.last_esc_time < 0.5:
                self.set_state(running=False)
            else:
                self.set_state(paused=True)
            self.last_esc_time = current_time

    # ─── Motor-Model Helpers ────────────────────────────────────────────────

    def _same_finger_penalty_ms(self, char, next_char):
        """Return a delay adjustment for same-finger / alternating-hand bigrams.

        Same finger → +25 ms penalty. Alternating hands → −5 ms bonus.
        Thumb (space) or missing chars → 0.
        """
        c1 = char.lower()
        c2 = next_char.lower() if next_char else ""
        if not c1 or not c2 or c1 == c2 == " ":
            return 0
        f1 = self._finger_map.get(c1, -1)
        f2 = self._finger_map.get(c2, -1)
        if f1 == -1 or f2 == -1:
            return 0
        if f1 == f2 and f1 < 8:
            return 25   # same finger penalty
        # Determine hand: left (0-3) vs right (4-7)
        left_hand = f1 <= 3
        right_hand = f2 <= 3
        if left_hand != right_hand and f1 < 8 and f2 < 8:
            return -5   # alternating hands bonus
        return 0

    def _update_fluency_state(self):
        """Update the 2-state Markov chain for fluent/disfluent typing."""
        if self._fluency_chars_remaining > 0:
            self._fluency_chars_remaining -= 1
            if self._fluency_chars_remaining == 0:
                self._fluent_state = True
            return
        if self._fluent_state:
            if random.random() < 0.015:  # 1.5 % chance to enter disfluent state
                self._fluent_state = False
                self._fluency_chars_remaining = random.randint(8, 35)
        else:
            if random.random() < 0.08:   # 8 % chance per char to recover
                self._fluent_state = True

    def _apply_fluency(self, variance, typo_chance):
        """Apply fluency state to variance and typo chance."""
        if not self._fluent_state:
            return (int(variance * 1.7), typo_chance + 4)
        return (variance, typo_chance)

    @staticmethod
    def _is_digit_or_symbol(char):
        """True for digits and common symbols that humans type deliberately."""
        return char in "0123456789!@#$%^&*()_+-=[]{}|;':\",./<>?\\`~"

    def _human_keystroke(self, char):
        dwell_time = random.randint(10, 40)
        if char.isupper() and char != " ":
            if self.settings["EnableCapsRunRealism"]:
                # Consecutive capitals: penalty on first cap in run only
                if not self._caps_run_active:
                    dwell_time += random.randint(30, 70)
                    self._caps_run_active = True
                self._caps_run_length += 1
            else:
                # Legacy: random per-capital penalty
                if random.randint(1, 10) > 7:
                    dwell_time += random.randint(20, 50)
        else:
            self._caps_run_active = False
            self._caps_run_length = 0
        self.driver.send_char(char, dwell_time / 1000.0)
        self._debug_char(char)

    def _get_neighbor(self, char, map_to_use):
        char = char.lower()
        if char in map_to_use:
            choices = map_to_use[char]
            return random.choice(choices)
        return None

    def _gaussian(self, mean, stddev):
        val = int(random.gauss(mean, stddev))
        return max(10, val)

    def _get_typo_weights(self, char, next_char, momentum, neighbor_map):
        weights = {
            "spatial": 40,
            "transposition": 15,
            "omission": 10,
            "doubling": 10
        }

        char_lower = char.lower()
        next_char_lower = next_char.lower() if next_char else ""

        if not self._get_neighbor(char, neighbor_map):
            weights["spatial"] = 0

        if not next_char or next_char in[" ", "\n", "\t"]:
            weights["transposition"] = 0
        else:
            if momentum > 10:
                weights["transposition"] += 25
                
            left_hand = set("qwertasdfgzxcvb")
            right_hand = set("yuiophjklnm")
            if (char_lower in left_hand and next_char_lower in right_hand) or \
               (char_lower in right_hand and next_char_lower in left_hand):
                weights["transposition"] += 30

        weak_fingers = set("qazwsxpolkmn")
        if char_lower in weak_fingers:
            weights["omission"] += 20
            
        if char_lower == next_char_lower:
            weights["omission"] += 50

        common_doubles = set("eotlspmra")
        if char_lower in common_doubles:
            weights["doubling"] += 25

        return [weights["spatial"], weights["transposition"], weights["omission"], weights["doubling"]]