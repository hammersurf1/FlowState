import time
import random
import configparser
import os
from pathlib import Path
import subprocess
import sys

OSD_SCRIPT = """
import tkinter as tk
import sys
import threading
import queue

q = queue.Queue()

def read_stdin():
    while True:
        line = sys.stdin.readline()
        if not line:
            q.put("EXIT_OSD")
            break
        q.put(line.strip())

threading.Thread(target=read_stdin, daemon=True).start()

def check_queue():
    try:
        while True:
            msg = q.get_nowait()
            if msg == "EXIT_OSD":
                root.destroy()
                return
            label.config(text=msg)
            root.deiconify()
            try:
                root.attributes("-alpha", 0.85)
            except:
                pass
            root.update_idletasks()
            w = root.winfo_width()
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            
            # Positioned nicely in the lower-middle of the screen
            root.geometry(f"+{(sw-w)//2}+{sh-150}")
            
            if hasattr(root, 'hide_timer') and root.hide_timer:
                root.after_cancel(root.hide_timer)
            root.hide_timer = root.after(2000, hide_osd)
    except queue.Empty:
        pass
    root.after(50, check_queue)

def hide_osd():
    try:
        root.attributes("-alpha", 0.0)
    except:
        pass
    root.withdraw()

root = tk.Tk()
root.overrideredirect(True)
root.attributes("-topmost", True)
try:
    root.attributes("-alpha", 0.0) # Start invisible
except:
    pass
root.configure(bg='#1e1e1e')
label = tk.Label(root, text="", fg='#ffffff', bg='#1e1e1e', font=('Arial', 22, 'bold'), padx=30, pady=15)
label.pack()

hide_osd()
root.after(50, check_queue)
root.mainloop()
"""

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

COMMON_TYPOS = {
    "the": ["teh"], "and": ["adn"], "that": ["taht"], "because": ["becuase", "becaus"],
    "definitely": ["definately"], "separate": ["seperate"], "a lot":["alot"],
    "receive": ["recieve"], "their": ["thier", "there"], "you're":["your"]
}

class TypingEngine:
    def __init__(self, driver):
        self.driver = driver
        
        self.ini_file = Path(os.path.dirname(__file__)) / "settings.ini"
        self.config = configparser.ConfigParser()
        
        self.defaults = {
            "UserMeanDelay": 35, "UserVariance": 45, "TypoChance": 3, 
            "TypoDelay": 125, "RevisionChance": 5, "SentencePauseMs": 1200, 
            "ParagraphPauseMs": 2000, "BrainstormFrequency": 60, "EmojiPauseMs": 1800
        }
        
        self.settings = self.defaults.copy()
        self.load_settings()

        self.settings_list = ["UserMeanDelay", "UserVariance", "TypoChance", "TypoDelay", "RevisionChance"]
        self.setting_names =["Typing Speed (Lower is Faster)", "Variance", "Typo Chance (%)", "Typo Correction Speed", "Base Revision Chance (%)"]
        self.current_setting_index = 0

        self.is_running = False
        self.is_paused = False
        self.current_momentum = 0
        self.last_esc_time = 0
        self.countdown = 0

        self.ui_update_callback = None
        self.status_callback = None

        # --- Launch OSD Overlay Server ---
        self.osd_process = None
        try:
            kwargs = {}
            if os.name == 'nt':
                # Prevent a Windows console pop-up behind the UI
                kwargs['creationflags'] = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                
            self.osd_process = subprocess.Popen(
                [sys.executable, '-c', OSD_SCRIPT],
                stdin=subprocess.PIPE,
                text=True,
                **kwargs
            )
        except Exception as e:
            print(f"Failed to start OSD overlay: {e}")

    def show_osd(self, message):
        """Sends a message directly to the hidden background UI without blocking macro execution."""
        if self.osd_process and self.osd_process.poll() is None:
            try:
                self.osd_process.stdin.write(message + "\n")
                self.osd_process.stdin.flush()
            except Exception:
                pass

    def load_settings(self):
        if self.ini_file.exists():
            self.config.read(self.ini_file)
            for section in self.config.sections():
                for key, val in self.config.items(section):
                    actual_key = next((k for k in self.settings if k.lower() == key.lower()), key)
                    self.settings[actual_key] = int(val)
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
        with open(self.ini_file, 'w') as configfile:
            self.config.write(configfile)

    def cycle_hud(self, direction):
        self.current_setting_index = (self.current_setting_index + direction) % len(self.settings_list)
        friendly = self.setting_names[self.current_setting_index]
        val = self.settings[self.settings_list[self.current_setting_index]]
        
        self.show_osd(f"{friendly}: {val}")
        
        if self.ui_update_callback:
            self.ui_update_callback()

    def adjust_hud(self, direction):
        var_name = self.settings_list[self.current_setting_index]
        step = 1 if var_name in ["TypoChance", "RevisionChance"] else (25 if var_name == "TypoDelay" else 5)
        
        self.settings[var_name] += (step * direction)
        if self.settings[var_name] < 0:
            self.settings[var_name] = 0
            
        self.save_settings()
        
        friendly = self.setting_names[self.current_setting_index]
        val = self.settings[var_name]
        self.show_osd(f"{friendly}: {val}")
        
        if self.ui_update_callback:
            self.ui_update_callback()

    def set_state(self, running=None, paused=None):
        changed = False
        was_running = self.is_running
        was_paused = self.is_paused

        if running is not None and self.is_running != running:
            self.is_running = running
            changed = True
        if paused is not None and self.is_paused != paused:
            self.is_paused = paused
            changed = True
            
        if changed:
            if self.is_running and self.is_paused:
                self.show_osd("AutoTyper: Paused ⏸")
            elif self.is_running and not self.is_paused and not was_running:
                pass # Countdown will organically handle "Starting..."
            elif self.is_running and not self.is_paused and was_running and was_paused:
                self.show_osd("AutoTyper: Resumed ▶")
            elif not self.is_running and was_running:
                self.show_osd("AutoTyper: Stopped ⏹")

        if self.status_callback:
            self.status_callback()

    def trigger_typing(self):
        if self.is_running:
            self.set_state(paused=not self.is_paused)
            return

        clipboard_text = self.driver.get_clipboard()
        if not clipboard_text:
            return

        clipboard_text = clipboard_text.replace("\r\n", "\n")
        
        # Lock in running state
        self.set_state(running=True, paused=False)

        # COUNTDOWN LOOP
        for i in range(3, 0, -1):
            if not self.is_running: return 
            self.countdown = i
            self.show_osd(f"Starting in {i}...")
            if self.ui_update_callback: self.ui_update_callback()
            time.sleep(0.5)

        self.countdown = 0
        if self.ui_update_callback: self.ui_update_callback()
        
        if not self.is_running: return

        self.show_osd("AutoTyper: Running ▶")

        # Actually grab the keyboard
        self.driver.start_blocker()

        layout_name = self.driver.detect_layout()
        neighbor_map = LAYOUTS.get(layout_name, LAYOUTS["QWERTY"])

        total_len = len(clipboard_text)
        self.current_momentum = 0
        words_typed_in_sentence = 0
        current_word_buffer = ""
        just_corrected_word = False
        
        i = 0
        while i < total_len:
            if self.is_paused:
                self.driver.stop_blocker()
                while self.is_paused and self.is_running:
                    time.sleep(0.1)
                if not self.is_running:
                    break
                self.driver.start_blocker()

            char = clipboard_text[i]
            char_code = ord(char)
            next_char = clipboard_text[i+1] if i + 1 < total_len else ""

            # --- COGNITIVE TYPO LOGIC ---
            if (i == 0 or clipboard_text[i-1] in[" ", "\n", "\t"]) and char.isalpha() and not just_corrected_word:
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
                        time.sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)
                    
                    time.sleep(random.randint(400, 800) / 1000.0)
                    
                    for _ in range(len(wrong_word)):
                        self.driver.send_backspace()
                        time.sleep(random.randint(40, 70) / 1000.0)
                    
                    time.sleep(random.randint(600, 1200) / 1000.0)
                    self.current_momentum = 0
                    
                    just_corrected_word = True
                    continue

            if not char.isalpha() or (i > 0 and clipboard_text[i-1] not in [" ", "\n", "\t"]):
                just_corrected_word = False

            # --- INTELLIGENT TYPO LOGIC ---
            if char_code < 128 and char not in [" ", "\n", "\t"] and random.randint(1, 100) <= self.settings["TypoChance"]:
                
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
                    time.sleep(max(10, self.settings["UserMeanDelay"] - 15) / 1000.0) 
                    
                elif typo_type == "omission":
                    typo_chars = ""
                    
                elif typo_type == "doubling":
                    typo_chars = char + char

                for c in typo_chars:
                    self._human_keystroke(c)
                    current_word_buffer += c
                    time.sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)

                realization_delay = random.randint(0, 3)
                if i + chars_consumed + realization_delay >= total_len:
                    realization_delay = 0

                for step in range(realization_delay):
                    buf_char = clipboard_text[i + chars_consumed + step]
                    self._human_keystroke(buf_char)
                    current_word_buffer += buf_char
                    time.sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)

                time.sleep(random.randint(self.settings["TypoDelay"] * 2, self.settings["TypoDelay"] * 4) / 1000.0)

                backspace_count = len(typo_chars) + realization_delay
                for _ in range(backspace_count):
                    self.driver.send_backspace()
                    current_word_buffer = current_word_buffer[:-1]
                    time.sleep(random.randint(30, 60) / 1000.0)
                
                time.sleep(random.randint(100, 200) / 1000.0)
                self.current_momentum = 0
                continue

            # --- NORMAL TYPING EXECUTION ---
            if 0xD800 <= char_code <= 0xDBFF or char_code > 0xFFFF:
                time.sleep(random.randint(self.settings["EmojiPauseMs"], self.settings["EmojiPauseMs"] + 500) / 1000.0)
                self.driver.surgical_paste(char)
                time.sleep(self.settings["UserMeanDelay"] / 1000.0)
                self.current_momentum = 0
                current_word_buffer = ""
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
                time.sleep(random.randint(self.settings["SentencePauseMs"], self.settings["SentencePauseMs"] + 400) / 1000.0)
                self.current_momentum = 0
                words_typed_in_sentence = 0
                i += 1
                continue
                
            if char in [",", ";"]:
                self._human_keystroke(char)
                time.sleep(random.randint(300, 600) / 1000.0)
                self.current_momentum = max(0, self.current_momentum - 5)
                i += 1
                continue
                
            if char == " " and random.randint(1, self.settings["BrainstormFrequency"]) == 1:
                time.sleep(random.randint(1500, 4000) / 1000.0)
                self.current_momentum = 0

            if char == "\n":
                self.driver.send_shift_enter()
                time.sleep(random.randint(self.settings["ParagraphPauseMs"], self.settings["ParagraphPauseMs"] + 1000) / 1000.0)
                self.current_momentum = 0
                words_typed_in_sentence = 0
            elif char == "\t":
                self.driver.send_tab()
                time.sleep(random.randint(50, 100) / 1000.0)
            else:
                self._human_keystroke(char)
                if self.current_momentum < 15:
                    self.current_momentum += 0.5

            calc_mean = self.settings["UserMeanDelay"] - self.current_momentum
            bigram = (char + next_char).lower()
            if bigram in["th", "he", "in", "er", "an", "re", "on", "at", "en", "nd", "ti", "es", "or", "te", "of", "ed", "is", "it", "al", "ar", "st", "to", "nt"]:
                calc_mean -= 10

            final_delay = self._gaussian(calc_mean, self.settings["UserVariance"])
            final_delay = max(10, min(final_delay, 250))
            time.sleep(final_delay / 1000.0)

            i += 1

        self.driver.stop_blocker()
        self.set_state(running=False, paused=False)

    def handle_esc(self):
        current_time = time.time()
        if self.is_running:
            if current_time - self.last_esc_time < 0.5:
                self.set_state(running=False)
            else:
                self.set_state(paused=True)
            self.last_esc_time = current_time

    def _human_keystroke(self, char):
        dwell_time = random.randint(10, 40)
        if char.isupper() and char != " " and random.randint(1, 10) > 7:
            dwell_time += random.randint(20, 50)
        self.driver.send_char(char, dwell_time / 1000.0)

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