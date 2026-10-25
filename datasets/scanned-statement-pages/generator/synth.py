"""Synthetic statement pages and degradations. No real documents are used."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

PAGE_SIZE = (1240, 1754)
ROW0 = 330
ROW_STEP = 38


def statement_page(lines=36, ink=20, seed=0, scale=1):
    """Draw a fake bank statement page with a header block, table rules and rows.

    scale=1 gives 1240x1754 (A4 at 150 dpi); scale=2 gives 2480x3508 (A4 at 300 dpi).
    """
    rng = np.random.default_rng(seed)
    page = Image.new("L", (PAGE_SIZE[0] * scale, PAGE_SIZE[1] * scale), 255)
    draw = ImageDraw.Draw(page)
    big = ImageFont.load_default(size=40 * scale)
    font = ImageFont.load_default(size=26 * scale)

    def text(x, y, s, f=font):
        draw.text((x * scale, y * scale), s, fill=ink, font=f)

    def rule(y, width):
        draw.line((90 * scale, y * scale, 1150 * scale, y * scale), fill=ink, width=width * scale)

    text(90, 70, "EXAMPLE BANK  -  ACCOUNT STATEMENT", big)
    text(90, 135, "Account 000-123-4567   Period 01/04 - 30/04")
    text(90, 175, "Customer: SAMPLE CUSTOMER   Currency: IDR")
    rule(240, 3)
    text(90, 260, "DATE   DESCRIPTION                              AMOUNT")
    rule(300, 2)
    for row in range(lines):
        ref = int(rng.integers(10000, 99999))
        text(90, ROW0 + row * ROW_STEP,
             f"0{row % 9 + 1}/04  TRSF E-BANKING DB  0404/FTSCY/WS{ref}  {250000 + row * 731:,}.00")
    rule(ROW0 + lines * ROW_STEP + 10, 2)
    return page


def gaussian(page, sigma):
    """Gaussian blur with standard deviation sigma pixels."""
    return page.filter(ImageFilter.GaussianBlur(sigma)) if sigma > 0 else page


def motion(page, length):
    """Horizontal motion blur: box average of the given length along x via cumsum."""
    if length <= 1:
        return page
    a = np.asarray(page, dtype=np.float64)
    pad = np.pad(a, ((0, 0), (length // 2, length - length // 2)), mode="edge")
    c = np.cumsum(pad, axis=1)
    c = np.concatenate([np.zeros((a.shape[0], 1)), c], axis=1)
    out = (c[:, length:] - c[:, :-length])[:, : a.shape[1]] / length
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def lowres(page, factor):
    """Downscale by factor (e.g. 0.25) with bilinear, then upscale back."""
    small = page.resize((round(page.width * factor), round(page.height * factor)), Image.Resampling.BILINEAR)
    return small.resize(page.size, Image.Resampling.BILINEAR)
