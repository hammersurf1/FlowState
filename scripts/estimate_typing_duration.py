#!/usr/bin/env python3
"""Estimate how long FlowState would take to type a piece of text.

Uses the same TypingPlanner + composition pause tiers as the app (no typos,
revisions, or fluency-state simulation). Clause pauses use a fixed RNG seed
so repeated runs match.

Examples:
    uv run python scripts/estimate_typing_duration.py
    uv run python scripts/estimate_typing_duration.py --preset essay
    uv run python scripts/estimate_typing_duration.py --file draft.txt
    uv run python scripts/estimate_typing_duration.py --settings
    type draft.txt | uv run python scripts/estimate_typing_duration.py -
"""

from __future__ import annotations

import argparse
import configparser
import random
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from typing_planner import CompositionSettings, TypingDirective, TypingPlanner  # noqa: E402
from semantic_analyzer import SemanticAnalyzer  # noqa: E402

PRESETS: dict[str, dict[str, int]] = {
    "essay": {
        "UserMeanDelay": 115,
        "UserVariance": 55,
        "EnableCompositionPauses": 1,
        "EnableClausePauses": 1,
        "EnableChunkBurst": 1,
        "CompositionPauseMinMs": 1500,
        "CompositionPauseMaxMs": 22000,
        "ParagraphPlanningMinMs": 12000,
        "ParagraphPlanningMaxMs": 45000,
        "CompositionSensitivity": 65,
        "SentencePauseMs": 1800,
        "ParagraphPauseMs": 3500,
    },
    "default": {
        "UserMeanDelay": 35,
        "UserVariance": 45,
        "EnableCompositionPauses": 0,
        "EnableClausePauses": 1,
        "EnableChunkBurst": 1,
        "CompositionPauseMinMs": 300,
        "CompositionPauseMaxMs": 6000,
        "ParagraphPlanningMinMs": 2000,
        "ParagraphPlanningMaxMs": 8000,
        "CompositionSensitivity": 50,
        "SentencePauseMs": 1200,
        "ParagraphPauseMs": 2000,
    },
}


@dataclass(frozen=True)
class TypingEstimate:
    total_ms: int
    keystroke_ms: int
    pause_before_ms: int
    pause_after_ms: int
    legacy_boundary_ms: int
    char_count: int
    word_count: int
    paragraph_count: int
    directive_count: int


def _format_duration(ms: int) -> str:
    if ms < 1000:
        return f"{ms} ms"
    total_seconds = ms / 1000.0
    if total_seconds < 60:
        return f"{total_seconds:.1f} s"
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    if minutes < 60:
        return f"{minutes}m {seconds:02d}s"
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours}h {minutes:02d}m {seconds:02d}s"


def _count_paragraphs(text: str) -> int:
    blocks = re.split(r"\n\s*\n", text.strip())
    return len([b for b in blocks if b.strip()]) or (1 if text.strip() else 0)


def _load_settings_ini() -> dict[str, int]:
    ini_path = Path.home() / ".flowstate" / "settings.ini"
    if not ini_path.is_file():
        raise FileNotFoundError(f"No settings file at {ini_path}")

    parser = configparser.ConfigParser()
    parser.read(ini_path, encoding="utf-8")
    settings = PRESETS["default"].copy()
    known_keys = set(settings) | {
        "EnableCompositionPauses",
        "CompositionPauseMinMs",
        "CompositionPauseMaxMs",
        "ParagraphPlanningMinMs",
        "ParagraphPlanningMaxMs",
        "CompositionSensitivity",
    }
    for section in parser.sections():
        if section.lower().startswith("profile:"):
            continue
        for key, value in parser.items(section):
            actual = next((k for k in known_keys if k.lower() == key.lower()), None)
            if not actual:
                continue
            try:
                settings[actual] = int(value)
            except ValueError:
                pass
    return settings


def _composition_from_settings(settings: dict[str, int]) -> CompositionSettings:
    return CompositionSettings(
        enabled=bool(settings.get("EnableCompositionPauses", 0)),
        sensitivity=settings.get("CompositionSensitivity", 50),
        pause_min_ms=settings.get("CompositionPauseMinMs", 300),
        pause_max_ms=settings.get("CompositionPauseMaxMs", 6000),
        paragraph_planning_min_ms=settings.get("ParagraphPlanningMinMs", 2000),
        paragraph_planning_max_ms=settings.get("ParagraphPlanningMaxMs", 8000),
    )


def _legacy_boundary_ms(
    directives: list[TypingDirective],
    settings: dict[str, int],
) -> int:
    """Sentence/paragraph sleeps applied by the engine when composition is off."""
    if settings.get("EnableCompositionPauses", 0):
        return 0

    sentence_ms = settings.get("SentencePauseMs", 1200)
    paragraph_ms = settings.get("ParagraphPauseMs", 2000)
    total = 0
    for directive in directives:
        stripped = directive.text.rstrip()
        if not stripped:
            continue
        if stripped[-1] in ".?!":
            total += sentence_ms + 200  # engine uses SentencePauseMs .. +400
        elif stripped[-1] == "\n":
            total += paragraph_ms + 1000  # engine uses ParagraphPauseMs .. +1000
    return total


def estimate_text(
    text: str,
    settings: dict[str, int],
    *,
    rng_seed: int = 42,
) -> TypingEstimate:
    if not text:
        return TypingEstimate(0, 0, 0, 0, 0, 0, 0, 0, 0)

    random.seed(rng_seed)
    planner = TypingPlanner(SemanticAnalyzer())
    mean_delay = settings["UserMeanDelay"]
    composition = _composition_from_settings(settings)
    directives = planner.plan(
        text,
        mean_delay,
        settings.get("UserVariance", 45),
        composition=composition,
    )

    keystroke_ms = 0
    pause_before_ms = 0
    pause_after_ms = 0
    for directive in directives:
        pause_before_ms += directive.pause_before_ms
        pause_after_ms += directive.pause_after_ms
        keystroke_ms += int(len(directive.text) * mean_delay * directive.delay_multiplier)

    legacy_boundary_ms = _legacy_boundary_ms(directives, settings)
    total_ms = keystroke_ms + pause_before_ms + pause_after_ms + legacy_boundary_ms

    return TypingEstimate(
        total_ms=total_ms,
        keystroke_ms=keystroke_ms,
        pause_before_ms=pause_before_ms,
        pause_after_ms=pause_after_ms,
        legacy_boundary_ms=legacy_boundary_ms,
        char_count=len(text),
        word_count=len(text.split()),
        paragraph_count=_count_paragraphs(text),
        directive_count=len(directives),
    )


def _read_input(args: argparse.Namespace) -> tuple[str, str]:
    if args.file:
        path = Path(args.file)
        return path.read_text(encoding="utf-8"), f"file:{path}"

    if args.clipboard:
        try:
            import pyperclip
        except ImportError as exc:
            raise SystemExit("pyperclip is required for --clipboard") from exc
        content = pyperclip.paste()
        if not content:
            raise SystemExit("Clipboard is empty.")
        return content, "clipboard"

    if args.text is not None:
        if args.text == "-":
            return sys.stdin.read(), "stdin"
        return args.text, "argument"

    # Default: clipboard
    try:
        import pyperclip
    except ImportError as exc:
        raise SystemExit("pyperclip is required; use --file or pipe text to stdin") from exc
    content = pyperclip.paste()
    if not content:
        raise SystemExit("Clipboard is empty. Copy text or use --file / stdin.")
    return content, "clipboard"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Estimate FlowState typing duration for text (planner-based).",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--clipboard",
        action="store_true",
        help="Read text from the system clipboard (default when no other source is given)",
    )
    source.add_argument(
        "--file",
        "-f",
        metavar="PATH",
        help="Read text from a file",
    )
    source.add_argument(
        "text",
        nargs="?",
        help='Text to analyze, or "-" for stdin',
    )
    parser.add_argument(
        "--preset",
        choices=sorted(PRESETS),
        default="essay",
        help="Timing preset (default: essay)",
    )
    parser.add_argument(
        "--settings",
        action="store_true",
        help="Load timing values from ~/.flowstate/settings.ini instead of a preset",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a single JSON object instead of a human-readable report",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.settings:
        try:
            settings = _load_settings_ini()
            preset_label = str(Path.home() / ".flowstate" / "settings.ini")
        except FileNotFoundError as exc:
            parser.error(str(exc))
    else:
        settings = PRESETS[args.preset].copy()
        preset_label = f"preset:{args.preset}"

    text, source_label = _read_input(args)
    estimate = estimate_text(text, settings)

    if args.json:
        import json

        payload = {
            "source": source_label,
            "preset": preset_label,
            "total_ms": estimate.total_ms,
            "total_human": _format_duration(estimate.total_ms),
            "keystroke_ms": estimate.keystroke_ms,
            "pause_before_ms": estimate.pause_before_ms,
            "pause_after_ms": estimate.pause_after_ms,
            "legacy_boundary_ms": estimate.legacy_boundary_ms,
            "char_count": estimate.char_count,
            "word_count": estimate.word_count,
            "paragraph_count": estimate.paragraph_count,
            "directive_count": estimate.directive_count,
            "composition_enabled": bool(settings.get("EnableCompositionPauses", 0)),
        }
        print(json.dumps(payload, indent=2))
        return 0

    print(f"Estimated typing time: {_format_duration(estimate.total_ms)}")
    print()
    print(f"  Keystrokes:              {_format_duration(estimate.keystroke_ms):>10}")
    print(f"  Pauses (before typing):  {_format_duration(estimate.pause_before_ms):>10}")
    print(f"  Pauses (after typing):   {_format_duration(estimate.pause_after_ms):>10}")
    if estimate.legacy_boundary_ms:
        print(
            f"  Sentence/paragraph:      {_format_duration(estimate.legacy_boundary_ms):>10}"
        )
    print()
    print(f"Source:      {source_label}")
    print(f"Profile:     {preset_label}")
    print(
        f"Characters:  {estimate.char_count:,}  |  "
        f"Words: {estimate.word_count:,}  |  "
        f"Paragraphs: {estimate.paragraph_count}"
    )
    print(f"Directives:  {estimate.directive_count:,}")
    print()
    print(
        "Note: Excludes typos, smart revisions, fluency states, and brainstorm pauses. "
        "Clause pauses use RNG seed 42 for a stable estimate."
    )
    if settings.get("EnableCompositionPauses", 0):
        print(
            "Note: With composition pauses on, SentencePauseMs / ParagraphPauseMs "
            "are not added (boundaries use composition tiers)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
