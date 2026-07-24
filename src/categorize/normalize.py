"""Turn raw bank text into a stable merchant key."""

from __future__ import annotations

import re

# Payment processors, card networks, and ACH noise that wrap the real merchant
# name. Applied repeatedly because feeds stack them ("POS DEBIT SQ *FOO").
_PREFIXES = re.compile(
    r"^(?:"
    r"sq\s*\*|tst\*|sp\s+|py\s*\*|paypal\s*\*|pp\s*\*|dd\s*\*|"
    r"pos\s+(?:debit|credit)|debit\s+card\s+purchase|check\s?card\s+purchase|"
    r"recurring\s+(?:payment|debit)|ach\s+(?:debit|credit|payment)|"
    r"purchase\s+authorized\s+on|point\s+of\s+sale\s+withdrawal|"
    r"visa\s+purchase|external\s+(?:withdrawal|deposit)|web\s+id:?|"
    r"electronic\s+(?:withdrawal|deposit)"
    r")\s*",
    re.IGNORECASE,
)

# Trailing corporate suffixes carry no signal about what was bought.
_SUFFIXES = {"llc", "inc", "co", "corp", "ltd", "lp", "plc", "sa", "nv"}

# Stripped only when trailing, so "IN N OUT" keeps its middle tokens.
_STATES = {
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id",
    "il", "in", "ia", "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms",
    "mo", "mt", "ne", "nv", "nh", "nj", "nm", "ny", "nc", "nd", "oh", "ok",
    "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv",
    "wi", "wy", "dc",
}

# Date-like tokens are usually a reference, not a merchant name.
_DATE_LIKE = re.compile(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b")

# Non-alphanumeric runs are replaced with a single space.
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def merchant_key(*parts: str | None) -> str:
    """Collapse raw bank text into a stable lookup key.

    Accepts several fields (description, transaction_code) and normalizes the
    concatenation. Returns "" when everything is stripped away.

    >>> merchant_key("SHELL OIL #087C70")
    'shell oil'
    >>> merchant_key("SQ *BLUE BOTTLE 04412 CHICAGO IL")
    'blue bottle'
    """
    text = " ".join(p for p in parts if p)

    # The auth/reference token after "#" is unique per transaction. Keeping it
    # would make every key a singleton and defeat the whole memory layer.
    text = text.split("#", 1)[0]
    text = text.lower()
    text = _DATE_LIKE.sub(" ", text)

    # Peel stacked processor prefixes until the string stops shrinking.
    while True:
        stripped = _PREFIXES.sub("", text, count=1)
        if stripped == text:
            break
        text = stripped

    text = _NON_ALNUM.sub(" ", text)
    tokens = text.split()

    # Store/terminal numbers vary per location. Short numbers stay because they
    # are often part of the brand ("7 eleven", "76").
    tokens = [t for t in tokens if not (t.isdigit() and len(t) >= 3)]

    # Mixed alphanumeric junk like "x4021" or "a12qx9" is a reference, not a name.
    tokens = [
        t for t in tokens
        if not (len(t) >= 4 and any(c.isdigit() for c in t) and any(c.isalpha() for c in t))
    ]

    while tokens and (tokens[-1] in _SUFFIXES or tokens[-1] in _STATES):
        tokens.pop()

    return " ".join(tokens)
