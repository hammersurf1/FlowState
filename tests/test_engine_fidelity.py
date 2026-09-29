"""Regression tests found by the tests/harness sweeps: what the user sees must equal
what was on the clipboard (typos and revisions must always be corrected)."""
import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "harness"))
import pytest
from engine import TypingEngine
from rich_text_formatter import RichTextFormatter, KeyAction
from sim_editor import SimEditorDriver

TEXT = "The quarterly results were excellent because Alice worked hard.\nSecond line here.\n\nThird after blank."
OFF = dict(EnableTypos=0, EnableRevisions=0, EnableSmartRevisions=0, TypoChance=0)


@pytest.fixture(scope="module")
def shared_nlp(tmp_path_factory):
    os.environ["HOME"] = str(tmp_path_factory.mktemp("home"))
    e = TypingEngine(SimEditorDriver())
    e._ensure_semantic_layer()
    return e._analyzer, e._planner


def make(shared_nlp, clip="", **s):
    drv = SimEditorDriver(clip)
    e = TypingEngine(drv)
    e._analyzer, e._planner = shared_nlp
    e._sleep = lambda d: None
    e.settings.update(dict(UserMeanDelay=5, UserVariance=2, TypoChance=25, RevisionChance=100, EnableRichText=0), **s)
    return e, drv


@pytest.mark.parametrize("seed", range(15))
def test_semantic_typos_and_revisions_never_lose_text(shared_nlp, seed):
    random.seed(seed)
    e, d = make(shared_nlp)
    e.is_running = True
    e._type_plain_text(TEXT, {})
    assert d.text == TEXT


def test_engine_not_stuck_running_after_error(shared_nlp):
    class Boom(SimEditorDriver):
        def send_char(self, c, dwell=0.0):
            raise RuntimeError("Target closed")
    e, _ = make(shared_nlp, EnableRichText=1, **OFF)
    e.driver = Boom("hello world")
    with pytest.raises(RuntimeError):
        e.trigger_typing()
    assert e.is_running is False


def test_newlines_use_same_keys_in_semantic_path(shared_nlp):
    e, d = make(shared_nlp, **OFF)
    e.is_running = True
    e._type_plain_text("a b\nc d", {})
    assert ("key", "Shift+Enter") in [(k, a) for k, a, _ in d.log]
    assert ("char", "\n") not in [(k, a) for k, a, _ in d.log]


def rich(text):
    return RichTextFormatter("win").parse(text)


def keys(text):
    return [a.shortcut for a in rich(text) if isinstance(a, KeyAction)]


def test_rich_keeps_blank_lines(shared_nlp):
    e, d = make(shared_nlp, EnableRichText=1, **OFF)
    e.is_running = True
    e._execute_actions(rich("a\n\nb"), {})
    assert d.text == "a\n\nb"


@pytest.mark.parametrize("t", ["use my_var_name here", "5 * 3 * 2 = 30", "(a*b)+(c*d)", "file__init__.py", "2024. The year began", "-5 degrees"])
def test_rich_leaves_ordinary_text_alone(t):
    assert keys(t) == []
    assert "".join(a.text for a in rich(t)) == t


def test_rich_still_formats_real_markdown():
    assert keys("a **b** and *c* and _d_") == ["Control+b", "Control+b", "Control+i", "Control+i", "Control+i", "Control+i"]
    assert keys("1. x") == ["Control+Shift+7"]


def test_nested_list_depth_returns_with_shift_tab():
    assert keys("- a\n  - b\n  - c\n- d") == ["Control+Shift+8", "Enter", "Tab", "Enter", "Enter", "Shift+Tab"]


def test_heading_uses_hard_enter_around_it():
    ks = keys("Intro\n# Title\nBody")
    assert ks == ["Enter", "Control+Alt+1", "Enter"]
