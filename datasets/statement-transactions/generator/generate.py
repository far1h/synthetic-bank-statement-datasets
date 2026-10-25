"""Generate the main synthetic corpus: statements with labelled positives and hard negatives.

Usage: OUT_DIR=<dir> SEED=<int> N_STATEMENTS=<int> python generate.py
Writes <OUT_DIR>/corpus.csv.gz (transactions), data/injections.csv (one row per
labelled pattern), data/statements.csv and data/members.csv.
"""

import csv
import gzip
import json

import numpy as np
import pandas as pd

from style import DATA
from synth import EOD_START, KEYWORDS, MONTHS_ID, Statement, company, typo

import os

SEED = int(os.environ.get("SEED", 20261020))
N_STATEMENTS = int(os.environ.get("N_STATEMENTS", 300))
BANKS = ["Bank A", "Bank B", "Bank C", "Bank D", "Bank E"]
POSITIVES = ["transit_mid", "transit_other", "transit_eod", "eom_transit", "eom_keyword",
             "spike", "affiliation", "monthly_pattern"]
NEGATIVES = ["invoice_eom", "abbrev_invoice_eom", "salary_moved", "receipt_stays_eom",
             "rtgs_receipt_eom", "family_transfer_eom", "large_mid_stays", "passthrough_nonexact",
             "partner_two_way"]


def mid_day(s, month):
    """A day well away from both month ends."""
    return int(s.rng.integers(5, month.days_in_month - 6))


def credit_time(s, dt_day, hour_lo=8, hour_hi=16):
    return dt_day + pd.Timedelta(hours=int(s.rng.integers(hour_lo, hour_hi)), minutes=int(s.rng.integers(0, 60)))


def transit_params(s):
    """Return ratio, parts and name variant for a return-to-sender transit."""
    rng = s.rng
    ratio = 1.0 if rng.random() < 0.4 else float(rng.uniform(0.955, 0.995))
    parts = int(rng.choice([1, 2, 3], p=[0.5, 0.3, 0.2]))
    variant = str(rng.choice(["exact", "truncated", "typo", "account"], p=[0.4, 0.2, 0.2, 0.2]))
    return ratio, parts, variant


def delay(s):
    """Hours until the outflow: under 24 h for timed statements, else None (T+0/T+1)."""
    return float(s.rng.uniform(0.5, 20)) if s.timed else None


def inject_positive(s, kind, months):
    rng = s.rng
    month = months[0]
    L = s.avg(month)
    if kind in ("transit_mid", "transit_other"):
        dt = credit_time(s, month.start_time + pd.Timedelta(days=mid_day(s, month) - 1))
        ratio, parts, variant = transit_params(s)
        if kind == "transit_other":
            ratio, parts, variant = 1.0, 1, "exact"
        s.transit(kind, dt, L * rng.uniform(1.5, 5), ratio, delay(s), parts, variant, to_other=kind == "transit_other")
    elif kind == "transit_eod":
        start_h, start_m = map(int, EOD_START[s.bank].split(":"))
        span = (23 * 60 + 59) - (start_h * 60 + start_m)
        day = month.start_time + pd.Timedelta(days=mid_day(s, month) - 1)
        dt = day + pd.Timedelta(minutes=start_h * 60 + start_m + int(rng.integers(0, span + 1)))
        out = day + pd.Timedelta(days=1, hours=int(rng.integers(6, 11)), minutes=int(rng.integers(0, 60)))
        ratio, parts, variant = transit_params(s)
        s.transit(kind, dt, L * rng.uniform(1.5, 5), ratio, (out - dt) / pd.Timedelta(hours=1), parts, variant)
    elif kind == "eom_transit":
        offset = int(rng.integers(-3, 2))
        dt = credit_time(s, s.eom_day(month, offset), 8, 20)
        ratio, parts, variant = transit_params(s)
        kw = str(rng.choice(KEYWORDS)) if rng.random() < 0.3 else None
        s.transit(kind, dt, L * rng.uniform(1.5, 5), ratio, delay(s), parts, variant, keyword=kw, offset=offset)
    elif kind == "eom_keyword":
        offset = int(rng.integers(-3, 2))
        kw = str(rng.choice(KEYWORDS))
        sender = company(rng)
        s.hold(kind, credit_time(s, s.eom_day(month, offset)), L * rng.uniform(0.5, 3), int(rng.integers(3, 7)),
               desc=f"{kw} {sender}", sender=sender, offset=offset, keyword=kw)
    elif kind == "spike":
        offset = int(rng.integers(-3, 2))
        s.hold(kind, credit_time(s, s.eom_day(month, offset)), max(L * rng.uniform(5, 10), 5e7),
               int(rng.integers(3, 7)), offset=offset)
    elif kind == "affiliation":
        offset = int(rng.integers(-3, 2))
        name, _role = s.members[int(rng.integers(1, len(s.members)))]
        variant = str(rng.choice(["exact", "titled", "cut", "typo"]))
        shown = {"exact": name, "titled": ("BPK " if rng.random() < 0.5 else "IBU ") + name,
                 "cut": name[:14].rstrip(), "typo": typo(rng, name)}[variant]
        s.hold(kind, credit_time(s, s.eom_day(month, offset)), L * rng.uniform(0.3, 2), int(rng.integers(3, 7)),
               desc=s.credit_desc(shown), sender=shown, offset=offset, variant=variant)
    elif kind == "monthly_pattern":
        sender = company(rng)
        ratio = 1.0 if rng.random() < 0.5 else float(rng.uniform(0.955, 0.995))
        first = None
        for m in months[:3]:
            dt = credit_time(s, m.start_time + pd.Timedelta(days=27), 8, 14)
            inj = s.transit(kind, dt, s.avg(m) * rng.uniform(0.2, 0.8), ratio, delay(s), 1, "exact",
                            sender=sender, untimed_next_day=True, group=first if first is not None else -1)
            first = inj if first is None else first
            s.injections[inj]["group"] = first


def inject_negative(s, kind):
    rng = s.rng
    month = s.months[int(rng.integers(0, len(s.months)))]
    L = s.avg(month)
    customer = str(rng.choice(s.customers))
    if kind == "salary_moved" and s.holder_type == "company":
        kind = "invoice_eom"
    offset = int(rng.integers(-3, 1))
    eom_dt = credit_time(s, s.eom_day(month, offset))
    if kind == "invoice_eom":
        desc = f"PEMBAYARAN INV/{int(rng.integers(100, 999))}/{month.year % 100} {customer}"
        s.hold(kind, eom_dt, L * rng.uniform(2, 6), 2, desc=desc, sender=customer, kind="neg", spend=True)
    elif kind == "abbrev_invoice_eom":
        desc = f"Pemb. Barang no inv {int(rng.integers(1, 99)):02d}-INV/ {customer}"
        s.hold(kind, eom_dt, L * rng.uniform(2, 6), 2, desc=desc, sender=customer, kind="neg", spend=True)
    elif kind == "salary_moved":
        desc = f"GAJI {MONTHS_ID[month.month - 1]} {s.employer}"
        inj = s.new_inj(kind, "neg", credit_date=str(eom_dt.date()))
        amount = L * rng.uniform(3, 5)
        s.add(eom_dt, "CREDIT", amount, desc, s.employer, inj, "anchor")
        s.add(eom_dt + pd.Timedelta(hours=20), "DEBIT", amount * 0.98, f"TRF KE {s.holder}", s.holder, inj, "leg")
    elif kind == "receipt_stays_eom":
        s.hold(kind, eom_dt, L * rng.uniform(4, 8), 3, desc=s.credit_desc(customer), sender=customer, kind="neg", spend=True)
    elif kind == "rtgs_receipt_eom":
        s.hold(kind, eom_dt, L * rng.uniform(0.5, 2), 3, desc=f"RTGS DARI {customer}", sender=customer, kind="neg", spend=True)
    elif kind == "family_transfer_eom":
        inj = s.new_inj(kind, "neg", credit_date=str(eom_dt.date()))
        s.add(eom_dt, "DEBIT", L * rng.uniform(0.05, 0.3), f"TRF KE {s.spouse}", s.spouse, inj, "anchor")
    elif kind == "large_mid_stays":
        dt = credit_time(s, month.start_time + pd.Timedelta(days=mid_day(s, month) - 1))
        s.hold(kind, dt, L * rng.uniform(3, 6), 2, desc=s.credit_desc(customer), sender=customer, kind="neg", spend=True)
    elif kind == "passthrough_nonexact":
        dt = credit_time(s, month.start_time + pd.Timedelta(days=mid_day(s, month) - 1))
        inj = s.new_inj(kind, "neg", credit_date=str(dt.date()))
        amount = L * rng.uniform(1.5, 3)
        supplier = str(rng.choice([x for x in s.suppliers if x not in s.customers]))
        customer = str(rng.choice([x for x in s.customers if x not in s.suppliers]))
        s.add(dt, "CREDIT", amount, s.credit_desc(customer), customer, inj, "anchor")
        s.add(dt + pd.Timedelta(hours=18), "DEBIT", amount * rng.uniform(0.96, 0.995), s.debit_desc(supplier), supplier, inj, "leg")
    elif kind == "partner_two_way":
        partner = s.customers[-1]
        dt = credit_time(s, month.start_time + pd.Timedelta(days=mid_day(s, month) - 1))
        inj = s.new_inj(kind, "neg", credit_date=str(dt.date()))
        amount = L * rng.uniform(1, 2)
        s.add(dt, "CREDIT", amount, s.credit_desc(partner), partner, inj, "anchor")
        s.add(dt + pd.Timedelta(days=int(rng.integers(3, 6))), "DEBIT", amount * rng.uniform(0.5, 0.8), s.debit_desc(partner), partner, inj, "leg")


def build_statement(i, rng):
    bank = BANKS[i % len(BANKS)]
    timed = bool(rng.random() < 0.5)
    holder_type = "company" if rng.random() < 0.6 else "individual"
    level = float(10 ** rng.uniform(np.log10(2e7), np.log10(2e9)))
    start = pd.Period("2024-01", "M") + int(rng.integers(0, 18))
    s = Statement(f"S{i:03d}", bank, timed, holder_type, level, start, 6, int(rng.integers(0, 2**31)))
    n_pos = int(rng.choice([0, 1, 2, 3], p=[0.35, 0.3, 0.2, 0.15]))
    free = list(range(6))
    for _ in range(n_pos):
        kinds = [k for k in POSITIVES if (k != "transit_eod" or timed)]
        kind = str(rng.choice(kinds))
        need = 3 if kind == "monthly_pattern" else 1
        starts = [m for m in free if all(m + j in free for j in range(need))]
        if not starts:
            continue
        m0 = int(rng.choice(starts))
        for j in range(need):
            free.remove(m0 + j)
        inject_positive(s, kind, [s.months[m0 + j] for j in range(need)])
    for _ in range(int(rng.integers(1, 4))):
        inject_negative(s, str(rng.choice(NEGATIVES)))
    return s


def main():
    rng = np.random.default_rng(SEED)
    corpus, injections, statements, members = [], [], [], []
    for i in range(N_STATEMENTS):
        s = build_statement(i, rng)
        rows = s.rows()
        corpus += rows
        by_inj = {}
        for r in rows:
            if r["inj"] >= 0:
                by_inj.setdefault(r["inj"], {"anchor": [], "leg": [], "spend": []})[r["role"]].append(r["pos"])
        for rec in s.injections:
            pos = by_inj.get(rec["inj"], {"anchor": [], "leg": [], "spend": []})
            injections.append({"sid": s.sid, **{k: rec[k] for k in ("inj", "scenario", "kind")},
                               "anchors": json.dumps(pos["anchor"]), "legs": json.dumps(pos["leg"]),
                               "spend": json.dumps(pos["spend"]),
                               "params": json.dumps({k: v for k, v in rec.items() if k not in ("inj", "scenario", "kind")})})
        statements.append({"sid": s.sid, "bank": s.bank, "timed": s.timed, "holder_type": s.holder_type,
                           "level": round(s.level), "start": str(s.start), "n_rows": len(rows), "rate": s.rate})
        members += [{"sid": s.sid, "name": n, "role": r} for n, r in s.members]
    write("corpus", corpus)
    write("injections", injections)
    write("statements", statements)
    write("members", members)
    print(len(statements), "statements,", len(corpus), "rows,", len(injections), "injections")


def write(name, rows):
    opener = gzip.open if name == "corpus" else open
    suffix = ".csv.gz" if name == "corpus" else ".csv"
    with opener(DATA / f"{name}{suffix}", "wt", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
