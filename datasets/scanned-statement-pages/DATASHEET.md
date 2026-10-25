# Datasheet: scanned-statement-pages

**Purpose.** Images of statement pages, clean and degraded in a controlled way, for testing readability gates and blur metrics. The set was built for the paper "Directional Tile Sharpness: A Model-Free Readability Gate for Scanned Bank Statements".

**Composition.**
- Each page is a grey A4 page at 150 dpi (1240 x 1754) with a header block, table rules and 20 to 36 transaction rows.
- Each page comes in 10 versions:
  - clean;
  - Gaussian blur, sigma 1, 2 and 3 px;
  - low resolution, downscaled to 50, 33 and 25% and then upscaled back;
  - horizontal motion blur of 6, 12 and 20 px.
- The default run makes 10 pages (100 images). The sample has 2 pages (20 images).

**Labels.** `labels.csv`: `file, page_seed, degradation, parameter`. There are no readability labels; derive them for your own task, for example by running OCR on each image.

**Generation.**
- `generator/synth.py` draws each page with PIL's default font and applies each degradation analytically.
- Text is placeholder: "EXAMPLE BANK", "SAMPLE CUSTOMER" and fixed reference patterns.
- Regenerate with `python make.py out --pages 10`.

**Known limits.**
- One layout and one font.
- Real scans also carry skew, noise, stains, JPEG artefacts and faded ink, none of which are modelled here.

**Licence.** MIT (see `LICENSE` at the repository root).
