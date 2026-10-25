# Datasheet: transaction-labels

**Purpose.** Labelled Indonesian transaction descriptions for detecting clearing (SKNBI/LLG and RTGS), rejected clearing (a cheque or bilyet giro refused for insufficient funds), loan disbursements and loan repayments. Built for the paper "Rule-Based Detection of Clearing, Rejected Clearing and Loan Transactions in Indonesian Bank Statements".

**Files.**
- `descriptions.csv` has one description per row. Default run: 60 draws of every template, 4,320 rows.
  - Columns: `id, desc, transaction_type, amount, label, kind, family, hn_type, bank, counterparty`.
  - `label` is `CLEARING`, `LOAN_CREDIT`, `LOAN_DEBIT` or `NONE`.
  - `kind` is `POS` (plain positive), `HPOS` (a perturbed positive: typo, lowercase, glued digits, unusual separator) or `HNEG` (a hard negative: fees, BI-FAST, payroll, keyword inside a name, retail instalments).
  - `family` names the template.
- `rejected_clearing.csv` holds account statements with running balances. Default run: 300 statements; the sample has 100 statements and 3,125 rows.
  - `rejected=1` marks a clearing debit refused for insufficient funds, whether listed with an unchanged balance or posted and then reversed.
  - `inward=1` marks a deposited cheque returned unpaid.
  - `rtype` names the event; hard negatives include non-clearing overdrafts, a "cek" memo in a personal transfer, and fees on a near-empty account.

**Generation.**
- Seeded `random` generators: `generator/synth.py`, `generator/make.py`, `generator/rejected.py`.
- Every person, company and lender name is coined from random syllables. Counterparty banks are `BANK XA` to `BANK XH`.
- One layout (Bank B) marks clearing with its own transaction codes; the release uses fictional codes (`XCLR IN`, `XCLR OUT`, `XRTG IN`, `XRTG OUT`).
- Regenerate with `python make.py out.csv` and `python rejected.py out.csv`.

**Known limits.**
- Templates come from description shapes seen in statement parsers; they are not a sample of real traffic.
- Label noise is zero by construction, which real data will not have.
- Coined lender names are not screened against real lender registries, beyond being nonsense syllable strings.

**Licence.** MIT (see `LICENSE` at the repository root).
