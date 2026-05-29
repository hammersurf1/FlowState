"""Inter-key interval spread — guards against overly uniform rhythm."""

import random
import statistics
from unittest.mock import MagicMock

from engine import TypingEngine


def _engine():
    return TypingEngine(MagicMock())


def _simulate_iki_delays(engine, *, n=4000, mean=115, variance=55):
    random.seed(0)
    engine.current_momentum = 0
    delays = []
    for _ in range(n):
        engine._advance_momentum(True)
        calc_mean = mean - engine.current_momentum
        if random.random() < 0.28:
            calc_mean -= 10
        delays.append(engine._sample_inter_key_delay_ms(calc_mean, variance))
    return delays


def test_inter_key_delay_has_sufficient_spread():
    engine = _engine()
    delays = _simulate_iki_delays(engine)
    cv = statistics.pstdev(delays) / statistics.mean(delays)
    assert cv >= 0.22, f"CV too low for natural rhythm: {cv:.3f}"
    assert max(delays) - min(delays) >= 200, "IKI range too narrow"
    assert sum(1 for d in delays if d >= 300) >= 20, "missing occasional slow keys"


def test_chunk_burst_uses_full_base_variance():
    engine = _engine()
    engine.settings["UserVariance"] = 50
    engine.settings["EnableChunkBurst"] = 1
    from typing_planner import TypingDirective

    burst = TypingDirective(text="chunk", base_delay_ms=50, chunk_burst=True)
    plain = TypingDirective(text="word", base_delay_ms=50, chunk_burst=False)
    _, burst_var, _ = engine._directive_timing(burst)
    _, plain_var, _ = engine._directive_timing(plain)
    assert burst_var == plain_var == 50


def test_chunk_burst_simulated_spread():
    """Chunk path should produce wider IKI spread than a flat mean with halved variance."""
    from typing_planner import TypingDirective

    engine = _engine()
    engine.settings["UserMeanDelay"] = 115
    engine.settings["UserVariance"] = 55
    engine.settings["EnableSemanticSpeed"] = 1
    engine.settings["EnableChunkBurst"] = 1
    engine.settings["EnableFingerPenalty"] = 0

    jitter = (0.9, 1.0, 1.1, 0.95, 1.05, 0.88, 1.15, 1.02, 0.92, 1.08)
    ranks = (0.85, 0.85, 0.85, 0.95, 0.95, 0.95, 1.05, 1.05, 1.05, 1.05)
    directive = TypingDirective(
        text="the big cat",
        base_delay_ms=115,
        chunk_burst=True,
        chunk_char_jitter=jitter,
        chunk_char_rank_mult=ranks,
        momentum_boost=True,
    )
    mean, variance, _ = engine._directive_timing(directive)

    random.seed(1)
    engine.current_momentum = 0
    delays = []
    for idx in range(len(directive.text)):
        char = directive.text[idx]
        engine._advance_chunk_momentum(char)
        calc_mean = engine._char_typing_mean(directive, mean, idx, 0) - engine.current_momentum
        var = engine._chunk_burst_variance(variance)
        delays.append(engine._sample_inter_key_delay_ms(calc_mean, var))

    cv = statistics.pstdev(delays) / statistics.mean(delays)
    assert cv >= 0.20
    assert len(set(round(d) for d in delays)) >= 6
