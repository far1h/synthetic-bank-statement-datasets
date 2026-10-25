#!/usr/bin/env bash
# Regenerate every committed sample from its generator (run from the repository root).
# The committed samples were then screened against a private list of real names,
# identity numbers and institution names; records that matched by coincidence were removed
# (see each DATASHEET.md), so a fresh run can contain a few more records than the sample.
set -euo pipefail
PY=${PY:-python}
cd datasets/statement-transactions/generator && OUT_DIR=../sample N_STATEMENTS=40 $PY generate.py && cd -
cd datasets/transaction-labels/generator && $PY make.py ../sample/descriptions.csv && $PY rejected.py ../sample/rejected_clearing.csv --statements 100 && cd -
cd datasets/beneficiary-names/generator && $PY make.py ../sample/descriptions.jsonl --rows-per-cell 10 --oov-rows-per-cell 4 && cd -
cd datasets/statement-pdfs/generator && $PY make.py ../sample --statements 1 && cd -
cd datasets/scanned-statement-pages/generator && $PY make.py ../sample --pages 2 && cd -
