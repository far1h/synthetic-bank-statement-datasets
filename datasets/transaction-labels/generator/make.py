"""Write the labelled clearing / loan description corpus to CSV.

Usage: python make.py <out.csv> [--seed 20261020] [--reps 60]
The bank with its own clearing transaction codes ("Bank B") uses fictional
codes here; lender names are coined syllable words.
"""

import argparse
import csv

from synth import corpus

CODES = ["XCLR IN", "XCLR OUT", "XRTG IN", "XRTG OUT", "KLIRING", "SKNBI"]
FIELDS = ["id", "desc", "transaction_type", "amount", "label", "kind", "family", "hn_type", "bank", "counterparty"]


def coined_lender(g):
    """Return a factory of coined lender words."""
    return lambda: g.word(3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=20261020)
    ap.add_argument("--reps", type=int, default=60)
    a = ap.parse_args()
    rows = corpus(a.seed, a.reps, coined_lender, CODES)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows({k: r[k] for k in FIELDS} for r in rows)
    print(len(rows), "rows")


if __name__ == "__main__":
    main()
