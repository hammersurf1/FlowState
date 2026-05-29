"""Unit tests for settings GUI helper logic."""

from settings_gui import _is_timing_setting_key


def test_is_timing_setting_key():
    assert _is_timing_setting_key("UserMeanDelay", 35) is True
    assert _is_timing_setting_key("SentencePauseMs", 1200) is True
    assert _is_timing_setting_key("TypoChance", 3) is False
    assert _is_timing_setting_key("EnableTypos", 1) is False
    assert _is_timing_setting_key("UserMeanDelay", "x") is False
