"""
FlowState — SemanticAnalyzer
Produces per-token and per-chunk metadata using spaCy.
Synonyms are found via WordNet (NLTK), with filtered vector fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Set

import numpy as np
import spacy


_POS_TO_WORDNET = {
    "NOUN": "n",
    "VERB": "v",
    "ADJ": "a",
    "ADV": "r",
}


@dataclass(frozen=True)
class TokenMeta:
    """Per-token typing metadata."""
    text: str                     # Original surface text (includes trailing space if token.has_space)
    pos: str                      # Universal POS tag
    dep: str                      # Dependency relation
    head_idx: int                 # Index of syntactic head
    is_entity: bool               # Inside a named entity span
    entity_label: Optional[str]   # e.g. 'PERSON', 'ORG', None
    rank: int                     # Lexeme frequency rank (lower = more common); fallback 10_000
    in_noun_chunk: bool           # Part of a doc.noun_chunks span
    chunk_end: bool               # True if this token is the last token of its noun chunk
    clause_boundary: bool         # True if token ends a subordinate clause


class SemanticAnalyzer:
    """Wraps spaCy to annotate text for humanized typing."""

    _CLAUSE_CLOSERS = {
        "advcl", "relcl", "ccomp", "xcomp", "acl", "acomp",
    }

    def __init__(self, model_name: str = "en_core_web_md"):
        try:
            self.nlp = spacy.load(model_name)
        except OSError as exc:
            raise RuntimeError(
                f"spaCy model '{model_name}' not found. "
                f"Run: python -m spacy download {model_name}"
            ) from exc

        self._synonym_cache: dict[tuple[str, str], list[str]] = {}
        self._wordnet_ready = False

    def _ensure_wordnet(self) -> bool:
        if self._wordnet_ready:
            return True
        try:
            import nltk
            from nltk.corpus import wordnet as wn  # noqa: F401
            nltk.data.find("corpora/wordnet")
        except LookupError:
            try:
                import nltk
                nltk.download("wordnet", quiet=True)
                nltk.download("omw-1.4", quiet=True)
            except Exception:
                return False
        except ImportError:
            return False
        self._wordnet_ready = True
        return True

    def analyze(self, text: str) -> List[TokenMeta]:
        """Parse *text* and return a list of TokenMeta, one per spaCy token."""
        doc = self.nlp(text)

        chunk_tokens: Set[int] = set()
        chunk_end_tokens: Set[int] = set()
        for chunk in doc.noun_chunks:
            for idx in range(chunk.start, chunk.end):
                chunk_tokens.add(idx)
            chunk_end_tokens.add(chunk.end - 1)

        entity_tokens: dict[int, str] = {}
        for ent in doc.ents:
            for idx in range(ent.start, ent.end):
                entity_tokens[idx] = ent.label_

        metas: List[TokenMeta] = []
        for token in doc:
            is_clause_boundary = token.dep_ in self._CLAUSE_CLOSERS

            if not is_clause_boundary and token.head.dep_ in self._CLAUSE_CLOSERS:
                subtree = list(token.head.subtree)
                if subtree and token.i == subtree[-1].i:
                    is_clause_boundary = True

            metas.append(TokenMeta(
                text=token.text_with_ws,
                pos=token.pos_,
                dep=token.dep_,
                head_idx=token.head.i,
                is_entity=token.i in entity_tokens,
                entity_label=entity_tokens.get(token.i),
                rank=token.rank if hasattr(token, "rank") else 10_000,
                in_noun_chunk=token.i in chunk_tokens,
                chunk_end=token.i in chunk_end_tokens,
                clause_boundary=is_clause_boundary,
            ))

        return metas

    @staticmethod
    def _match_case(source: str, candidate: str) -> str:
        if source.istitle():
            return candidate.title()
        if source.isupper():
            return candidate.upper()
        return candidate.lower()

    @staticmethod
    def _is_valid_candidate(source: str, word: str) -> bool:
        if word.lower() == source.lower():
            return False
        if not word.isascii() or not word.isalpha():
            return False
        if " " in word:
            return False
        src_len = len(source)
        if len(word) < 3 or len(word) > 14:
            return False
        if abs(len(word) - src_len) > 3:
            return False
        if word != word.lower() and word != word.title() and word != word.upper():
            return False
        return True

    def _pos_matches(self, word: str, expected_pos: str) -> bool:
        doc = self.nlp(word)
        if not doc:
            return False
        actual = doc[0].pos_
        if actual == expected_pos:
            return True
        if expected_pos == "ADJ" and actual in ("ADJ", "NOUN"):
            return True
        return False

    def _wordnet_candidates(self, token_text: str, pos: str, max_results: int) -> List[str]:
        if not self._ensure_wordnet():
            return []

        from nltk.corpus import wordnet as wn

        wn_pos = _POS_TO_WORDNET.get(pos)
        if not wn_pos:
            return []

        seen: set[str] = set()
        candidates: list[str] = []

        synsets = wn.synsets(token_text.lower(), pos=wn_pos)
        if not synsets and pos == "ADJ":
            synsets = wn.synsets(token_text.lower(), pos="s")

        for synset in synsets:
            for lemma in synset.lemmas():
                raw = lemma.name().replace("_", " ")
                if not self._is_valid_candidate(token_text, raw):
                    continue
                key = raw.lower()
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(self._match_case(token_text, raw))
                if len(candidates) >= max_results:
                    return candidates

        return candidates

    def _vector_candidates(self, token_text: str, pos: str, max_results: int) -> List[str]:
        lexeme = self.nlp.vocab[token_text.lower()]
        if not lexeme.has_vector:
            return []

        try:
            keys, _, _ = self.nlp.vocab.vectors.most_similar(
                np.asarray([lexeme.vector]), n=max_results + 20
            )
        except Exception:
            return []

        candidates: list[str] = []
        for key in keys[0]:
            word = self.nlp.vocab.strings[key]
            if not self._is_valid_candidate(token_text, word):
                continue
            if not self._pos_matches(word, pos):
                continue
            candidates.append(self._match_case(token_text, word))
            if len(candidates) >= max_results:
                break

        return candidates

    def synonym_candidates(self, token_text: str, pos: str, max_results: int = 5) -> List[str]:
        """Return plausible synonym substitutes for smart revisions."""
        cache_key = (token_text.lower(), pos)
        if cache_key in self._synonym_cache:
            return [self._match_case(token_text, c) for c in self._synonym_cache[cache_key]]

        raw_candidates = self._wordnet_candidates(token_text, pos, max_results)
        if not raw_candidates:
            raw_candidates = self._vector_candidates(token_text, pos, max_results)

        # Store lowercase forms; apply surface capitalization on read.
        stored = [c.lower() for c in raw_candidates]
        self._synonym_cache[cache_key] = stored
        return [self._match_case(token_text, c) for c in stored]
