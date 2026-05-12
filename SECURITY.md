# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in FlowState, please **do not open a public GitHub Issue**.

Instead, report it by opening a [GitHub Security Advisory](https://github.com/hammersurf1/FlowState/security/advisories/new) (private by default). This allows the issue to be assessed and patched before public disclosure.

Please include:
- A description of the vulnerability
- Steps to reproduce it
- The potential impact

## Scope

FlowState is a local desktop application with no server component. The relevant attack surface is:

- **Clipboard access** — reads the clipboard to obtain text to type
- **Global keyboard hooks** — registers hotkeys system-wide (requires Admin on Windows, Accessibility on macOS)
- **Chrome DevTools Protocol** — connects to a locally running Chrome instance via `localhost` only

FlowState makes **no outbound network requests** beyond `localhost`.
