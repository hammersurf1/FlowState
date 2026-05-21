"""
FlowState — TypingPlanner
Converts TokenMeta stream into directives that the TypingEngine executes.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional

from semantic_analyzer import SemanticAnalyzer, TokenMeta


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

            # --- Chunk-level burst detection ---
            # If a token is inside a noun chunk and not the last, we coalesce
            # the entire chunk into one directive so the engine types it as
            # a continuous burst.
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

                # Use the most "difficult" token in the chunk to set speed
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
                    pause_after_ms=self._clause_pause_ms(any_clause),
                    is_entity=is_ent,
                    chunk_burst=True,
                ))
                i = j + 1
                continue

            # --- Single-token directive ---
            # Revision candidate: only on content words at sentence/word boundaries
            rev_cand = self._pick_revision(meta)

            directives.append(TypingDirective(
                text=meta.text,
                base_delay_ms=mean_delay,
                delay_multiplier=self._rank_multiplier(meta.rank),
                momentum_boost=not meta.is_entity,
                typo_chance=self._entity_typo_override(meta.is_entity),
                typo_chance_adjustment=self._typo_adjustment(meta.rank),
                revision_candidate=rev_cand,
                pause_after_ms=self._clause_pause_ms(meta.clause_boundary),
                is_entity=meta.is_entity,
                chunk_burst=False,
            ))
            i += 1

        return directives

    # --- Internal helpers ---

    @staticmethod
    def _rank_multiplier(rank: int) -> float:
        """Map spaCy token rank to a speed multiplier.

        Rank is roughly logarithmic in corpus frequency. Lower rank = common word.
        We compress the dynamic range so the effect is subtle, not robotic.
        """
        if rank < 500:
            return 0.85          # Very common → faster
        if rank < 2000:
            return 0.95
        if rank < 6000:
            return 1.05
        if rank < 12000:
            return 1.25          # Uncommon → slower / more careful
        return 1.45              # Rare → deliberate

    @staticmethod
    def _clause_pause_ms(is_boundary: bool) -> int:
        return random.randint(250, 550) if is_boundary else 0

    @staticmethod
    def _entity_typo_override(is_entity: bool) -> int:
        """Return an *override* typo chance for entities (lower = more careful).
        0 means 'use the global TypoChance setting'.
        """
        return -1 if is_entity else 0   # -1 signals 'suppress typos entirely'

    @staticmethod
    def _typo_adjustment(rank: int) -> int:
        """Map spaCy token rank to a typo-chance adjustment.

        Very common words (low rank) get a negative adjustment → fewer typos.
        Rare words (high rank) get 0 → no change.
        """
        familiarity = max(0.0, min(1.0, 1.0 - (rank / 15000)))
        return -int(familiarity * 3)

    def _pick_revision(self, meta: TokenMeta) -> Optional[str]:
        """Stochastically choose a similar word to type-then-replace."""
        if meta.pos not in ("NOUN", "VERB", "ADJ"):
            return None
        # Only offer revision at word-start tokens (no in-word suffixes)
        if not meta.text.strip().isalpha():
            return None
        # 10 % base revision probability per eligible token
        if random.random() > 0.10:
            return None
        cands = self.analyzer.synonym_candidates(meta.text.strip(), meta.pos, max_results=3)
        return random.choice(cands) if cands else None
