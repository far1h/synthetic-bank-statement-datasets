# Datasheet: beneficiary-names

**Purpose.** Indonesian transfer descriptions labelled with the counterparty (beneficiary) name as printed. Use it for name extraction (NER) and for affiliated-party matching: does the counterparty belong to the applicant's family or company? Built for the papers "Extracting Beneficiary Names from Indonesian Bank Transaction Descriptions: System Rules, spaCy, IndoBERT and GLiNER2 Compared" and "Rule-Based Affiliated-Party Name Extraction and Matching for Indonesian Bank Statement Transactions".

**Composition.**
- **Layouts:** 13 description formats from three anonymised layouts (Bank A, B, C), including e-banking, BI-FAST, cash deposit, bill payment, in-house, RTGS, e-statement and remittance formats.
- **Noise types:** 10: clean, truncation, missing space, honorific, initials, abbreviation, reordered tokens, OCR confusions, lowercase, line break.
- **Negatives:** 15% non-beneficiary rows: fees, interest, tax, cash.
- **OOV subset:** an `oov` subset built from name tokens absent from the main lexicon.
- **Size:** the default run has 40 rows per (format, noise) cell plus 8 per OOV cell. The sample has 1,905 rows.

**Fields (JSON lines).**
- `description`: the printed text.
- `gold_span`: the name as printed, or empty.
- `span`: character offsets of `gold_span` in `description`, or null when the printed name is not a verbatim substring (for example after a line-break join).
- `true_name`: the undamaged name.
- `is_affiliated`, `target_role`, `members`: the applicant's family-card or company members, with roles.
- `neg_type`: why a non-affiliated row is negative (stranger, hard negative, bill).
- `layout`, `bank`, `noise`, `direction`, `party_kind`.

**Generation.**
- Seeded `random` generator: `generator/corpus.py`, `generator/lexicon.py`, `generator/negatives.py`, `generator/make.py`.
- Names are drawn from generic given-name, surname and company-word lists.
- Counterparty bank names inside descriptions are coined (`generator/banks.py`), not real banks.
- Regenerate with `python make.py out.jsonl`.

**Known limits.**
- The layouts imitate common Indonesian statement formats under anonymised labels.
- Name distributions are uniform over the lexicon, unlike real populations.
- 2-word names can coincide with real people by chance. The committed sample was screened against a private reference list and 108 rows were removed.

**Licence.** MIT (see `LICENSE` at the repository root).
