# Datasheet: statement-transactions

**Purpose.** Multi-month bank-statement transactions with labelled window-dressing patterns and hard negatives, for testing detectors that tell a temporary balance boost from genuine income. Built for the paper "Detecting Window Dressing in Indonesian Bank Statements: A Rule-Based Engine and Its Measured Limits".

**Composition.** One statement is one account over 6 months, from one of five anonymised layouts (Bank A to Bank E), with or without transaction times. The default run gives 300 statements, about 230k rows and about 1,000 labelled patterns. The sample has 31 statements and 24,818 rows.

**Labels.**
- Positives (`kind=pos`):
  - `transit_mid`, `transit_other`, `transit_eod`: money in, then most of it back out within 24 h;
  - `eom_transit`, `eom_keyword`: the same around month end, the second with a deposit word such as SETORAN MODAL or TITIPAN;
  - `spike`: a large month-end credit that stays a few days;
  - `affiliation`: a month-end credit from a family member of the holder;
  - `monthly_pattern`: a transit repeated over three months.
- Hard negatives (`kind=neg`):
  - `invoice_eom`, `abbrev_invoice_eom`: invoice payments at month end;
  - `salary_moved`: salary moved to the holder's own account;
  - `receipt_stays_eom`, `rtgs_receipt_eom`: large month-end receipts that stay;
  - `family_transfer_eom`: a transfer to the spouse at month end;
  - `large_mid_stays`: a large receipt mid-month that stays;
  - `passthrough_nonexact`: a receipt passed on to a supplier at an inexact amount;
  - `partner_two_way`: two-way flows with one business partner.

**Files.**
- `corpus.csv.gz`: one row per transaction. Columns: `sid, pos, Date, transaction_time, bank, account_number, desc, category, beneficiary_name, amount, transaction_type, balance, inj, role`. `inj` is the pattern id, or -1. `role` is `anchor` (the triggering credit), `leg` (its outflows) or `spend`.
- `injections.csv`: one row per pattern. Gives the row positions of anchors, legs and spends, and the pattern parameters as JSON.
- `statements.csv`: layout, timed flag, holder type, balance level, start month and monthly interest rate.
- `members.csv`: the holder's affiliated parties (KK members or company officers) with their roles.

**Generation.**
- Seeded NumPy generator (`generator/synth.py`, `generator/generate.py`).
- Background activity is ordinary business or household flow.
- Each pattern is injected by its own method, and running balances and month-end interest are recomputed afterwards.
- Names come from generic Indonesian word lists.
- Regenerate with `OUT_DIR=out SEED=20261020 N_STATEMENTS=300 python generate.py`; the default seed reproduces the paper's corpus exactly.

**Known limits.**
- Patterns follow the authors' reading of window dressing; they are not drawn from confirmed cases.
- Real statements mix patterns more freely and have messier descriptions.
- End-of-day cut-off times are per-layout assumptions.
- 2-word person names are combinations of common given names and surnames, so a few coincide with real people by chance. The committed sample was screened against a private reference list and 9 statements were removed, so a fresh run of the sample command contains them.

**Licence.** MIT (see `LICENSE` at the repository root).
