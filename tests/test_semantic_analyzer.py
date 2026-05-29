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


def test_paragraph_start_detection(analyzer):
    text = "First paragraph ends here.\n\nHowever, the second begins."
    metas, _ = analyzer.analyze(text)
    however = next(m for m in metas if m.text.strip().lower().startswith("however"))
    assert however.paragraph_start is True
    assert however.sentence_start is True
    assert however.is_discourse_marker is True


def test_blank_lines_are_not_paragraphs(analyzer):
    text = "First paragraph here.\n\n\nSecond paragraph starts."
    metas, _ = analyzer.analyze(text)
    newline_directives = [m for m in metas if "\n" in m.text and not m.text.strip().isalpha()]
    for meta in newline_directives:
        assert not meta.paragraph_start, repr(meta.text)
        assert not meta.paragraph_end, repr(meta.text)
    second = next(m for m in metas if m.text.strip().startswith("Second"))
    assert second.paragraph_start is True
    first_period = next(m for m in metas if m.paragraph_end and m.text.strip() == ".")
    assert first_period.paragraph_end is True


def test_sentence_and_paragraph_end_flags(analyzer):
    text = "First sentence ends. Second ends paragraph.\n\nNew paragraph starts."
    metas, _ = analyzer.analyze(text)
    mid_sentence_end = next(m for m in metas if m.sentence_end and not m.paragraph_end)
    assert mid_sentence_end.sentence_end is True
    assert mid_sentence_end.paragraph_end is False
    para_end = next(m for m in metas if m.paragraph_end and m.text.strip() == ".")
    assert para_end.paragraph_end is True


def test_hard_word_flag(analyzer):
    metas, _ = analyzer.analyze("The government must implement significant reforms.")
    reforms = next(m for m in metas if m.text.strip() == "reforms")
    assert reforms.is_hard_word is True
    the = next(m for m in metas if m.text.strip() == "The")
    assert the.is_hard_word is False


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
