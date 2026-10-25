"""Synthetic labeled corpus of Indonesian bank-statement transfer rows.

Each row carries its own affiliated-party set (holder plus KK/akta members),
a printed counterparty (possibly noised), the description built from an
anonymized bank layout, the gold span and the gold affiliated label.
Layouts follow the formats documented in the system's code comments and
tests; every name and number is generated here.
"""

from __future__ import annotations

import random
import re
import string

from lexicon import (
    ABBREVIATIONS, ABBREVIABLE_PREFIX, BILLERS, COMPANY_FORMS, COMPANY_WORDS,
    DEGREE_SUFFIXES, GIVEN_FEMALE, GIVEN_MALE, HONORIFICS, REMARKS_LOWER,
    REMARKS_UPPER, SURNAMES, SYNTHETIC_BANK_QUALIFIERS,
)
from banks import BANK_PREFIXES, TRAILING_BANK_NAMES

FORMATS = (
    "A-EBK", "A-BIF", "A-CDM", "A-BILL",
    "B-BIC", "B-INH", "B-RTE", "B-EST",
    "C-ECH", "C-QUAL", "C-BFS", "C-RMT", "C-TRF",
)
NOISES = (
    "clean", "truncation", "missing_space", "honorific", "initials",
    "abbreviation", "reorder", "ocr", "lowercase", "linebreak",
)
FORMAT_WIDTH = {"A": 18, "B": 20, "C": 16}
OCR_CONFUSIONS = {
    "O": "0", "I": "1", "S": "5", "B": "8", "E": "F", "G": "6", "Z": "2",
    "A": "4", "U": "V", "N": "M", "M": "N", "H": "N", "L": "I", "D": "O",
}
HALLUCINATION_RATE = 0.12
ARTIFACT_RATE = 0.5


# ---------------------------------------------------------------- names
def person(rng, *, tokens=None, prefix=None, surname=None, given=None):
    """Return a synthetic person name as a token list."""
    tokens = tokens or rng.choice((2, 2, 3))
    pool = GIVEN_MALE + GIVEN_FEMALE
    words = [prefix] if prefix else []
    words.append(given or rng.choice(pool))
    while len(words) < tokens - 1:
        words.append(rng.choice(pool))
    if len(words) < tokens:
        words.append(surname or rng.choice(SURNAMES))
    return _unique(words, rng)


def company(rng, *, words=None, form=None):
    """Return a synthetic company name as a token list."""
    body = words or rng.sample(COMPANY_WORDS, rng.choice((2, 3)))
    return [form or rng.choice(COMPANY_FORMS), *body]


def _unique(words, rng):
    seen, out = set(), []
    for word in words:
        while word in seen:
            word = rng.choice(GIVEN_MALE + GIVEN_FEMALE)
        seen.add(word)
        out.append(word)
    return out


def needs_shape(noise):
    """Return name constraints a noise type needs to be expressible."""
    if noise == "truncation":
        return {"long": True}
    if noise == "abbreviation":
        return {"prefix": True}
    return {}


def shaped_person(rng, shape, **kwargs):
    """Return a person name satisfying ``shape``."""
    if shape.get("prefix"):
        kwargs.setdefault("prefix", rng.choice(ABBREVIABLE_PREFIX))
        kwargs.setdefault("tokens", 3)
    while True:
        words = person(rng, **kwargs)
        if not shape.get("long") or (len(words) >= 3 and len(" ".join(words)) > 21):
            return words
        kwargs["tokens"] = rng.choice((3, 4))


def shaped_company(rng, shape):
    while True:
        words = company(rng, words=rng.sample(COMPANY_WORDS, 3) if shape.get("long") else None)
        if not shape.get("long") or len(" ".join(words)) > 21:
            return words


# ---------------------------------------------------------------- cases
def build_case(rng, kind, shape):
    """Return holder kind, members [(name, role)] and a target index pool."""
    if kind == "person":
        holder = shaped_person(rng, shape)
        surname = holder[-1]
        members = [(holder, "Debitur")]
        spouse = shaped_person(rng, shape)
        members.append((spouse, rng.choice(("ISTRI", "SUAMI"))))
        for _ in range(rng.randint(1, 3)):
            share = rng.random() < 0.5
            child = shaped_person(rng, shape, surname=surname if share else None)
            members.append((child, "ANAK"))
        if rng.random() < 0.4:
            members.append((shaped_person(rng, shape), "ORANG TUA"))
    else:
        holder = shaped_company(rng, shape)
        members = [(holder, "Debitur Company")]
        for role in rng.sample(("Direktur", "Komisaris", "Pemegang Saham"), rng.randint(2, 3)):
            members.append((shaped_person(rng, shape), role))
        if rng.random() < 0.3:
            members.append((shaped_company(rng, shape), "Perusahaan Afiliasi"))
    return members


def hard_negative(rng, members, shape):
    """Return (tokens, neg_type) for a non-affiliated counterparty."""
    persons = [m for m, role in members if m[0] not in COMPANY_FORMS]
    companies = [m for m, role in members if m[0] in COMPANY_FORMS]
    draw = rng.random()
    if companies and draw < 0.35:
        base = rng.choice(companies)
        body = list(base[1:])
        body[-1] = rng.choice([w for w in COMPANY_WORDS if w not in body])
        form = rng.choice([f for f in COMPANY_FORMS if f != base[0]])
        return [form, *body], "company_shares_words"
    if not persons:
        return shaped_company(rng, shape), "stranger"
    base = rng.choice(persons)
    draw = rng.random()
    if draw < 0.35:
        words = shaped_person(rng, shape, surname=base[-1], tokens=len(base))
        if words[0] == base[0]:
            words[0] = rng.choice([g for g in GIVEN_MALE + GIVEN_FEMALE if g != base[0]])
        return words, "same_surname"
    if draw < 0.55:
        words = shaped_person(rng, shape, given=base[0], tokens=len(base))
        if words[-1] == base[-1]:
            words[-1] = rng.choice([s for s in SURNAMES if s != base[-1]])
        return words, "same_given"
    if draw < 0.8 and len(base) >= 3:
        words = list(base)
        words[-1] = rng.choice([s for s in SURNAMES if s not in base])
        return words, "shares_two_tokens"
    extra = rng.choice([s for s in SURNAMES if s not in base])
    return [*base, extra], "superset_extra_token"


# ---------------------------------------------------------------- noise
def apply_noise(rng, words, noise, cer=0.08):
    """Return the printed form of a name under one noise type."""
    words = list(words)
    is_company = words[0] in COMPANY_FORMS
    if noise in ("clean", "truncation"):
        return " ".join(words)
    if noise == "missing_space":
        index = rng.randrange(len(words) - 1)
        words[index : index + 2] = [words[index] + words[index + 1]]
        return " ".join(words)
    if noise == "honorific":
        if is_company or rng.random() < 0.8:
            title = rng.choice(HONORIFICS) if not is_company else rng.choice(("PT.", "TBK"))
            return f"{title} {' '.join(words)}" if title != "TBK" else f"{' '.join(words)} TBK"
        return f"{' '.join(words)}{rng.choice((' ', ', '))}{rng.choice(DEGREE_SUFFIXES)}"
    if noise == "initials":
        index = 1 if is_company else rng.randrange(len(words) - 1)
        words[index] = words[index][0] + rng.choice(("", "."))
        return " ".join(words)
    if noise == "abbreviation":
        if is_company:
            choice = rng.random()
            if choice < 0.35:
                return " ".join(words[1:] + [words[0]])
            if choice < 0.65:
                return f"{words[0]}.{' '.join(words[1:])}"
            return " ".join(words[1:])
        index = next((i for i, w in enumerate(words) if w in ABBREVIATIONS), None)
        if index is None:
            words[0] = words[0][0] + "."
            return " ".join(words)
        short = rng.choice(ABBREVIATIONS[words[index]])
        words[index] = short + ("." if len(short) == 1 and rng.random() < 0.5 else "")
        return " ".join(words)
    if noise == "reorder":
        if is_company:
            return " ".join(words[1:] + [words[0]])
        words = words[-1:] + words[:-1]
        return " ".join(words)
    if noise == "ocr":
        return ocr_noise(rng, " ".join(words), cer)
    if noise == "lowercase":
        text = " ".join(words)
        return text.lower() if rng.random() < 0.6 else text.title()
    if noise == "linebreak":
        return " ".join(words)
    raise ValueError(noise)


def ocr_noise(rng, text, cer):
    """Substitute or drop characters at character error rate ``cer`` (>=1 edit if cer>0)."""
    chars = list(text)
    positions = [i for i, c in enumerate(chars) if c.isalpha()]
    edits = max(1, round(cer * len(positions))) if cer > 0 else 0
    for index in rng.sample(positions, min(edits, len(positions))):
        char = chars[index]
        if rng.random() < 0.8 and char in OCR_CONFUSIONS:
            chars[index] = OCR_CONFUSIONS[char]
        elif rng.random() < 0.5:
            chars[index] = ""
        else:
            chars[index] = rng.choice(string.ascii_uppercase)
    return "".join(chars)


def line_break(rng, text):
    """Insert a separator inside one word, as a wrapped description does."""
    spans = [m for m in re.finditer(r"[A-Za-z]{4,}", text)]
    if not spans:
        return text, 0
    match = rng.choice(spans)
    cut = rng.randint(match.start() + 2, match.end() - 2)
    return text[:cut] + " " + text[cut:], cut


def cut_width(text, width):
    """Cut a printed field at the bank's column width."""
    return text[:width].rstrip()


# ---------------------------------------------------------------- layouts
def digits(rng, n):
    return "".join(rng.choice(string.digits) for _ in range(n))


def synthetic_bic(rng):
    """Return a BIC with a real-country shape and a synthetic institution code."""
    return "Q" + "".join(rng.choice(string.ascii_uppercase) for _ in range(3)) + "IDJA"


def render(rng, fmt, printed, direction, cut=True, truncate=False):
    """Return (printed span, direction, extra) for one layout."""
    group = fmt[0]
    width = FORMAT_WIDTH[group]
    if cut and (group == "A" or fmt == "B-RTE" or truncate):
        printed = cut_width(printed, width)
    extra = {}
    dd, mm = rng.randint(1, 28), rng.randint(1, 12)
    amount = f"{rng.randint(5, 9000) * 1000}.00"
    if fmt == "A-EBK":
        remarks = rng.sample(REMARKS_UPPER, rng.choice((0, 0, 1, 2)))
        details = [f"{dd:02d}{mm:02d}/FTSCY/WS950{rng.choice((31, 51, 71))}", amount, *remarks, printed]
        extra["layout_a"] = ([f"TRSF E-BANKING {direction}"], details)
    elif fmt == "A-BIF":
        code = digits(rng, 3)
        extra["layout_a"] = ([f"BI-FAST {direction}"], [f"BIF TRANSFER {'DR' if direction == 'CR' else 'KE'}", code, printed])
    elif fmt == "A-CDM":
        direction = "CR"
        extra["layout_a"] = (["SETORAN VIA CDM"], [f"{dd:02d}/{mm:02d} WSID:{rng.choice('ZXY')}{digits(rng, 4)}", printed])
    elif fmt == "A-BILL":
        direction = "DB"
        biller = rng.choice(BILLERS)
        extra["layout_a"] = (["BYR VIA E-BANKING"], [f"{dd:02d}/{mm:02d}  WSID9503100", f"{digits(rng, 4)} {biller}", f"{digits(rng, 11)} {printed}"])
        extra["gold_override"] = biller
    elif fmt == "B-BIC":
        bic = synthetic_bic(rng)
        note = rng.choice(("", "", " PEMBAYARAN KE REK " + rng.choice(REMARKS_UPPER)))
        extra["desc"] = f"2026{mm:02d}{dd:02d}{bic}010O0 {digits(rng, 9)} {bic}/{printed}{note} {digits(rng, 15)}"
    elif fmt == "B-INH":
        if direction == "DB":
            extra["desc"] = f"MCM InhouseTrf KE {printed} Transfer Fee EFN DPST TWH99102"
        else:
            remark = rng.choice(REMARKS_LOWER)
            extra["desc"] = f"{remark} MCM InhouseTrf DARI {printed} {remark}99101"
    elif fmt == "B-RTE":
        direction = "CR"
        extra["desc"] = f"{printed} - 0{digits(rng, 2)} {digits(rng, 5)}"
    elif fmt == "B-EST":
        kind = rng.choice(("BI Fast", "SKN", "RTGS", "Online"))
        bank = rng.choice(BANK_PREFIXES[:-7])
        if rng.random() < 0.2:
            bank = "Bank lain " + rng.choice(BANK_PREFIXES[-7:])
        word = "Ke" if direction == "DB" else "Dari"
        extra["desc"] = f"Transfer {kind} {word} {bank} {printed} {digits(rng, rng.choice((10, 13)))}"
    elif fmt == "C-ECH":
        purpose = " Lainnya" if rng.random() < 0.6 else ""
        word = "KE" if direction == "DB" else "DARI"
        extra["desc"] = f"TRF/PAY/TOP-UP ECHANNEL | PEMINDAHAN {word} {digits(rng, 13)} | 0000000000000000 | {printed}{purpose}"
        extra["artifact"] = printed + purpose if purpose else None
    elif fmt == "C-QUAL":
        qualifier = rng.choice(SYNTHETIC_BANK_QUALIFIERS + BANK_PREFIXES[-7:])
        extra["desc"] = f"Transfer {qualifier} - {printed}"
        extra["artifact"] = f"{qualifier} - {printed}"
    elif fmt == "C-BFS":
        direction = "CR"
        bic = synthetic_bic(rng)
        extra["desc"] = f"REMITTANCE CR - BIFAST 2026{mm:02d}{dd:02d}{bic}010O0{digits(rng, 10)} - BFS FR {bic} UN {printed}"
        extra["artifact"] = f"{bic} UN {printed}"
    elif fmt == "C-RMT":
        direction = "DB"
        bic = synthetic_bic(rng)
        extra["desc"] = f"TR TO REMITT {bic} {printed} {digits(rng, 15)} 26{mm:02d}{dd:02d}GM{digits(rng, 8)}"
        extra["artifact"] = f"{bic} {printed}"
    elif fmt == "C-TRF":
        bank = rng.choice(TRAILING_BANK_NAMES)
        word = "KE" if direction == "DB" else "DARI"
        remark = rng.choice(("Pembayaran Inv " + digits(rng, 2), "/LLG", " " + rng.choice(REMARKS_UPPER)))
        extra["desc"] = f"TRF {word} {printed} {bank}{remark}"
        extra["artifact"] = f"{printed} {bank}"
    return printed, direction, extra


# ---------------------------------------------------------------- rows
def make_row(rng, index, fmt, noise, *, cer=0.08, positive=None):
    """Generate one labeled transaction row."""
    shape = needs_shape(noise)
    kind = "company" if rng.random() < 0.3 else "person"
    members = build_case(rng, kind, shape)
    positive = (rng.random() < 0.5) if positive is None else positive
    if fmt == "A-BILL":
        positive = False
    neg_type = ""
    role = ""
    if positive:
        target, role = rng.choice(members)
    elif fmt == "A-BILL":
        target, neg_type = (members[0][0], "bill_holder") if rng.random() < 0.7 else (person(rng), "bill_other")
    elif rng.random() < 0.5:
        target = shaped_company(rng, shape) if rng.random() < 0.3 else shaped_person(rng, shape)
        neg_type = "stranger"
    else:
        target, neg_type = hard_negative(rng, members, shape)
    printed = apply_noise(rng, target, noise, cer=cer)
    direction = rng.choice(("DB", "CR"))
    truncate = noise == "truncation"
    printed_cut, direction, extra = render(rng, fmt, printed, direction, truncate=truncate)
    gold = printed_cut
    if noise == "linebreak":
        broken, _ = line_break(rng, printed_cut)
        if fmt[0] == "C" and rng.random() < 0.3:
            extra["desc_joined"] = True
        else:
            _, direction, extra = render(rng, fmt, broken, direction, cut=False)
        extra["joined"] = printed_cut
        extra["broken"] = broken
    gold = extra.get("gold_override", gold)
    return {
        "id": index,
        "bank": fmt[0],
        "format": fmt,
        "noise": noise,
        "cer": cer if noise == "ocr" else 0.0,
        "direction": direction,
        "party_kind": "company" if target[0] in COMPANY_FORMS else "person",
        "true_name": " ".join(target),
        "printed_name": printed_cut,
        "gold_span": gold,
        "is_affiliated": bool(positive),
        "neg_type": neg_type,
        "target_role": role,
        "members": [(" ".join(m), r) for m, r in members],
        "_extra": extra,
    }


def transcriber_candidate(rng, row):
    """Simulate the LLM transcriber's counterparty_text for a Bank C row.

    Mostly the printed span; sometimes keeps a layout artifact the verifier
    has to strip; sometimes hallucinates (reorders, completes or drops), which
    the verifier must reject or which leaves a partial name. Hallucination
    kinds: another party's name (the account holder's, printed elsewhere on
    the page), reordered tokens, a normalized/completed name, a dropped token.
    """
    extra = row["_extra"]
    printed = extra.get("joined", row["printed_name"])
    candidate, kind = printed, "literal"
    if "broken" in extra and extra["broken"] != printed and rng.random() < 0.3:
        broken = extra["broken"]
        cut = next(i for i, (a, b) in enumerate(zip(broken, printed)) if a != b)
        candidate, kind = broken[cut + 1 :], "second_line_only"
    elif extra.get("artifact") and rng.random() < ARTIFACT_RATE:
        candidate, kind = extra["artifact"], "layout_artifact"
        if "broken" in extra:
            candidate = candidate.replace(extra["broken"], printed)
    if rng.random() < HALLUCINATION_RATE:
        words = printed.split()
        choice = rng.random()
        if choice < 0.25:
            candidate, kind = row["members"][0][0], "halluc_other_party"
        elif choice < 0.45 and len(words) > 1:
            candidate, kind = " ".join(words[-1:] + words[:-1]), "halluc_reorder"
        elif choice < 0.75:
            candidate, kind = row["true_name"], "halluc_normalized"
            if candidate == printed:
                candidate, kind = printed + " " + random.Random(row["id"]).choice(SURNAMES), "halluc_completed"
        elif len(words) > 1:
            candidate, kind = " ".join(words[1:]), "halluc_dropped_token"
    if kind.startswith("halluc") and candidate == printed:
        kind = "literal"
    return candidate, kind
