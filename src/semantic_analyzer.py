"""
FlowState — SemanticAnalyzer
Produces per-token and per-chunk metadata using spaCy.
Synonyms are found via vector similarity (en_core_web_md vectors).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Set

import numpy as np
import spacy


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

    # Dependency relations that mark the *closing* token of a subordinate clause
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

        # Cache for vector-similarity synonym lookups
        self._synonym_cache: dict[tuple[str, str], list[str]] = {}

    def analyze(self, text: str) -> List[TokenMeta]:
        """Parse *text* and return a list of TokenMeta, one per spaCy token."""
        doc = self.nlp(text)

        # Pre-compute noun chunk token indices
        chunk_tokens: Set[int] = set()
        chunk_end_tokens: Set[int] = set()
        for chunk in doc.noun_chunks:
            for idx in range(chunk.start, chunk.end):
                chunk_tokens.add(idx)
            chunk_end_tokens.add(chunk.end - 1)

        # Pre-compute entity token indices
        entity_tokens: dict[int, str] = {}
        for ent in doc.ents:
            for idx in range(ent.start, ent.end):
                entity_tokens[idx] = ent.label_

        metas: List[TokenMeta] = []
        for token in doc:
            # Clause boundary heuristic:
            # token is the closing token of a clause if its dependency is in _CLAUSE_CLOSERS
            # OR if it is the last token of a dependency subtree rooted at a clause head.
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

    def synonym_candidates(self, token_text: str, pos: str, max_results: int = 5) -> List[str]:
        """Return semantically similar words from the spaCy vocab vectors.

        Uses en_core_web_md vectors; no external synonym lexicon required.
        """
        cache_key = (token_text.lower(), pos)
        if cache_key in self._synonym_cache:
            return self._synonym_cache[cache_key]

        lexeme = self.nlp.vocab[token_text.lower()]
        if not lexeme.has_vector:
            self._synonym_cache[cache_key] = []
            return []

        # Query most similar vectors in the vocab
        try:
            keys, _, _ = self.nlp.vocab.vectors.most_similar(
                np.asarray([lexeme.vector]), n=max_results + 10
            )
        except Exception:
            self._synonym_cache[cache_key] = []
            return []

        candidates: list[str] = []
        for key in keys[0]:
            word = self.nlp.vocab.strings[key]
            # Filter out identical words, non-alpha, and very short words
            if (
                word.lower() == token_text.lower()
                or not word.isalpha()
                or len(word) < 3
            ):
                continue
            candidates.append(word)
            if len(candidates) >= max_results:
                break

        self._synonym_cache[cache_key] = candidates
        return candidates
