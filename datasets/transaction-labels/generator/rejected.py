"""Synthetic statements with running balances and labelled rejected clearing.

Usage: python rejected.py <out.csv> [--seed 20261022] [--statements 300]
Each statement is one account with background rows plus injected events.
``rejected`` marks a clearing debit refused for insufficient funds;
``inward`` marks a deposited cheque returned unpaid; ``rtype`` names the event.
"""

import argparse
import csv

from synth import BANK_LABELS, CODE_BANK, MONTHS, Gen

OUT_TEMPLATES = ["KLIRING KELUAR CEK NO {c}", "SKN DEBIT BG {c}", "CEK {c} DITOLAK",
                 "PENOLAKAN BILYET GIRO {c}"]


class Statement:
    """Build one account's rows while tracking the running balance."""

    def __init__(self, g, sid, bank, name):
        self.g, self.rows, self.day = g, [], 1
        self.bank, self.acct = bank, f"{sid:06d}"
        self.bal = float(g.r.randrange(2_000_000, 40_000_000, 1000))
        self.name = name

    def add(self, desc, ttype, amount, rtype="", balance=None, cp=""):
        """Append a row; ``balance`` overrides the posted balance (refused item)."""
        if not self.rows and rtype == "pos_refused_listed":
            rtype = "pos_first_row"
        if balance is None:
            self.bal += amount if ttype == "CREDIT" else -amount
            balance = self.bal
        self.day = min(28, self.day + self.g.r.choice([0, 0, 1, 1, 2]))
        self.rows.append({
            "Date": f"2026-07-{self.day:02d}", "bank_name": self.name, "account_number": self.acct,
            "desc": f"{desc} {self.g.ref(6)}", "transaction_type": ttype, "amount": amount,
            "balance": balance, "beneficiary_name": cp, "rtype": rtype or "background",
            "bank": self.bank, "rejected": int(rtype.startswith("pos_")),
            "inward": int(rtype == "inward_bounce"),
        })

    def background(self):
        """One ordinary row; debits never exceed the balance."""
        g = self.g
        k = g.r.random()
        room = self.bal // 1000 * 1000
        if k < 0.35 or room < 200_000:
            self.add(f"TRF MBANK CR {g.person()}", "CREDIT", g.amount(100_000, 5_000_000))
        elif k < 0.55:
            self.add(f"TRF MBANK DB {g.person()}", "DEBIT", float(g.r.randrange(1000, int(room * 0.3), 1000)))
        elif k < 0.70:
            self.add(f"KLIRING KELUAR CEK NO {g.alnum(6)}", "DEBIT",
                     float(g.r.randrange(1000, int(room * 0.6), 1000)), "neg_clearing_covered")
        elif k < 0.80:
            self.add(f"PAYROLL {g.company()} {g.pick(MONTHS)}", "CREDIT", g.amount(3_000_000, 15_000_000))
        else:
            self.add("BIAYA ADM BULANAN", "DEBIT", 15_000.0)


def short(st, extra):
    """An amount that exceeds the current balance by ``extra``."""
    return float(max(st.bal, 0) // 1000 * 1000 + extra)


EVENTS = {}


def event(fn):
    EVENTS[fn.__name__] = fn
    return fn


@event
def pos_refused_listed(st, g):
    """Bank lists the refused cheque/BG; balance is unchanged."""
    desc = g.pick(OUT_TEMPLATES).format(c=g.alnum(6))
    st.add(desc, "DEBIT", short(st, g.amount(10_000, 5_000_000)), "pos_refused_listed", balance=st.bal)


@event
def pos_overdraft_reversed(st, g):
    """Debit posted below zero, then reversed by a rejection credit."""
    c, amt = g.alnum(6), short(st, g.amount(10_000, 5_000_000))
    st.add(f"KLIRING KELUAR CEK NO {c}", "DEBIT", amt, "pos_overdraft_reversed")
    st.add(f"KOREKSI TOLAKAN KLIRING {c}", "CREDIT", amt, "reversal_credit")


@event
def inward_bounce(st, g):
    """A deposited cheque comes back unpaid: credit then reversing debit."""
    c, amt = g.alnum(6), g.amount(500_000, 10_000_000)
    st.add(f"SETORAN KLIRING CEK {c}", "CREDIT", amt, "inward_credit")
    st.add(f"TOLAKAN KLIRING CEK {c}", "DEBIT", amt, "inward_bounce")


@event
def neg_overdraft_nonclearing(st, g):
    """A non-clearing debit that overdraws the account."""
    st.add(f"TARIK TUNAI ATM {g.ref(4)}", "DEBIT", short(st, g.amount(10_000, 2_000_000)),
           "neg_overdraft_nonclearing")


@event
def neg_cek_memo_overdraft(st, g):
    """Personal transfer whose memo says 'cek' and overdraws the account."""
    p = g.person()
    st.add(f"TRF MBANK DB cek mobil {p}", "DEBIT", short(st, g.amount(10_000, 2_000_000)),
           "neg_cek_memo_overdraft", cp=p)


@event
def neg_fee_low_balance(st, g):
    """A clearing or giro fee charged on a near-empty account."""
    if st.bal > 4000:
        st.add(f"TRF MBANK DB {g.person()}", "DEBIT", float(st.bal // 1000 * 1000 - 2000))
    fee = g.pick(["BIAYA KLIRING", "BIAYA ADM GIRO", "Clearing Fee INV"])
    st.add(fee, "DEBIT", float(max(st.bal, 0) // 1000 * 1000 + 5000), "neg_fee_low_balance")


def make_statement(g, sid):
    bank = g.pick(BANK_LABELS + [CODE_BANK])
    name = bank.upper()
    st = Statement(g, sid, bank, name)
    if g.r.random() < 0.15:
        st.bal = float(g.r.randrange(100_000, 900_000, 1000))
        st.add(g.pick(OUT_TEMPLATES).format(c=g.alnum(6)), "DEBIT",
               short(st, g.amount(10_000, 3_000_000)), "pos_first_row", balance=st.bal)
    for _ in range(g.r.randint(20, 40)):
        if g.r.random() < 0.12:
            EVENTS[g.pick(sorted(EVENTS))](st, g)
        else:
            st.background()
    return st.rows


def corpus(seed, statements):
    g = Gen(seed)
    rows = []
    for sid in range(statements):
        rows += make_statement(g, sid)
    for i, r in enumerate(rows):
        r["row_id"] = i
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=20261022)
    ap.add_argument("--statements", type=int, default=300)
    a = ap.parse_args()
    rows = corpus(a.seed, a.statements)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["row_id"] + [k for k in rows[0] if k != "row_id"])
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "rows,", sum(r["rejected"] for r in rows), "rejected,", sum(r["inward"] for r in rows), "inward")


if __name__ == "__main__":
    main()
