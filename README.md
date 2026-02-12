# FlowState

**A realistic typing simulator for AutoHotkey v2.**

FlowState pastes your clipboard content by "typing" it out character-by-character. Unlike standard macro pastes that dump text instantly, this script simulates human behavior using variable speeds, rhythm imperfections, and corrected typos.

Useful for screen recordings, demos, or testing input fields.

## Features

* **Natural Rhythm:** Uses Gaussian distribution for keystroke delays so typing doesn't look robotic.
* **Context Aware:** Types faster on common bigrams (like "th", "he") and pauses slightly for punctuation.
* **Error Simulation:** Occasionally hits adjacent keys based on your layout (QWERTY/QWERTZ/AZERTY), realizes the mistake, pauses, and backspaces.
* **Live Tuning:** Includes a visual HUD to adjust speed and error rates while the script is running.
* **Cognitive Pauses:** Adds realistic delays for sentences, paragraphs, and "thinking" moments.

## Setup

1. Download and install [AutoHotkey v2.0+](https://www.autohotkey.com/).
2. Download `FlowState.ahk` from this repository.
3. Double-click the script to run it.

> **Note:** On the first run, it will generate a `settings.ini` file in the same folder.

## Usage

1. Copy text to your clipboard (`Ctrl+C`).
2. Place your cursor in the target text field.
3. Press **`Ctrl` + `Alt` + `V`** to start typing.

### Controls

| Hotkey | Action |
| :--- | :--- |
| **Ctrl + Alt + V** | Start / Pause / Resume typing |
| **Esc** | Pause immediately |
| **Esc (Double-tap)** | Abort and reset |
| **Alt + ↑ / ↓** | Cycle through settings (Speed, Variance, Typo Chance) |
| **Alt + ← / →** | Adjust the selected setting value |

## Configuration

You can adjust the "feel" of the typing in two ways:

### 1. The HUD (Real-time)
While the script is running, use `Alt + Arrows` to tweak:
* **Typing Speed:** Base delay in milliseconds (Lower = Faster).
* **Variance:** How inconsistent the rhythm is.
* **Typo Chance:** % chance to fat-finger a key.
* **Typo Delay:** Reaction time before correcting a typo.

### 2. Settings.ini (Advanced)
Open `settings.ini` to tweak specific behaviors:

```ini
[Advanced]
SentencePauseMs=1200      ; Pause after . ? !
ParagraphPauseMs=2000     ; Pause after Enter
BrainstormFrequency=60    ; 1 in X chance to pause at a space (thinking)
EmojiPauseMs=1800         ; Delay before pasting emojis
