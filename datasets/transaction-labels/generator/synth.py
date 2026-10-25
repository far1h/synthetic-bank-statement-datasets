"""Seeded synthetic transaction descriptions with labels.

Every name here is coined from random syllables, so no real person, company,
bank or lender appears. Labels: CLEARING, LOAN_CREDIT, LOAN_DEBIT or NONE.
``kind`` is POS (plain positive), HPOS (perturbed positive) or HNEG (hard
negative); ``family`` names the template family.
"""

import random

SYL = ["KA", "RO", "MI", "TA", "LU", "SE", "NA", "DI", "PO", "GA", "WE", "BI", "RU", "YO", "ZE"]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MEI", "JUN", "JUL", "AGU", "SEP", "OKT", "NOV", "DES"]
BANK_LABELS = ["Bank A", "Bank C", "Bank D"]
CODE_BANK = "Bank B"


class Gen:
    """Random helpers bound to one seeded generator."""

    def __init__(self, seed):
        self.r = random.Random(seed)

    def word(self, n=3):
        return "".join(self.r.choice(SYL) for _ in range(n))

    def person(self):
        return f"{self.word(3)} {self.word(3)}"

    def company(self):
        return f"PT {self.word(3)} {self.word(2)}"

    def bankx(self):
        return f"BANK X{self.r.choice('ABCDEFGH')}"

    def ref(self, n=8):
        return "".join(self.r.choice("0123456789") for _ in range(n))

    def alnum(self, n=4):
        return "".join(self.r.choice("ABCDEFHJKMNPQUVWXYZ0123456789") for _ in range(n))

    def pick(self, seq):
        return self.r.choice(seq)

    def amount(self, lo=50_000, hi=50_000_000):
        return float(self.r.randrange(lo, hi, 1000))


def _row(desc, ttype, label, kind, family, bank=None, cp="", hn=""):
    return {"desc": desc, "transaction_type": ttype, "label": label, "kind": kind,
            "family": family, "bank": bank, "counterparty": cp, "hn_type": hn or family}


def clearing_rows(g):
    """Clearing positives, perturbed positives and hard negatives."""
    b = lambda: g.pick(BANK_LABELS)
    p, co = g.person(), g.company()
    t = [
        _row(f"KLIRING MASUK {g.ref()} {p}", "CREDIT", "CLEARING", "POS", "kliring", b(), p),
        _row(f"KLIRING KELUAR {g.ref()} {p}", "DEBIT", "CLEARING", "POS", "kliring", b(), p),
        _row(f"TRF LLG {g.bankx()} {p}", "DEBIT", "CLEARING", "POS", "llg", b(), p),
        _row(f"LLG-{g.bankx()} {g.ref()}", "CREDIT", "CLEARING", "POS", "llg", b()),
        _row(f"SKN KREDIT {g.ref()} {p}", "CREDIT", "CLEARING", "POS", "skn", b(), p),
        _row(f"TRF SKN-BI {g.bankx()} {p}", "DEBIT", "CLEARING", "POS", "skn", b(), p),
        _row(f"TRF RTGS {g.bankx()} {g.ref()} {p}", "DEBIT", "CLEARING", "POS", "rtgs", b(), p),
        _row(f"INWARD RTGS {g.ref()} {co}", "CREDIT", "CLEARING", "POS", "rtgs", b(), co),
        _row(f"OUTWARD RTGS {g.ref()} {co}", "DEBIT", "CLEARING", "POS", "rtgs", b(), co),
        _row(f"SETORAN KLIRING CEK NO {g.alnum(6)}", "CREDIT", "CLEARING", "POS", "cheque_bg", b()),
        _row(f"KLIRING BG {g.alnum(6)} {co}", "DEBIT", "CLEARING", "POS", "cheque_bg", b(), co),
        _row(f"CLEARING CHQ {g.alnum(6)}", "CREDIT", "CLEARING", "POS", "cheque_bg", b()),
        _row(f"KLRG IN {g.ref()}", "CREDIT", "CLEARING", "POS", "klrg_abbrev", b()),
        _row(f"KLR {g.ref()} {p}", "DEBIT", "CLEARING", "POS", "klrg_abbrev", b(), p),
        _row(f"LALU LINTAS GIRO {g.ref()}", "CREDIT", "CLEARING", "POS", "llg", b()),
        _row(f"TOLAKAN KLIRING CEK {g.alnum(6)}", "CREDIT", "CLEARING", "POS", "cheque_bg", b()),
        # perturbed positives
        _row(f"kliring masuk {g.ref()} {p.lower()}", "CREDIT", "CLEARING", "HPOS", "lowercase", b(), p),
        _row(f"KLIRING/{g.ref()}/{p}", "DEBIT", "CLEARING", "HPOS", "separator", b(), p),
        _row(f"TRF SKNBI {g.bankx()} {p}", "DEBIT", "CLEARING", "HPOS", "sknbi_closed", b(), p),
        _row(f"RTGS{g.ref()} {co}", "CREDIT", "CLEARING", "HPOS", "glued_digits", b(), co),
        _row(f"{g.pick(['KLIRNG', 'KLRING', 'CLEARNG', 'KLIRIG'])} {g.ref()}", "CREDIT",
             "CLEARING", "HPOS", "typo", b()),
        _row(f"PENCAIRAN CEK KLIRING {g.alnum(6)}", "CREDIT", "CLEARING", "HPOS",
             "loan_word_in_clearing", b()),
        # hard negatives
        _row(g.pick(["BIAYA KLIRING", f"BIAYA RTGS {g.ref()}", f"CLEARING FEE {g.ref()}",
                     "BIAYA TRF SKN", "BIAYA LLG"]), "DEBIT", "NONE", "HNEG", "clearing_fee", b()),
        _row(f"DEBIT CARD SHOP* A-{g.alnum(3)}LLG{g.alnum(3)} {g.ref(16)}", "DEBIT",
             "NONE", "HNEG", "keyword_substring", b()),
        _row(f"REF {g.alnum(2)}RTGS{g.alnum(2)} {p}", "DEBIT", "NONE", "HNEG",
             "keyword_substring", b(), p),
        _row(f"BI-FAST DB {g.bankx()} {p}", "DEBIT", "NONE", "HNEG", "bifast", b(), p),
        _row(f"BI-FAST CR {g.ref(3)} {p}", "CREDIT", "NONE", "HNEG", "bifast", b(), p),
        _row(f"PAYROLL {co} {g.pick(MONTHS)}", "CREDIT", "NONE", "HNEG", "payroll", b(), co),
        _row(f"TOP UP EWALLET {g.word(2)} {g.ref(12)}", "DEBIT", "NONE", "HNEG", "ewallet_topup", b()),
        _row(f"JASA GIRO {g.pick(MONTHS)}", "CREDIT", "NONE", "HNEG", "jasa_giro", b()),
        _row(f"TRF MBANK CR {g.ref(4)}/{g.ref(6)} cek mobil {p}", "CREDIT",
             "NONE", "HNEG", "cek_memo", b(), p),
    ]
    return t


def code_bank_rows(g, codes):
    """Rows of the one bank that marks clearing with a transaction code.

    ``codes`` is that bank's code list read from the real module at run time:
    inward and outward clearing, inward and outward RTGS, then channel words.
    """
    inw, outw, inw_rtg, outw_rtg = codes[:4]
    p, co, bx = g.person(), g.company(), g.bankx()
    memo = f"INV {g.word(2)} {g.pick(MONTHS)}"
    return [
        _row(f"{co} - {g.ref(3)} TRF {inw} {bx} {g.ref(3)}/INV/{g.ref(4)}", "CREDIT",
             "CLEARING", "POS", "code_inward", CODE_BANK, co),
        _row(f"PEMBAYARAN KE REK {memo} CMS {outw} {p} Clearing Fee {memo}{g.ref(5)}",
             "DEBIT", "CLEARING", "POS", "code_outward", CODE_BANK, p),
        _row(f"{co} - {g.ref(3)} TRF {inw_rtg} {bx} {g.ref(6)}", "CREDIT", "CLEARING", "POS",
             "code_rtgs", CODE_BANK, co),
        _row(f"CMS {outw_rtg} {p} {memo}", "DEBIT", "CLEARING", "POS", "code_rtgs", CODE_BANK, p),
        _row(f"{g.pick(list(codes[4:]))} {g.ref()} {co}", "CREDIT", "CLEARING",
             "POS", "code_channel_word", CODE_BANK, co),
        _row(f"{co} - {g.ref(3)} TRF {inw_rtg}S {bx} {g.ref(6)}", "CREDIT", "CLEARING", "HPOS",
             "code_full_rtgs", CODE_BANK, co),
        _row(f"KLRG IN {g.ref()}", "CREDIT", "CLEARING", "HPOS", "code_generic_word", CODE_BANK),
        _row(f"Clearing Fee {memo} {memo} Clearing Fee {g.ref(5)}{memo}", "DEBIT", "NONE",
             "HNEG", "clearing_fee", CODE_BANK),
        _row(f"BIAYA KLIRING {g.ref()}", "DEBIT", "NONE", "HNEG", "clearing_fee", CODE_BANK),
        _row(f"PEMBAYARAN {memo} CMS INHOUSE KE {co} Transfer Fee {g.ref(5)}", "DEBIT",
             "NONE", "HNEG", "inhouse_transfer", CODE_BANK, co),
    ]


def loan_rows(g, fict_lender):
    """Loan positives, perturbed positives and hard negatives (fictional names)."""
    b = lambda: g.pick(BANK_LABELS + [CODE_BANK])
    p, co, lend = g.person(), g.company(), fict_lender()
    kur_name = f"{g.word(3)} {g.pick(['KUR', 'KTA', 'KPR'])}"
    t = [
        _row(f"PENCAIRAN {g.pick(['KREDIT', 'PINJAMAN', 'PLAFON'])} {g.ref()}", "CREDIT",
             "LOAN_CREDIT", "POS", "lc_pencairan", b()),
        _row(f"REALISASI KREDIT {g.ref()}", "CREDIT", "LOAN_CREDIT", "POS", "lc_realisasi", b()),
        _row(f"{g.pick(['PENCAIRAN KUR', 'DROPPING KMK', 'KTA'])} {g.ref()}", "CREDIT",
             "LOAN_CREDIT", "POS", "lc_product", b()),
        _row(f"{g.pick(['LOAN DISBURSEMENT', 'LOAN PROCEEDS'])} {g.ref()}", "CREDIT",
             "LOAN_CREDIT", "POS", "lc_english", b()),
        _row(f"TRANSFER DARI PT {lend} MULTI FINANCE", "CREDIT", "LOAN_CREDIT", "POS",
             "lc_generic_category", b(), f"PT {lend} MULTI FINANCE"),
        _row(f"PENCAIRAN GADAI {g.ref()}", "CREDIT", "LOAN_CREDIT", "POS", "lc_gadai", b()),
        _row(f"TRF RTGS {g.bankx()} PENCAIRAN KREDIT {g.ref()}", "CREDIT", "LOAN_CREDIT",
             "POS", "lc_via_clearing", b()),
        _row(f"TRANSFER DARI PT {lend} FINANCE", "CREDIT", "LOAN_CREDIT", "HPOS",
             "unregistered_lender", b(), f"PT {lend} FINANCE"),
        _row(f"{g.pick(['PENCAIRN KREDIT', 'PNCRN KRD', 'PENC KREDIT'])} {g.ref()}", "CREDIT",
             "LOAN_CREDIT", "HPOS", "typo", b()),
        _row(f"ANGSURAN {g.pick(['KREDIT', 'KE-3', 'PINJAMAN'])} {g.ref()}", "DEBIT",
             "LOAN_DEBIT", "POS", "ld_angsuran", b()),
        _row(f"{g.pick(['BAYAR PINJAMAN', 'PEMBAYARAN KREDIT', 'BAYAR-KREDIT'])} {g.ref()}",
             "DEBIT", "LOAN_DEBIT", "POS", "ld_bayar", b()),
        _row(f"AUTODEBET ANGSURAN KPR {g.ref()}", "DEBIT", "LOAN_DEBIT", "POS", "ld_kpr", b()),
        _row(f"{g.pick(['LOAN INST', 'INSTALLMENT 3/12', 'LOAN PAYMENT', 'REPAYMENT'])} {g.ref()}",
             "DEBIT", "LOAN_DEBIT", "POS", "ld_english", b()),
        _row(f"TAGIHAN PT {lend} MULTIFINANCE {g.ref()}", "DEBIT", "LOAN_DEBIT", "POS",
             "ld_generic_category", b()),
        _row(f"PELUNASAN GADAI {g.ref()}", "DEBIT", "LOAN_DEBIT", "POS", "ld_gadai", b()),
        _row(f"BUNGA PINJAMAN {g.ref()}", "DEBIT", "LOAN_DEBIT", "POS", "ld_interest", b()),
        _row(f"CICILAN KE-{g.r.randint(2, 11)} PT {lend} FINANCE", "DEBIT", "LOAN_DEBIT", "HPOS",
             "cicilan_unregistered", b(), f"PT {lend} FINANCE"),
        _row(f"{g.pick(['ANGSRAN KREDIT', 'ANGS KRD', 'ANGSURN PINJ'])} {g.ref()}", "DEBIT",
             "LOAN_DEBIT", "HPOS", "typo", b()),
        # hard negatives
        _row(g.pick([f"TAGIHAN LISTRIK {g.ref(12)}", f"BILL PAYMENT INTERNET {g.ref(10)}",
                     f"TGH TELEPON {g.ref(10)}"]), "DEBIT", "NONE", "HNEG", "billing", b()),
        _row(f"SETTLEMENT EDC {g.ref(10)}", "CREDIT", "NONE", "HNEG", "billing", b()),
        _row(g.pick([f"AUTODEBET PREMI ASURANSI {g.ref()}", f"AUTODEBET IURAN SEKOLAH {g.ref()}",
                     f"DEBET OTOMATIS TAGIHAN AIR {g.ref()}",
                     f"STANDING INSTRUCTION TABUNGAN RENCANA {g.ref()}"]), "DEBIT", "NONE", "HNEG",
             "autodebit_nonloan", b()),
        _row(f"TRF MBANK CR {g.ref(4)}/{g.ref(6)} PINJAMAN {p}", "CREDIT", "NONE",
             "HNEG", "personal_loan", b(), p),
        _row(f"TRF MBANK DB {g.ref(4)}/{g.ref(6)} BYR PINJAMAN {p}", "DEBIT", "NONE",
             "HNEG", "personal_loan", b(), p),
        _row(f"TRF MBANK CR {g.ref(4)}/{g.ref(6)} {kur_name}", "CREDIT", "NONE",
             "HNEG", "keyword_in_name", b(), kur_name),
        _row(f"TRF MBANK CR {g.ref(4)}/{g.ref(6)} {kur_name}", "CREDIT", "NONE",
             "HNEG", "keyword_in_name_no_cp", b(), ""),
        _row(f"{g.pick(['DISBURSEMENT TERMIN PROYEK', 'REALISASI ANGGARAN', 'DISBURSEMENT KOMISI'])} {co}",
             "CREDIT", "NONE", "HNEG", "generic_disbursement", b(), co),
        _row(f"PAYROLL {co} {g.pick(MONTHS)}", "CREDIT", "NONE", "HNEG", "payroll", b(), co),
        _row(f"GAJI {g.pick(MONTHS)} {co}", "CREDIT", "NONE", "HNEG", "payroll", b(), co),
        _row(f"TOP UP EWALLET {g.word(2)} {g.ref(12)}", "DEBIT", "NONE", "HNEG", "ewallet_topup", b()),
        _row(f"NOTA KREDIT {g.ref()}", "CREDIT", "NONE", "HNEG", "kredit_word", b()),
        _row(f"CICILAN {g.r.randint(1, 12)} {co} ELEKTRONIK", "DEBIT", "NONE", "HNEG",
             "retail_instalment", b(), co),
    ]
    return t


def corpus(seed, reps, fict_lender_factory, codes):
    """Return the labelled corpus: ``reps`` draws of every template."""
    g = Gen(seed)
    fict = fict_lender_factory(g)
    rows = []
    for _ in range(reps):
        rows += clearing_rows(g) + code_bank_rows(g, codes) + loan_rows(g, fict)
    for i, row in enumerate(rows):
        row["id"] = i
        row["amount"] = g.amount()
    return rows
