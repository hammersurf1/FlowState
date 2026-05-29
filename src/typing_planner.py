"""
FlowState — TypingPlanner
Converts TokenMeta stream into directives that the TypingEngine executes.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import List, Literal, Optional, Tuple

from semantic_analyzer import SemanticAnalyzer, TokenMeta
from spacy.tokens import Doc

_REVISION_POS = ("NOUN", "VERB", "ADJ", "ADV")
RevisionSpan = Tuple[int, int, str]  # (start, end, wrong_word)
_COMPOSITION_PAUSE_CAP_MS = 30_000

CompositionTier = Literal[
    "mid_sentence", "sentence_end", "paragraph_end", "paragraph_start",
]


@dataclass(frozen=True)
class CompositionSettings:
    """Knobs for content-aware composition pauses."""
    enabled: bool = False
    sensitivity: int = 50
    pause_min_ms: int = 300
    pause_max_ms: int = 6000
    paragraph_planning_min_ms: int = 2000
    paragraph_planning_max_ms: int = 8000


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
    pause_before_ms: int = 0      # Composition hesitation before typing
    pause_after_ms: int = 0       # Extra pause after this directive finishes
    is_entity: bool = False
    chunk_burst: bool = False     # True if part of a noun chunk
    chunk_char_jitter: Optional[Tuple[float, ...]] = None   # Per-char speed wobble (~1.0)
    chunk_char_rank_mult: Optional[Tuple[float, ...]] = None  # Per-char rank multiplier
    composition_score: float = 0.0  # Relative composition difficulty (debug)


class TypingPlanner:
    """Plans typing directives from TokenMeta."""

    def __init__(self, analyzer: SemanticAnalyzer):
        self.analyzer = analyzer

    def plan(
        self,
        text: str,
        mean_delay: int,
        variance: int,
        composition: Optional[CompositionSettings] = None,
    ) -> List[TypingDirective]:
        """Return directives for the engine."""
        comp = composition or CompositionSettings()
        metas, doc = self.analyzer.analyze(text)
        directives: List[TypingDirective] = []

        prior_paragraph_tokens = 0
        directive_index = 0
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

                pause_before, pause_after, score = self._composition_pauses(
                    chunk_metas, doc, text, directive_index, comp, prior_paragraph_tokens,
                )
                if chunk_metas[0].paragraph_start and directive_index > 0:
                    prior_paragraph_tokens = 0

                chunk_jitter, chunk_rank = self._chunk_char_profiles(chunk_metas)
                directives.append(TypingDirective(
                    text=chunk_text,
                    base_delay_ms=mean_delay,
                    delay_multiplier=self._rank_multiplier(max_rank),
                    momentum_boost=True,
                    typo_chance=0,
                    typo_chance_adjustment=self._typo_adjustment(max_rank),
                    revision_candidate=None,
                    revision_span=self._pick_chunk_revision(chunk_text, chunk_metas, doc),
                    pause_before_ms=pause_before,
                    pause_after_ms=self._clause_pause_ms(any_clause) + pause_after,
                    is_entity=is_ent,
                    chunk_burst=True,
                    chunk_char_jitter=chunk_jitter,
                    chunk_char_rank_mult=chunk_rank,
                    composition_score=score,
                ))
                prior_paragraph_tokens += len(chunk_metas)
                directive_index += 1
                i = j + 1
                continue

            rev_cand = self._pick_revision(meta, doc)

            pause_before, pause_after, score = self._composition_pauses(
                [meta], doc, text, directive_index, comp, prior_paragraph_tokens,
            )
            if meta.paragraph_start and directive_index > 0:
                prior_paragraph_tokens = 0

            directives.append(TypingDirective(
                text=meta.text,
                base_delay_ms=mean_delay,
                delay_multiplier=self._rank_multiplier(meta.rank),
                momentum_boost=not meta.is_entity,
                typo_chance=self._entity_typo_override(meta.is_entity),
                typo_chance_adjustment=self._typo_adjustment(meta.rank),
                revision_candidate=rev_cand,
                revision_span=None,
                pause_before_ms=pause_before,
                pause_after_ms=self._clause_pause_ms(meta.clause_boundary) + pause_after,
                is_entity=meta.is_entity,
                chunk_burst=False,
                composition_score=score,
            ))
            prior_paragraph_tokens += 1
            directive_index += 1
            i += 1

        return directives

    def _composition_pauses(
        self,
        metas: List[TokenMeta],
        doc: Doc,
        text: str,
        directive_index: int,
        comp: CompositionSettings,
        prior_paragraph_tokens: int,
    ) -> Tuple[int, int, float]:
        if not comp.enabled or not metas:
            return 0, 0, 0.0

        rng = self._directive_rng(text, directive_index)
        scale = max(0.0, min(2.0, comp.sensitivity / 50.0))
        score = 0.0
        before_ms = 0
        after_ms = 0

        tier = self._position_tier(metas)
        any_hard = any(m.is_hard_word for m in metas)

        if tier == "paragraph_start":
            para_lo = comp.paragraph_planning_min_ms
            para_hi = comp.paragraph_planning_max_ms
            length_factor = min(1.0, prior_paragraph_tokens / 40.0)
            para_lo = int(para_lo + length_factor * (para_hi - para_lo) * 0.4)
            score += 0.5 + length_factor * 0.3
            before_ms = self._sample_pause_ms(para_lo, para_hi, rng)
            before_ms = self._scale_pause(
                before_ms, scale, comp.paragraph_planning_max_ms,
            )

        if tier == "mid_sentence":
            content_score = self._content_trigger_score(metas, doc)
            if content_score > 0:
                score += content_score
                lo, hi = self._tier_band_ms("mid_sentence", comp)
                before_ms = self._sample_pause_ms(lo, hi, rng)
                if any_hard:
                    before_ms = int(before_ms * rng.uniform(1.0, 1.15))
                before_ms = self._scale_pause(before_ms, scale, comp.pause_max_ms)

        if tier == "paragraph_end":
            score += 0.4
            lo, hi = self._tier_band_ms("paragraph_end", comp)
            after_ms = self._sample_pause_ms(lo, hi, rng)
            after_ms = self._scale_pause(after_ms, scale, comp.pause_max_ms)
        elif tier == "sentence_end":
            score += 0.25
            lo, hi = self._tier_band_ms("sentence_end", comp)
            after_ms = self._sample_pause_ms(lo, hi, rng)
            after_ms = self._scale_pause(after_ms, scale, comp.pause_max_ms)

        return before_ms, after_ms, min(1.0, score)

    @staticmethod
    def _position_tier(metas: List[TokenMeta]) -> CompositionTier:
        primary = metas[0]
        terminal = metas[-1]
        if primary.paragraph_start:
            return "paragraph_start"
        if terminal.paragraph_end:
            return "paragraph_end"
        if terminal.sentence_end:
            return "sentence_end"
        return "mid_sentence"

    @staticmethod
    def _tier_band_ms(tier: str, comp: CompositionSettings) -> Tuple[int, int]:
        lo_setting = comp.pause_min_ms
        hi_setting = comp.pause_max_ms
        span = max(0, hi_setting - lo_setting)
        if tier == "mid_sentence":
            return lo_setting, int(lo_setting + 0.35 * span)
        if tier == "sentence_end":
            return int(lo_setting + 0.35 * span), int(lo_setting + 0.70 * span)
        if tier == "paragraph_end":
            return int(lo_setting + 0.70 * span), hi_setting
        raise ValueError(f"unknown composition tier: {tier}")

    @staticmethod
    def _sample_pause_ms(lo: int, hi: int, rng: random.Random) -> int:
        if hi <= lo:
            return lo
        return rng.randint(lo, hi)

    @staticmethod
    def _scale_pause(ms: int, scale: float, cap: int) -> int:
        ms = int(ms * scale)
        if ms <= 0:
            return 0
        effective_cap = max(_COMPOSITION_PAUSE_CAP_MS, cap)
        return min(ms, effective_cap)

    def _content_trigger_score(self, metas: List[TokenMeta], doc: Doc) -> float:
        primary = metas[0]
        score = 0.0
        if any(m.is_hard_word for m in metas):
            score += 0.35
        if any(m.is_entity for m in metas):
            score += 0.15
        if primary.is_discourse_marker:
            score += 0.25
        for meta in metas:
            if meta.text.strip().isalpha() and meta.pos in _REVISION_POS:
                ambiguity = self.analyzer.synonym_ambiguity_score(doc, meta.idx)
                if ambiguity > 0.3:
                    score += ambiguity * 0.3
                break
        return score

    @staticmethod
    def _directive_rng(text: str, directive_index: int) -> random.Random:
        digest = hashlib.md5(f"{text}:{directive_index}".encode()).hexdigest()
        return random.Random(int(digest[:8], 16))

    def _is_revision_eligible(self, meta: TokenMeta) -> bool:
        if meta.is_entity:
            return False
        if meta.pos not in _REVISION_POS:
            return False
        return meta.text.strip().isalpha()

    @staticmethod
    def _weighted_pick(candidates: List[str]) -> Optional[str]:
        if not candidates:
            return None
        top = candidates[:3]
        weights = list(range(len(top), 0, -1))
        return random.choices(top, weights=weights, k=1)[0]

    def _pick_revision_word(self, meta: TokenMeta, doc: Doc) -> Optional[str]:
        cands = self.analyzer.contextual_synonym_candidates(doc, meta.idx, max_results=5)
        return self._weighted_pick(cands)

    def _pick_revision(self, meta: TokenMeta, doc: Doc) -> Optional[str]:
        if not self._is_revision_eligible(meta):
            return None
        return self._pick_revision_word(meta, doc)

    def _pick_chunk_revision(
        self, chunk_text: str, chunk_metas: List[TokenMeta], doc: Doc
    ) -> Optional[RevisionSpan]:
        eligible = [m for m in chunk_metas if self._is_revision_eligible(m)]
        if not eligible:
            return None

        random.shuffle(eligible)
        for meta in eligible:
            wrong = self._pick_revision_word(meta, doc)
            if not wrong:
                continue

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
    def _token_rng(meta: TokenMeta) -> random.Random:
        digest = hashlib.md5(f"{meta.idx}:{meta.text}".encode()).hexdigest()
        return random.Random(int(digest[:8], 16))

    def _chunk_char_profiles(
        self, chunk_metas: List[TokenMeta],
    ) -> Tuple[Tuple[float, ...], Tuple[float, ...]]:
        """Per-character jitter and rank multipliers (one entry per character in chunk text)."""
        jitters: List[float] = []
        ranks: List[float] = []
        for meta in chunk_metas:
            jitter = self._token_rng(meta).uniform(0.84, 1.22)
            rank_mult = self._rank_multiplier(meta.rank)
            n = len(meta.text)
            jitters.extend([jitter] * n)
            ranks.extend([rank_mult] * n)
        return tuple(jitters), tuple(ranks)

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
