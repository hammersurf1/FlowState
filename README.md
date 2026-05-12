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

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

* [![Python][Python.org]][Python-url]
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

2. **Run the setup script for your platform:**

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
   - Check that Python 3 is installed
   - Create a virtual environment in `.venv/`
   - Install dependencies from the platform-specific requirements file
   - Print clear instructions for running the app

3. **Run FlowState:**

   **Windows** (run as Administrator):
   ```sh
   .venv\Scripts\activate
   python src\main_win.py
   ```

   **macOS:**
   ```sh
   source .venv/bin/activate
   python3 src/main_mac.py
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

### System tray HUD

The icon gives a live status readout. It shows the active setting's short name and current value.

| Icon color | Meaning |
|---|---|
| 🔵 Blue | Idle |
| 🟢 Green | Typing / countdown |
| 🟠 Orange | Paused |

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

The setup scripts echo every step they perform. The source code is MIT-licensed and fully auditable.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ROADMAP -->
## Roadmap

- [x] Windows Support
- [x] macOS Support
- [ ] Linux Driver Implementation
- [ ] Custom Macro Support
- [ ] Profile Saving/Loading
- [ ] Intelligent revision history w/ NLP

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
[license-url]: https://github.com/hammersurf1/FlowState/blob/master/LICENSE.txt
[product-screenshot]: assets/screenshot.png

[Python.org]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[Python-url]: https://www.python.org/
[Pillow.readthedocs.io]: https://img.shields.io/badge/Pillow-111111?style=for-the-badge&logo=python&logoColor=white
[Pillow-url]: https://python-pillow.org/
[PyPI.org]: https://img.shields.io/badge/PyPI-3775A9?style=for-the-badge&logo=pypi&logoColor=white
[PyPI-url]: https://pypi.org/
