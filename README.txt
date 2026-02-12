==============================================================================
REALISTIC HUMAN TYPER (AutoHotkey v2)
"Tuned for Realism v3"
==============================================================================

[ OVERVIEW ]
This script simulates human typing behavior to paste clipboard content into any 
text field. Unlike standard "send" commands, this engine uses Gaussian 
randomization for rhythm, simulates "fat finger" typos based on your 
keyboard layout, performs delayed backspace corrections, and adds "cognitive" 
pauses for sentences and paragraphs.

[ REQUIREMENTS ]
1. AutoHotkey v2.0 or higher (Will not work on v1.1).
2. Windows OS.

[ QUICK START ]
1. Run the script (`.ahk` file).
2. Copy the text you want to type into your Clipboard (Ctrl+C).
3. Place your cursor in the target text field (Notepad, Word, Browser, etc.).
4. Press [ Ctrl + Alt + V ] to begin typing.

------------------------------------------------------------------------------
[ CONTROLS & HOTKEYS ]
------------------------------------------------------------------------------

PRIMARY COMMANDS:
  Ctrl + Alt + V      : START typing (or RESUME if paused).
                        * Note: Can also be used to PAUSE if currently typing.

  ESC (Single Tap)    : PAUSE typing immediately.
  ESC (Double Tap)    : CANCEL/ABORT typing and unlock the keyboard.

Heads-Up Display (HUD) SETTINGS:
(Adjust speed and accuracy while the script is running)
  Alt + Up / Down     : Cycle through settings (Speed, Variance, Typo Chance).
  Alt + Right / Left  : Increase or Decrease the selected setting.

------------------------------------------------------------------------------
[ FEATURES & BEHAVIOR ]
------------------------------------------------------------------------------

1. KEYBOARD BLOCKING
   While the script is typing, your physical keyboard input is blocked to 
   prevent you from accidentally interfering with the stream. 
   > Press ESC to pause/unlock or Double-Tap ESC to quit.

2. INTELLIGENT TYPOS ("Fat Finger")
   - The script knows your keyboard layout (QWERTY, QWERTZ, or AZERTY).
   - If a typo occurs, it hits a physically adjacent key (e.g., hitting 'S' 
     instead of 'A').
   - It simulates a "delayed realization": it may type 1-3 more characters 
     before "realizing" the mistake, pausing, and backspacing rapidly.

3. COGNITIVE PAUSES
   - The script pauses briefly after punctuation (., ?, !) to simulate 
     finishing a sentence.
   - It pauses longer after New Lines (Enter) to simulate paragraph thinking.
   - It occasionally pauses in the middle of sentences (Brainstorming).

4. EMOJI SUPPORT
   - Emojis are detected and "Surgically Pasted" rather than typed.
   - The script adds a realistic delay before emojis to simulate the user 
     opening an emoji picker menu.

------------------------------------------------------------------------------
[ CONFIGURATION (Advanced) ]
------------------------------------------------------------------------------
The script generates a `settings.ini` file in the same folder after the first 
run. You can edit this file to permanently change behavior.

[Settings] Section:
  UserMeanDelay     : Base typing speed in ms (Lower = Faster).
  UserVariance      : Rhythm inconsistency (Higher = More "human/messy").
  TypoChance        : Percentage chance (0-100) of making a mistake.
  TypoDelay         : How long it freezes before correcting a typo.

[Advanced] Section:
  SentencePauseMs   : Pause duration after periods/exclamation marks.
  ParagraphPauseMs  : Pause duration after pressing Enter.
  EmojiPauseMs      : Pause duration before inserting an emoji.
  BrainstormFrequency : 1 in X chance to pause at a space bar (Writer's block).

------------------------------------------------------------------------------
[ TROUBLESHOOTING ]
------------------------------------------------------------------------------
* "The script crashes immediately": Ensure you have AutoHotkey v2 installed.
* "It's typing gibberish": Ensure your system keyboard layout matches the 
  internal map (QWERTY is default).
* "I can't stop it!": Double-tap ESC rapidly.

==============================================================================