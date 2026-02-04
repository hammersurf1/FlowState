REALISTIC HUMAN TYPING SCRIPT
-----------------------------

REQUIREMENTS:
- AutoHotkey v2.0 (or higher) installed on your system.

QUICK START:
1. Copy the text you want to type into your clipboard (Ctrl + C).
2. Click into the document, text box, or window where you want the text to appear.
3. Press [Ctrl] + [Alt] + [V] to start typing.

CONTROLS:
-----------------------------
[Ctrl] + [Alt] + [V]   : START typing (if idle).
[Ctrl] + [Alt] + [V]   : PAUSE / RESUME (if currently typing).
[Esc]                  : CANCEL immediately (stops typing and reloads the script).

*Note: While the script is typing, your keyboard input is blocked to prevent interference. Pressing Pause will unlock your keyboard.*

ON-SCREEN SETTINGS (HUD):
You can adjust typing speed and error rates on the fly without opening the code.

[Alt] + [Up] / [Down]  : Cycle through the different settings.
[Alt] + [Left] / [Right]: Adjust the value of the selected setting.

Adjustable Settings:
1. UserMeanDelay: Base typing speed (Lower number = Faster).
2. UserVariance:  Rhythm consistency (Higher = more "human" irregularity).
3. TypoChance:    Percentage chance to make a mistake and fix it.
4. TypoDelay:     How fast you correct mistakes.

FILES:
- script.ahk   : The main script file.
- settings.ini : Generated automatically to save your speed/typo preferences.