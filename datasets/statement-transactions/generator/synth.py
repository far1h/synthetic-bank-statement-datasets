"""Seeded synthetic bank-statement builder with injectable window-dressing patterns.

A statement is a list of events (one account, several months). Base activity
is ordinary business or household flow. Inject methods add one labelled
pattern each and return its record. ``rows()`` sorts the events, computes the
running balance and month-end interest, and returns the rows plus the
position of every labelled event. All names are generated from generic word
lists and are fictional.
"""

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

FIRST = ["BUDI", "AGUS", "SITI", "DEWI", "RINA", "ANDI", "HENDRA", "YULI", "WAHYU", "RUDI",
         "LINDA", "FAJAR", "ARIF", "NINA", "DIAN", "EKO", "SRI", "TONO", "MAYA", "IRWAN",
         "RATNA", "BAYU", "GITA", "HARI", "INDRA", "LUSI", "TEGUH", "WATI", "YOGA", "ZAINAL",
         "ADI", "AHMAD", "ALI", "ANITA", "ARI", "ASTUTI", "BAMBANG", "CITRA", "DANI", "DEDI",
         "DENI", "DONI", "ELLY", "ERNA", "FARIDA", "FITRI", "GALIH", "HADI", "HANA", "HERU",
         "IKA", "IMAM", "IWAN", "JOKO", "LILIS", "MARIA", "NOVI", "PUTRI", "RAHMAT", "RENI",
         "RIZKY", "SARI", "SLAMET", "SUSI", "TIKA", "TUTI", "UMAR", "VINA", "WULAN", "YANTO"]
LAST = ["SANTOSO", "WIJAYA", "PRATAMA", "KUSUMA", "HIDAYAT", "SAPUTRA", "SETIAWAN", "NUGROHO",
        "HALIM", "GUNAWAN", "SUSANTO", "RAHAYU", "PURNOMO", "SURYADI", "WIBOWO", "HARTONO",
        "KURNIAWAN", "SIREGAR", "NASUTION", "TANJUNG", "PANGESTU", "SIMANJUNTAK", "UTOMO",
        "ANGGRAINI", "BUDIMAN", "CAHYONO", "DARMAWAN", "EFENDI", "FIRMANSYAH", "HAKIM", "IRAWAN",
        "LUBIS", "MAHENDRA", "NAINGGOLAN", "PERMANA", "RAMADHAN", "SAMOSIR", "SITUMORANG",
        "SUHENDRA", "TAMBUNAN", "WINATA", "YULIANTO", "HARAHAP", "MARPAUNG", "SINAGA", "PARDEDE",
        "HUTAPEA", "GINTING", "SEMBIRING", "TARIGAN", "PURBA", "SARAGIH", "DAMANIK", "WIRAWAN",
        "PRASETYO", "SUGIARTO", "SETIADI", "ISKANDAR", "MULYADI", "SUPRIADI"]
CO_WORDS = ["SINAR", "MAKMUR", "JAYA", "ABADI", "SENTOSA", "LESTARI", "PRIMA", "UTAMA", "KARYA",
            "SUKSES", "GEMILANG", "CAHAYA", "BERKAH", "SEJAHTERA", "NUSANTARA", "PERKASA", "INTI",
            "TEKNIK", "LOGISTIK", "AGUNG", "ANUGRAH", "MULIA", "TUNGGAL", "DUTA", "SAMUDRA",
            "BINTANG", "PANGAN", "ENERGI", "KONSTRUKSI", "TEKSTIL", "MITRA", "SARANA", "ALAM",
            "BUANA", "CIPTA", "DAYA", "FAJAR", "GRAHA", "HARAPAN", "INDAH", "KENCANA", "LANGGENG",
            "MAJU", "NUSA", "PERSADA", "SAKTI", "SURYA", "TATA", "UNGGUL", "WAHANA", "WIRA",
            "BAHARI", "CEMERLANG", "DINAMIKA", "ELOK", "FORTUNA", "GRAFIKA", "HIJAU", "KREASI",
            "MEDIKA", "OPTIMA", "PERDANA", "RESTU", "SELARAS", "TIMUR", "BARAT", "ANDALAN",
            "BANGUN", "CITRA", "SEMESTA", "TERANG", "MAPAN", "PLASTIK", "KERAMIK"]
KEYWORDS = ["SETORAN MODAL", "TITIPAN", "PINJAMAN SEMENTARA", "DROPPING", "SUBSIDI", "RTGS DARI"]
MONTHS_ID = ["JAN", "FEB", "MAR", "APR", "MEI", "JUN", "JUL", "AGU", "SEP", "OKT", "NOV", "DES"]
EOD_START = {"Bank A": "21:00", "Bank B": "21:30", "Bank C": "22:00", "Bank D": "23:50", "Bank E": "21:00"}


def person(rng, parts=None):
    """A fictional person name of two or three words."""
    parts = parts or rng.choice([2, 3], p=[0.6, 0.4])
    words = [rng.choice(FIRST)] + list(rng.choice(LAST, size=parts - 1, replace=False))
    return " ".join(words)


def company(rng):
    """A fictional company name of three generic words."""
    return "PT " + " ".join(rng.choice(CO_WORDS, size=3, replace=False))


def account_no(rng):
    return "".join(str(d) for d in rng.integers(0, 10, size=10)).replace("0", "1", 1)


def truncate(name, width=18):
    """A counterparty cut to a fixed-width field."""
    return name[:width].rstrip()


def typo(rng, name):
    """Swap one letter inside the longest word."""
    words = name.split()
    i = max(range(len(words)), key=lambda k: len(words[k]))
    w = list(words[i])
    j = int(rng.integers(1, len(w) - 1))
    w[j] = "A" if w[j] != "A" else "E"
    words[i] = "".join(w)
    return " ".join(words)


@dataclass
class Event:
    dt: pd.Timestamp
    kind: str
    amount: float
    desc: str
    ben: str = ""
    inj: int = -1
    role: str = ""
    seq: int = 0


@dataclass
class Statement:
    """One synthetic account statement."""

    sid: str
    bank: str
    timed: bool
    holder_type: str
    level: float
    start: pd.Period
    n_months: int
    seed: int
    base: bool = True
    events: list = field(default_factory=list)
    injections: list = field(default_factory=list)

    def __post_init__(self):
        self.rng = np.random.default_rng(self.seed)
        rng = self.rng
        self.account = account_no(rng)
        self.holder = company(rng) if self.holder_type == "company" else person(rng)
        self.months = [self.start + i for i in range(self.n_months)]
        self.customers = [company(rng) if rng.random() < 0.6 else person(rng) for _ in range(int(rng.integers(12, 30)))]
        self.suppliers = [company(rng) if rng.random() < 0.7 else person(rng) for _ in range(int(rng.integers(8, 20)))]
        partners = [company(rng) for _ in range(2)]
        self.customers += partners
        self.suppliers += partners
        self.spouse = person(rng)
        self.members = [(self.holder, "Debitur"), (self.spouse, "Pasangan")]
        self.members += [(person(rng), rng.choice(["Anak", "Direktur", "Komisaris"])) for _ in range(int(rng.integers(1, 3)))]
        self.rate = float(rng.choice([0.0025, 0.005, 0.01]))
        self.n_inj = 0
        self._seq = 0
        if self.base:
            self._add_base()
        self.base_avg = {m: self._average_daily_balance(m) for m in self.months}

    def _average_daily_balance(self, month):
        """Mean end-of-day balance of a month over the events added so far."""
        events = sorted(self.events, key=lambda e: (e.dt, e.seq))
        balance, eod = self.level, {}
        for e in events:
            balance += e.amount if e.kind == "CREDIT" else -e.amount
            eod[e.dt.normalize()] = balance
        days = pd.date_range(month.start_time, month.end_time.normalize(), freq="D")
        if not eod:
            return self.level
        series = pd.Series(eod).sort_index()
        before = series[series.index < days[0]]
        start = before.iloc[-1] if len(before) else self.level
        return float(series.reindex(series.index.union(days)).ffill().fillna(start).reindex(days).mean())

    def avg(self, month):
        """Base average daily balance of the month: the scale for injected amounts."""
        return self.base_avg[month]

    # ---------- helpers ----------
    def add(self, dt, kind, amount, desc, ben="", inj=-1, role=""):
        self._seq += 1
        self.events.append(Event(pd.Timestamp(dt), kind, float(round(amount)), desc, ben, inj, role, self._seq))

    def day(self, month, day, hour=None, minute=None):
        """Timestamp on a day of a month; random daytime unless given."""
        hour = int(self.rng.integers(7, 20)) if hour is None else hour
        minute = int(self.rng.integers(0, 60)) if minute is None else minute
        second = int(self.rng.integers(0, 60))
        return month.start_time + pd.Timedelta(days=day - 1, hours=hour, minutes=minute, seconds=second)

    def month_end(self, month):
        return (month.end_time.normalize())

    def eom_day(self, month, offset):
        """Calendar day at month end + offset (offset 0 = last day)."""
        return self.month_end(month) + pd.Timedelta(days=offset)

    def new_inj(self, scenario, kind, **params):
        rec = {"inj": self.n_inj, "scenario": scenario, "kind": kind, **params}
        self.injections.append(rec)
        self.n_inj += 1
        return rec["inj"]

    def credit_desc(self, name, acct=None):
        prefix = self.rng.choice(["TRF DARI", "BI-FAST CR", "TRSF E-BANKING CR"])
        return f"{prefix} {name}" + (f" {acct}" if acct else "")

    def debit_desc(self, name, acct=None):
        prefix = self.rng.choice(["TRF KE", "BI-FAST DB", "TRSF E-BANKING DB"])
        return f"{prefix} {name}" + (f" {acct}" if acct else "")

    # ---------- base activity ----------
    def _add_base(self):
        rng, L = self.rng, self.level
        lam = float(rng.uniform(1.0, 3.0))
        balance = L
        for month in self.months:
            for d in range(1, month.days_in_month + 1):
                for _ in range(rng.poisson(lam)):
                    amt = min(L * rng.lognormal(math.log(0.06), 0.8), 0.8 * L)
                    name = rng.choice(self.customers)
                    desc = f"RTGS DARI {name}" if amt >= 1e8 and rng.random() < 0.3 else self.credit_desc(name)
                    if rng.random() < 0.15:
                        desc, name = "SETORAN TUNAI", ""
                    self.add(self.day(month, d), "CREDIT", amt, desc, name)
                    balance += round(amt)
                for _ in range(rng.poisson(lam)):
                    scale = min(max(balance / L, 0.3), 2.0)
                    amt = min(L * scale * rng.lognormal(math.log(0.06), 0.8), 0.5 * balance)
                    if amt < 1e4:
                        continue
                    r = rng.random()
                    if r < 0.6:
                        name = rng.choice(self.suppliers)
                        desc = self.debit_desc(name)
                    elif r < 0.8:
                        name, desc = "", rng.choice(["TARIK TUNAI ATM", "PEMBAYARAN PLN", "PEMBAYARAN TAGIHAN KARTU", "QRIS PEMBELIAN"])
                    else:
                        name = rng.choice(self.suppliers)
                        desc = f"PEMBAYARAN INV {int(rng.integers(100, 9999))} {name}"
                    self.add(self.day(month, d), "DEBIT", amt, desc, name)
                    balance -= round(amt)
                if balance < 0.2 * L:
                    top = L * rng.uniform(0.5, 1.0)
                    self.add(self.day(month, d, 20, 0), "CREDIT", top, "SETORAN TUNAI", "")
                    balance += round(top)
            pay_day = min(25, month.days_in_month)
            if self.holder_type == "company":
                self.add(self.day(month, pay_day, 9), "DEBIT", 0.25 * L, "PAYROLL GAJI KARYAWAN", "")
                balance -= round(0.25 * L)
            else:
                employer = getattr(self, "employer", None) or company(rng)
                self.employer = employer
                self.add(self.day(month, pay_day, 8), "CREDIT", 0.4 * L, f"GAJI {MONTHS_ID[month.month - 1]} {employer}", employer)
                balance += round(0.4 * L)

    # ---------- labelled patterns ----------
    def _return_name(self, sender, variant, acct):
        """Counterparty name and description for a debit back to the sender."""
        if variant == "exact":
            return sender, self.debit_desc(sender)
        if variant == "truncated":
            return truncate(sender), self.debit_desc(truncate(sender))
        if variant == "typo":
            return typo(self.rng, sender), self.debit_desc(typo(self.rng, sender))
        return "", self.debit_desc("", "0" + acct).replace("  ", " ")

    def _split(self, total, parts):
        """Split an amount into parts that sum to it."""
        w = self.rng.dirichlet(np.ones(parts) * 3)
        amounts = [round(total * x) for x in w[:-1]]
        return amounts + [round(total) - sum(amounts)]

    def transit(self, scenario, credit_dt, amount, ratio=1.0, delay_h=None, parts=1, variant="exact",
                to_other=False, keyword=None, sender=None, untimed_next_day=None, kind="pos", **extra):
        """Credit followed by debits that carry ratio*amount out again."""
        rng = self.rng
        sender = sender or (company(rng) if rng.random() < 0.5 else person(rng))
        acct = account_no(rng)
        inj = self.new_inj(scenario, kind, amount=round(amount), ratio=ratio, parts=parts, variant=variant,
                           to_other=to_other, credit_date=str(credit_dt.date()), **extra)
        desc = f"{keyword} {sender}" if keyword else self.credit_desc(sender, acct if variant == "account" else None)
        self.add(credit_dt, "CREDIT", amount, desc, sender, inj, "anchor")
        if delay_h is None:
            if untimed_next_day is None:
                untimed_next_day = bool(rng.random() < 0.6)
            if untimed_next_day:
                delay = pd.Timedelta(days=1) - pd.Timedelta(hours=credit_dt.hour) + pd.Timedelta(hours=int(rng.integers(8, 16)))
            else:
                delay = pd.Timedelta(minutes=int(rng.integers(5, max(6, (23 - credit_dt.hour) * 60))))
        else:
            delay = pd.Timedelta(hours=delay_h)
        out_dt = credit_dt + delay
        if to_other:
            other = company(rng)
            self.add(out_dt, "DEBIT", amount, self.debit_desc(other), other, inj, "leg")
            return inj
        for i, part in enumerate(self._split(amount * ratio, parts)):
            name, ddesc = self._return_name(sender, variant, acct)
            self.add(out_dt + pd.Timedelta(minutes=3 * i), "DEBIT", part, ddesc, name, inj, "leg")
        return inj

    def hold(self, scenario, credit_dt, amount, stay_days, desc=None, sender=None, kind="pos", spend=False, **extra):
        """Credit that stays some days, then leaves (or is spent if ``spend``)."""
        rng = self.rng
        sender = sender or (company(rng) if rng.random() < 0.5 else person(rng))
        inj = self.new_inj(scenario, kind, amount=round(amount), stay_days=stay_days, credit_date=str(credit_dt.date()), **extra)
        self.add(credit_dt, "CREDIT", amount, desc or self.credit_desc(sender), sender, inj, "anchor")
        if spend:
            chunks = self._split(amount * 0.9, int(rng.integers(4, 9)))
            for i, part in enumerate(chunks):
                name = rng.choice(self.suppliers)
                when = credit_dt + pd.Timedelta(days=stay_days + 2 * i, hours=int(rng.integers(1, 6)))
                self.add(when, "DEBIT", part, self.debit_desc(name), name, inj, "spend")
        else:
            when = credit_dt + pd.Timedelta(days=stay_days, hours=int(rng.integers(1, 6)))
            self.add(when, "DEBIT", amount, self.debit_desc(sender), sender, inj, "leg")
        return inj

    # ---------- output ----------
    def rows(self):
        """Sorted rows with running balance and month-end interest; label positions."""
        self._post_interest()
        events = sorted(self.events, key=lambda e: (e.dt, e.seq))
        balance = self.level
        rows = []
        for pos, e in enumerate(events):
            balance += e.amount if e.kind == "CREDIT" else -e.amount
            rows.append({
                "sid": self.sid, "pos": pos, "Date": e.dt.strftime("%Y-%m-%d"),
                "transaction_time": e.dt.strftime("%H:%M:%S") if self.timed else None,
                "bank": self.bank, "account_number": self.account, "desc": e.desc, "category": "",
                "beneficiary_name": e.ben, "amount": e.amount, "transaction_type": e.kind,
                "balance": float(round(balance, 2)), "inj": e.inj, "role": e.role,
            })
        return rows

    def _post_interest(self):
        """Post month-end interest on the average daily balance, then tax and fee."""
        if getattr(self, "_interest_done", False) or not self.base:
            return
        self._interest_done = True
        events = sorted(self.events, key=lambda e: (e.dt, e.seq))
        balance, eod = self.level, {}
        for e in events:
            balance += e.amount if e.kind == "CREDIT" else -e.amount
            eod[e.dt.normalize()] = balance
        series = pd.Series(eod).sort_index()
        for month in self.months:
            days = pd.date_range(month.start_time, month.end_time.normalize(), freq="D")
            daily = series.reindex(series.index.union(days)).ffill().fillna(self.level).reindex(days)
            interest = float(daily.mean()) * self.rate * month.days_in_month / 365
            me = self.month_end(month)
            self.add(me + pd.Timedelta(hours=23, minutes=55), "CREDIT", interest, "BUNGA", "")
            self.add(me + pd.Timedelta(hours=23, minutes=56), "DEBIT", 0.2 * interest, "PAJAK BUNGA", "")
            self.add(me + pd.Timedelta(hours=23, minutes=57), "DEBIT", 15_000, "BIAYA ADM", "")
