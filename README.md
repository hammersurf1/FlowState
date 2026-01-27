<div align="center">

# 🎹 HumanTyperHUD

### Simulate Human Typing with Uncanny Realism

[![AutoHotkey](https://img.shields.io/badge/AutoHotkey-v2.0+-blue.svg)](https://www.autohotkey.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

**Human-like typing simulation** • **Realistic typos** • **Cognitive pauses** • **Multi-layout support**

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Configuration](#-configuration)

---

</div>

## 📖 About

HumanTyperHUD is a sophisticated AutoHotkey script that transforms clipboard text into realistic human typing. It simulates natural typing patterns including momentum building, cognitive pauses, realistic typos with auto-correction, and adapts to QWERTY, QWERTZ, and AZERTY keyboard layouts.

Perfect for testing chat interfaces, creating demonstrations, screen recordings, or accessibility needs.

## ✨ Features

<table>
<tr>
<td width="50%">

### 🎯 Core Capabilities
- ⚡ **Human-like Typing** — Gaussian-distributed delays with momentum
- 🔄 **Realistic Typos** — Transposition & neighbor-key mistakes
- 🧠 **Cognitive Pauses** — Natural breaks at sentences & paragraphs
- 🌍 **Multi-Layout** — Auto-detects QWERTY, QWERTZ, AZERTY
- 😊 **Emoji Support** — Smart handling of Unicode characters
- 🎛️ **Real-time HUD** — Live on-screen configuration

</td>
<td width="50%">

### ⚙️ Adjustable Parameters
- 🏃 **Typing Speed** — Base delay between keystrokes
- 📊 **Variance** — Consistency vs randomness
- 🎲 **Typo Chance** — Probability of mistakes (%)
- ⏱️ **Typo Delay** — Correction reaction time
- 💭 **Advanced Timing** — Sentence, paragraph, brainstorm pauses

</td>
</tr>
</table>

## 🚀 Installation

### Prerequisites
- Windows 10 or 11
- [AutoHotkey v2.0+](https://www.autohotkey.com/download/) (not v1.1)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/HumanTyperHUD.git
cd HumanTyperHUD

# Run the script
HumanTyperHUD.ahk
```

Or simply download `HumanTyperHUD.ahk` and double-click to run.

> **Note:** On first run, the script automatically creates `settings.ini` with default values.

## 💻 Usage

### Quick Start Guide

1. **Copy** text to clipboard (`Ctrl+C`)
2. **Click** in your target application
3. **Press** `Ctrl+Alt+V` to start typing
4. **Press** `Esc` to cancel anytime

### ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|:---------|:-------|
| <kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>V</kbd> | Start typing from clipboard |
| <kbd>Alt</kbd>+<kbd>↑</kbd> / <kbd>↓</kbd> | Navigate settings |
| <kbd>Alt</kbd>+<kbd>←</kbd> / <kbd>→</kbd> | Adjust current setting |
| <kbd>Esc</kbd> | Cancel typing / Reload script |

### 🎛️ HUD Controls

The on-screen HUD lets you adjust settings in real-time:

- Navigate with <kbd>Alt</kbd>+<kbd>↑</kbd>/<kbd>↓</kbd>
- Modify values with <kbd>Alt</kbd>+<kbd>←</kbd>/<kbd>→</kbd>
- View current value vs default

Settings auto-save to `settings.ini`.

## ⚙️ Configuration

### Main Settings

| Setting | Default | Range | Description |
|:--------|:-------:|:-----:|:------------|
| **Typing Speed** | 60ms | 20-200ms | Mean delay between keystrokes *(lower = faster)* |
| **Variance** | 25ms | 0-50ms | Randomness in timing *(creates natural rhythm)* |
| **Typo Chance** | 4% | 0-20% | Probability of making a typo |
| **Typo Delay** | 150ms | 50-500ms | Reaction time before fixing typos |

<details>
<summary><b>📝 Advanced Settings</b> (edit <code>settings.ini</code>)</summary>

```ini
[Advanced]
SentencePauseMs=1200        # Pause after . ? !
ParagraphPauseMs=2000       # Pause after paragraph breaks
BrainstormFrequency=60      # 1 in N chance of thinking pause
EmojiPauseMs=1800          # Pause before typing emoji
```

- **SentencePauseMs** — Pause duration after sentence-ending punctuation
- **ParagraphPauseMs** — Pause duration after newlines/paragraphs
- **BrainstormFrequency** — How often random "thinking" pauses occur
- **EmojiPauseMs** — Delay before pasting emoji characters

</details>

## 🔬 How It Works

<details>
<summary><b>Typing Simulation Engine</b></summary>

The script employs multiple sophisticated techniques:

1. **Gaussian Randomization** — Keystroke delays follow a natural bell curve distribution
2. **Momentum Building** — Typing gradually accelerates, mimicking muscle memory (up to 15ms speedup)
3. **Bigram Optimization** — Common letter pairs (`th`, `he`, `in`, etc.) are typed 10ms faster
4. **Cognitive Load Modeling** — Realistic pauses at natural breakpoints

</details>

<details>
<summary><b>Typo Generation System</b></summary>

Two types of realistic mistakes:

- **Character Transposition** (40%) — Wrong order: `wrold` → `world`
- **Neighbor Key Mistakes** (60%) — Adjacent key: `heklo` → `hello`

The script:
- Auto-detects active keyboard layout (QWERTY/QWERTZ/AZERTY)
- Uses layout-specific neighbor maps for accuracy
- Pauses realistically before correcting with backspace
- Resets momentum after typo corrections

</details>

<details>
<summary><b>Layout Detection</b></summary>

Automatically detects keyboard layout via Windows API:

- **QWERTY** — English/US (default)
- **QWERTZ** — German (z/y swapped)
- **AZERTY** — French (a/q/w rearranged)

Each layout has custom neighbor-key maps for realistic typos.

</details>

## 📋 Examples

### Typical Typing Flow

When typing **"Hello, world!"** the script will:

```
H → e → l → l → o [momentum builds] → , [pause 300-600ms] 
→ w → o → r → l → d [possible typo: "worldd"] 
→ [backspace] → d [pause 1200ms+] → !
```

**Key behaviors:**
- Momentum gradually increases speed across `H-e-l-l-o`
- Natural pause at comma
- 4% chance of typo (e.g., extra 'd')
- Realistic correction delay + backspace
- Longer pause after period

### Use Cases

<table>
<tr><td>

**🎥 Demonstrations**
```ini
UserMeanDelay=80
TypoChance=2
SentencePauseMs=1800
```
Slower, fewer typos, longer pauses

</td><td>

**⚡ Speed Testing**
```ini
UserMeanDelay=30
TypoChance=0
SentencePauseMs=500
```
Fast, no typos, minimal pauses

</td></tr>
<tr><td>

**🎭 Realistic Chat**
```ini
UserMeanDelay=60
TypoChance=5
BrainstormFrequency=40
```
Natural speed, occasional typos, thinking pauses

</td><td>

**📝 Transcription**
```ini
UserMeanDelay=50
Variance=15
TypoChance=1
```
Quick and consistent, rare mistakes

</td></tr>
</table>

## 🛠️ Troubleshooting

<details>
<summary><b>Script won't type anything</b></summary>

- ✅ Verify target window is active and focused
- ✅ Confirm clipboard contains text (not empty)
- ✅ Check AutoHotkey v2.0+ is installed (v1.1 won't work)
- ✅ Try reloading script with <kbd>Esc</kbd>

</details>

<details>
<summary><b>Typos aren't being generated</b></summary>

- ✅ Ensure Typo Chance > 0% (check HUD)
- ✅ Verify target app accepts keyboard input
- ✅ Confirm correct layout is detected (QWERTY/QWERTZ/AZERTY)
- ✅ Some apps may block rapid backspace sequences

</details>

<details>
<summary><b>Settings not persisting</b></summary>

- ✅ Check script has write permissions in directory
- ✅ Ensure `settings.ini` isn't read-only
- ✅ Verify no other AutoHotkey instance is running
- ✅ Try running script as administrator

</details>

<details>
<summary><b>Large text confirmation appears</b></summary>

This is intentional for clipboard content >5000 characters to prevent accidental massive pastes. Click "Yes" to continue or "No" to cancel.

</details>

## 💡 Tips & Best Practices

| Goal | Recommendations |
|:-----|:----------------|
| **Natural typing** | Variance 30-50% of speed • Typo chance 2-5% • Use momentum |
| **Demonstrations** | Speed 80-100ms • Sentence pause 1500-2000ms • Typo chance 1-2% |
| **Testing/QA** | Disable typos (0%) • Reduce pauses • Lower variance for consistency |
| **Screen recording** | Match your speaking pace • Increase cognitive pauses • Fewer typos |

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

Contributions are welcome! Here are some ideas:

- 🌐 Additional keyboard layouts (Dvorak, Colemak, etc.)
- 📊 Per-application typing profiles
- 🎯 Recording/playback of real typing patterns
- 🤖 ML-based timing prediction
- 🎨 GUI configuration interface
- 🌍 Internationalization support

Feel free to open an issue or submit a pull request!

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is designed for **legitimate purposes** such as:
- Testing chat interfaces and applications
- Creating demonstrations and tutorials
- Screen recording and content creation
- Accessibility assistance

**Please use responsibly** and respect the terms of service of any platform where you use automated typing.

---

<div align="center">

**Made with ❤️ for testers, developers, and content creators**

If you find this useful, consider giving it a ⭐!

[Report Bug](https://github.com/yourusername/HumanTyperHUD/issues) • [Request Feature](https://github.com/yourusername/HumanTyperHUD/issues)

</div>
