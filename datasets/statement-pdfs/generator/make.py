"""Write clean, benign-handled and tampered statement PDFs for the fictional Bank Z.

Usage: python make.py <out dir> [--statements 40]
Clean files come as G_NNN (plain) and T_NNN (Bank Z's fictional encryption).
Each tampering operation edits one transaction amount; manifest.csv records
the base file, the operation and the edited amount.
"""

import argparse
import csv
from pathlib import Path

import make_corpus as M
import tamper as T

EDITS = {}


def _recording_edit(original):
    """Wrap tamper._edit so the edited page and amounts are recorded.

    The amount is chosen by the first draws of ``rng``; the same draws are
    replayed on a probe copy before the real edit.
    """
    def wrapped(pdf, rng, **kw):
        state = rng.getstate()
        page, span = T._pick(T._open(pdf), rng)
        rng.setstate(state)
        old = span["text"].strip()
        EDITS["last"] = {"page": page.number + 1, "old_amount": old,
                         "new_amount": old + "0" if kw.get("digit") else T._raised(old)}
        return original(pdf, rng, **kw)
    return wrapped


T._edit = _recording_edit(T._edit)


def write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--statements", type=int, default=40)
    a = ap.parse_args()
    out, rows = Path(a.out), []
    for i in range(a.statements):
        info, tx, created = M.statement(i)
        raw = M.render(info, tx)
        for prefix, encrypt in (("G", False), ("T", True)):
            base = out / "clean" / f"{prefix}_{i:03d}.pdf"
            write(base, M.finish(raw, created, encrypt=encrypt))
            rows.append({"file": str(base.relative_to(out)), "base": base.name, "kind": "clean", "operation": ""})
            cases = [("benign", n, f) for n, f in T.BENIGN.items() if not (encrypt and n in T.GENERIC_ONLY)]
            cases += [("tampered", n, f) for n, f in T.OPS.items() if encrypt or n not in T.TABLE_ONLY]
            for kind, name, fn in cases:
                EDITS.clear()
                path = out / kind / name / f"{prefix}_{i:03d}.pdf"
                write(path, fn(base.read_bytes(), T.seeded(name, i)))
                rows.append({"file": str(path.relative_to(out)), "base": base.name, "kind": kind,
                             "operation": name, **EDITS.get("last", {})})
    with open(out / "manifest.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "base", "kind", "operation", "page", "old_amount", "new_amount"])
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "files")


if __name__ == "__main__":
    main()
