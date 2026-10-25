# Synthetic Indonesian Bank-Statement Datasets

Five seeded synthetic datasets for testing bank-statement parsing, fraud checks and transaction labelling without real customer data. Every name, number and bank is fictional; layouts appear as "Bank A", "Bank B" and so on.

| Dataset | What it contains | Sample |
|---|---|---|
| `statement-transactions` | Multi-month statements with labelled window-dressing patterns and hard negatives | 31 statements, 24,818 rows |
| `transaction-labels` | Descriptions labelled clearing / loan / none, plus statements with rejected clearing | 4,320 + 3,125 rows |
| `beneficiary-names` | Transfer descriptions with the printed counterparty-name span and affiliation labels | 1,905 rows |
| `statement-pdfs` | Clean, benign-handled and tampered statement PDFs from one fictional issuer | 30 PDFs |
| `scanned-statement-pages` | Statement page images, clean and blurred / low-resolution / motion-blurred | 20 images |

## File structure

```
datasets/<name>/
  DATASHEET.md     purpose, composition, labels, generation, limits
  generator/       seeded generator scripts (run from this folder)
  sample/          small committed sample
scripts/
  make_samples.sh      regenerate every sample
  check_fictional.py   scan outputs against private lists of real names, IDs and institutions
requirements.txt
LICENSE
```

## Regenerate

```
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
PY=$PWD/.venv/bin/python scripts/make_samples.sh
```

Each `DATASHEET.md` gives the command for the full-size set. Generators are deterministic for a given seed.

## Privacy screen

Names are built from common Indonesian names or random syllables, so a generated value can match a real person by chance. Every committed sample was scanned with `scripts/check_fictional.py` against private lists of real names, identity numbers and institutions kept outside this repository; matching records were removed, and each datasheet gives the count.

## Licence

MIT, see `LICENSE`.
