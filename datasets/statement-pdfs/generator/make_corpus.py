"""Generate seeded synthetic statements for the fictional issuer.

Writes corpus/clean/G_NNN.pdf (plain issuer file) and corpus/clean/T_NNN.pdf
(the same statement saved with the issuer's encryption profile).
"""

import random
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

import pikepdf
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import issuer as Z
from repo_bridge import issuer_encryption, set_profile_permissions

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "corpus" / "clean"
N_STATEMENTS = 40
WORDS = ("TRANSFER FROM", "TRANSFER TO", "CARD PURCHASE", "ATM WITHDRAWAL",
         "SALARY CREDIT", "BILL PAYMENT", "PHONE TOPUP", "ONLINE MARKETPLACE",
         "INTEREST", "ADMIN FEE", "CASH DEPOSIT", "INSURANCE PREMIUM")
PLACES = ("GROCERY 12", "CAFE 7", "SUPPLIER 3", "UTILITY CO", "SCHOOL FEES",
          "PHARMACY 4", "FUEL STATION", "HARDWARE 9", "MOBILE OP", "RENT")

for name, path in Z.FONT_FILES.items():
    pdfmetrics.registerFont(TTFont(name, str(path)))


def money(x: float) -> str:
    """Format an amount with thousands separators and two decimals."""
    return f"{x:,.2f}"


def make_rows(rng: random.Random, n: int, opening: float, start: datetime):
    """Return statement rows as (date, desc, ref, amount, dc, balance)."""
    rows, balance, day = [], opening, start
    for _ in range(n):
        day += timedelta(hours=rng.randint(4, 14))
        credit = rng.random() < 0.35
        amount = round(rng.choice((rng.uniform(1e4, 5e5), rng.uniform(5e5, 2e7))), -2)
        if not credit and amount > balance:
            credit = True
        balance += amount if credit else -amount
        desc = f"{rng.choice(WORDS)} {rng.choice(PLACES)}"[: Z.DESC_CHARS]
        ref = f"{rng.randint(10**9, 10**10 - 1)}"[: Z.REF_CHARS]
        rows.append((day.strftime("%d/%m/%Y"), desc, ref, amount, "CR" if credit else "DB", balance))
    return rows


def draw_header(c, page_no: int, n_pages: int, info: dict) -> None:
    """Draw the page header, the table header and the footer."""
    top = lambda y: Z.PAGE_H - y  # noqa: E731
    if page_no == 1:
        c.setFont(Z.FONT_BOLD, 12)
        c.drawString(30, top(50), "BANK Z")
        c.setFont(Z.FONT_BOLD, 10)
        c.drawString(30, top(68), "ACCOUNT STATEMENT")
        c.setFont(Z.FONT_REGULAR, 8)
        for i, line in enumerate((f"Account holder : {info['holder']}",
                                  f"Account number : {info['number']}",
                                  f"Period         : {info['period']}",
                                  f"Opening amount : {money(info['opening'])}")):
            c.drawString(30, top(92 + 12 * i), line)
    else:
        c.setFont(Z.FONT_REGULAR, 8)
        c.drawString(30, top(60), f"BANK Z ACCOUNT STATEMENT  {info['number']}")
    c.setFont(Z.FONT_BOLD, Z.TABLE_SIZE)
    y = top(Z.TABLE_HEADER_Y)
    c.drawString(Z.X_DATE, y, "DATE")
    c.drawString(Z.X_DESC, y, "DESCRIPTION")
    c.drawString(Z.X_REF, y, "REFERENCE")
    c.drawRightString(Z.R_AMOUNT, y, "AMOUNT")
    c.drawString(Z.X_DC, y, "DC")
    c.drawRightString(Z.R_BALANCE, y, "BALANCE")
    c.setLineWidth(0.5)
    c.line(28, y - 3, 562, y - 3)
    c.setFont(Z.FONT_REGULAR, 6)
    c.drawString(30, top(826), f"Page {page_no} of {n_pages}")


def draw_row(c, y_top: float, row) -> None:
    """Draw one transaction row in the issuer font and size."""
    date, desc, ref, amount, dc, balance = row
    y = Z.PAGE_H - y_top
    c.setFont(Z.FONT_REGULAR, Z.TABLE_SIZE)
    c.drawString(Z.X_DATE, y, date)
    c.drawString(Z.X_DESC, y, desc)
    c.drawString(Z.X_REF, y, ref)
    c.drawRightString(Z.R_AMOUNT, y, money(amount))
    c.drawString(Z.X_DC, y, dc)
    c.drawRightString(Z.R_BALANCE, y, money(balance))


def render(info: dict, rows) -> bytes:
    """Render the statement with ReportLab and return the PDF bytes."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(Z.PAGE_W, Z.PAGE_H))
    c.setAuthor(Z.AUTHOR)
    c.setCreator(Z.CREATOR)
    c.setTitle(f"Statement {info['number']}")
    pages = [rows[i:i + Z.ROWS_PER_PAGE] for i in range(0, len(rows), Z.ROWS_PER_PAGE)]
    if len(pages[-1]) > Z.ROWS_PER_PAGE - 3:
        pages.append([])
    for page_no, page_rows in enumerate(pages, start=1):
        draw_header(c, page_no, len(pages), info)
        for k, row in enumerate(page_rows):
            draw_row(c, Z.ROW0_Y + k * Z.ROW_STEP, row)
        if page_no == len(pages):
            y = Z.ROW0_Y + len(page_rows) * Z.ROW_STEP + 6
            c.setFont(Z.FONT_BOLD, Z.TABLE_SIZE)
            c.drawString(Z.X_DESC, Z.PAGE_H - y, Z.END_MARKER)
            c.setFont(Z.FONT_REGULAR, Z.TABLE_SIZE)
            c.drawString(Z.X_DESC, Z.PAGE_H - (y + 14), f"Closing amount : {money(rows[-1][5])}")
        c.showPage()
    c.save()
    return buf.getvalue()


def pdf_date(dt: datetime) -> str:
    """Return a PDF date string with a +07'00' offset."""
    return dt.strftime("D:%Y%m%d%H%M%S+07'00'")


def finish(raw: bytes, created: datetime, encrypt: bool) -> bytes:
    """Stamp issuer dates in one full save, optionally with the issuer encryption."""
    out = BytesIO()
    with pikepdf.open(BytesIO(raw)) as pdf:
        pdf.docinfo["/CreationDate"] = pdf_date(created)
        pdf.docinfo["/ModDate"] = pdf_date(created)
        pdf.save(out, encryption=issuer_encryption() if encrypt else False)
    return set_profile_permissions(out.getvalue()) if encrypt else out.getvalue()


def statement(i: int):
    """Return (info, rows, creation time) for statement i."""
    rng = random.Random(1000 + i)
    month = 1 + i % 9
    start = datetime(2026, month, 1, 8)
    info = {"holder": f"SYNTHETIC CUSTOMER {i:03d}", "number": f"{rng.randint(10**9, 10**10 - 1)}",
            "period": f"{start:%m/%Y}", "opening": round(rng.uniform(1e6, 5e7), -2)}
    rows = make_rows(rng, rng.randint(25, 190), info["opening"], start)
    created = datetime(2026, month + 1, 1, 2, rng.randint(0, 59), rng.randint(0, 59))
    return info, rows, created


def main() -> None:
    """Write the clean corpus."""
    CLEAN.mkdir(parents=True, exist_ok=True)
    for i in range(N_STATEMENTS):
        info, rows, created = statement(i)
        raw = render(info, rows)
        (CLEAN / f"G_{i:03d}.pdf").write_bytes(finish(raw, created, encrypt=False))
        (CLEAN / f"T_{i:03d}.pdf").write_bytes(finish(raw, created, encrypt=True))
    print(f"wrote {2 * N_STATEMENTS} clean files to {CLEAN}")


if __name__ == "__main__":
    main()
