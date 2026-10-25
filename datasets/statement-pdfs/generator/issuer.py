"""Fictional issuer profile ("Bank Z") and its statement geometry.

Every value here is invented for the experiments. Coordinates are PDF points
with the origin at the top-left of an A4 page, as PyMuPDF reports them.
"""

from pathlib import Path

import matplotlib

BANK = "BANK Z"
GENERIC_TYPE = "BANK Z e-statement"
AUTHOR = "Bank Z"
CREATOR = "Bank Z Statement Generator"
PRODUCER_TOKEN = "ReportLab"

FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
FONT_REGULAR = "DejaVuSansMono"
FONT_BOLD = "DejaVuSansMono-Bold"
FONT_FILES = {FONT_REGULAR: FONT_DIR / "DejaVuSansMono.ttf",
              FONT_BOLD: FONT_DIR / "DejaVuSansMono-Bold.ttf"}
TABLE_SIZE = 7.0
CHAR_W = 0.602 * TABLE_SIZE

PAGE_W, PAGE_H = 595.28, 841.89
TABLE_HEADER_Y = 170.0
ROW0_Y = 186.0
ROW_STEP = 10.0
ROWS_PER_PAGE = 58

X_DATE, X_DESC, X_REF = 30.0, 80.0, 245.0
R_AMOUNT, X_DC, R_BALANCE = 420.0, 428.0, 560.0
DESC_CHARS, REF_CHARS = 36, 12

# Table area (top, left, bottom, right) read by the table-font check.
TABLE_AREA = (165, 25, 800, 575)
COLUMNS_X = (78, 240, 300, 424, 440)

# Areas that must stay empty: (top, left, bottom, right); right=None is page edge.
EMPTY_AREAS = (
    (0, 0, 842, 27),
    (0, 74, 842, 78),
    (0, 234, 842, 242),
    (0, 300, 842, 356),
    (0, 422, 842, 426),
    (0, 440, 842, 488),
    (0, 563, 842, None),
)
EMPTY_LABELS = (
    "Left margin", "Date | description", "Description | reference",
    "Reference | amount", "Amount | D/C", "D/C | balance", "Right margin",
)
START_MARKER = "REFERENCE"
START_GAP = 4.0
END_MARKER = "END OF STATEMENT"
DARK_THRESHOLD = 125
MIN_DARK_PIXELS = 5
