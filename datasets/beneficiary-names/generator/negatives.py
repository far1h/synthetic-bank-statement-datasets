"""Synthetic non-beneficiary rows (fees, interest, tax, cash) per layout.

The descriptions use the generic Indonesian keywords the system's category
rules look for; the gold label is "no beneficiary".
"""

from __future__ import annotations

from corpus import digits

A_NEGATIVE = (
    (["BIAYA ADM"], [], "DB"),
    (["BUNGA"], [], "CR"),
    (["PAJAK BUNGA"], [], "DB"),
    (["SETORAN TUNAI"], [], "CR"),
    (["TARIKAN TUNAI"], [], "DB"),
    (["DR KOREKSI BUNGA"], [], "DB"),
    (["TARIKAN ATM {dd}/{mm}"], [], "DB"),
)
B_NEGATIVE_EST = (
    "Biaya Administrasi Rekening", "Bunga Tabungan", "Pajak Bunga",
    "Setoran Tunai {dd}/{mm} {n6}",
)
B_NEGATIVE_CORP = ("BUNGA REKENING {n6}", "PAJAK BUNGA {n6}", "SETOR TUNAI {dd}/{mm} {n6}")


def make_negative(rng, index, bank):
    """Return one labeled non-beneficiary row for Bank A or Bank B."""
    dd, mm = f"{rng.randint(1, 28):02d}", f"{rng.randint(1, 12):02d}"
    fill = {"dd": dd, "mm": mm, "n6": digits(rng, 6)}
    if bank == "A":
        descs, details, direction = rng.choice(A_NEGATIVE)
        extra = {"layout_a": ([d.format(**fill) for d in descs], list(details))}
        fmt = "A-NEG"
    else:
        corporate = rng.random() < 0.5
        template = rng.choice(B_NEGATIVE_CORP if corporate else B_NEGATIVE_EST)
        extra = {"desc": template.format(**fill)}
        direction = "CR" if "Bunga" in template or "BUNGA R" in template or "etor" in template.lower() else "DB"
        fmt = "B-NEGC" if corporate else "B-NEGE"
    return {
        "id": index, "bank": bank, "format": fmt, "noise": "none", "direction": direction,
        "party_kind": "none", "true_name": "", "printed_name": "", "gold_span": "",
        "_extra": extra,
    }
