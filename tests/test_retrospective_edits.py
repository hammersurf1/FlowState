import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine import TypingEngine
from retrospective_edits import (
    DeferredRevision,
    TypedPositionTracker,
    should_defer_revision,
)
from typing_planner import TypingPlanner
from semantic_analyzer import SemanticAnalyzer


class MockDriver:
    def __init__(self):
        self.log = []

    def send_char(self, c, dwell=0.01):
        self.log.append(("char", c))

    def send_backspace(self):
        self.log.append(("backspace",))

    def send_key(self, k):
        self.log.append(("key", k))

    def send_enter(self):
        self.log.append(("key", "Enter"))

    def send_shift_enter(self):
        self.log.append(("key", "Shift+Enter"))

    def send_tab(self):
        self.log.append(("key", "Tab"))

    def surgical_paste(self, text):
        self.log.append(("paste", text))

    def attach(self, title=None):
        pass

    def detach(self):
        pass

    def focus_page(self):
        pass

    def get_clipboard(self):
        return ""

    def detect_layout(self):
        return "QWERTY"


@pytest.fixture(scope="module")
def planner():
    return TypingPlanner(SemanticAnalyzer())


@pytest.fixture
def engine():
    driver = MockDriver()
    eng = TypingEngine(driver)
    eng.settings["UserMeanDelay"] = 5
    eng.settings["UserVariance"] = 2
    eng.settings["EnableSemanticSpeed"] = 1
    eng.settings["EnableClausePauses"] = 1
    eng.settings["EnableChunkBurst"] = 1
    eng.settings["EnableSmartRevisions"] = 1
    eng.settings["EnableEntityCare"] = 1
    eng.settings["EnableRevisions"] = 1
    eng.settings["EnableTypos"] = 0
    eng.settings["EnableFingerPenalty"] = 0
    eng.settings["EnableFluencyStates"] = 0
    eng.settings["EnableNumberSymbolCare"] = 0
    eng.settings["EnableCapsRunRealism"] = 0
    eng.settings["EnableFrequencyTypos"] = 0
    eng.settings["EnableDeferredCorrections"] = 0
    eng.settings["RetrospectiveLookbackChars"] = 1200
    return eng


ESSAY = (
    "The government must demonstrate that significant reforms will benefit society. "
    "Furthermore, the results were excellent because the policy worked well."
)


def test_tracker_single_line_nav_back():
    tracker = TypedPositionTracker()
    tracker.record_text("The results were excellent.")
    tracker.cursor_offset = len("The results were excellent.")
    keys = tracker.plan_navigate_back(4, use_mac_cmd=False)
    assert "ArrowLeft" in keys or "Control+ArrowLeft" in keys
    assert tracker.chars_to_navigate_back(4) == len("The results were excellent.") - 4


def test_tracker_multiline_position():
    tracker = TypedPositionTracker()
    tracker.record_text("hello\nworld")
    assert tracker.offset_to_position(6) == (1, 0)
    assert tracker.offset_to_position(8) == (1, 2)


def test_tracker_multiline_nav_uses_arrow_up():
    tracker = TypedPositionTracker()
    tracker.record_text("hello\nworld")
    keys = tracker.plan_navigate_back(2, use_mac_cmd=False)
    assert "ArrowUp" in keys


def test_should_defer_revision_is_deterministic():
    assert should_defer_revision(0, "sample text") == should_defer_revision(0, "sample text")


def test_plan_with_deferred_splits_revisions(planner):
    random.seed(42)
    directives, deferred = planner.plan_with_deferred(ESSAY, 110, 45)
    plain = planner.plan(ESSAY, 110, 45)

    plain_revisions = sum(
        1 for d in plain if d.revision_candidate or d.revision_span
    )
    deferred_count = len(deferred)
    remaining_in_place = sum(
        1 for d in directives if d.revision_candidate or d.revision_span
    )

    assert plain_revisions >= 1
    assert deferred_count + remaining_in_place <= plain_revisions
    if deferred_count > 0:
        assert remaining_in_place < plain_revisions


def test_deferred_revision_offsets_are_valid(planner):
    random.seed(7)
    directives, deferred = planner.plan_with_deferred(ESSAY, 110, 45)
    full_text = "".join(d.text for d in directives)
    offset = 0
    for d in directives:
        offset += len(d.text)

    for rev in deferred:
        assert 0 <= rev.char_offset < offset
        assert rev.right == full_text[rev.char_offset:rev.char_offset + rev.word_len]
        assert rev.wrong.lower() != rev.right.lower()


def test_lookback_cap(engine):
    tracker = TypedPositionTracker()
    tracker.record_text("a" * 200)
    rev = DeferredRevision(
        trigger_after_directive=0,
        char_offset=10,
        word_len=4,
        wrong="word",
        right="aaaa",
    )
    engine.settings["RetrospectiveLookbackChars"] = 50
    assert engine._is_retrospective_eligible(rev, tracker) is False


def test_nonlinear_keystroke_log(engine):
    random.seed(1)
    engine.settings["RevisionChance"] = 100
    engine.is_running = True
    engine._type_plain_text(ESSAY, {})

    log = engine.driver.log
    char_count = sum(1 for entry in log if entry[0] == "char")
    arrow_keys = [
        entry for entry in log
        if entry[0] == "key" and "Arrow" in entry[1]
    ]
    backspaces = [entry for entry in log if entry[0] == "backspace"]

    assert char_count > 20
    assert len(arrow_keys) >= 1
    assert len(backspaces) >= 1

    first_arrow = next(i for i, e in enumerate(log) if e[0] == "key" and "Arrow" in e[1])
    chars_before_arrow = sum(1 for e in log[:first_arrow] if e[0] == "char")
    assert chars_before_arrow >= 40
