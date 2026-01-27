<div align="center">

<img width="600" alt="FlowState - Intelligent Typing" src="https://github.com/user-attachments/assets/07ef38d8-dadd-41d9-bd76-98cfbe5cb22c" />

<p align="center">
  <strong>Experience typing that feels impossibly human</strong>
</p>

[![AutoHotkey](https://img.shields.io/badge/AutoHotkey-v2.0+-1C4A8D.svg?style=flat-square)](https://www.autohotkey.com/)
[![License](https://img.shields.io/badge/license-MIT-00C853.svg?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-0078D6.svg?style=flat-square)](https://www.microsoft.com/windows)
[![Made with Love](https://img.shields.io/badge/made%20with-❤️-ff69b4.svg?style=flat-square)](https://github.com/hammersurf1/FlowState)

[Quick Start](#-quick-start) • [Features](#-core-features) • [Usage](#-usage-guide) • [Configuration](#️-configuration) • [How It Works](#-how-flowstate-works)

</div>

---

## 📑 Table of Contents

- [What is FlowState?](#-what-is-flowstate)
- [Core Features](#-core-features)
- [Quick Start](#-quick-start)
- [Usage Guide](#-usage-guide)
- [Configuration](#️-configuration)
- [How FlowState Works](#-how-flowstate-works)
- [Use Cases & Examples](#-use-cases--examples)
- [Troubleshooting & FAQ](#️-troubleshooting--faq)
- [Technical Details](#-technical-details)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌊 What is FlowState?

FlowState transforms clipboard text into **indistinguishably human typing**. Using advanced behavioral modeling, it replicates the subtle imperfections that make typing feel authentic: momentum building, cognitive pauses, realistic typos, correction delays, and even "thinking" moments.

Whether you're testing chat interfaces, recording demos, or need accessibility tools, FlowState delivers typing that passes the human test.

### ✨ Why FlowState?

- 🧠 **Cognitive Realism** — Pauses at sentences, paragraphs, and random "brainstorm" moments
- ⚡ **Dynamic Momentum** — Gradual acceleration as typing continues, just like real muscle memory
- 🎯 **Smart Typos** — Character transpositions and neighbor-key mistakes that auto-correct naturally
- 🌍 **Layout Aware** — Auto-detects and adapts to QWERTY, QWERTZ, and AZERTY keyboards
- 🎛️ **Live Tuning** — Real-time HUD lets you adjust every parameter on the fly
- 🚀 **Zero Setup** — Works out of the box with sensible defaults

## 🎯 Core Features

<table>
<tr>
<td width="50%" valign="top">

### 🎭 Human Behavioral Modeling

**Gaussian Timing Distribution**  
Keystroke delays follow a natural bell curve, not robotic intervals

**Momentum System**  
Typing accelerates as you continue, mimicking muscle memory (up to 15ms speedup)

**Bigram Optimization**  
Common letter pairs (`th`, `he`, `in`) are typed 10ms faster—just like real typing

**Cognitive Load Pauses**  
- 1.2s+ at sentence endings (`. ? !`)
- 2s+ at paragraph breaks
- 0.3-0.6s at commas and semicolons
- Random 1.5-4s "thinking" pauses

</td>
<td width="50%" valign="top">

### 🎲 Realistic Error Simulation

**Two Typo Types**
- **Transposition** (40%) — `teh` → `the`
- **Neighbor Keys** (60%) — `heklo` → `hello`

**Smart Correction Behavior**
- Natural pause before noticing mistake
- Visible backspace correction
- Momentum reset after errors
- Layout-specific neighbor maps

**Emoji Intelligence**  
Special handling with 1.8s pause before paste

</td>
</tr>
</table>

### 🎛️ Real-Time Control HUD

Adjust settings **while typing** using intuitive keyboard shortcuts:

<table>
<tr>
<td align="center">

**⏱️ Typing Speed**  
*Lower = Faster*

</td>
<td align="center">

**📊 Variance**  
*Consistency vs Randomness*

</td>
<td align="center">

**🎲 Typo Chance**  
*Mistake Probability*

</td>
<td align="center">

**⚡ Typo Delay**  
*Correction Speed*

</td>
</tr>
</table>

Navigate with `Alt+↑↓`, adjust with `Alt+←→`, and watch the HUD update in real-time.

## 🚀 Quick Start

### Prerequisites

- ✅ Windows 10 or 11
- ✅ [AutoHotkey v2.0+](https://www.autohotkey.com/download/) *(note: v1.1 will not work)*

### Installation

**Option 1: Clone the repository**
```bash
git clone https://github.com/hammersurf1/FlowState.git
cd FlowState
```

**Option 2: Direct download**  
Download `FlowState.ahk` from [releases](https://github.com/hammersurf1/FlowState/releases) and save anywhere

### Launch

Simply **double-click** `FlowState.ahk` to run

> 💡 **First run**: A `settings.ini` file is automatically created with optimal defaults

### Basic Usage

```
1. Copy any text to clipboard (Ctrl+C)
2. Click in your target application
3. Press Ctrl+Alt+V to begin typing
4. Press Esc to stop at any time
```

That's it! FlowState will type with human-like realism automatically.

## 💻 Usage Guide

### ⌨️ Keyboard Shortcuts

<div align="center">

| Shortcut | Function |
|:--------:|:---------|
| <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>V</kbd> | **Start typing** from clipboard |
| <kbd>Alt</kbd> + <kbd>↑</kbd> <kbd>↓</kbd> | **Navigate** settings in HUD |
| <kbd>Alt</kbd> + <kbd>←</kbd> <kbd>→</kbd> | **Adjust** current setting value |
| <kbd>Esc</kbd> | **Cancel** typing or reload script |

</div>

### 🎛️ The HUD (Heads-Up Display)

Press `Alt+↑` or `Alt+↓` to open the settings overlay:

```
⚙️ SETTING: Typing Speed (Lower is Faster)
VALUE: 60  (Default: 60)
(Use Alt+Left/Right to adjust)
```

**All four adjustable settings:**
1. **Typing Speed** — Base delay in milliseconds (20-200ms recommended)
2. **Variance** — Randomness factor (0-50ms recommended)
3. **Typo Chance** — Error probability as percentage (0-20% recommended)
4. **Typo Delay** — How long before correcting mistakes (50-500ms)

> 💾 **Auto-save**: All changes persist immediately to `settings.ini`

### 🎬 Real-World Example

**Typing "Hello, world! How are you?"**

```
H → e → l → l → o              [momentum builds: 60→55→50→45ms]
,                              [pause: 450ms]
 → w → o → r → l → d           [speed maintained]
!                              [pause: 1350ms - end of sentence]
 → H → o → w →  → a → r → e    
 → y → o → u → o               [typo: extra 'o']
[backspace]                    [pause: 180ms]
u                              [correction complete]
?                              [pause: 1200ms]
```

**What just happened:**
- ✅ Gradual speed increase across "Hello"
- ✅ Natural pause at comma
- ✅ Long pause after exclamation
- ✅ Realistic typo + correction
- ✅ Final pause at question mark

## ⚙️ Configuration

### 🎚️ Main Settings (HUD Adjustable)

<div align="center">

| Setting | Default | Range | Impact |
|:--------|:-------:|:-----:|:-------|
| **Typing Speed** | `60ms` | 20-200ms | Base delay between keys — *lower is faster* |
| **Variance** | `25ms` | 0-50ms | Timing randomness — *higher is less robotic* |
| **Typo Chance** | `4%` | 0-20% | Mistake probability — *4-6% feels natural* |
| **Typo Delay** | `150ms` | 50-500ms | Recognition time — *how long to notice errors* |

</div>

### 🔧 Advanced Settings

<details>
<summary><b>Click to expand advanced timing parameters</b></summary>

<br>

These settings require manual editing of `settings.ini`:

```ini
[Advanced]
SentencePauseMs=1200        # Pause after sentence endings (. ? !)
ParagraphPauseMs=2000       # Pause after paragraph breaks
BrainstormFrequency=60      # 1-in-N chance of random thinking pause
EmojiPauseMs=1800          # Delay before pasting emoji
```

**Detailed explanations:**

| Parameter | Purpose | Recommended Range |
|:----------|:--------|:------------------|
| `SentencePauseMs` | Pause duration after `.` `?` `!` followed by space | 800-2000ms |
| `ParagraphPauseMs` | Pause duration after line breaks (`Enter`) | 1500-3000ms |
| `BrainstormFrequency` | Inverse probability of long pause (60 = 1/60 chance) | 40-100 |
| `EmojiPauseMs` | Delay before pasting Unicode emoji | 1000-2500ms |

> 💡 **Tip**: Lower pause values for speed, higher for thoughtful/demo typing

</details>

### 📋 Preset Configurations

<details>
<summary><b>Click for ready-to-use configuration presets</b></summary>

<br>

**🎥 Demo/Presentation Mode**
```ini
UserMeanDelay=85
UserVariance=30
TypoChance=2
SentencePauseMs=1800
```
*Slower pace, fewer errors, longer pauses for audience comprehension*

---

**⚡ Speed Testing Mode**
```ini
UserMeanDelay=30
UserVariance=10
TypoChance=0
SentencePauseMs=400
```
*Fast, consistent, no typos, minimal pauses*

---

**💬 Natural Chat Mode**
```ini
UserMeanDelay=55
UserVariance=28
TypoChance=5
BrainstormFrequency=40
```
*Realistic conversational typing with occasional thinking pauses*

---

**📝 Transcription Mode**
```ini
UserMeanDelay=45
UserVariance=15
TypoChance=1
SentencePauseMs=600
```
*Fast and accurate with minimal errors*

</details>

## 🔬 How FlowState Works

### The Science of Human Typing

<details open>
<summary><b>🎲 Statistical Timing Model</b></summary>

<br>

FlowState doesn't use fixed delays. Instead, it uses a **Gaussian (bell curve) distribution**:

```
Delay = GaussianRandom(mean - momentum, variance)
```

**Why this matters:**
- ✅ Most keystrokes cluster around the mean (natural)
- ✅ Occasional faster/slower strokes (realistic variation)
- ✅ Avoids the robotic rhythm of fixed delays
- ❌ Traditional automation: `Sleep(50)` every keystroke = detectable

**Momentum System:**
```
Initial speed:  60ms
After 5 chars:  57.5ms  (momentum += 0.5)
After 10 chars: 55ms
After 20 chars: 50ms
Maximum boost:  15ms reduction
Reset on:       Typos, punctuation, pauses
```

</details>

<details>
<summary><b>🎯 Typo Generation Algorithm</b></summary>

<br>

**Two realistic error types:**

1. **Transposition Errors (40%)**
   ```
   Intended: "world"
   Typed:    "w" "o" "l" "r" [wrong order!]
   Result:   "wolr" → [backspace × 2] → "world"
   ```

2. **Neighbor Key Errors (60%)**
   ```
   Intended: "hello"
   Target:   "e"
   Neighbor: "r" (adjacent on QWERTY)
   Typed:    "h" "r" [wrong key!]
   Result:   "hr" → [backspace] → "he" "l" "l" "o"
   ```

**Layout-Aware Neighbor Maps:**

FlowState maintains physical keyboard maps for accurate mistakes:

```python
QWERTY['e'] = ['w', 's', 'd', 'r']  # Keys adjacent to 'e'
QWERTZ['z'] = ['t', 'g', 'h', 'u']  # Different layout!
AZERTY['e'] = ['z', 's', 'd', 'r']  # Different again!
```

**Detection Logic:**
```
1. Check active window's keyboard layout ID
2. Load corresponding neighbor map
3. On typo trigger: select random adjacent key
4. Type wrong key → pause → backspace → correct key
```

</details>

<details>
<summary><b>🧠 Cognitive Pause Modeling</b></summary>

<br>

Humans don't type continuously. FlowState models natural breakpoints:

**Punctuation-Based Pauses:**
```
Period/Question/Exclamation:  1200-1600ms  (end of thought)
Comma/Semicolon:              300-600ms    (clause break)
```

**Content-Based Pauses:**
```
Paragraph breaks (Enter):     2000-3000ms  (topic shift)
Emoji characters:             1800-2300ms  (UI interaction)
```

**Random Cognitive Pauses:**
```
Frequency:  1 in 60 spaces (configurable)
Duration:   1500-4000ms
Purpose:    Simulates "thinking" or hesitation
```

**Why it works:**  
These pauses mirror how humans mentally parse and compose text, making the typing pattern indistinguishable from real human input.

</details>

<details>
<summary><b>⚡ Bigram Speed Optimization</b></summary>

<br>

Common letter pairs are typed faster due to muscle memory:

```javascript
common_bigrams = ['th', 'he', 'in', 'er', 'an', 're', 'on', 
                  'at', 'en', 'nd', 'ti', 'es', 'or', 'te']

if (current_char + next_char in common_bigrams):
    typing_speed -= 10ms  // Faster by habit
```

**Example:**
```
Typing "the":    't'[60ms] 'h'[50ms] 'e'[50ms]  ← 'th' and 'he' optimized
Typing "xyz":    'x'[60ms] 'y'[60ms] 'z'[60ms]  ← No optimization
```

This subtle detail adds another layer of human-like behavior.

</details>

### 🌍 Multi-Layout Support

FlowState auto-detects your keyboard layout using Windows API:

```cpp
ThreadID = GetWindowThreadProcessId(ActiveWindow)
LayoutID = GetKeyboardLayout(ThreadID)

if (LayoutID & 0xFFFF == 0x0407):  // German
    return QWERTZ
elif (LayoutID & 0xFFFF == 0x040C):  // French
    return AZERTY
else:
    return QWERTY  // Default
```

Each layout has custom neighbor maps for accurate typo simulation.

## 🎯 Use Cases & Examples

### Common Scenarios

<table>
<tr>
<td width="33%" valign="top">

**🎬 Screen Recording**
```ini
UserMeanDelay=75
TypoChance=2
SentencePauseMs=1600
```
Clear, professional with minimal errors

</td>
<td width="33%" valign="top">

**🧪 QA Testing**
```ini
UserMeanDelay=35
TypoChance=0
SentencePauseMs=400
```
Fast and deterministic

</td>
<td width="33%" valign="top">

**💬 Chat Simulation**
```ini
UserMeanDelay=58
TypoChance=5
BrainstormFrequency=45
```
Natural conversation feel

</td>
</tr>
</table>

### Video Demonstration

> 🎥 **Coming soon**: Watch FlowState in action

### Real Performance

**Input:** "Hello, world! 🌍"

**Output timeline:**
```
0.00s  → H
0.06s  → e
0.11s  → l  (momentum building)
0.15s  → l
0.19s  → o
0.58s  → ,  (comma pause)
0.64s  → [space]
0.70s  → w
0.75s  → o
0.80s  → r
0.85s  → l
0.90s  → d
2.15s  → !  (sentence pause)
2.20s  → [space]
4.05s  → 🌍 (emoji pause + paste)
```

**Total: 4.05 seconds** for 15 characters — exactly how a human would type it.

## 🛠️ Troubleshooting & FAQ

<details>
<summary><b>❌ Nothing happens when I press Ctrl+Alt+V</b></summary>

<br>

**Check these:**
1. Is text in your clipboard? (Try copying something first)
2. Is the target window active? (Click into the application)
3. Is AutoHotkey v2.0+ installed? (v1.1 is incompatible)
4. Is the script running? (Check system tray for AutoHotkey icon)

**Quick fix:** Press `Esc` to reload the script

</details>

<details>
<summary><b>🤔 Typos never appear</b></summary>

<br>

1. Check `TypoChance` in HUD (press `Alt+↑` to navigate)
2. Ensure it's not set to 0%
3. Some apps block rapid backspace (Discord, some IDEs)
4. Typos only trigger on ASCII characters (not special chars)

**Note:** At 4% chance, you'll see ~1 typo per 25 characters

</details>

<details>
<summary><b>⚙️ Settings reset every launch</b></summary>

<br>

1. Check file permissions in script directory
2. Verify `settings.ini` exists and isn't read-only
3. Don't run multiple instances simultaneously
4. Try running as administrator

**Location:** `settings.ini` is created in same folder as `FlowState.ahk`

</details>

<details>
<summary><b>⚡ Typing is too slow/fast</b></summary>

<br>

Use the HUD to adjust in real-time:
1. Press `Alt+↑` until "Typing Speed" is selected
2. Press `Alt+←` to decrease (faster) or `Alt+→` to increase (slower)
3. Step size: 5ms per press

**Recommended ranges:**
- Fast: 30-45ms
- Normal: 50-70ms
- Slow: 75-100ms

</details>

<details>
<summary><b>📝 Large text confirmation keeps appearing</b></summary>

<br>

This is a safety feature for clipboards >5000 characters.

**To skip:** Click "Yes" to proceed

**Why it exists:** Prevents accidental 30+ minute typing sessions

</details>

<details>
<summary><b>🌍 Wrong keyboard layout detected</b></summary>

<br>

FlowState auto-detects layout from the active window:
- QWERTY (English/US) — Default
- QWERTZ (German) — Lang ID: 0x0407
- AZERTY (French) — Lang ID: 0x040C

**If wrong:**
1. Check Windows keyboard language in active window
2. Switch input method before typing
3. Restart script after changing layout

</details>

## 💡 Pro Tips

| Tip | Benefit |
|:----|:--------|
| 🎯 **Match content type** | Use slower speed (80ms) for creative writing, faster (40ms) for code |
| 📊 **Variance = 30-50% of speed** | `Speed: 60ms` → `Variance: 20-30ms` feels most natural |
| 🎲 **Typo sweet spot: 3-6%** | Too low = robotic, too high = frustrating |
| ⏸️ **Increase pauses for demos** | Sentence pause 1800ms+ gives audiences time to read |
| ⚡ **Disable typos for testing** | Set to 0% for deterministic QA automation |
| 🧠 **Lower BrainstormFreq for chat** | 40-50 adds realistic "thinking" moments |
| 🎬 **Test before recording** | Run a short test to dial in perfect settings |

## 🔧 Technical Details

<details>
<summary><b>System Integration</b></summary>

- Uses `SendEvent` for maximum application compatibility
- Detects keyboard layout via Windows API (`GetKeyboardLayout`)
- Preserves clipboard during emoji paste operations
- Monitors window focus to prevent mistyped input
- Event-driven architecture (no background polling)

</details>

<details>
<summary><b>Performance Characteristics</b></summary>

- **CPU Usage:** Minimal during idle, negligible during typing
- **Memory:** <5MB footprint
- **Compatibility:** Works with most Windows applications
- **Large Text:** Efficient string processing for 5000+ character texts
- **Safety:** Clipboard preservation, focus monitoring, cancellation support

</details>

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

**Ideas for enhancement:**
- 🎹 Additional layouts (Dvorak, Colemak, etc.)
- 📱 Mobile keyboard simulation
- 🎨 GUI configuration panel
- 📊 Typing pattern recording/playback
- 🤖 ML-based behavioral modeling
- 🌐 Multi-language support

**How to contribute:**
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the **MIT License** - see [LICENSE](LICENSE) for details.

**TL;DR:** Free to use, modify, and distribute. Just keep the license notice.

## ⚠️ Responsible Use

FlowState is designed for **legitimate purposes**:

✅ Testing chat applications and user interfaces  
✅ Creating educational content and tutorials  
✅ Screen recording and demonstrations  
✅ Accessibility and assistive technology  
✅ Quality assurance automation

❌ Do not use to:
- Spam or harass users
- Circumvent rate limits or anti-bot measures
- Violate platform terms of service
- Impersonate others maliciously

**Use ethically. Respect others. Follow the rules.**

---

<div align="center">

### 💙 Built by [hammersurf1](https://github.com/hammersurf1)

**If FlowState helps your workflow, give it a ⭐**

[![Star History](https://img.shields.io/github/stars/hammersurf1/FlowState?style=social)](https://github.com/hammersurf1/FlowState/stargazers)

[🐛 Report Bug](https://github.com/hammersurf1/FlowState/issues) • [💡 Request Feature](https://github.com/hammersurf1/FlowState/issues) • [📖 Documentation](https://github.com/hammersurf1/FlowState/wiki)

---

*Made with passion for developers, testers, and content creators*

</div>
