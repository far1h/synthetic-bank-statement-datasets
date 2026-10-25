"""Write the labelled beneficiary-name corpus (NER spans plus affiliation labels).

Usage: python make.py <out.jsonl> [--seed 20261021] [--rows-per-cell 40] [--oov-rows-per-cell 8]
One JSON object per transfer description. ``gold_span`` is the counterparty
name as printed (empty for rows with no beneficiary); ``span`` gives its
character offsets in ``description`` when it occurs there verbatim.
"""

import argparse
import json
import random

import corpus
from negatives import make_negative

NEGATIVE_RATE = 0.15
OOV = {
    "GIVEN_MALE": "ARIS DONI GUNTUR JAYADI KEVIN MARIO NANANG OKTA PANJI RANGGA SATRIA UMAR VINO WISNU YANUAR ZAKI".split(),
    "GIVEN_FEMALE": "AMELIA BELLA CINDY DELLA ELSA FANNY GITA HANA JIHAN KIKI MIRA NINA OLIVIA RENI SALSA TASYA VERA YOLA".split(),
    "SURNAMES": "ALAMSYAH BUDIMAN DARMAWAN EFFENDI FAUZI GINTING HUSIN ISKANDAR JUNAEDI LIMBONG MANURUNG NAINGGOLAN PANGARIBUAN RUSDI SEMBIRING TAMBUNAN".split(),
    "COMPANY_WORDS": "BAHARI CIPTA ELOK GRIYA HARAPAN KENCANA LANGGENG MANDALA PESONA RIMBA SUMBER TERANG WARNA".split(),
}


def description(row):
    """Return the printed description; layout A joins its description and detail lines."""
    extra = row["_extra"]
    if "layout_a" in extra:
        descs, details = extra["layout_a"]
        return f"{' '.join(descs)} {' '.join(details)}".strip()
    return extra["desc"]


def record(row, subset):
    """Return one output record."""
    desc = description(row)
    gold = row["gold_span"]
    start = desc.find(gold) if gold else -1
    return {
        "id": row["id"], "subset": subset, "layout": row["format"], "bank": f"Bank {row['bank']}",
        "noise": row["noise"], "direction": row["direction"], "party_kind": row["party_kind"],
        "description": desc, "gold_span": gold,
        "span": [start, start + len(gold)] if start >= 0 else None,
        "true_name": row["true_name"], "is_affiliated": bool(row.get("is_affiliated", False)),
        "neg_type": row.get("neg_type", ""), "target_role": row.get("target_role", ""),
        "members": [{"name": n, "role": r} for n, r in row.get("members", [])],
    }


def generate(rng, per_cell, subset, start):
    """Return positive and hard-negative rows for every layout and noise type."""
    rows = []
    for fmt in corpus.FORMATS:
        for noise in corpus.NOISES:
            for _ in range(per_cell // 2 if fmt == "A-BILL" else per_cell):
                rows.append(corpus.make_row(rng, start + len(rows), fmt, noise))
    for k in range(round(len(rows) * NEGATIVE_RATE)):
        rows.append(make_negative(rng, start + len(rows), "A" if k % 2 == 0 else "B"))
    return [record(r, subset) for r in rows]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=20261021)
    ap.add_argument("--rows-per-cell", type=int, default=40)
    ap.add_argument("--oov-rows-per-cell", type=int, default=8)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    rows = generate(rng, a.rows_per_cell, "main", 0)
    for key, value in OOV.items():
        setattr(corpus, key, value)
    rows += generate(rng, a.oov_rows_per_cell, "oov", len(rows))
    with open(a.out, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(len(rows), "rows,", sum(r["span"] is not None for r in rows), "with an exact span")


if __name__ == "__main__":
    main()
