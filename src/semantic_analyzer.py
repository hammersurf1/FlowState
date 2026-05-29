"""
FlowState — SemanticAnalyzer
Produces per-token and per-chunk metadata using spaCy.
Synonyms are found via WordNet (NLTK), with filtered vector fallback.
Context-aware smart revisions use Lesk WSD plus local vector fit scoring.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple

import numpy as np
import spacy
from spacy.tokens import Doc


_POS_TO_WORDNET = {
    "NOUN": "n",
    "VERB": "v",
    "ADJ": "a",
    "ADV": "r",
}

_CONTEXT_WINDOW = 3
_DEFAULT_MIN_FIT = 0.97
_HARD_WORD_RANK = 6000

_DISCOURSE_MARKERS = frozenset({
    "however", "therefore", "moreover", "although", "because", "furthermore",
    "nevertheless", "meanwhile", "consequently", "thus", "hence", "nonetheless",
    "otherwise", "instead", "similarly", "likewise", "indeed", "finally",
    "firstly", "secondly", "ultimately", "specifically", "particularly",
})


@dataclass(frozen=True)
class TokenMeta:
    """Per-token typing metadata."""
    idx: int                      # spaCy token index in the parsed Doc
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
    sentence_start: bool = False  # First token of a spaCy sentence
    sentence_end: bool = False      # Last token of a spaCy sentence
    paragraph_start: bool = False   # First token after a blank line or start of doc
    paragraph_end: bool = False     # Last content token before a paragraph break or doc end
    is_discourse_marker: bool = False  # Sentence-initial discourse connective
    is_hard_word: bool = False      # Uncommon vocabulary (rank above threshold)


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
        self._context_synonym_cache: dict[tuple[str, str, tuple[str, ...]], list[str]] = {}
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

    def analyze(self, text: str) -> Tuple[List[TokenMeta], Doc]:
        """Parse *text* and return TokenMeta list plus the spaCy Doc."""
        return self._build_metas(self.nlp(text))

    @staticmethod
    def _token_has_content(token) -> bool:
        return not token.is_space and bool(token.text.strip())

    @staticmethod
    def _is_sentence_end_token(token, sentence_ends: Set[int]) -> bool:
        if token.i not in sentence_ends:
            return False
        if SemanticAnalyzer._token_has_content(token):
            stripped = token.text.strip()
            if stripped in ".?!":
                return True
            if any(ch.isalnum() for ch in stripped):
                return True
        return False

    @staticmethod
    def _paragraph_start_indices(doc: Doc) -> Set[int]:
        """Token indices that begin a content paragraph (not blank-line-only gaps)."""
        if not len(doc) or not doc.text.strip():
            return set()

        starts: Set[int] = {0}
        text = doc.text
        for match in re.finditer(r"\n\n+", text):
            before = text[: match.start()]
            after = text[match.end() :]
            if not before.strip() or not after.strip():
                continue
            char_pos = match.end() + (len(after) - len(after.lstrip()))
            for token in doc:
                if token.idx >= char_pos and SemanticAnalyzer._token_has_content(token):
                    starts.add(token.i)
                    break
        return starts

    @staticmethod
    def _last_content_token_before(doc: Doc, token_idx: int) -> int | None:
        for i in range(token_idx - 1, -1, -1):
            if SemanticAnalyzer._token_has_content(doc[i]):
                return i
        return None

    @staticmethod
    def _paragraph_end_indices(doc: Doc, paragraph_starts: Set[int]) -> Set[int]:
        """Token indices that end a content paragraph (last content token before a break)."""
        ends: Set[int] = set()
        for start_idx in sorted(paragraph_starts):
            if start_idx == 0:
                continue
            end_idx = SemanticAnalyzer._last_content_token_before(doc, start_idx)
            if end_idx is not None:
                ends.add(end_idx)
        if len(doc):
            end_idx = SemanticAnalyzer._last_content_token_before(doc, len(doc))
            if end_idx is not None:
                ends.add(end_idx)
        return ends

    def _build_metas(self, doc: Doc) -> Tuple[List[TokenMeta], Doc]:
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

        sentence_starts = {sent.start for sent in doc.sents}
        sentence_ends = {sent.end - 1 for sent in doc.sents}
        paragraph_starts = self._paragraph_start_indices(doc)
        paragraph_ends = self._paragraph_end_indices(doc, paragraph_starts)

        metas: List[TokenMeta] = []
        for token in doc:
            is_clause_boundary = token.dep_ in self._CLAUSE_CLOSERS

            if not is_clause_boundary and token.head.dep_ in self._CLAUSE_CLOSERS:
                subtree = list(token.head.subtree)
                if subtree and token.i == subtree[-1].i:
                    is_clause_boundary = True

            rank = token.rank if hasattr(token, "rank") else 10_000
            lemma = token.text.lower().rstrip(",:;")
            is_sentence_start = token.i in sentence_starts
            is_discourse = (
                is_sentence_start
                and lemma in _DISCOURSE_MARKERS
            )

            metas.append(TokenMeta(
                idx=token.i,
                text=token.text_with_ws,
                pos=token.pos_,
                dep=token.dep_,
                head_idx=token.head.i,
                is_entity=token.i in entity_tokens,
                entity_label=entity_tokens.get(token.i),
                rank=rank,
                in_noun_chunk=token.i in chunk_tokens,
                chunk_end=token.i in chunk_end_tokens,
                clause_boundary=is_clause_boundary,
                sentence_start=is_sentence_start,
                sentence_end=SemanticAnalyzer._is_sentence_end_token(token, sentence_ends),
                paragraph_start=token.i in paragraph_starts,
                paragraph_end=token.i in paragraph_ends,
                is_discourse_marker=is_discourse,
                is_hard_word=(
                    rank > _HARD_WORD_RANK
                    and SemanticAnalyzer._token_has_content(token)
                ),
            ))

        return metas, doc

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

    def _disambiguated_synset(self, token_text: str, pos: str, context_words: List[str]):
        if not self._ensure_wordnet():
            return None

        from nltk.corpus import wordnet as wn
        from nltk.wsd import lesk

        wn_pos = _POS_TO_WORDNET.get(pos)
        if not wn_pos:
            return None

        synset = lesk(context_words, token_text.lower(), pos=wn_pos)
        if synset is None and pos == "ADJ":
            synset = lesk(context_words, token_text.lower(), pos="s")
        if synset is None:
            synsets = wn.synsets(token_text.lower(), pos=wn_pos)
            if not synsets and pos == "ADJ":
                synsets = wn.synsets(token_text.lower(), pos="s")
            synset = synsets[0] if synsets else None
        return synset

    def _wordnet_candidates_from_synset(
        self, token_text: str, synset, max_results: int
    ) -> List[str]:
        seen: set[str] = set()
        candidates: list[str] = []

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
                break

        return candidates

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

    def _context_fingerprint(self, doc: Doc, token_idx: int) -> tuple[str, ...]:
        start = max(0, token_idx - _CONTEXT_WINDOW)
        end = min(len(doc), token_idx + _CONTEXT_WINDOW + 1)
        return tuple(doc[i].lemma_.lower() for i in range(start, end) if doc[i].is_alpha)

    def _token_vector(self, word: str) -> Optional[np.ndarray]:
        lexeme = self.nlp.vocab[word.lower()]
        if not lexeme.has_vector:
            return None
        return lexeme.vector

    def _window_vector(
        self, doc: Doc, token_idx: int, substitute: Optional[str] = None
    ) -> Optional[np.ndarray]:
        start = max(0, token_idx - _CONTEXT_WINDOW)
        end = min(len(doc), token_idx + _CONTEXT_WINDOW + 1)
        vecs: list[np.ndarray] = []
        for i in range(start, end):
            if i == token_idx and substitute is not None:
                vec = self._token_vector(substitute)
            elif doc[i].has_vector:
                vec = doc[i].vector
            else:
                vec = None
            if vec is not None:
                vecs.append(vec)
        if not vecs:
            return None
        return np.mean(vecs, axis=0)

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def _collocation_fit(self, doc: Doc, token_idx: int, substitute: str) -> float:
        token = doc[token_idx]
        prep = doc[token_idx - 1].text if token_idx > 0 and doc[token_idx - 1].is_alpha else ""
        follow = doc[token_idx + 1].text if token_idx + 1 < len(doc) and doc[token_idx + 1].is_alpha else ""
        if not follow:
            return 1.0

        orig_phrase = " ".join(part for part in (prep, token.text, follow) if part)
        sub_phrase = " ".join(
            part for part in (prep, self._match_case(token.text, substitute), follow) if part
        )
        orig_doc = self.nlp(orig_phrase)
        sub_doc = self.nlp(sub_phrase)
        if not orig_doc.has_vector or not sub_doc.has_vector:
            return 1.0
        return self._cosine_similarity(orig_doc.vector, sub_doc.vector)

    def _contextual_fit(self, doc: Doc, token_idx: int, substitute: str) -> float:
        window_fit = self._window_fit(doc, token_idx, substitute)
        if token_idx + 1 < len(doc) and doc[token_idx + 1].is_alpha:
            return min(window_fit, self._collocation_fit(doc, token_idx, substitute))
        return window_fit

    def _window_fit(self, doc: Doc, token_idx: int, substitute: str) -> float:
        orig = self._window_vector(doc, token_idx)
        sub = self._window_vector(doc, token_idx, substitute=substitute)
        if orig is None or sub is None:
            return 0.0
        return self._cosine_similarity(orig, sub)

    def contextual_synonym_candidates(
        self,
        doc: Doc,
        token_idx: int,
        max_results: int = 5,
        min_fit: float = _DEFAULT_MIN_FIT,
    ) -> List[str]:
        """Return contextually valid synonym substitutes for smart revisions."""
        token = doc[token_idx]
        token_text = token.text
        pos = token.pos_

        cache_key = (token_text.lower(), pos, self._context_fingerprint(doc, token_idx))
        if cache_key in self._context_synonym_cache:
            return [self._match_case(token_text, c) for c in self._context_synonym_cache[cache_key]]

        context_words = [t.text for t in doc if t.is_alpha]
        pool_size = max(max_results * 3, 10)

        raw_candidates: list[str] = []
        seen: set[str] = set()

        synset = self._disambiguated_synset(token_text, pos, context_words)
        if synset is not None:
            for cand in self._wordnet_candidates_from_synset(token_text, synset, pool_size):
                key = cand.lower()
                if key not in seen:
                    seen.add(key)
                    raw_candidates.append(cand)

        for cand in self._wordnet_candidates(token_text, pos, pool_size):
            key = cand.lower()
            if key in seen:
                continue
            seen.add(key)
            raw_candidates.append(cand)
            if len(raw_candidates) >= pool_size:
                break

        if not raw_candidates:
            raw_candidates = self._vector_candidates(token_text, pos, pool_size)

        scored: list[tuple[float, str]] = []
        for cand in raw_candidates:
            fit = self._contextual_fit(doc, token_idx, cand)
            if fit >= min_fit:
                scored.append((fit, cand))

        scored.sort(key=lambda item: item[0], reverse=True)
        stored = [c.lower() for _, c in scored[:max_results]]
        self._context_synonym_cache[cache_key] = stored
        return [self._match_case(token_text, c) for c in stored]

    def synonym_ambiguity_score(self, doc: Doc, token_idx: int) -> float:
        """Return 0–1 score: higher when many plausible synonym alternatives exist."""
        token = doc[token_idx]
        if not token.text.strip().isalpha():
            return 0.0
        if token.pos_ not in ("NOUN", "VERB", "ADJ", "ADV"):
            return 0.0

        cands = self.contextual_synonym_candidates(
            doc, token_idx, max_results=5, min_fit=0.95,
        )
        if len(cands) < 2:
            return 0.0

        fits = [self._contextual_fit(doc, token_idx, cand) for cand in cands[:3]]
        if not fits:
            return 0.0

        count_factor = min(len(cands), 5) / 5.0
        spread = max(fits) - min(fits) if len(fits) > 1 else 0.0
        # Many close-fit alternatives imply word-choice hesitation.
        ambiguity = count_factor * (1.0 - min(spread, 0.05) / 0.05)
        return min(1.0, max(0.0, ambiguity))

    def synonym_candidates(self, token_text: str, pos: str, max_results: int = 5) -> List[str]:
        """Return plausible synonym substitutes (word-only, no context)."""
        cache_key = (token_text.lower(), pos)
        if cache_key in self._synonym_cache:
            return [self._match_case(token_text, c) for c in self._synonym_cache[cache_key]]

        raw_candidates = self._wordnet_candidates(token_text, pos, max_results)
        if not raw_candidates:
            raw_candidates = self._vector_candidates(token_text, pos, max_results)

        stored = [c.lower() for c in raw_candidates]
        self._synonym_cache[cache_key] = stored
        return [self._match_case(token_text, c) for c in stored]
