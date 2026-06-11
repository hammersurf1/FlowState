import time
import random
import configparser
import os
import datetime
import html as html_lib
from pathlib import Path
import subprocess
import sys

from rich_text_formatter import RichTextFormatter, TypeAction, KeyAction, PasteHtmlAction, _platform_string
from semantic_analyzer import SemanticAnalyzer
from iki_timing import sample_inter_key_delay_ms
from typing_planner import TypingPlanner, CompositionSettings
from retrospective_edits import DeferredRevision, TypedPositionTracker
try:
    from clipboard_reader import get_clipboard_styled_runs
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
            "RetrospectiveLookbackChars": 600,
            "EnableCompositionPauses": 0,
            "CompositionPauseMinMs": 300, "CompositionPauseMaxMs": 6000,
            "ParagraphPlanningMinMs": 2000, "ParagraphPlanningMaxMs": 8000,
            "CompositionSensitivity": 50,
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
            if self._ini_missing_settings():
                self.save_settings()
        else:
            self.save_settings()

    def _ini_missing_settings(self) -> bool:
        """True when settings.ini predates newly added schema keys."""
        if not self.ini_file.exists():
            return False

        present = set()
        for section in self.config.sections():
            if section.lower().startswith("profile:"):
                continue
            for key, _ in self.config.items(section):
                present.add(key.lower())

        for key in self.defaults:
            if key.lower() not in present:
                return True
        for key in self.default_hotkeys:
            if key.lower() not in present:
                return True
        return False

    def save_settings(self):
        self.config['Settings'] = {
            'UserMeanDelay': str(self.settings['UserMeanDelay']),
            'UserVariance': str(self.settings['UserVariance']),
            'TypoChance': str(self.settings['TypoChance']),
            'TypoDelay': str(self.settings['TypoDelay']),
            'RevisionChance': str(self.settings['RevisionChance']),
            'RetrospectiveLookbackChars': str(self.settings['RetrospectiveLookbackChars']),
        }
        self.config['Advanced'] = {
            'SentencePauseMs': str(self.settings['SentencePauseMs']),
            'ParagraphPauseMs': str(self.settings['ParagraphPauseMs']),
            'BrainstormFrequency': str(self.settings['BrainstormFrequency']),
            'EmojiPauseMs': str(self.settings['EmojiPauseMs']),
            'CompositionPauseMinMs': str(self.settings['CompositionPauseMinMs']),
            'CompositionPauseMaxMs': str(self.settings['CompositionPauseMaxMs']),
            'ParagraphPlanningMinMs': str(self.settings['ParagraphPlanningMinMs']),
            'ParagraphPlanningMaxMs': str(self.settings['ParagraphPlanningMaxMs']),
            'CompositionSensitivity': str(self.settings['CompositionSensitivity']),
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
            'EnableCompositionPauses': str(self.settings['EnableCompositionPauses']),
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

            # Focus the Google Docs editor surface for reliable
            # keyboard shortcut delivery (once per session)
            if hasattr(self.driver, 'focus_editor'):
                self.driver.focus_editor()

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
                            self._debug_log(f"HTML: {len(runs)} elements from clipboard")
                            actions = self._elements_to_actions(runs)
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
            if isinstance(action, PasteHtmlAction):
                # Google Docs can parse HTML when it's provided through
                # the native clipboard paste handler.
                html = action.html
                if hasattr(self.driver, 'paste_html'):
                    self.driver.paste_html(html)
                else:
                    self.driver.inject_html(html)
                if html.strip().lower() == "<hr>":
                    # Move below the inserted rule so following Enter keys create
                    # real blank paragraphs between consecutive horizontal lines.
                    self._sleep(random.randint(80, 150) / 1000.0)
                    if hasattr(self.driver, "send_key"):
                        self.driver.send_key("ArrowDown")
                    self._sleep(random.randint(80, 150) / 1000.0)
                continue
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
                elif shortcut == "Enter":
                    # Explicit Enter (from headings/lists) stays as Enter
                    pass

                # Small human-like pause before the shortcut
                self._sleep(random.randint(60, 130) / 1000.0)
                self._debug_log(f"KEY: {shortcut}")
                self._debug_flush_chars()
                self.driver.send_key(shortcut)
                # Small pause after the shortcut
                self._sleep(random.randint(60, 130) / 1000.0)
                self.current_momentum = 0

    # ─── Plain-text Typing Loop ──────────────────────────────────────────────

    @staticmethod
    def _element_has_text(el) -> bool:
        """True if the element has non-whitespace text runs."""
        return any(r.text.strip() for r in el.runs)

    @staticmethod
    def _runs_to_html(runs) -> str:
        """Convert styled runs to inline HTML for table cell paste."""
        parts = []
        for run in runs:
            if not run.text:
                continue
            text = html_lib.escape(run.text)
            if run.bold:
                text = f"<strong>{text}</strong>"
            if run.italic:
                text = f"<em>{text}</em>"
            if run.underline:
                text = f"<u>{text}</u>"
            parts.append(text)
        return "".join(parts)

    def _elements_to_actions(self, elements):
        """Convert parsed DocElements to TypeAction/KeyAction list.
        
        Handles headings (Ctrl+Alt+N), tables (paste_html via clipboard),
        horizontal rules, lists, and inline formatting
        (Ctrl+B/I/U toggles).
        """
        mod = self._formatter._mod
        actions = []
        prev = {"bold": False, "italic": False, "underline": False}
        in_list = False  # Track list context to avoid toggling on every item
        current_list_type = ""
        
        def _close_inline():
            """Close only inline formatting (bold/italic/underline)."""
            if prev["bold"]:
                actions.append(KeyAction(f"{mod}+b"))
                prev["bold"] = False
            if prev["italic"]:
                actions.append(KeyAction(f"{mod}+i"))
                prev["italic"] = False
            if prev["underline"]:
                actions.append(KeyAction(f"{mod}+u"))
                prev["underline"] = False

        def _exit_list(reason: str = "unknown", idx: int = -1, next_kind: str | None = None):
            """Exit list mode by pressing Enter twice (empty bullet → exit)."""
            nonlocal in_list, current_list_type
            if in_list:
                # If the next source element is already an explicit blank block,
                # avoid stacking list-exit spacing + blank spacing.
                if next_kind == "blank":
                    actions.append(KeyAction("Enter"))
                elif next_kind == "paragraph":
                    # Google Docs: Enter on a non-empty item creates the empty item;
                    # Enter again exits the list and keeps the cursor on that line.
                    actions.append(KeyAction("Enter"))
                    actions.append(KeyAction("Enter"))
                else:
                    actions.append(KeyAction("Enter"))
                    actions.append(KeyAction("Enter"))
                in_list = False
                current_list_type = ""
        
        prev_kind: str | None = None
        for idx, el in enumerate(elements):
            # Peek at next element to decide list continuation
            next_el = elements[idx + 1] if idx + 1 < len(elements) else None

            if el.kind == "heading":
                if not self._element_has_text(el):
                    continue
                _close_inline()
                _exit_list(reason="before heading", idx=idx, next_kind=next_el.kind if next_el else None)
                # Apply heading style
                level = min(el.level, 6)
                actions.append(KeyAction(f"{mod}+Alt+{level}"))
                # Type heading text with inline formatting
                for run in el.runs:
                    self._emit_inline_run(run, actions, mod, prev)
                _close_inline()
                # Enter after heading — Google Docs automatically reverts
                # to Normal Text on the next line after a heading
                actions.append(KeyAction("Enter"))
                # Extra blank line between consecutive headings to prevent
                # them merging into a single visual block when exported.
                if next_el is not None and next_el.kind == "heading":
                    actions.append(KeyAction("Enter"))
                
            elif el.kind == "table":
                _close_inline()
                _exit_list(reason="before table", idx=idx, next_kind=next_el.kind if next_el else None)
                # Ensure pasted table does not inherit heading/list paragraph style.
                actions.append(KeyAction(f"{mod}+Alt+0"))
                # Build table HTML for clipboard paste (preserve inline formatting)
                html = '<table style="border-collapse:collapse;width:100%"><tbody>'
                for row in el.rows:
                    html += "<tr>"
                    for cell in row.cells:
                        tag = "th" if row.is_header else "td"
                        cell_html = self._runs_to_html(cell.runs)
                        html += f"<{tag} style=\"border:1pt solid #000;padding:5pt\">{cell_html}</{tag}>"
                    html += "</tr>"
                html += "</tbody></table>"
                actions.append(PasteHtmlAction(html))
                actions.append(KeyAction("Enter"))
                
            elif el.kind == "hr":
                _close_inline()
                _exit_list(reason="before hr", idx=idx, next_kind=next_el.kind if next_el else None)
                actions.append(PasteHtmlAction("<hr>"))
                actions.append(KeyAction("Enter"))
                if next_el is not None and next_el.kind in ("blank", "hr"):
                    actions.append(KeyAction("Enter"))

            elif el.kind == "page_break":
                _close_inline()
                _exit_list(reason="before page_break", idx=idx, next_kind=next_el.kind if next_el else None)
                # Google Docs: Ctrl+Enter inserts page break
                actions.append(KeyAction(f"{mod}+Enter"))
                actions.append(KeyAction("Enter"))
                
            elif el.kind == "list_item":
                _close_inline()
                list_shortcut = f"{mod}+Shift+8"
                if el.list_type == "ol":
                    list_shortcut = f"{mod}+Shift+7"
                # Start list mode or switch list type (ol ↔ ul)
                if not in_list:
                    actions.append(KeyAction(list_shortcut))
                    in_list = True
                    current_list_type = el.list_type
                elif el.list_type != current_list_type:
                    _exit_list(reason="switch list type", idx=idx, next_kind=next_el.kind if next_el else None)
                    actions.append(KeyAction(list_shortcut))
                    in_list = True
                    current_list_type = el.list_type
                for run in el.runs:
                    self._emit_inline_run(run, actions, mod, prev)
                _close_inline()
                # If next element is also a list item, Enter continues the list.
                # Otherwise, exit list mode via `_exit_list()` which emits Enter twice.
                if next_el is not None and next_el.kind == "list_item":
                    actions.append(KeyAction("Enter"))
                else:
                    _exit_list(reason="after final list item", idx=idx, next_kind=next_el.kind if next_el else None)
                
            elif el.kind == "paragraph":
                if not self._element_has_text(el):
                    continue
                _exit_list(reason="before paragraph", idx=idx, next_kind=next_el.kind if next_el else None)
                para_preview = "".join(r.text for r in el.runs).strip()[:80]
                for run in el.runs:
                    text = run.text
                    if text == "\n":
                        continue  # skip standalone newline runs
                    self._emit_inline_run(run, actions, mod, prev)
                _close_inline()

                # Hard Enter between block paragraphs — Shift+Enter merges into
                # the next list item in Google Docs.
                actions.append(KeyAction("Enter"))
                if next_el is not None and next_el.kind == "paragraph":
                    # Consecutive paragraph blocks need an extra Enter to
                    # preserve blank-line separation in downstream markdown export.
                    actions.append(KeyAction("Enter"))
                elif next_el is not None and next_el.kind == "list_item":
                    # Blank line between section intro text and first list item
                    # (e.g. "Learning targets:" uses mixed bold/normal runs).
                    actions.append(KeyAction("Enter"))
            elif el.kind == "blank":
                _close_inline()
                _exit_list(reason="before blank", idx=idx, next_kind=next_el.kind if next_el else None)
                # Explicit blank paragraph from source HTML.
                actions.append(KeyAction("Enter"))

        
            prev_kind = el.kind

        _close_inline()
        _exit_list(reason="finalize actions")
        return actions
    
    def _emit_inline_run(self, run, actions, mod, prev):
        """Emit formatting toggles + TypeAction for a single StyledRun."""
        if not run.text:
            return
        if run.bold != prev["bold"]:
            actions.append(KeyAction(f"{mod}+b"))
            prev["bold"] = run.bold
        if run.italic != prev["italic"]:
            actions.append(KeyAction(f"{mod}+i"))
            prev["italic"] = run.italic
        if run.underline != prev["underline"]:
            actions.append(KeyAction(f"{mod}+u"))
            prev["underline"] = run.underline
        actions.append(TypeAction(run.text))

    def _type_plain_text(self, clipboard_text, neighbor_map):
        """Entry point. Chooses semantic path or legacy path."""
        semantic_active = any([
            self.settings["EnableSemanticSpeed"],
            self.settings["EnableClausePauses"],
            self.settings["EnableChunkBurst"],
            self.settings["EnableSmartRevisions"],
            self.settings["EnableEntityCare"],
            self.settings["EnableCompositionPauses"],
            self.settings["EnableRevisions"],
        ])

        if semantic_active:
            self._ensure_semantic_layer()
            assert self._planner is not None
            composition = CompositionSettings(
                enabled=bool(self.settings["EnableCompositionPauses"]),
                sensitivity=self.settings["CompositionSensitivity"],
                pause_min_ms=self.settings["CompositionPauseMinMs"],
                pause_max_ms=self.settings["CompositionPauseMaxMs"],
                paragraph_planning_min_ms=self.settings["ParagraphPlanningMinMs"],
                paragraph_planning_max_ms=self.settings["ParagraphPlanningMaxMs"],
            )
            deferred: list[DeferredRevision] = []
            if self.settings["EnableRevisions"]:
                directives, deferred = self._planner.plan_with_deferred(
                    text=clipboard_text,
                    mean_delay=self.settings["UserMeanDelay"],
                    variance=self.settings["UserVariance"],
                    composition=composition,
                )
            else:
                directives = self._planner.plan(
                    text=clipboard_text,
                    mean_delay=self.settings["UserMeanDelay"],
                    variance=self.settings["UserVariance"],
                    composition=composition,
                )
            self._execute_directives(directives, neighbor_map, deferred=deferred)
        else:
            self._legacy_type_plain_text(clipboard_text, neighbor_map)

    def _should_smart_revise(self, directive) -> bool:
        if not self.settings["EnableSmartRevisions"]:
            return False
        if not directive.revision_candidate and not directive.revision_span:
            return False
        return random.randint(1, 100) <= self.settings["RevisionChance"]

    def _directive_timing(self, directive):
        """Compute mean delay and variance for a directive."""
        effective_variance = self.settings["UserVariance"]

        effective_typo_chance = self.settings["TypoChance"]
        if self.settings["EnableEntityCare"] and directive.is_entity:
            effective_typo_chance = max(0, effective_typo_chance - 2)
        if self.settings["EnableFrequencyTypos"]:
            effective_typo_chance = max(0, effective_typo_chance + directive.typo_chance_adjustment)

        if self.settings["EnableFluencyStates"]:
            self._update_fluency_state()
            effective_variance, effective_typo_chance = self._apply_fluency(
                effective_variance, effective_typo_chance
            )

        mean = self.settings["UserMeanDelay"]
        if self.settings["EnableSemanticSpeed"]:
            mean = mean * directive.delay_multiplier
        mean = max(10, mean)

        return mean, effective_variance, effective_typo_chance

    def _emit_directive_range(self, directive, neighbor_map, start_idx, end_idx, mean, effective_variance, effective_typo_chance):
        """Type directive.text[start_idx:end_idx] with full motor/typo logic."""
        text = directive.text
        idx = start_idx
        while idx < end_idx:
            self._sleep(0)
            char = text[idx]
            char_code = ord(char)

            if 0xD800 <= char_code <= 0xDBFF and idx + 1 < end_idx:
                self._sleep(random.randint(self.settings["EmojiPauseMs"], self.settings["EmojiPauseMs"] + 500) / 1000.0)
                self.driver.surgical_paste(text[idx:idx + 2])
                self._sleep(self.settings["UserMeanDelay"] / 1000.0)
                self.current_momentum = 0
                self._in_number_symbol_run = False
                idx += 2
                continue
            if char_code > 0xFFFF:
                self._sleep(random.randint(self.settings["EmojiPauseMs"], self.settings["EmojiPauseMs"] + 500) / 1000.0)
                self.driver.surgical_paste(char)
                self._sleep(self.settings["UserMeanDelay"] / 1000.0)
                self.current_momentum = 0
                self._in_number_symbol_run = False
                idx += 1
                continue

            if self.settings["EnableNumberSymbolCare"]:
                if self._is_digit_or_symbol(char):
                    if not self._in_number_symbol_run:
                        self._in_number_symbol_run = True
                else:
                    self._in_number_symbol_run = False

            local_typo_chance = effective_typo_chance
            if self.settings["EnableNumberSymbolCare"] and self._in_number_symbol_run:
                local_typo_chance = max(0, local_typo_chance - 5)

            if (self.settings["EnableTypos"]
                    and local_typo_chance > 0
                    and char_code < 128
                    and char not in [" ", "\n", "\t"]
                    and random.randint(1, 100) <= local_typo_chance):
                consumed = self._inject_typo(char, text[idx + 1:end_idx], neighbor_map)
                if consumed:
                    idx += consumed
                    continue

            self._human_keystroke(char)

            if directive.chunk_burst:
                self._advance_chunk_momentum(char)
            else:
                self._advance_momentum(directive.momentum_boost)

            calc_mean = self._char_typing_mean(directive, mean, idx, start_idx)
            calc_mean -= self.current_momentum
            next_char = text[idx + 1] if idx + 1 < end_idx else ""
            bigram = (char + next_char).lower()
            if bigram in ["th", "he", "in", "er", "an", "re", "on", "at", "en",
                          "nd", "ti", "es", "or", "te", "of", "ed", "is", "it",
                          "al", "ar", "st", "to", "nt"]:
                calc_mean -= 10

            if self.settings["EnableFingerPenalty"]:
                calc_mean += self._same_finger_penalty_ms(char, next_char)

            if self.settings["EnableNumberSymbolCare"] and self._in_number_symbol_run:
                calc_mean = int(calc_mean * 1.35)

            variance = effective_variance
            if directive.chunk_burst:
                variance = self._chunk_burst_variance(effective_variance)
            delay = sample_inter_key_delay_ms(calc_mean, variance)
            self._sleep(delay / 1000.0)
            if directive.chunk_burst and char == " ":
                self._sleep(random.uniform(25, 110) / 1000.0)
            idx += 1

    def _use_mac_navigation(self) -> bool:
        return sys.platform == "darwin"

    def _human_arrow(self, key: str):
        """Arrow key with slower, variable timing than typing."""
        self.driver.send_key(key)
        delay = sample_inter_key_delay_ms(
            self.settings["UserMeanDelay"] * 1.4,
            int(self.settings["UserVariance"] * 1.3),
        )
        self._sleep(delay / 1000.0)

    def _execute_nav_keys(self, keys: list[str]):
        for key in keys:
            self._human_arrow(key)

    def _navigate_to_offset(self, tracker: TypedPositionTracker, target_offset: int):
        keys = tracker.plan_navigate_back(
            target_offset,
            use_mac_cmd=self._use_mac_navigation(),
        )
        self._execute_nav_keys(keys)

    def _navigate_to_frontier(self, tracker: TypedPositionTracker, from_offset: int):
        keys = tracker.plan_navigate_forward(
            from_offset,
            use_mac_cmd=self._use_mac_navigation(),
        )
        self._execute_nav_keys(keys)

    def _retrospective_lookback_distance(
        self,
        rev: DeferredRevision,
        tracker: TypedPositionTracker,
    ) -> int:
        return tracker.chars_to_navigate_back(rev.char_offset + rev.word_len)

    def _is_retrospective_eligible(
        self,
        rev: DeferredRevision,
        tracker: TypedPositionTracker,
    ) -> bool:
        if not self.settings["EnableRevisions"]:
            return False
        if not self.settings["EnableSmartRevisions"]:
            return False
        if not self.is_running:
            return False
        lookback = self.settings["RetrospectiveLookbackChars"]
        dist = self._retrospective_lookback_distance(rev, tracker)
        return dist >= 40 and dist <= lookback

    def _should_fire_deferred_revision(
        self,
        rev: DeferredRevision,
        tracker: TypedPositionTracker,
    ) -> bool:
        if not self._is_retrospective_eligible(rev, tracker):
            return False
        return random.randint(1, 100) <= self.settings["RevisionChance"]

    def _do_retrospective_revision(self, rev: DeferredRevision, tracker: TypedPositionTracker):
        """Navigate back, delete existing word, perform synonym swap, return to frontier."""
        frontier = tracker.cursor_offset
        word_end = rev.char_offset + rev.word_len

        self._sleep(random.randint(800, 1800) / 1000.0)
        self.current_momentum = 0

        self._navigate_to_offset(tracker, word_end)

        for _ in range(rev.word_len):
            self.driver.send_backspace()
            self._sleep(random.randint(45, 85) / 1000.0)

        self._do_word_revision(rev.wrong, rev.right)
        self._navigate_to_frontier(tracker, rev.char_offset + len(rev.right))

    def _process_deferred_revisions(
        self,
        deferred: list[DeferredRevision],
        pending: list[DeferredRevision],
        directive_index: int,
        tracker: TypedPositionTracker,
    ):
        """Fire at most one deferred revision whose trigger has passed."""
        lookback = self.settings["RetrospectiveLookbackChars"]

        for rev in list(pending):
            if rev.trigger_after_directive > directive_index:
                continue

            dist = self._retrospective_lookback_distance(rev, tracker)
            if dist > lookback:
                pending.remove(rev)
                continue
            if dist < 40:
                continue

            if not self._should_fire_deferred_revision(rev, tracker):
                pending.remove(rev)
                continue

            pending.remove(rev)
            self._do_retrospective_revision(rev, tracker)
            break

    def _do_word_revision(self, wrong: str, right: str):
        """Type wrong word, hesitate, backspace, type correct word."""
        for c in wrong:
            self._human_keystroke(c)
            self._sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)

        hesitate_lo = 500 + min(len(wrong), 12) * 30
        hesitate_hi = hesitate_lo + 600
        self._sleep(random.randint(hesitate_lo, hesitate_hi) / 1000.0)

        for _ in range(len(wrong)):
            self.driver.send_backspace()
            self._sleep(random.randint(40, 70) / 1000.0)

        self._sleep(random.randint(600, 1200) / 1000.0)
        self.current_momentum = 0

        for c in right:
            self._human_keystroke(c)
            calc_mean = self.settings["UserMeanDelay"] * 1.15
            delay = self._gaussian(calc_mean, self.settings["UserVariance"])
            self._sleep(max(10, delay) / 1000.0)

    def _execute_directives(self, directives, neighbor_map, deferred=None):
        """Typed-loop over directives instead of raw characters."""
        deferred = list(deferred or [])
        pending = list(deferred)
        tracker = TypedPositionTracker()

        for directive_index, directive in enumerate(directives):
            self._sleep(0)
            mean, effective_variance, effective_typo_chance = self._directive_timing(directive)
            text = directive.text
            text_len = len(text)

            if self.settings["EnableCompositionPauses"] and directive.pause_before_ms:
                self._sleep(directive.pause_before_ms / 1000.0)
                self.current_momentum = 0

            if self._should_smart_revise(directive):
                if directive.revision_span:
                    start, end, wrong = directive.revision_span
                    right = text[start:end]
                    self._emit_directive_range(
                        directive, neighbor_map, 0, start,
                        mean, effective_variance, effective_typo_chance,
                    )
                    self._do_word_revision(wrong, right)
                    self._emit_directive_range(
                        directive, neighbor_map, end, text_len,
                        mean, effective_variance, effective_typo_chance,
                    )
                elif directive.revision_candidate:
                    wrong = directive.revision_candidate
                    right = text.strip()
                    self._do_word_revision(wrong, right)
                    trailing_ws = text[len(text.rstrip()):]
                    for c in trailing_ws:
                        self._human_keystroke(c)
                        self._sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)
            else:
                self._emit_directive_range(
                    directive, neighbor_map, 0, text_len,
                    mean, effective_variance, effective_typo_chance,
                )

            tracker.record_text(directive.text)
            self._process_deferred_revisions(
                deferred, pending, directive_index, tracker,
            )

            if directive.pause_after_ms and (
                self.settings["EnableCompositionPauses"]
                or self.settings["EnableClausePauses"]
            ):
                self._sleep(directive.pause_after_ms / 1000.0)
                self.current_momentum = max(0, self.current_momentum - 3)

            stripped = directive.text.rstrip()
            composition_boundaries = self.settings["EnableCompositionPauses"]
            if stripped and stripped[-1] in [".", "?", "!"]:
                if not composition_boundaries:
                    self._sleep(
                        random.randint(
                            self.settings["SentencePauseMs"],
                            self.settings["SentencePauseMs"] + 400,
                        ) / 1000.0
                    )
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
                if not composition_boundaries:
                    self._sleep(
                        random.randint(
                            self.settings["ParagraphPauseMs"],
                            self.settings["ParagraphPauseMs"] + 1000,
                        ) / 1000.0
                    )
                self.current_momentum = 0
                self._in_number_symbol_run = False

            if self.settings["EnableBrainstormPauses"] and not self.settings["EnableCompositionPauses"]:
                ends_with_space = directive.text.endswith(" ")
                ends_with_sentence = stripped and stripped[-1] in [".", "?", "!", "\n"]
                freq = self.settings["BrainstormFrequency"]
                roll = random.randint(1, freq)
                if ends_with_space and roll == 1:
                    self._sleep(random.randint(1500, 4000) / 1000.0)
                    self.current_momentum = 0
                elif ends_with_sentence and roll <= 2:
                    self._sleep(random.randint(1500, 4000) / 1000.0)
                    self.current_momentum = 0
            elif self.settings["EnableBrainstormPauses"] and self.settings["EnableCompositionPauses"]:
                if random.randint(1, self.settings["BrainstormFrequency"]) == 1:
                    self._sleep(random.randint(0, 500) / 1000.0)

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

        i = 0
        while i < total_len:
                self._sleep(0)

                char = clipboard_text[i]
                char_code = ord(char)
                next_char = clipboard_text[i+1] if i + 1 < total_len else ""

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
                    self._advance_momentum(True)

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

                final_delay = sample_inter_key_delay_ms(calc_mean, effective_variance)
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

    def _advance_momentum(self, enabled):
        """Ramp typing speed within a word/chunk with irregular steps and occasional resets."""
        if not enabled:
            return
        if self.current_momentum < 15:
            self.current_momentum += random.uniform(0.2, 0.7)
        if random.random() < 0.04:
            self.current_momentum = random.uniform(0, min(self.current_momentum, 9))

    def _advance_chunk_momentum(self, char):
        """Irregular speed within a noun chunk — reset at word boundaries, not a steady ramp."""
        if char.isspace():
            self.current_momentum = random.uniform(0, 6)
            return
        if random.random() < 0.14:
            self.current_momentum = max(0, self.current_momentum - random.uniform(1.5, 6))
        elif self.current_momentum < 13:
            self.current_momentum += random.uniform(0.05, 0.55)
        if random.random() < 0.06:
            self.current_momentum = random.uniform(0, 8)

    def _char_typing_mean(self, directive, fallback_mean, idx, start_idx):
        if not directive.chunk_burst or not directive.chunk_char_jitter:
            return fallback_mean
        rel = idx - start_idx
        if rel < 0 or rel >= len(directive.chunk_char_jitter):
            return fallback_mean
        base = self.settings["UserMeanDelay"]
        jitter = directive.chunk_char_jitter[rel]
        if self.settings["EnableSemanticSpeed"] and directive.chunk_char_rank_mult:
            rank = directive.chunk_char_rank_mult[rel]
            return max(10.0, base * rank * jitter)
        return max(10.0, base * jitter)

    @staticmethod
    def _chunk_burst_variance(base_variance):
        return max(10, int(base_variance * random.uniform(0.88, 1.22)))

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