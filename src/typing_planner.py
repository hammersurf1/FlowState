"""
FlowState — TypingPlanner
Converts TokenMeta stream into directives that the TypingEngine executes.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

from semantic_analyzer import SemanticAnalyzer, TokenMeta

_REVISION_POS = ("NOUN", "VERB", "ADJ", "ADV")
RevisionSpan = Tuple[int, int, str]  # (start, end, wrong_word)


@dataclass(frozen=True)
class TypingDirective:
    """A single unit of work for the typing loop."""
    text: str                     # Characters to emit
    base_delay_ms: float          # Starting point (e.g. UserMeanDelay)
    delay_multiplier: float = 1.0 # Applied on top of base
    momentum_boost: bool = True     # Whether momentum reduces delay for this directive
    typo_chance: int = 0          # Override typo chance (0 = use global)
    typo_chance_adjustment: int = 0  # Rank-based adjustment (negative = fewer typos)
    revision_candidate: Optional[str] = None  # Similar word to type-then-replace
    revision_span: Optional[RevisionSpan] = None  # In-chunk word revision
    pause_after_ms: int = 0       # Extra pause after this directive finishes
    is_entity: bool = False
    chunk_burst: bool = False     # True if part of a noun chunk


class TypingPlanner:
    """Plans typing directives from TokenMeta."""

    def __init__(self, analyzer: SemanticAnalyzer):
        self.analyzer = analyzer

    def plan(self, text: str, mean_delay: int, variance: int) -> List[TypingDirective]:
        """Return directives for the engine."""
        metas = self.analyzer.analyze(text)
        directives: List[TypingDirective] = []

        i = 0
        while i < len(metas):
            meta = metas[i]

            if meta.in_noun_chunk and not meta.chunk_end:
                chunk_text = ""
                chunk_metas: List[TokenMeta] = []
                j = i
                while j < len(metas) and metas[j].in_noun_chunk:
                    chunk_text += metas[j].text
                    chunk_metas.append(metas[j])
                    if metas[j].chunk_end:
                        break
                    j += 1

                max_rank = max(m.rank for m in chunk_metas)
                is_ent = any(m.is_entity for m in chunk_metas)
                any_clause = any(m.clause_boundary for m in chunk_metas)

                directives.append(TypingDirective(
                    text=chunk_text,
                    base_delay_ms=mean_delay,
                    delay_multiplier=self._rank_multiplier(max_rank),
                    momentum_boost=True,
                    typo_chance=0,
                    typo_chance_adjustment=self._typo_adjustment(max_rank),
                    revision_candidate=None,
                    revision_span=self._pick_chunk_revision(chunk_text, chunk_metas),
                    pause_after_ms=self._clause_pause_ms(any_clause),
                    is_entity=is_ent,
                    chunk_burst=True,
                ))
                i = j + 1
                continue

            rev_cand = self._pick_revision(meta)

            directives.append(TypingDirective(
                text=meta.text,
                base_delay_ms=mean_delay,
                delay_multiplier=self._rank_multiplier(meta.rank),
                momentum_boost=not meta.is_entity,
                typo_chance=self._entity_typo_override(meta.is_entity),
                typo_chance_adjustment=self._typo_adjustment(meta.rank),
                revision_candidate=rev_cand,
                revision_span=None,
                pause_after_ms=self._clause_pause_ms(meta.clause_boundary),
                is_entity=meta.is_entity,
                chunk_burst=False,
            ))
            i += 1

        return directives

    def _is_revision_eligible(self, meta: TokenMeta) -> bool:
        if meta.is_entity:
            return False
        if meta.pos not in _REVISION_POS:
            return False
        return meta.text.strip().isalpha()

    def _pick_revision_word(self, meta: TokenMeta) -> Optional[str]:
        word = meta.text.strip()
        cands = self.analyzer.synonym_candidates(word, meta.pos, max_results=5)
        return random.choice(cands) if cands else None

    def _pick_revision(self, meta: TokenMeta) -> Optional[str]:
        if not self._is_revision_eligible(meta):
            return None
        return self._pick_revision_word(meta)

    def _pick_chunk_revision(self, chunk_text: str, chunk_metas: List[TokenMeta]) -> Optional[RevisionSpan]:
        eligible = [m for m in chunk_metas if self._is_revision_eligible(m)]
        if not eligible:
            return None

        meta = random.choice(eligible)
        wrong = self._pick_revision_word(meta)
        if not wrong:
            return None

        offset = 0
        for m in chunk_metas:
            token_text = m.text
            if m is meta:
                ws_prefix = len(token_text) - len(token_text.lstrip())
                word = token_text.strip()
                start = offset + ws_prefix
                end = start + len(word)
                return (start, end, wrong)
            offset += len(token_text)

        return None

    @staticmethod
    def _rank_multiplier(rank: int) -> float:
        if rank < 500:
            return 0.85
        if rank < 2000:
            return 0.95
        if rank < 6000:
            return 1.05
        if rank < 12000:
            return 1.25
        return 1.45

    @staticmethod
    def _clause_pause_ms(is_boundary: bool) -> int:
        return random.randint(250, 550) if is_boundary else 0

    @staticmethod
    def _entity_typo_override(is_entity: bool) -> int:
        return -1 if is_entity else 0

    @staticmethod
    def _typo_adjustment(rank: int) -> int:
        familiarity = max(0.0, min(1.0, 1.0 - (rank / 15000)))
        return -int(familiarity * 3)
