import random

import pytest
from typing_planner import TypingPlanner, CompositionSettings
from semantic_analyzer import SemanticAnalyzer


@pytest.fixture(scope="module")
def planner():
    return TypingPlanner(SemanticAnalyzer())


def test_chunk_burst(planner):
    directives = planner.plan("the quarterly results were good.", 50, 30)
    chunk_directives = [d for d in directives if d.chunk_burst]
    assert len(chunk_directives) >= 1
    assert "the quarterly results" in "".join(d.text for d in chunk_directives)


def test_chunk_burst_per_char_profiles_vary(planner):
    directives = planner.plan("the quarterly results were good.", 110, 45)
    chunk = next(d for d in directives if d.chunk_burst)
    assert chunk.chunk_char_jitter is not None
    assert chunk.chunk_char_rank_mult is not None
    assert len(chunk.chunk_char_jitter) == len(chunk.text)
    assert len(chunk.chunk_char_rank_mult) == len(chunk.text)
    assert len(set(chunk.chunk_char_jitter)) > 1
    assert min(chunk.chunk_char_jitter) < max(chunk.chunk_char_jitter)


def test_entity_flag(planner):
    directives = planner.plan("Alice visited Paris.", 50, 30)
    entity_dirs = [d for d in directives if d.is_entity]
    assert len(entity_dirs) >= 2


def test_rank_multiplier_varies(planner):
    directives = planner.plan("The cat ran.", 50, 30)
    multipliers = [d.delay_multiplier for d in directives if d.text.strip().isalpha()]
    assert len(multipliers) > 0


def test_chunk_revision_span(planner):
    random.seed(0)
    directives = planner.plan("the quarterly results were good.", 50, 30)
    chunk = next(d for d in directives if d.chunk_burst)
    if chunk.revision_span:
        start, end, wrong = chunk.revision_span
        assert 0 <= start < end <= len(chunk.text)
        assert chunk.text[start:end].isalpha()
        assert wrong.isalpha()
        assert wrong.lower() != chunk.text[start:end].lower()


def test_revision_candidates_without_double_gate(planner):
    random.seed(42)
    essay = (
        "The government must demonstrate that significant reforms will benefit society."
    )
    directives = planner.plan(essay, 110, 45)
    with_candidates = [d for d in directives if d.revision_candidate or d.revision_span]
    assert len(with_candidates) >= 1


def _composition_settings(**overrides):
    defaults = dict(
        enabled=True,
        sensitivity=50,
        pause_min_ms=300,
        pause_max_ms=6000,
        paragraph_planning_min_ms=2000,
        paragraph_planning_max_ms=8000,
    )
    defaults.update(overrides)
    return CompositionSettings(**defaults)


def test_composition_disabled_has_no_pre_pauses(planner):
    text = "First line.\n\nHowever, the second paragraph uses reforms."
    directives = planner.plan(text, 50, 30, composition=CompositionSettings())
    assert all(d.pause_before_ms == 0 for d in directives)


def test_composition_paragraph_start_pause(planner):
    text = "Opening paragraph here.\n\nHowever, another begins."
    comp = _composition_settings()
    directives = planner.plan(text, 50, 30, composition=comp)
    however = next(d for d in directives if d.text.strip().lower().startswith("however"))
    assert however.pause_before_ms >= comp.paragraph_planning_min_ms


def test_composition_hard_word_pause(planner):
    text = "The government must implement significant reforms."
    comp = _composition_settings()
    directives = planner.plan(text, 50, 30, composition=comp)
    reforms = next(d for d in directives if "reforms" in d.text)
    assert reforms.pause_before_ms >= comp.pause_min_ms
    assert reforms.composition_score > 0


def test_composition_deterministic(planner):
    text = "First.\n\nHowever, implement the reforms."
    comp = _composition_settings()
    first = planner.plan(text, 50, 30, composition=comp)
    second = planner.plan(text, 50, 30, composition=comp)
    assert [d.pause_before_ms for d in first] == [d.pause_before_ms for d in second]
    assert [d.pause_after_ms for d in first] == [d.pause_after_ms for d in second]


def test_composition_skips_blank_line_gap(planner):
    text = "First paragraph here.\n\n\nSecond paragraph starts."
    comp = _composition_settings(sensitivity=100)
    directives = planner.plan(text, 50, 30, composition=comp)
    newline_dirs = [d for d in directives if "\n" in d.text and not d.text.strip().isalpha()]
    assert all(d.pause_before_ms == 0 and d.pause_after_ms == 0 for d in newline_dirs)
    planning = [d for d in directives if d.pause_before_ms >= comp.paragraph_planning_min_ms]
    assert len(planning) == 1
    assert planning[0].text.strip().startswith("Second")


def test_composition_tier_ordering(planner):
    text = "One two three. Four five six.\n\nSeven eight nine."
    comp = _composition_settings(
        pause_min_ms=1000,
        pause_max_ms=10000,
        sensitivity=100,
    )
    directives = planner.plan(text, 50, 30, composition=comp)

    two = next(d for d in directives if d.text.strip() == "two")
    period_pauses = [
        d.pause_after_ms for d in directives
        if d.text.strip() == "." and d.pause_after_ms > 0
    ]

    assert two.pause_before_ms == 0
    assert len(period_pauses) >= 2
    assert period_pauses[0] < period_pauses[-1]


def test_composition_variation(planner):
    text = "Alpha beta gamma. Delta epsilon zeta."
    comp = _composition_settings(pause_min_ms=1000, pause_max_ms=10000, sensitivity=100)
    directives = planner.plan(text, 50, 30, composition=comp)
    ends = [d.pause_after_ms for d in directives if d.pause_after_ms > 0]
    assert len(ends) >= 2
    assert len(set(ends)) > 1


def test_composition_mid_only_on_content(planner):
    text = "The cat sat. The dog ran."
    comp = _composition_settings()
    directives = planner.plan(text, 50, 30, composition=comp)
    sat = next(d for d in directives if d.text.strip() == "sat")
    ran = next(d for d in directives if d.text.strip() == "ran")
    assert sat.pause_before_ms == 0
    assert ran.pause_before_ms == 0


def _essay_composition_settings():
    return CompositionSettings(
        enabled=True,
        sensitivity=65,
        pause_min_ms=1500,
        pause_max_ms=22000,
        paragraph_planning_min_ms=12000,
        paragraph_planning_max_ms=45000,
    )


def _estimate_typing_ms(directives, mean_delay_ms: int) -> int:
    total = 0
    for d in directives:
        total += d.pause_before_ms + d.pause_after_ms
        total += int(len(d.text) * mean_delay_ms * d.delay_multiplier)
    return total


def test_composition_essay_calibration_duration(planner):
    para = (
        "Climate policy requires careful analysis of economic trade-offs, "
        "environmental outcomes, and political feasibility across regions. "
        "Scholars debate whether carbon pricing alone can redirect investment "
        "toward renewable infrastructure without triggering regressive burdens "
        "on households that already face rising energy costs. Empirical studies "
        "often emphasize institutional capacity, administrative transparency, "
        "and the credibility of enforcement mechanisms when projecting long-term "
        "emissions reductions under uncertain technological change. "
    )
    essay = (para * 2 + "\n\n") * 4
    mean_delay = 115
    comp = _essay_composition_settings()
    directives = planner.plan(essay, mean_delay, 55, composition=comp)
    estimated_ms = _estimate_typing_ms(directives, mean_delay)
    assert 30 * 60 * 1000 <= estimated_ms <= 50 * 60 * 1000
