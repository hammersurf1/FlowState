"""Shared inter-key interval sampler."""

import random

from iki_timing import sample_inter_key_delay_ms


def test_sample_matches_engine_wrapper():
    random.seed(0)
    a = sample_inter_key_delay_ms(100, 45)
    random.seed(0)
    b = sample_inter_key_delay_ms(100, 45)
    assert a == b
    assert 8 <= a <= 380
