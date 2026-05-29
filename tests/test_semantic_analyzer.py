import pytest
from semantic_analyzer import SemanticAnalyzer


@pytest.fixture(scope="module")
def analyzer():
    return SemanticAnalyzer()


def test_analyze_tokens(analyzer):
    metas, doc = analyzer.analyze("Alice works at Google in New York.")
    texts = [m.text.strip() for m in metas]
    assert texts == ["Alice", "works", "at", "Google", "in", "New", "York", "."]

    assert metas[0].is_entity and metas[0].entity_label == "PERSON"
    assert metas[3].is_entity and metas[3].entity_label == "ORG"

    assert metas[0].in_noun_chunk is True
    assert metas[0].chunk_end is True
    assert metas[3].in_noun_chunk is True

    assert metas[1].pos == "VERB"
    assert metas[3].pos == "PROPN"
    assert metas[0].idx == 0
    assert len(doc) == len(metas)


def test_synonym_candidates_verb(analyzer):
    syns = analyzer.synonym_candidates("run", "VERB")
    assert len(syns) > 0
    assert all(s.isascii() and s.isalpha() for s in syns)
    assert all(s.lower() != "run" for s in syns)


def test_synonym_candidates_essay_words(analyzer):
    for word, pos in [
        ("important", "ADJ"),
        ("demonstrate", "VERB"),
        ("government", "NOUN"),
        ("significant", "ADJ"),
    ]:
        syns = analyzer.synonym_candidates(word, pos)
        assert syns, f"expected synonyms for {word}"
        for syn in syns:
            assert syn.isascii(), f"non-ascii synonym {syn!r} for {word}"
            assert syn.isalpha(), f"non-alpha synonym {syn!r} for {word}"
            assert syn.lower() != word.lower()


def test_synonym_capitalization(analyzer):
    syns = analyzer.synonym_candidates("Important", "ADJ")
    assert syns
    assert all(s[0].isupper() for s in syns)


def test_contextual_explore_rejects_search(analyzer):
    text = (
        "In Andy Weir's novel, Weir uses the friendship to explore "
        "how friendship can lead to growth and challenges."
    )
    _, doc = analyzer.analyze(text)
    explore_idx = next(i for i, t in enumerate(doc) if t.text.lower() == "explore")
    syns = analyzer.contextual_synonym_candidates(doc, explore_idx)
    assert "search" not in [s.lower() for s in syns]


def test_contextual_important_accepts_near_synonym(analyzer):
    text = "The government must implement important reforms for society."
    _, doc = analyzer.analyze(text)
    important_idx = next(i for i, t in enumerate(doc) if t.text.lower() == "important")
    syns = analyzer.contextual_synonym_candidates(doc, important_idx)
    assert syns
    assert any(s.lower() in {"significant", "crucial", "vital", "essential"} for s in syns)


def test_contextual_fit_scores_sorted(analyzer):
    text = "The government must implement important reforms for society."
    _, doc = analyzer.analyze(text)
    important_idx = next(i for i, t in enumerate(doc) if t.text.lower() == "important")
    syns = analyzer.contextual_synonym_candidates(doc, important_idx)
    assert syns

    fits = [
        analyzer._contextual_fit(doc, important_idx, syn)
        for syn in syns
    ]
    assert fits == sorted(fits, reverse=True)
