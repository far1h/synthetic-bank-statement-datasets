"""Tampering operations applied to clean statements, and benign handling cases.

Each operation takes the clean PDF bytes and a seeded random generator and
returns new PDF bytes. Content edits change one transaction amount.
"""

import random
import re
import tempfile
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

import fitz
import pikepdf
import pypdf

import issuer as Z
from repo_bridge import issuer_encryption, pu, set_profile_permissions

MONEY = re.compile(r"^\d{1,3}(,\d{3})*\.\d{2}$")
FONT_ALIAS = "IssuerCopy"


_TMP = tempfile.TemporaryDirectory()


def _open(pdf: bytes) -> fitz.Document:
    """Open PDF bytes with PyMuPDF from a temporary file, so incremental saves work."""
    path = Path(_TMP.name) / f"{uuid.uuid4().hex}.pdf"
    path.write_bytes(pdf)
    return fitz.open(path)


def _incr(doc) -> bytes:
    """Append the changes as an incremental update and return the whole file."""
    doc.saveIncr()
    path = Path(doc.name)
    doc.close()
    return path.read_bytes()


def _amount_spans(page) -> list[dict]:
    """Return table spans in the amount column."""
    return [s for b in page.get_text("dict")["blocks"] for l in b.get("lines", ())
            for s in l["spans"] if MONEY.match(s["text"].strip())
            and abs(s["bbox"][2] - Z.R_AMOUNT) < 1.5 and s["origin"][1] > Z.ROW0_Y - 5]


def _pick(doc, rng):
    """Pick one amount span on a random page that has transaction rows."""
    pages = [p for p in doc if _amount_spans(p)]
    page = rng.choice(pages)
    return page, rng.choice(_amount_spans(page))


def _raised(text: str) -> str:
    """Raise an amount by changing its leading digit (same printed width)."""
    return ("9" if text[0] != "9" else "8") + text[1:]


def _cover(page, span) -> None:
    """Paint a white box over the original glyphs, as a viewer's whiteout tool does."""
    r = fitz.Rect(span["bbox"])
    page.draw_rect(r + (-0.3, -0.3, 0.3, 0.3), color=None, fill=(1, 1, 1), overlay=True)


def _write(page, span, text, font="issuer", size=Z.TABLE_SIZE, right_align=True) -> None:
    """Insert replacement text at the span's baseline."""
    if font == "issuer":
        page.insert_font(fontname=FONT_ALIAS, fontfile=str(Z.FONT_FILES[Z.FONT_REGULAR]))
        name, width = FONT_ALIAS, fitz.Font(fontfile=str(Z.FONT_FILES[Z.FONT_REGULAR])).text_length(text, size)
    else:
        name, width = "helv", fitz.get_text_length(text, fontname="helv", fontsize=size)
    x = Z.R_AMOUNT - width if right_align else span["origin"][0]
    page.insert_text((x, span["origin"][1]), text, fontname=name, fontsize=size, color=(0, 0, 0))


def _edit(pdf: bytes, rng, font="issuer", size=Z.TABLE_SIZE, digit=False, redact=False):
    """Edit one amount in an opened copy; return the document."""
    doc = _open(pdf)
    page, span = _pick(doc, rng)
    old = span["text"].strip()
    if redact:
        page.add_redact_annot(fitz.Rect(span["bbox"]))
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
    else:
        _cover(page, span)
    if digit:
        _write(page, span, old + "0", font, size, right_align=False)
    else:
        _write(page, span, _raised(old), font, size)
    return doc


def _stamp(doc, rng, info) -> None:
    """Set ModDate and Producer as a desktop editor does on save."""
    edited = datetime.strptime(info["creationDate"][2:16], "%Y%m%d%H%M%S") + timedelta(
        days=rng.randint(3, 40), minutes=rng.randint(0, 600))
    doc.set_metadata({**info, "modDate": edited.strftime("D:%Y%m%d%H%M%S+07'00'"),
                      "producer": f"PyMuPDF {fitz.VersionBind}"})


def _full(doc) -> bytes:
    """Rewrite the whole file (no earlier revision kept)."""
    return doc.tobytes(garbage=3, deflate=True)


def _pypdf_pages(pdf: bytes) -> bytes:
    """Copy pages into a new pypdf writer, as page-extraction tools do."""
    w = pypdf.PdfWriter()
    for p in pypdf.PdfReader(BytesIO(pdf)).pages:
        w.add_page(p)
    out = BytesIO()
    w.write(out)
    return out.getvalue()


def _flatten(pdf: bytes, info=None) -> bytes:
    """Rasterise every page into a new image-only PDF (print-to-image)."""
    src, out = _open(pdf), fitz.open()
    for page in src:
        pix = page.get_pixmap(dpi=200)
        new = out.new_page(width=page.rect.width, height=page.rect.height)
        new.insert_image(new.rect, pixmap=pix)
    if info:
        out.set_metadata(info)
    return out.tobytes(garbage=3, deflate=True)


def _meta(pdf: bytes) -> dict:
    """Return the PyMuPDF metadata dict for set_metadata."""
    m = _open(pdf).metadata
    return {k: m[k] for k in ("title", "author", "subject", "keywords", "creator",
                              "producer", "creationDate", "modDate")}


def op_helv_incr(pdf, rng):
    """Retype one amount in Helvetica; incremental save; metadata untouched."""
    return _incr(_edit(pdf, rng, font="helv"))


def op_size_incr(pdf, rng):
    """Retype one amount in the issuer font at 7.5 pt; incremental save."""
    return _incr(_edit(pdf, rng, size=7.5))


def op_matched_incr(pdf, rng):
    """Retype one amount in the issuer font and size over a white box; incremental save."""
    return _incr(_edit(pdf, rng))


def op_digit_gutter(pdf, rng):
    """Append a digit to an amount without re-aligning it, so it runs into a gap."""
    return _incr(_edit(pdf, rng, digit=True))


def op_redact_full(pdf, rng):
    """Redact the original glyphs, retype in the issuer font, rewrite the file."""
    return _full(_edit(pdf, rng, redact=True))


def op_stamped_full(pdf, rng):
    """Matched retype, saved by an editor that stamps ModDate and Producer."""
    doc = _edit(pdf, rng)
    _stamp(doc, rng, _meta(pdf))
    return _full(doc)


def op_pypdf_pages(pdf, rng):
    """Matched retype, then pages copied into a new file with pypdf."""
    return _pypdf_pages(_full(_edit(pdf, rng)))


def op_spoof_incr(pdf, rng):
    """Stamped edit, then an incremental update that restores the issuer metadata."""
    stamped = op_stamped_full(pdf, rng)
    doc = _open(stamped)
    doc.set_metadata(_meta(pdf))
    return _incr(doc)


def op_flatten(pdf, rng):
    """Helvetica retype, then every page rasterised into an image-only PDF."""
    return _flatten(_full(_edit(pdf, rng, font="helv")))


def op_flatten_spoof(pdf, rng):
    """As flatten, with the issuer metadata copied onto the new file."""
    return _flatten(_full(_edit(pdf, rng, font="helv")), info=_meta(pdf))


def op_reencrypt(pdf, rng):
    """Redacted matched retype, re-saved with the issuer's encryption profile."""
    plain = op_redact_full(pdf, rng)
    out = BytesIO()
    with pikepdf.open(BytesIO(plain)) as p:
        p.save(out, encryption=issuer_encryption())
    return set_profile_permissions(out.getvalue())


OPS = {
    "helv_incr": op_helv_incr, "size_incr": op_size_incr, "matched_incr": op_matched_incr,
    "digit_gutter": op_digit_gutter, "redact_full": op_redact_full,
    "stamped_full": op_stamped_full, "pypdf_pages": op_pypdf_pages,
    "spoof_incr": op_spoof_incr, "flatten": op_flatten, "flatten_spoof": op_flatten_spoof,
    "reencrypt": op_reencrypt,
}
TABLE_ONLY = {"reencrypt"}


def benign_linearized(pdf, rng):
    """Issuer finishing pass: linearise and move ModDate minutes later, same day.

    An encrypted issuer file is encrypted again with the issuer profile.
    """
    m = _meta(pdf)
    created = datetime.strptime(m["creationDate"][2:16], "%Y%m%d%H%M%S")
    moved = (created + timedelta(minutes=rng.randint(1, 20))).strftime("D:%Y%m%d%H%M%S+07'00'")
    out = BytesIO()
    with pikepdf.open(BytesIO(pdf)) as p:
        encrypted = p.is_encrypted
        p.docinfo["/ModDate"] = moved
        p.save(out, linearize=True, encryption=issuer_encryption() if encrypted else False)
    return set_profile_permissions(out.getvalue()) if encrypted else out.getvalue()


def benign_decrypted(pdf, rng):
    """Issuer file with a user password, opened by the system's own decrypt step."""
    locked = BytesIO()
    with pikepdf.open(BytesIO(pdf)) as p:
        p.save(locked, encryption=pikepdf.Encryption(owner="o", user="1234", R=6))
    return pu.decrypt_pdf(locked.getvalue(), "1234")


def benign_pypdf_pages(pdf, rng):
    """No edit; pages copied into a new file with pypdf (split/merge tool)."""
    return _pypdf_pages(pdf)


def benign_highlight(pdf, rng):
    """No edit; a reader highlights one row and saves incrementally."""
    doc = _open(pdf)
    page, span = _pick(doc, rng)
    r = fitz.Rect(Z.X_DATE, span["bbox"][1], Z.R_BALANCE, span["bbox"][3])
    page.add_highlight_annot(r)
    return _incr(doc)


BENIGN = {"linearized": benign_linearized, "decrypted": benign_decrypted,
          "pypdf_pages_noedit": benign_pypdf_pages, "highlight": benign_highlight}
GENERIC_ONLY = {"decrypted"}


def seeded(name: str, index: int) -> random.Random:
    """Return a generator seeded by operation name and statement index."""
    return random.Random(f"{name}:{index}")
