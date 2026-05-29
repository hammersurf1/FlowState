import pytest
from engine import TypingEngine
from pathlib import Path
from unittest.mock import patch


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


@pytest.fixture
def engine():
    driver = MockDriver()
    eng = TypingEngine(driver)
    eng.settings["UserMeanDelay"] = 1
    eng.settings["UserVariance"] = 1
    eng.settings["TypoChance"] = 0
    eng.settings["RevisionChance"] = 0
    eng.settings["SentencePauseMs"] = 1
    eng.settings["ParagraphPauseMs"] = 1
    eng.settings["EnableSemanticSpeed"] = 1
    eng.settings["EnableClausePauses"] = 0
    eng.settings["EnableChunkBurst"] = 0
    eng.settings["EnableSmartRevisions"] = 0
    eng.settings["EnableEntityCare"] = 0
    eng.settings["EnableBrainstormPauses"] = 0
    eng.settings["EnableCompositionPauses"] = 1
    eng.settings["CompositionPauseMinMs"] = 100
    eng.settings["CompositionPauseMaxMs"] = 5000
    eng.settings["ParagraphPlanningMinMs"] = 500
    eng.settings["ParagraphPlanningMaxMs"] = 2000
    eng.settings["CompositionSensitivity"] = 50
    return eng


def test_engine_applies_composition_pre_pause(engine):
    sleeps = []
    engine._sleep = lambda duration: sleeps.append(duration)

    engine.is_running = True
    text = "Intro.\n\nHowever, implement the reforms."
    engine._type_plain_text(text, {})

    assert any(s >= 0.5 for s in sleeps), "expected paragraph/composition pause >= 500ms"
    assert len(engine.driver.log) > 0


def test_composition_off_matches_no_pre_pause(engine):
    engine.settings["EnableCompositionPauses"] = 0
    engine.settings["EnableSemanticSpeed"] = 1
    sleeps = []
    engine._sleep = lambda duration: sleeps.append(duration)

    engine.is_running = True
    engine._type_plain_text("Hello world.", {})

    assert all(s < 0.5 for s in sleeps)


_LEGACY_INI = """[Settings]
usermeandelay = 40
uservariance = 45
typochance = 3
typodelay = 125
revisionchance = 5

[Advanced]
sentencepausems = 1200
paragraphpausems = 2000
brainstormfrequency = 60
emojipausems = 1800

[Behavior]
useenteronly = 0
enabletypos = 1
enablerevisions = 1
enablebrainstormpauses = 1
enablerichtext = 1
enablesemanticspeed = 1
enableclausepauses = 1
enablechunkburst = 1
enablesmartrevisions = 1
enableentitycare = 1
enablefingerpenalty = 1
enablefluencystates = 1
enablenumbersymbolcare = 1
enablecapsrunrealism = 1
enablefrequencytypos = 1
enabledeferredcorrections = 1

[Hotkeys]
triggerhotkey = ctrl+alt+v
pausekey = esc
"""


def test_load_settings_migrates_composition_keys(tmp_path):
    config_dir = tmp_path / ".flowstate"
    config_dir.mkdir()
    ini = config_dir / "settings.ini"
    ini.write_text(_LEGACY_INI, encoding="utf-8")

    with patch.object(Path, "home", return_value=tmp_path):
        eng = TypingEngine(MockDriver())

    saved = ini.read_text(encoding="utf-8").lower()
    assert "enablecompositionpauses" in saved
    assert "compositionpauseminms" in saved
    assert "compositionsensitivity" in saved
    assert eng.settings["EnableCompositionPauses"] == 0
    assert eng.settings["CompositionPauseMinMs"] == 300
