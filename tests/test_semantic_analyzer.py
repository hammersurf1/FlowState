import pytest
from semantic_analyzer import SemanticAnalyzer


@pytest.fixture(scope="module")
def analyzer():
    return SemanticAnalyzer()


def test_analyze_tokens(analyzer):
    metas = analyzer.analyze("Alice works at Google in New York.")
    texts = [m.text.strip() for m in metas]
    assert texts == ["Alice", "works", "at", "Google", "in", "New", "York", "."]

    # Named entities
    assert metas[0].is_entity and metas[0].entity_label == "PERSON"
    assert metas[3].is_entity and metas[3].entity_label == "ORG"

    # Noun chunk membership
    assert metas[0].in_noun_chunk is True   # "Alice"
    assert metas[0].chunk_end is True
    assert metas[3].in_noun_chunk is True   # "Google"

    # POS
    assert metas[1].pos == "VERB"
    assert metas[3].pos == "PROPN"


def test_synonym_candidates(analyzer):
    syns = analyzer.synonym_candidates("run", "VERB")
    assert len(syns) > 0
