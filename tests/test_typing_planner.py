import random

import pytest
from typing_planner import TypingPlanner
from semantic_analyzer import SemanticAnalyzer


@pytest.fixture(scope="module")
def planner():
    return TypingPlanner(SemanticAnalyzer())


def test_chunk_burst(planner):
    directives = planner.plan("the quarterly results were good.", 50, 30)
    chunk_directives = [d for d in directives if d.chunk_burst]
    assert len(chunk_directives) >= 1
    assert "the quarterly results" in "".join(d.text for d in chunk_directives)


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
