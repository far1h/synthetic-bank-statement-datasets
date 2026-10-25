"""Fictional counterparty bank names used inside transfer descriptions.

The source system's lists name real banks; these coined names keep the same
list lengths (33 prefixes, the last 7 short codes; 20 trailing names) so the
generator's draws keep their shape. None is a real bank.
"""

import random

_SYL = ["KA", "RO", "MI", "TA", "LU", "SE", "NA", "DI", "PO", "GA", "WE", "BI", "RU", "YO", "ZE"]


def _coined(n, syllables, seed):
    """Return n distinct coined words of the given syllable count."""
    rng, out = random.Random(seed), []
    while len(out) < n:
        w = "".join(rng.choice(_SYL) for _ in range(syllables))
        if w not in out:
            out.append(w)
    return out


BANK_PREFIXES = tuple(f"BANK {w}" for w in _coined(26, 3, 1)) + tuple(f"BX{w}" for w in _coined(7, 1, 2))
TRAILING_BANK_NAMES = tuple(f"BANK {a} {b}" for a, b in zip(_coined(20, 2, 3), _coined(20, 2, 4)))
