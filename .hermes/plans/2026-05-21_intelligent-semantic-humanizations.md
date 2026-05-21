# FlowState: Intelligent Semantic Humanizations Implementation Plan

> **For Hermes:** Use `subagent-driven-development` skill to implement this plan task-by-task.

**Goal:** Replace FlowState’s primitive typo/revision system with a spaCy-powered semantic layer that simulates real human typing behavior: synonym reconsideration, frequency-aware speed modulation, careful named-entity handling, clause-boundary breathing pauses, and noun-chunk burst typing.

**Architecture:** A new `SemanticAnalyzer` wraps spaCy/NLTK and produces a list of `TypingDirective` objects (one per token or chunk). The `TypingEngine` consumes directives instead of raw characters, applying per-directive delay multipliers, pause hints, and revision candidates. The existing character-loop mechanics (typo simulation, backspace, momentum) remain untouched — only the *delay calculation* and *segment boundaries* become semantic.

**Tech Stack:** Python ≥3.10, spaCy (`en_core_web_md`), NLTK (WordNet), existing FlowState stack (Playwright, pynput, etc.)

---

## Assumptions & Constraints

- We keep the existing `_human_keystroke`, `_get_typo_weights`, `send_backspace`, `send_char`, and momentum logic intact. This plan only changes *what* gets typed and *how fast*.
- spaCy is invoked **once per clipboard trigger**, not per character. Latency is acceptable because clipboard paste already has a 3-second countdown.
- `en_core_web_md` is the target model (has vectors, rank, NER, parser, noun chunks). `sm` works as a fallback but vectors are weaker.
- NLTK WordNet is used for synonym lookup. spaCy does not ship synonyms natively.
- Rich-text `TypeAction.text` segments are semantically analyzed *before* hitting the character loop.

---

## Task 1: Add Dependencies

**Objective:** Add `spacy`, `nltk`, and model download to the project.

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.txt`
- Create: `scripts/download_models.py`

**Step 1: Add to pyproject.toml**

```toml
dependencies = [
    "configparser>=7.2.0",
    "keyboard>=0.13.5",
    "pillow>=12.2.0",
    "playwright>=1.59.0",
    "pynput>=1.8.1",
    "pyperclip>=1.11.0",
    "pystray>=0.19.5",
    "spacy>=3.7.0",
    "nltk>=3.8",
]
```

**Step 2: Add to requirements.txt**

```
pystray==0.19.5
Pillow==10.2.0
keyboard==0.13.5
pynput==1.7.6
pyperclip==1.8.2
playwright==1.42.0
spacy==3.7.4
nltk==3.8.1
```

**Step 3: Create model download script**

Create `scripts/download_models.py`:

```python
import subprocess
import sys
import nltk

def main():
    # spaCy model
    try:
        import spacy
        spacy.load("en_core_web_md")
    except OSError:
        subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_md"])

    # NLTK data
    nltk.download("wordnet", quiet=True)
    nltk.download("omw-1.4", quiet=True)

if __name__ == "__main__":
    main()
```

**Step 4: Verify install**

Run: `python -m pip install -e . && python scripts/download_models.py`
Expected: `en_core_web_md` downloads and NLTK data installs without error.

**Step 5: Commit**

```bash
git add pyproject.toml requirements.txt scripts/download_models.py
git commit -m "deps: add spacy, nltk, and model download script"
```

---

## Task 2: Create SemanticAnalyzer Module

**Objective:** Build the core NLP wrapper that parses text and exposes per-token metadata needed by all five humanization features.

**Files:**
- Create: `src/semantic_analyzer.py`
- Test: `tests/test_semantic_analyzer.py`

**Step 1: Write `src/semantic_analyzer.py`**

```python
"""
FlowState — SemanticAnalyzer
Produces per-token and per-chunk metadata using spaCy + NLTK WordNet.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Set

import spacy
from nltk.corpus import wordnet as wn


@dataclass(frozen=True)
class TokenMeta:
    """Per-token typing metadata."""
    text: str                     # Original surface text (includes any trailing space if token.has_space)
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
    """Wraps spaCy and NLTK to annotate text for humanized typing."""

    # POS map: spaCy UPOS → WordNet pos constant
    _WN_POS_MAP = {
        "NOUN": wn.NOUN,
        "VERB": wn.VERB,
        "ADJ": wn.ADJ,
        "ADV": wn.ADV,
    }

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

            # If the token's head has a clause relation and this token is the rightmost
            # descendant of that head, we also mark it. (Simplest accurate version.)
            if not is_clause_boundary and token.head.dep_ in self._CLAUSE_CLOSERS:
                # Check if we're the last token in the head's subtree
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
        """Return synonym lemmas from WordNet for the given word + POS."""
        wn_pos = self._WN_POS_MAP.get(pos)
        if wn_pos is None:
            return []

        synsets = wn.synsets(token_text.lower(), pos=wn_pos)
        candidates: list[str] = []
        for syn in synsets[:3]:          # Limit depth to avoid obscure senses
            for lemma in syn.lemmas():
                name = lemma.name().replace("_", " ")
                if name.lower() != token_text.lower() and name not in candidates:
                    candidates.append(name)
                if len(candidates) >= max_results:
                    break
            if len(candidates) >= max_results:
                break

        return candidates
```

**Step 2: Write failing test**

Create `tests/test_semantic_analyzer.py`:

```python
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
    assert any("sprint" in s.lower() for s in syns)
```

**Step 3: Run test to verify failure**

Run: `pytest tests/test_semantic_analyzer.py -v`
Expected: FAIL — `ModuleNotFoundError: semantic_analyzer` (file not in PYTHONPATH yet) or import error if env not set up.

**Step 4: Fix PYTHONPATH / run from project root**

Run: `PYTHONPATH=src pytest tests/test_semantic_analyzer.py -v`
Expected: PASS (after model download).

**Step 5: Commit**

```bash
git add src/semantic_analyzer.py tests/test_semantic_analyzer.py
git commit -m "feat: add SemanticAnalyzer with spaCy/WordNet integration"
```

---

## Task 3: Create TypingDirective Pipeline

**Objective:** Bridge the analyzer output to the engine by building a `TypingPlanner` that turns `List[TokenMeta]` into an ordered list of directives the engine can consume character-by-character.

**Files:**
- Create: `src/typing_planner.py`
- Modify: `src/engine.py` (import only; no logic change yet)
- Test: `tests/test_typing_planner.py`

**Step 1: Write `src/typing_planner.py`**

```python
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
    revision_candidate: Optional[str] = None  # Synonym to type-then-replace
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

    def _pick_revision(self, meta: TokenMeta) -> Optional[str]:
        """Stochastically choose a synonym to type-then-replace."""
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
```

**Step 2: Write failing test**

Create `tests/test_typing_planner.py`:

```python
import pytest
from typing_planner import TypingPlanner
from semantic_analyzer import SemanticAnalyzer

@pytest.fixture(scope="module")
def planner():
    return TypingPlanner(SemanticAnalyzer())

def test_chunk_burst(planner):
    # "the quarterly results" should be one chunk directive
    directives = planner.plan("the quarterly results were good.", 50, 30)
    texts = [d.text for d in directives]
    # spaCy noun_chunks for this sentence usually yields "the quarterly results"
    chunk_directives = [d for d in directives if d.chunk_burst]
    assert len(chunk_directives) >= 1
    assert "the quarterly results" in "".join(d.text for d in chunk_directives)

def test_entity_flag(planner):
    directives = planner.plan("Alice visited Paris.", 50, 30)
    entity_dirs = [d for d in directives if d.is_entity]
    assert len(entity_dirs) >= 2  # Alice, Paris
```

**Step 3: Run test**

Run: `PYTHONPATH=src pytest tests/test_typing_planner.py -v`
Expected: PASS after implementation.

**Step 4: Commit**

```bash
git add src/typing_planner.py tests/test_typing_planner.py
git commit -m "feat: add TypingPlanner with chunk-burst and rank-based speed"
```

---

## Task 4: Wire Semantic Layer into TypingEngine

**Objective:** Teach `TypingEngine` to optionally route text through the semantic pipeline before falling back to the legacy plain-text loop.

**Files:**
- Modify: `src/engine.py`
- Modify: `src/settings_gui.py` (add toggles)

**Step 1: Add imports and initialization in `engine.py`**

At top of `engine.py`:

```python
from semantic_analyzer import SemanticAnalyzer
from typing_planner import TypingPlanner
```

In `TypingEngine.__init__` (after `self._formatter = ...`):

```python
        # Semantic layer (lazy-loaded so the app starts fast even if spaCy is heavy)
        self._analyzer: SemanticAnalyzer | None = None
        self._planner: TypingPlanner | None = None
```

**Step 2: Add lazy loader**

Add method to `TypingEngine`:

```python
    def _ensure_semantic_layer(self):
        if self._analyzer is None:
            self._analyzer = SemanticAnalyzer()
            self._planner = TypingPlanner(self._analyzer)
```

**Step 3: Add new settings**

Add to `self.defaults` in `__init__`:

```python
            "EnableSemanticSpeed": 1,
            "EnableClausePauses": 1,
            "EnableChunkBurst": 1,
            "EnableSmartRevisions": 1,
            "EnableEntityCare": 1,
```

Add to `self.settings_list` / `self.setting_names` for HUD exposure:

```python
        self.settings_list = [
            "UserMeanDelay", "UserVariance", "TypoChance",
            "TypoDelay", "RevisionChance",
            "EnableSemanticSpeed", "EnableClausePauses",
            "EnableChunkBurst", "EnableSmartRevisions", "EnableEntityCare",
        ]
        self.setting_names = [
            "Typing Speed (Lower is Faster)", "Variance", "Typo Chance (%)",
            "Typo Correction Speed", "Base Revision Chance (%)",
            "Semantic Speed", "Clause Pauses",
            "Chunk Burst", "Smart Revisions", "Entity Care",
        ]
```

**Step 4: Refactor `_type_plain_text` to consume directives**

Replace `_type_plain_text` with a two-path implementation:

```python
    def _type_plain_text(self, text, neighbor_map):
        """Entry point. Chooses semantic path or legacy path."""
        semantic_active = any([
            self.settings["EnableSemanticSpeed"],
            self.settings["EnableClausePauses"],
            self.settings["EnableChunkBurst"],
            self.settings["EnableSmartRevisions"],
            self.settings["EnableEntityCare"],
        ])

        if semantic_active:
            self._ensure_semantic_layer()
            directives = self._planner.plan(
                text,
                mean_delay=self.settings["UserMeanDelay"],
                variance=self.settings["UserVariance"],
            )
            self._execute_directives(directives, neighbor_map)
        else:
            self._legacy_type_plain_text(text, neighbor_map)
```

Then rename the existing `_type_plain_text` body → `_legacy_type_plain_text(...)` (keep untouched).

**Step 5: Implement `_execute_directives`**

```python
    def _execute_directives(self, directives, neighbor_map):
        """Typed-loop over directives instead of raw characters."""
        total_len = sum(len(d.text) for d in directives)
        self.current_momentum = 0

        for directive in directives:
            self._sleep(0)

            # --- SMART REVISION: type synonym, pause, backspace, type real word ---
            if (self.settings["EnableSmartRevisions"]
                    and directive.revision_candidate
                    and random.randint(1, 100) <= self.settings["RevisionChance"]):
                self._simulate_revision(directive, neighbor_map)
                continue

            # --- CHUNK BURST: lower variance inside noun chunks ---
            effective_variance = (
                self.settings["UserVariance"] // 2
                if (self.settings["EnableChunkBurst"] and directive.chunk_burst)
                else self.settings["UserVariance"]
            )

            # --- ENTITY CARE: override typo chance ---
            effective_typo_chance = self.settings["TypoChance"]
            if self.settings["EnableEntityCare"] and directive.is_entity:
                effective_typo_chance = max(0, effective_typo_chance - 2)

            # --- SPEED MODULATION: apply rank-based multiplier ---
            mean = self.settings["UserMeanDelay"]
            if self.settings["EnableSemanticSpeed"]:
                mean *= directive.delay_multiplier
            mean = max(10, mean)

            # Emit characters in this directive
            for idx, char in enumerate(directive.text):
                self._sleep(0)

                # Intra-directive typo logic (reuse existing helpers)
                if (self.settings["EnableTypos"]
                        and random.randint(1, 100) <= effective_typo_chance):
                    # Quick path: use the same typo logic but scoped to single char
                    consumed = self._inject_typo(char, directive.text[idx + 1:], neighbor_map)
                    if consumed:
                        continue

                # Normal keystroke
                self._human_keystroke(char)

                # Momentum
                if directive.momentum_boost and self.current_momentum < 15:
                    self.current_momentum += 0.5

                # Delay calculation
                calc_mean = mean - self.current_momentum
                next_char = directive.text[idx + 1] if idx + 1 < len(directive.text) else ""
                bigram = (char + next_char).lower()
                if bigram in ["th", "he", "in", "er", "an", "re", "on", "at", "en",
                              "nd", "ti", "es", "or", "te", "of", "ed", "is", "it",
                              "al", "ar", "st", "to", "nt"]:
                    calc_mean -= 10

                delay = self._gaussian(calc_mean, effective_variance)
                delay = max(10, min(delay, 250))
                self._sleep(delay / 1000.0)

            # --- Pause after directive (clause boundaries, etc.) ---
            if self.settings["EnableClausePauses"] and directive.pause_after_ms:
                self._sleep(directive.pause_after_ms / 1000.0)
                self.current_momentum = max(0, self.current_momentum - 3)
```

**Step 6: Implement `_simulate_revision`**

```python
    def _simulate_revision(self, directive, neighbor_map):
        """Type the synonym candidate, hesitate, backspace, then type the real text."""
        wrong = directive.revision_candidate
        right = directive.text.strip()

        # Type wrong word
        for c in wrong:
            self._human_keystroke(c)
            self._sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)

        # Hesitation (the 'reconsideration' moment)
        self._sleep(random.randint(500, 1100) / 1000.0)

        # Backspace wrong word
        for _ in range(len(wrong)):
            self.driver.send_backspace()
            self._sleep(random.randint(40, 70) / 1000.0)

        # Pause before choosing correct word
        self._sleep(random.randint(600, 1200) / 1000.0)
        self.current_momentum = 0

        # Type correct word with slightly more care (higher delay multiplier)
        for c in right:
            self._human_keystroke(c)
            calc_mean = self.settings["UserMeanDelay"] * 1.15
            delay = self._gaussian(calc_mean, self.settings["UserVariance"])
            self._sleep(max(10, delay) / 1000.0)

        # Re-inject trailing whitespace if directive had it
        trailing_ws = directive.text[len(directive.text.rstrip()):]
        for c in trailing_ws:
            self._human_keystroke(c)
            self._sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)
```

**Step 7: Add `_inject_typo` helper**

Extract a reusable single-typo helper from the legacy logic so `_execute_directives` doesn't duplicate the whole typo block:

```python
    def _inject_typo(self, char, remaining_text, neighbor_map):
        """Attempt a single-character typo. Returns True if a typo was injected."""
        next_char = remaining_text[0] if remaining_text else ""
        weights = self._get_typo_weights(char, next_char, self.current_momentum, neighbor_map)
        choices = ["spatial", "transposition", "omission", "doubling"]
        typo_type = random.choices(choices, weights=weights, k=1)[0]

        typo_chars = ""
        chars_consumed = 1

        if typo_type == "spatial":
            neighbor = self._get_neighbor(char, neighbor_map)
            typo_chars = neighbor if neighbor else char
        elif typo_type == "transposition":
            typo_chars = next_char + char
            chars_consumed = 2
            self._sleep(max(10, self.settings["UserMeanDelay"] - 15) / 1000.0)
        elif typo_type == "omission":
            typo_chars = ""
        elif typo_type == "doubling":
            typo_chars = char + char

        for c in typo_chars:
            self._human_keystroke(c)
            self._sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)

        realization = random.randint(0, 3)
        buf = remaining_text[:realization]
        for c in buf:
            self._human_keystroke(c)
            self._sleep(self._gaussian(self.settings["UserMeanDelay"], self.settings["UserVariance"]) / 1000.0)

        self._sleep(random.randint(self.settings["TypoDelay"] * 2, self.settings["TypoDelay"] * 4) / 1000.0)

        back_count = len(typo_chars) + len(buf)
        for _ in range(back_count):
            self.driver.send_backspace()
            self._sleep(random.randint(30, 60) / 1000.0)

        self._sleep(random.randint(100, 200) / 1000.0)
        self.current_momentum = 0
        return True
```

**Step 8: Update settings save/load**

In `save_settings`, add the new keys to the `[Behavior]` section.

**Step 9: Run integration test**

Run: `PYTHONPATH=src pytest tests/ -v -k "engine or semantic or planner"`
Expected: PASS on new tests; existing engine tests should still pass.

**Step 10: Commit**

```bash
git add src/engine.py src/settings_gui.py tests/
git commit -m "feat: wire semantic layer into TypingEngine with directive loop"
```

---

## Task 5: Settings GUI Toggle Integration

**Objective:** Expose the five new semantic toggles in the settings window so users can enable/disable features.

**Files:**
- Modify: `src/settings_gui.py`

**Step 1: Locate the checkbox / toggle creation code**

Read `src/settings_gui.py` and find where `EnableTypos`, `EnableRevisions`, etc. are rendered. Add five new boolean checkboxes:

- `EnableSemanticSpeed`
- `EnableClausePauses`
- `EnableChunkBurst`
- `EnableSmartRevisions`
- `EnableEntityCare`

**Step 2: Bind to engine settings**

Each checkbox should read from / write to `engine.settings["Enable..."]` and call `engine.save_settings()` on change.

**Step 3: Verify UI manually**

Launch the app, open settings, confirm all five toggles appear and persist across restarts.

**Step 4: Commit**

```bash
git add src/settings_gui.py
git commit -m "ui: add semantic humanization toggles to settings GUI"
```

---

## Task 6: Integration Smoke Test & Calibration

**Objective:** Run a real end-to-end smoke test and calibrate multipliers so the effect feels natural, not exaggerated.

**Files:**
- Create: `tests/test_semantic_e2e.py`
- Modify: `src/typing_planner.py` (calibrate constants)

**Step 1: Write end-to-end test**

Create `tests/test_semantic_e2e.py`:

```python
import pytest
from engine import TypingEngine
from unittest.mock import MagicMock

class MockDriver:
    def __init__(self):
        self.log = []
    def send_char(self, c, dwell=0.01):
        self.log.append(("char", c))
    def send_backspace(self):
        self.log.append(("backspace",))
    def send_key(self, k):
        self.log.append(("key", k))
    def attach(self, title=None): pass
    def detach(self): pass
    def focus_page(self): pass
    def get_clipboard(self): return ""
    def detect_layout(self): return "QWERTY"

@pytest.fixture
def engine():
    driver = MockDriver()
    eng = TypingEngine(driver)
    # Speed up for test
    eng.settings["UserMeanDelay"] = 5
    eng.settings["UserVariance"] = 2
    eng.settings["EnableSemanticSpeed"] = 1
    eng.settings["EnableClausePauses"] = 1
    eng.settings["EnableChunkBurst"] = 1
    eng.settings["EnableSmartRevisions"] = 1
    eng.settings["EnableEntityCare"] = 1
    eng.settings["TypoChance"] = 0
    return eng

def test_semantic_path_runs(engine):
    """Ensure the semantic loop executes without crashing."""
    # We call the internal helper directly because trigger_typing expects clipboard + driver attach
    engine._type_plain_text("The quarterly results were excellent because Alice worked hard.", {})
    assert len(engine.driver.log) > 10
```

**Step 2: Run**

Run: `PYTHONPATH=src pytest tests/test_semantic_e2e.py -v`
Expected: PASS.

**Step 3: Calibrate multipliers**

After smoke test, review `_rank_multiplier` in `typing_planner.py`. If 0.85/1.45 feels too dramatic, tighten to 0.90/1.25. If clause pauses feel robotic, widen their random range or make them conditional on sentence length.

**Step 4: Commit**

```bash
git add tests/test_semantic_e2e.py
git commit -m "test: add semantic e2e smoke test"
```

---

## Task 7: Documentation & README Update

**Objective:** Document the new features so users know what toggles do.

**Files:**
- Modify: `README.md`

**Step 1: Add "Semantic Humanization" section**

Insert after the existing "Typing Behaviour" section:

```markdown
### Semantic Humanization (New)

FlowState now uses spaCy + WordNet to make typing feel genuinely human:

- **Smart Revisions** — Occasionally types a synonym first, then backspaces and reconsiders (verbs, adjectives, nouns only).
- **Semantic Speed** — Rare words are typed more slowly; common words flow faster (based on corpus frequency rank).
- **Entity Care** — Named entities (people, companies, places) are typed with fewer typos and steadier rhythm.
- **Clause Pauses** — Uses dependency parsing to insert micro-pauses at the end of subordinate clauses, not just at sentence ends.
- **Chunk Burst** — Treats noun phrases like "the quarterly results" as a single cognitive burst, reducing hesitation inside the phrase.
```

**Step 2: Add spaCy model setup instructions**

Add to setup section:

```bash
python -m spacy download en_core_web_md
python scripts/download_models.py
```

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add semantic humanization section to README"
```

---

## Summary of New / Modified Files

| File | Action | Purpose |
|------|--------|---------|
| `pyproject.toml` | Modify | Add `spacy`, `nltk` dependencies |
| `requirements.txt` | Modify | Pin `spacy`, `nltk` versions |
| `scripts/download_models.py` | Create | One-shot spaCy model + NLTK data downloader |
| `src/semantic_analyzer.py` | Create | spaCy/WordNet wrapper; `TokenMeta` dataclass |
| `src/typing_planner.py` | Create | Converts `TokenMeta` → `TypingDirective` list |
| `src/engine.py` | Modify | Integrate planner; `_execute_directives`, `_simulate_revision` |
| `src/settings_gui.py` | Modify | Add 5 boolean toggles |
| `tests/test_semantic_analyzer.py` | Create | Unit tests for analyzer |
| `tests/test_typing_planner.py` | Create | Unit tests for planner |
| `tests/test_semantic_e2e.py` | Create | Smoke test for engine integration |
| `README.md` | Modify | Document new features |

---

## Risks, Tradeoffs, and Open Questions

1. **spaCy model size**: `en_core_web_md` is ~40 MB. For a packaged PyInstaller app, this increases binary size. Consider documenting how to strip unused pipeline components (`nlp.remove_pipe(...)`) if size matters.
2. **Performance on long paste**: Very long clipboard text (>5000 tokens) will take noticeable time to parse. Mitigation: add a token-count guard that falls back to legacy mode if `len(doc) > 2000`.
3. **WordNet coverage**: Some domain-specific words have no synonyms. The `_pick_revision` method gracefully falls back to `None`.
4. **Cross-platform paths**: `scripts/download_models.py` should work on Windows, macOS, and Linux. Test on all three before release.
5. **License**: NLTK and spaCy are permissive (Apache 2.0 / BSD / MIT). No GPL contamination.

---

## Execution Handoff

Plan complete and saved to `.hermes/plans/2026-05-21_intelligent-semantic-humanizations.md`.

Ready to execute using `subagent-driven-development` — I'll dispatch a fresh subagent per task with two-stage review (spec compliance then code quality). Shall I proceed?
