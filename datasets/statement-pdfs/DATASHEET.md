# Datasheet: statement-pdfs

**Purpose.** Text-based statement PDFs from one fictional issuer ("Bank Z"), each in three versions: clean, handled in a benign way, and tampered by one of 11 editing operations. The set is meant for testing document-level forensic checks such as metadata, revisions, fonts and must-be-empty areas. It was built for the paper "Lightweight Document-Level Forensic Indicators for Tampered Bank Statement PDFs: What They Catch and What Evades Them".

**Composition.** For each statement there are two clean files: `G_NNN` (plain) and `T_NNN` (saved with Bank Z's fictional AES-256 profile). From each clean file:
- **Benign (`benign/`):** linearised by the issuer; decrypted from a user password (plain files only); pages copied by a split/merge tool; a reader's highlight saved incrementally.
- **Tampered (`tampered/`)**, where one transaction amount is changed in each:
  - `helv_incr`: Helvetica retype, incremental save;
  - `size_incr`: issuer font at 7.5 pt;
  - `matched_incr`: issuer font and size over a white box;
  - `digit_gutter`: a digit appended that runs into a gap;
  - `redact_full`: true redaction and a full rewrite;
  - `stamped_full`: the editor stamps ModDate and Producer;
  - `pypdf_pages`: retyped, then pages copied;
  - `spoof_incr`: stamped, then the issuer metadata restored;
  - `flatten` and `flatten_spoof`: rasterised to images, the second with the issuer metadata copied over;
  - `reencrypt`: redacted retype re-saved with the issuer profile (encrypted files only).

The default run has 40 statements, which gives 600 files. The sample has 1 statement and 30 files.

**Labels.** `manifest.csv` has one row per file, with these columns:
- `file`
- `base`: the clean file it came from
- `kind`: clean, benign or tampered
- `operation`
- for tampered files, `page`, `old_amount` and `new_amount`

In every retype except `redact_full`, the old amount is still stored in the file under the white box.

**Generation.**
- Code: `generator/make_corpus.py`, `issuer.py`, `tamper.py`, `make.py`.
- Rows are drawn with `random.Random(1000 + i)`, and each operation is seeded by its name and the statement index.
- Fonts are DejaVu Sans Mono, shipped with matplotlib.
- The holder is "SYNTHETIC CUSTOMER NNN".
- `repo_bridge.py` stands in for the source system's helpers. Its encryption profile is invented.
- To regenerate: `python make.py out --statements 40`.

**Known limits.**
- There is one issuer layout only.
- Real issuers differ in producers, fonts and encryption.
- Each operation edits one amount, so multi-field forgeries are not covered.
- A detector tuned on Bank Z must still be validated on real issuer files.

**Licence.** MIT (see `LICENSE` at the repository root).
