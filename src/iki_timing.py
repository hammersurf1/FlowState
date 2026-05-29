"""Shared inter-key interval (IKI) sampling for engine and settings preview."""

from __future__ import annotations

import random


def sample_inter_key_delay_ms(calc_mean: float, variance: float) -> float:
    """Sample an inter-key interval with enough spread to avoid uniform rhythm detectors."""
    mean = max(10.0, float(calc_mean))
    std = max(8.0, float(variance))
    delay = random.gauss(mean, std)
    if random.random() < 0.14:
        delay = max(delay, random.gauss(mean * 1.2, std * 1.35))
    delay *= random.uniform(0.80, 1.22)
    if random.random() < 0.03:
        delay += random.uniform(70, 420)
    cap = max(380.0, mean * 2.8)
    return max(8.0, min(delay, cap))
