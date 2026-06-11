import random

import pytest
from engine import TypingEngine


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
    eng.settings["UserMeanDelay"] = 5
    eng.settings["UserVariance"] = 2
    eng.settings["EnableSemanticSpeed"] = 1
    eng.settings["EnableClausePauses"] = 1
    eng.settings["EnableChunkBurst"] = 1
    eng.settings["EnableSmartRevisions"] = 1
    eng.settings["EnableEntityCare"] = 1
    eng.settings["TypoChance"] = 0
    eng.settings["EnableFingerPenalty"] = 1
    eng.settings["EnableFluencyStates"] = 1
    eng.settings["EnableNumberSymbolCare"] = 1
    eng.settings["EnableCapsRunRealism"] = 1
    eng.settings["EnableFrequencyTypos"] = 1
    eng.settings["EnableDeferredCorrections"] = 1
    return eng


def test_smart_revision_produces_backspaces(engine):
    random.seed(1)
    engine.settings["RevisionChance"] = 100
    engine.settings["EnableRevisions"] = 0
    engine.is_running = True
    engine._type_plain_text("The results were excellent.", {})
    assert any(entry[0] == "backspace" for entry in engine.driver.log)


def test_semantic_path_runs(engine):
    engine.is_running = True
    engine._type_plain_text(
        "The quarterly results were excellent because Alice worked hard.", {}
    )
    assert len(engine.driver.log) > 10


def test_legacy_path_runs(engine):
    engine.is_running = True
    engine.settings["EnableSemanticSpeed"] = 0
    engine.settings["EnableClausePauses"] = 0
    engine.settings["EnableChunkBurst"] = 0
    engine.settings["EnableSmartRevisions"] = 0
    engine.settings["EnableEntityCare"] = 0
    engine._type_plain_text(
        "The quarterly results were excellent because Alice worked hard.", {}
    )
    assert len(engine.driver.log) > 10
