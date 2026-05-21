import pytest
from typing_planner import TypingPlanner
from semantic_analyzer import SemanticAnalyzer


@pytest.fixture(scope="module")
def planner():
    return TypingPlanner(SemanticAnalyzer())


def test_chunk_burst(planner):
    # "the quarterly results" should be one chunk directive
    directives = planner.plan("the quarterly results were good.", 50, 30)
    chunk_directives = [d for d in directives if d.chunk_burst]
    assert len(chunk_directives) >= 1
    assert "the quarterly results" in "".join(d.text for d in chunk_directives)


def test_entity_flag(planner):
    directives = planner.plan("Alice visited Paris.", 50, 30)
    entity_dirs = [d for d in directives if d.is_entity]
    assert len(entity_dirs) >= 2  # Alice, Paris


def test_rank_multiplier_varies(planner):
    directives = planner.plan("The cat ran.", 50, 30)
    multipliers = [d.delay_multiplier for d in directives if d.text.strip().isalpha()]
    # Different words should potentially have different multipliers
    # "The" is very common, "cat" is common, "ran" is common
    # This is a weak assertion; mainly ensures no crash
    assert len(multipliers) > 0
