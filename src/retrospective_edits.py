"""
FlowState — Retrospective (look-back) edit planning and cursor tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Tuple

NavKey = Literal[
    "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown",
    "Control+ArrowLeft", "Control+ArrowRight",
    "Command+ArrowLeft", "Command+ArrowRight",
]

_DEFER_FRACTION = 0.70
_MIN_LOOKBACK_CHARS = 40


@dataclass(frozen=True)
class DeferredRevision:
    """A synonym-swap revision to perform after typing ahead."""
    trigger_after_directive: int
    char_offset: int
    word_len: int
    wrong: str
    right: str


@dataclass
class TypedPositionTracker:
    """Tracks emitted text layout for arrow-key navigation."""
    cursor_offset: int = 0
    line_lengths: List[int] = field(default_factory=lambda: [0])

    def record_text(self, text: str) -> None:
        """Advance cursor and line lengths for emitted directive text."""
        for char in text:
            if char == "\n":
                self.line_lengths.append(0)
            else:
                if not self.line_lengths:
                    self.line_lengths = [0]
                self.line_lengths[-1] += 1
            self.cursor_offset += 1

    def record_newline_key(self) -> None:
        """Record a newline emitted via Enter/Shift+Enter (not in directive text)."""
        self.line_lengths.append(0)
        self.cursor_offset += 1

    def offset_to_position(self, offset: int) -> Tuple[int, int]:
        """Return (line_index, column) for a character offset."""
        if offset < 0:
            offset = 0
        if offset > self.cursor_offset:
            offset = self.cursor_offset

        remaining = offset
        for line_idx, length in enumerate(self.line_lengths):
            if remaining <= length:
                return line_idx, remaining
            remaining -= length + 1  # +1 for newline between lines

        if self.line_lengths:
            return len(self.line_lengths) - 1, self.line_lengths[-1]
        return 0, 0

    def chars_to_navigate_back(self, target_offset: int) -> int:
        """Characters back from cursor to target offset (cursor lands before target)."""
        return max(0, self.cursor_offset - target_offset)

    def plan_navigate_back(
        self,
        target_offset: int,
        *,
        use_mac_cmd: bool = False,
    ) -> List[NavKey]:
        """Plan arrow keys to move from frontier to target_offset."""
        if target_offset >= self.cursor_offset:
            return []

        cur_line, cur_col = self.offset_to_position(self.cursor_offset)
        tgt_line, tgt_col = self.offset_to_position(target_offset)
        keys: List[NavKey] = []

        word_mod = "Command" if use_mac_cmd else "Control"

        while cur_line > tgt_line:
            keys.append("ArrowUp")
            cur_line -= 1
            cur_col = self.line_lengths[cur_line] if cur_line < len(self.line_lengths) else 0

        if cur_line == tgt_line and cur_col > tgt_col:
            dist = cur_col - tgt_col
            while dist > 8:
                keys.append(f"{word_mod}+ArrowLeft")  # type: ignore[arg-type]
                dist -= 5
            for _ in range(dist):
                keys.append("ArrowLeft")

        return keys

    def plan_navigate_forward(
        self,
        target_offset: int,
        *,
        use_mac_cmd: bool = False,
    ) -> List[NavKey]:
        """Plan arrow keys to return from target_offset to frontier."""
        if target_offset >= self.cursor_offset:
            return []

        cur_line, cur_col = self.offset_to_position(target_offset)
        end_line, end_col = self.offset_to_position(self.cursor_offset)
        keys: List[NavKey] = []

        word_mod = "Command" if use_mac_cmd else "Control"

        if cur_line == end_line:
            dist = end_col - cur_col
            while dist > 8:
                keys.append(f"{word_mod}+ArrowRight")  # type: ignore[arg-type]
                dist -= 5
            for _ in range(dist):
                keys.append("ArrowRight")
            return keys

        if cur_col < self.line_lengths[cur_line] if cur_line < len(self.line_lengths) else 0:
            dist = (self.line_lengths[cur_line] if cur_line < len(self.line_lengths) else 0) - cur_col
            while dist > 8:
                keys.append(f"{word_mod}+ArrowRight")  # type: ignore[arg-type]
                dist -= 5
            for _ in range(dist):
                keys.append("ArrowRight")

        while cur_line < end_line:
            keys.append("ArrowDown")
            cur_line += 1

        end_line_len = self.line_lengths[end_line] if end_line < len(self.line_lengths) else 0
        for _ in range(end_col):
            keys.append("ArrowRight")

        return keys

    def is_within_lookback(self, target_offset: int, lookback_chars: int) -> bool:
        """True if target is far enough back and within lookback window."""
        dist = self.chars_to_navigate_back(target_offset)
        return dist >= _MIN_LOOKBACK_CHARS and dist <= lookback_chars


def should_defer_revision(directive_index: int, text: str) -> bool:
    """Deterministic ~70% split for deferring revisions to look-back."""
    import hashlib
    digest = hashlib.md5(f"defer:{text}:{directive_index}".encode()).hexdigest()
    roll = int(digest[:8], 16) % 100
    return roll < int(_DEFER_FRACTION * 100)
