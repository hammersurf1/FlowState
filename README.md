<a id="readme-top"></a>

<div align="center">

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
![GitHub License](https://img.shields.io/github/license/hammersurf1/FlowState?style=for-the-badge)

</div>

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/hammersurf1/FlowState">
    <img src="assets/logo.png" alt="Logo" width="" height="">
  </a>

<h3 align="center">FlowState</h3>

  <p align="center">
    A realistic typing simulator that pastes clipboard content by "typing" it out with human-like imperfections.
    <br />
    <a href="https://github.com/hammersurf1/FlowState"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/hammersurf1/FlowState">View Demo</a>
    &middot;
    <a href="https://github.com/hammersurf1/FlowState/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
    &middot;
    <a href="https://github.com/hammersurf1/FlowState/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#option-1-download-the-installer-recommended">Option 1: Installer</a></li>
        <li><a href="#option-2-manual-setup-clone--zip">Option 2: Manual Setup</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#transparency">Transparency</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->
## About The Project

<!-- [![FlowState Screen Shot][product-screenshot]](https://github.com/hammersurf1/FlowState) -->

FlowState is a cross-platform typing simulator designed for intelligent humanlike autotyping. Unlike standard macro pastes that dump text instantly, FlowState simulates a human touch by incorporating:

* **Natural Rhythm:** Gaussian distribution for keystroke delays to avoid robotic patterns.
* **Context Awareness:** Faster typing on common bigrams and realistic pauses at punctuation.
* **Intelligent Errors:** Simulated mistakes determined by content, followed by realistic correction pauses.
* **Cognitive Pauses:** Random "thinking" moments and paragraph breaks.
* **Per-App Profiles:** Override typing settings per application (e.g., fast in Slack, careful in Google Docs).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

* [![Python][Python.org]][Python-url]
* [![spaCy][spaCy.io]][spaCy-url]
* [![Pillow][Pillow.readthedocs.io]][Pillow-url]
* [![PyPI][PyPI.org]][PyPI-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->
## Getting Started

FlowState has separate builds for **Windows** and **macOS**. Choose the method that works best for you.

### Option 1: Download the Installer (Recommended)

Pre-built installers are available on the [Releases](https://github.com/hammersurf1/FlowState/releases) page.

| Platform | Download | What it does |
|----------|----------|--------------|
| **Windows** | `FlowState_Windows_Setup.exe` | Standard Windows installer (Inno Setup). Installs to Program Files, creates Start Menu & desktop shortcuts. |
| **macOS** | `FlowState_Mac_Installer.dmg` | Standard macOS disk image. Drag `FlowState.app` to your Applications folder. |

> **Windows Note:** FlowState requires **Administrator** to run because it uses global keyboard hooks (a Windows security requirement).
>
> **macOS Note:** On first launch, macOS will ask you to grant **Accessibility** permission (System Settings → Privacy & Security → Accessibility). This is required for global hotkeys and is a standard Apple security prompt.

### Option 2: Manual Setup (Clone / ZIP)

If you prefer to run from source, or you want to inspect exactly what FlowState does:

1. **Clone the repo** (or download the ZIP)
   ```sh
   git clone https://github.com/hammersurf1/FlowState.git
   cd FlowState
   ```

2. **Install [uv](https://docs.astral.sh/uv/getting-started/installation/)** if you don't have it yet.

3. **Run the setup script for your platform:**

   **Windows:**
   ```sh
   setup_windows.bat
   ```

   **macOS:**
   ```sh
   chmod +x setup_mac.sh
   ./setup_mac.sh
   ```

   The setup scripts will:
   - Install Python 3.12 via uv (if needed)
   - Create a virtual environment in `.venv/`
   - Run `uv sync` to install dependencies from `pyproject.toml`
   - Download the spaCy `en_core_web_md` model and NLTK WordNet corpora

4. **Run FlowState:**

   **Windows** (run as Administrator):
   ```sh
   uv run python src\main_win.py
   ```

   **macOS:**
   ```sh
   uv run python3 src/main_mac.py
   ```

   **Updating dependencies or models after pulling changes:**
   ```sh
   uv sync
   uv run python scripts/download_models.py
   ```

   **Estimate typing duration** (planner + composition pauses; no typos/revisions):
   ```sh
   uv run python scripts/estimate_typing_duration.py --preset essay --file draft.txt
   ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- USAGE EXAMPLES -->
## Usage

1. **Copy text** to your clipboard (`Ctrl+C` / `Cmd+C`).
2. **Click into** the target text field (in Chrome).
3. Press the trigger hotkey. A 3-second countdown lets you release the hotkey before typing starts.

### Controls

| Hotkey | Windows | macOS |
|---|---|---|
| Start / Pause / Resume | `Ctrl+Alt+V` | `⌘+⌥+V` |
| Pause immediately | `Esc` | `Esc` |
| Abort and reset | `Esc` (double-tap, <0.5s) | `Esc` (double-tap, <0.5s) |
| Cycle through settings | `Ctrl+Shift+Alt+↑/↓` | `⌘+⇧+⌥+↑/↓` |
| Adjust selected setting | `Ctrl+Shift+Alt+→/←` | `⌘+⇧+⌥+→/←` |

### Rich Text Formatting

FlowState can type with **rich formatting** (bold, italic, lists, headings, etc.) when **Enable Rich Text** is turned on in Settings. Use Markdown syntax in your clipboard text:

| Syntax | Result | Shortcut sent |
|---|---|---|
| `**text**` or `__text__` | **Bold** | Ctrl/Cmd+B |
| `*text*` or `_text_` | *Italic* | Ctrl/Cmd+I |
| `___text___` | <u>Underline</u> | Ctrl/Cmd+U |
| `~~text~~` | ~~Strikethrough~~ | Alt+Shift+5 (Google Docs) |
| `# Heading` | Heading 1 | Ctrl/Cmd+Alt+1 |
| `## Heading` | Heading 2 | Ctrl/Cmd+Alt+2 |
| `### Heading` | Heading 3 | Ctrl/Cmd+Alt+3 |
| `- item` or `* item` | • Bullet list | Ctrl/Cmd+Shift+8 |
| `1. item` | 1. Numbered list | Ctrl/Cmd+Shift+7 |
| `  - item` (2 spaces) | → Sub-bullet | Tab indent |
| `\t- item` (tab) | → Sub-bullet | Tab indent |

**Example clipboard text:**
```markdown
# Meeting Notes

**Attendees:** Alice, Bob

## Agenda
- Intro
  - Welcome
- ~~Old item~~ (cancelled)
1. Action items
  1. Send report
```

**Notes:**
- Strikethrough (`~~`) works best in **Google Docs** (uses the Docs-specific Alt+Shift+5 shortcut).
- Sub-bullets and sub-numbers are created by indenting with **2 spaces** or a **tab**.
- The target editor must support the standard Ctrl/Cmd shortcuts for formatting.

### System tray HUD

The icon gives a live status readout. It shows the active setting's short name and current value.

| Icon color | Meaning |
|---|---|
| 🔵 Blue | Idle |
| 🟢 Green | Typing / countdown |
| 🟠 Orange | Paused |

### Semantic Humanization

FlowState uses **spaCy** with the `en_core_web_md` model to make typing feel genuinely human. These features can be toggled individually in Settings under the *Semantic Humanization* section:

| Feature | What it does |
|---|---|
| **Smart Revisions** | Occasionally types a WordNet synonym first, hesitates, backspaces, and types the correct word. Works on nouns, verbs, adjectives, and adverbs — including inside noun phrases. |
| **Semantic Speed** | Adjusts typing speed based on word frequency. Common words (e.g., "the", "and") flow faster; rare words slow down slightly. |
| **Entity Care** | Named entities (people, companies, places) are typed with extra care — fewer typos and steadier rhythm. |
| **Clause Pauses** | Uses dependency parsing to insert micro-pauses at the end of subordinate clauses, not just at sentence boundaries. |
| **Chunk Burst** | Treats noun phrases like "the quarterly results" as a single cognitive burst, reducing hesitation inside the phrase. |
| **Frequency Typos** | Very common words get fewer typos; rare words get the full typo chance. |
| **Deferred Corrections** | Sometimes finishes the current word before backspacing a typo, just like a real person would. |
| **Composition Pauses** | Content-aware drafting hesitation before hard words, discourse markers, and new paragraphs. Uses the **Essay Drafting** preset or enable manually in Settings. Replaces random brainstorm pauses when active. |

### Motor Realism

Beyond semantic understanding, FlowState models actual motor constraints:

| Feature | What it does |
|---|---|
| **Same-Finger Penalty** | Slightly slower when the same finger types two consecutive keys. |
| **Fluency States** | Alternates between "in the zone" (low variance) and "stumbling" (higher variance) periods. |
| **Number / Symbol Care** | Digits and symbols are typed more deliberately with fewer typos. |
| **Caps Lock Realism** | Delay penalty applies only to the first capital in a run, not every capital letter. |

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- TRANSPARENCY -->
## Transparency

FlowState is fully open-source and designed to be transparent about what it does:

**Why does it need Administrator / Accessibility permissions?**
- **Windows:** The `keyboard` library requires Administrator to register global hotkeys. This is a Windows security policy — any app that listens for keystrokes system-wide needs elevated privileges.
- **macOS:** The `pynput` library requires Accessibility permission to register global hotkeys. This is Apple's standard security model — you enable it once in System Settings and it persists.

**What does FlowState access?**
- Your **clipboard** (to read the text you want typed)
- Your **keyboard** (to simulate keystrokes and listen for hotkeys)
- **Google Chrome** (connects via Chrome's debugging port to type into browser tabs)

**What FlowState does NOT do:**
- ❌ No network requests (except localhost to Chrome)
- ❌ No telemetry or analytics
- ❌ No data collection
- ❌ No registry/system modifications

The setup scripts echo every step they perform. The source code is MIT-licensed and fully auditable. The system is 100% local.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ROADMAP -->
## Roadmap

- [x] Windows Support
- [x] macOS Support
- [x] Custom Macro Support
- [x] Intelligent revision history w/ NLP
- [x] Per-App Profiles
- [ ] Linux Driver Implementation

See the [open issues](https://github.com/hammersurf1/FlowState/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Top contributors:

<a href="https://github.com/hammersurf1/FlowState/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=hammersurf1/FlowState" alt="contrib.rocks image" />
</a>

<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

* [Playwright](https://playwright.dev/)
* [pystray](https://github.com/moses-palmer/pystray)
* [pynput](https://github.com/moses-palmer/pynput)
* [keyboard library](https://github.com/boppreh/keyboard)
* [Best-README-Template](https://github.com/othneildrew/Best-README-Template)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/hammersurf1/FlowState.svg?style=for-the-badge
[contributors-url]: https://github.com/hammersurf1/FlowState/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/hammersurf1/FlowState.svg?style=for-the-badge
[forks-url]: https://github.com/hammersurf1/FlowState/network/members
[stars-shield]: https://img.shields.io/github/stars/hammersurf1/FlowState.svg?style=for-the-badge
[stars-url]: https://github.com/hammersurf1/FlowState/stargazers
[issues-shield]: https://img.shields.io/github/issues/hammersurf1/FlowState.svg?style=for-the-badge
[issues-url]: https://github.com/hammersurf1/FlowState/issues
[license-shield]: https://img.shields.io/github/license/hammersurf1/FlowState.svg?style=for-the-badge
[license-url]: https://github.com/hammersurf1/FlowState/blob/main/LICENSE.txt
[product-screenshot]: assets/screenshot.png

[Python.org]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[Python-url]: https://www.python.org/
[spaCy.io]: https://img.shields.io/badge/spaCy-09A3D5?style=for-the-badge&logo=spacy&logoColor=white
[spaCy-url]: https://spacy.io/
[Pillow.readthedocs.io]: https://img.shields.io/badge/Pillow-111111?style=for-the-badge&logo=python&logoColor=white
[Pillow-url]: https://python-pillow.org/
[PyPI.org]: https://img.shields.io/badge/PyPI-3775A9?style=for-the-badge&logo=pypi&logoColor=white
[PyPI-url]: https://pypi.org/
