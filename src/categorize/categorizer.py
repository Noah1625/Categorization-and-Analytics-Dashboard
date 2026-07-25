from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Iterable, Sequence

from .normalize import merchant_key

# Confidence at or above this is safe to apply without asking.
AUTO_APPLY = 0.85
# Below this a guess is shown but grayed out.
SUGGEST_FLOOR = 0.50

# Observations older than this count for half as much.
HALF_LIFE_DAYS = 150.0
# A correction the user typed is worth several passive observations.
CORRECTION_WEIGHT = 6.0
# Damps confidence when a key has thin support, so one sighting suggests but does not auto-apply.
SUPPORT_DAMPING = 0.5

# Everything a subset match yields is scaled by this. The ceiling for a perfect
# subset match is therefore ~0.79 (purity 1.0 x support damping x this), which
# sits below AUTO_APPLY on purpose.
SUBSET_PENALTY = 0.8
# Shared tokens must account for at least this share of the stored merchant's
# distinctiveness. Blocks "grocery store" from matching "hardware store" on the
# strength of "store" alone.
SUBSET_MIN_OVERLAP = 0.5
# A token this common across merchants identifies nothing on its own, so a
# match resting only on such tokens is rejected outright.
SUBSET_STOPWORD_DF = 0.25

# Where a merchant puts its spaces is formatting, not identity.
COMPACT_PENALTY = 0.98

# Similarity is 1 - distance/length, so 0.82 permits one edit in a 6-character
# token and two in an 11-character one.
TYPO_MIN_SIMILARITY = 0.82
# Short tokens are not corrected at all.
TYPO_MIN_TOKEN_LEN = 4
# Extra hedge on top of SUBSET_PENALTY when a correction was needed, so a
# guess resting on a typo reads as less certain than one that matched cleanly.
TYPO_PENALTY = 0.9


@dataclass(frozen=True)
class Prediction:
    """A category guess plus everything needed to explain or audit it."""

    category_id: int | None
    category_name: str | None
    confidence: float
    source: str  # "rule" | "memory" | "none"
    alternatives: tuple[tuple[int, str, float], ...] = ()

    @property
    def should_auto_apply(self) -> bool:
        return self.category_id is not None and self.confidence >= AUTO_APPLY

    @property
    def should_suggest(self) -> bool:
        return self.category_id is not None and self.confidence >= SUGGEST_FLOOR


# Memory is keyed at three levels and their votes are pooled.
_SCOPES = ("both", "description", "code")

# How much each scope's opinion counts when the three are pooled.
_SCOPE_WEIGHTS = {"both": 3.0, "description": 2.0, "code": 2.0}


@dataclass
class _Observation:
    """One labelled example, already normalized."""

    keys: dict[str, str]
    category_id: int
    when: date
    weight: float = 1.0


@dataclass
class _Rule:
    """A user-defined regex that pins a merchant to a category, overriding memory."""

    pattern: re.Pattern[str]
    category_id: int


@dataclass
class Categorizer:
    """Predicts a category for a transaction, and learns from corrections."""

    category_names: dict[int, str] = field(default_factory=dict)
    _rules: list[_Rule] = field(default_factory=list)
    # Decayed weights, for deciding which category a key votes for.
    _memory: dict[str, dict[str, dict[int, float]]] = field(default_factory=dict)
    # The same observations undecayed, for deciding how much evidence there is.
    _support: dict[str, dict[str, dict[int, float]]] = field(default_factory=dict)
    _token_keys: dict[str, dict[str, set[str]]] = field(default_factory=dict)
    _key_tokens: dict[str, dict[str, frozenset[str]]] = field(default_factory=dict)
    _token_grams: dict[str, dict[str, set[str]]] = field(default_factory=dict)
    _compact_keys: dict[str, dict[str, set[str]]] = field(default_factory=dict)
    _reference_date: date | None = None

    def fit(
        self,
        transactions: Iterable[object],
        categories: Iterable[object] | None = None,
    ) -> "Categorizer":
        """Learn from history. Replaces any existing state."""
        if categories is not None:
            self.category_names = {
                int(getattr(c, "category_id")): str(getattr(c, "category_name"))
                for c in categories
            }

        self._memory = {scope: defaultdict(lambda: defaultdict(float)) for scope in _SCOPES}
        self._support = {scope: defaultdict(lambda: defaultdict(float)) for scope in _SCOPES}
        self._token_keys = {scope: defaultdict(set) for scope in _SCOPES}
        self._key_tokens = {scope: {} for scope in _SCOPES}
        self._token_grams = {scope: defaultdict(set) for scope in _SCOPES}
        self._compact_keys = {scope: defaultdict(set) for scope in _SCOPES}

        observations: list[_Observation] = []
        for txn in transactions:
            category_id = getattr(txn, "category_id", None)
            if category_id is None:
                continue
            observations.append(
                _Observation(
                    keys=_build_keys(
                        getattr(txn, "description", None),
                        getattr(txn, "transaction_code", None),
                    ),
                    category_id=int(category_id),
                    when=_as_date(getattr(txn, "transaction_date", None)),
                )
            )

        # Decay is measured against the newest transaction, so the reference has
        # to be known before anything is recorded.
        self._reference_date = (
            max(o.when for o in observations) if observations else date.today()
        )
        for obs in observations:
            self._remember(obs)

        return self

    def learn(
        self,
        description: str | None,
        transaction_code: str | None,
        category_id: int,
        transaction_date: object = None,
        corrected: bool = False,
    ) -> None:
        """Record one labelled transaction, effective immediately."""
        obs = _Observation(
            keys=_build_keys(description, transaction_code),
            category_id=int(category_id),
            when=_as_date(transaction_date) or self._reference_date or date.today(),
            weight=CORRECTION_WEIGHT if corrected else 1.0,
        )
        if self._reference_date is None or obs.when > self._reference_date:
            self._reference_date = obs.when
        self._remember(obs)

    def add_rule(self, pattern: str, category_id: int) -> None:
        """Pin every transaction matching ``pattern`` to a category. """
        self._rules.append(_Rule(re.compile(pattern, re.IGNORECASE), int(category_id)))

    def _remember(self, obs: _Observation) -> None:
        weight = obs.weight * self._decay(obs.when)
        for scope, key in obs.keys.items():
            if not key:
                continue
            self._memory[scope][key][obs.category_id] += weight
            # Undecayed, so an old merchant still counts as known. Decay belongs
            # in the vote, not in the question of whether evidence exists.
            self._support[scope][key][obs.category_id] += obs.weight
            if key in self._key_tokens[scope]:
                continue
            tokens = _tokens_of(key)
            self._key_tokens[scope][key] = tokens
            self._compact_keys[scope][_compact(key)].add(key)
            for token in tokens:
                # Gram-index only on a token's first sighting in this scope.
                if token not in self._token_keys[scope]:
                    for gram in _bigrams(token):
                        self._token_grams[scope][gram].add(token)
                self._token_keys[scope][token].add(key)

    def _decay(self, when: date) -> float:
        """Exponential recency weight, relative to the newest known transaction."""
        reference = self._reference_date or date.today()
        age_days = max((reference - when).days, 0)
        return 0.5 ** (age_days / HALF_LIFE_DAYS)

    def _idf(self, scope: str, token: str) -> float:
        """How much a token narrows things down, by document frequency."""
        total_keys = len(self._key_tokens.get(scope, {}))
        if not total_keys:
            return 0.0
        frequency = len(self._token_keys.get(scope, {}).get(token, ()))
        if not frequency:
            return 0.0
        # Tokens on more than a quarter of all merchants carry no signal alone.
        if frequency / total_keys > SUBSET_STOPWORD_DF:
            return 0.0
        return math.log(1.0 + total_keys / frequency)

    def _closest_token(self, scope: str, token: str) -> tuple[str, float] | None:
        """Find the known token a misspelling most likely meant."""
        if len(token) < TYPO_MIN_TOKEN_LEN or token.isdigit():
            return None

        candidates: set[str] = set()
        for gram in _bigrams(token):
            candidates |= self._token_grams.get(scope, {}).get(gram, set())
        if not candidates:
            return None

        # The most an accepted correction may change the token's length.
        budget = max(1, int(len(token) * (1.0 - TYPO_MIN_SIMILARITY)))

        best: tuple[str, float] | None = None
        for candidate in candidates:
            if abs(len(candidate) - len(token)) > budget:
                continue
            distance = _edit_distance(token, candidate, budget)
            if distance is None:
                continue
            similarity = 1.0 - distance / max(len(token), len(candidate))
            if similarity >= TYPO_MIN_SIMILARITY and (best is None or similarity > best[1]):
                best = (candidate, similarity)
        return best

    def _resolve_tokens(self, scope: str, tokens: frozenset[str]) -> tuple[frozenset[str], float]:
        """Map misspelled tokens onto known ones."""
        known = self._token_keys.get(scope, {})
        if all(t in known for t in tokens):
            return tokens, 1.0

        resolved: set[str] = set()
        factor = 1.0
        for token in tokens:
            if token in known:
                resolved.add(token)
                continue
            match = self._closest_token(scope, token)
            if match is None:
                resolved.add(token) # Leave it as-is; it will be ignored by subset matching.
            else:
                resolved.add(match[0])
                factor = min(factor, match[1] * TYPO_PENALTY)
        return frozenset(resolved), factor

    def _support_for(self, scope: str, key: str) -> float:
        """Total undecayed evidence recorded for a key."""
        return sum(self._support.get(scope, {}).get(key, {}).values())

    def _compact_match(self, scope: str, key: str) -> tuple[str, float] | None:
        """Find a stored key that differs from ``key`` only in its spacing."""
        candidates = self._compact_keys.get(scope, {}).get(_compact(key), set()) - {key}
        if not candidates:
            return None
        # Several spellings can collapse to the same string; trust the best-attested.
        best_key = max(candidates, key=lambda k: self._support_for(scope, k))
        return best_key, COMPACT_PENALTY

    def _subset_match(self, scope: str, key: str) -> tuple[str, float] | None:
        """Find the best stored key whose tokens subset-match ``key``."""
        query_tokens = _tokens_of(key)
        if not query_tokens:
            return None

        # Correct misspellings first.
        query_tokens, typo_factor = self._resolve_tokens(scope, query_tokens)

        # Only keys sharing a token can possibly subset-match.
        candidates: set[str] = set()
        for token in query_tokens:
            candidates |= self._token_keys.get(scope, {}).get(token, set())
        candidates.discard(key)
        if not candidates:
            return None

        best_key: str | None = None
        best_quality = 0.0
        best_score = 0.0
        for candidate in candidates:
            candidate_tokens = self._key_tokens[scope][candidate]
            if not (query_tokens <= candidate_tokens or candidate_tokens <= query_tokens):
                continue

            shared = query_tokens & candidate_tokens
            shared_idf = sum(self._idf(scope, t) for t in shared)
            candidate_idf = sum(self._idf(scope, t) for t in candidate_tokens)

            # Reject matches resting only on common tokens, which are not distinctive enough to trust.
            if shared_idf <= 0.0 or candidate_idf <= 0.0:
                continue

            # Quality is how much of the stored merchant's distinctiveness is accounted for by the overlap.
            quality = min(shared_idf / candidate_idf, 1.0)
            if quality < SUBSET_MIN_OVERLAP:
                continue

            # Score is a combination of quality and support.
            support = self._support_for(scope, candidate)
            score = shared_idf * (support / (support + SUPPORT_DAMPING))
            if score > best_score:
                best_key, best_quality, best_score = candidate, quality, score

        if best_key is None:
            return None
        return best_key, best_quality * typo_factor * SUBSET_PENALTY

    # -------------------------------------------------------------- predicting

    def predict(
        self,
        description: str | None,
        transaction_code: str | None = None,
    ) -> Prediction:
        """Predict a category."""
        keys = _build_keys(description, transaction_code)

        for rule in self._rules:
            if any(key and rule.pattern.search(key) for key in keys.values()):
                return self._build(rule.category_id, 1.0, "rule")

        memory = self._predict_from_memory(keys)
        return memory if memory is not None else Prediction(None, None, 0.0, "none")

    def _predict_from_memory(self, keys: dict[str, str]) -> Prediction | None:
        """Pool the evidence from all three scopes into one vote."""
        pooled: dict[int, float] = defaultdict(float)
        influence = 0.0
        raw_support = 0.0
        best_quality = 0.0

        for scope in _SCOPES:
            key = keys.get(scope, "")
            if not key:
                continue

            counts = self._memory.get(scope, {}).get(key)
            quality = 1.0
            if not counts:
                # Exact miss - try a respacing first, then a partial rename.
                fallback = self._compact_match(scope, key) or self._subset_match(scope, key)
                if fallback is None:
                    continue
                key, quality = fallback
                counts = self._memory[scope][key]

            total = sum(counts.values())
            if total <= 0:
                continue
            # How many observations back this key, ignoring their age. Using the
            # decayed total here would read every merchant older than a few
            # half-lives as unsupported and zero out its confidence.
            support = self._support_for(scope, key)

            # Weight the scope's opinion by its configured weight, the support for this key, and the quality of the match.
            weight = _SCOPE_WEIGHTS[scope] * (support / (support + SUPPORT_DAMPING)) * quality
            for category_id, category_weight in counts.items():
                pooled[category_id] += weight * (category_weight / total)
            influence += weight
            raw_support = max(raw_support, support)
            best_quality = max(best_quality, quality)

        if not pooled or influence <= 0:
            return None

        ranked = sorted(pooled.items(), key=lambda kv: kv[1], reverse=True)
        top_id, top_score = ranked[0]
        confidence = (top_score / influence) * (raw_support / (raw_support + SUPPORT_DAMPING))
        confidence *= best_quality

        alternatives = tuple(
            (cid, self.category_names.get(cid, str(cid)), score / influence)
            for cid, score in ranked[:3]
        )
        return self._build(top_id, confidence, "memory", alternatives)

    def _build(
        self,
        category_id: int,
        confidence: float,
        source: str,
        alternatives: tuple[tuple[int, str, float], ...] = (),
    ) -> Prediction:
        """Construct a Prediction object, capping confidence at 1.0."""
        return Prediction(
            category_id=category_id,
            category_name=self.category_names.get(category_id, str(category_id)),
            confidence=min(confidence, 1.0),
            source=source,
            alternatives=alternatives,
        )

    @property
    def known_merchants(self) -> int:
        """Distinct merchants recognized by the single-field scopes."""
        return len(self._memory.get("description", {})) + len(self._memory.get("code", {}))

    def explain(self, text: str) -> Sequence[tuple[str, str, float]]:
        """Show what memory holds for some raw text. For debugging bad guesses."""
        key = merchant_key(text)
        out: list[tuple[str, str, float]] = []
        for scope in _SCOPES:
            counts = self._memory.get(scope, {}).get(key)
            if not counts:
                continue
            total = sum(counts.values()) or 1.0
            out.extend(
                (scope, self.category_names.get(cid, str(cid)), w / total)
                for cid, w in counts.items()
            )
        return sorted(out, key=lambda row: row[2], reverse=True)


def _tokens_of(key: str) -> frozenset[str]:
    """Split a normalized key into its token set, dropping the scope separator."""
    return frozenset(key.replace("|", " ").split())


def _compact(key: str) -> str:
    """Strip a key's spacing, keeping the scope separator so fields stay distinct."""
    return "|".join("".join(part.split()) for part in key.split("|"))


def _bigrams(token: str) -> frozenset[str]:
    """Character bigrams, used to find spelling-similar tokens cheaply."""
    if len(token) < 2:
        return frozenset({token})
    return frozenset(token[i : i + 2] for i in range(len(token) - 1))


def _edit_distance(a: str, b: str, budget: int) -> int | None:
    """Edit distance, or None once it provably exceeds ``budget``.

    Optimal string alignment rather than plain Levenshtein, so transpositions count as one edit.
    This is what the Damerau-Levenshtein algorithm does."""
    if a == b:
        return 0
    if abs(len(a) - len(b)) > budget:
        return None

    before_previous: list[int] = []
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current = [i]
        for j, char_b in enumerate(b, start=1):
            cost = min(
                previous[j] + 1,                      # deletion
                current[j - 1] + 1,                   # insertion
                previous[j - 1] + (char_a != char_b), # substitution
            )
            if (
                i > 1
                and j > 1
                and char_a == b[j - 2]
                and a[i - 2] == char_b
            ):
                cost = min(cost, before_previous[j - 2] + 1) # transposition
            current.append(cost)
        if min(current) > budget:
            return None
        before_previous, previous = previous, current

    distance = previous[-1]
    return distance if distance <= budget else None


def _build_keys(description: str | None, transaction_code: str | None) -> dict[str, str]:
    """Normalize a transaction's text into one key per memory scope."""
    desc = merchant_key(description)
    code = merchant_key(transaction_code)
    return {
        "both": f"{desc}|{code}" if desc or code else "",
        "description": desc,
        "code": code,
    }


def _as_date(value: object) -> date:
    """Convert a transaction_date into a date object, or today if it can't be parsed."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            pass
    return date.today()
