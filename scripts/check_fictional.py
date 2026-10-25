"""Scan dataset files for terms that must not appear (real institutions, real people, real IDs).

Usage: python check_fictional.py <dir> [<dir> ...] [--terms f.txt ...] [--names f.txt] [--ids f.txt]
                                 [--image-dir <dir>]
--terms: one term per line, matched as whole words, case-insensitive.
--names: one full name per line, matched as a whole phrase after normalising spaces and case.
--ids:   one identifier per line (e.g. 16-digit numbers), matched exactly as digit runs.
--image-dir: images whose bytes must not occur in the datasets (compared by SHA-1).
The term lists stay outside this repository. Prints only counts and file names, never matches.
"""

import argparse
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

TEXT = {".csv", ".jsonl", ".json", ".py", ".md", ".txt"}
IMAGES = {".jpg", ".jpeg", ".png"}


def texts(root):
    """Yield (path, text) for every text file, PDF (text and metadata) and file name."""
    import pymupdf
    for p in sorted(Path(root).rglob("*")):
        if not p.is_file() or ".venv" in p.parts or ".git" in p.parts:
            continue
        yield p, p.name
        if p.suffix in TEXT:
            yield p, p.read_text(errors="ignore")
        elif p.suffix == ".pdf":
            try:
                doc = pymupdf.open(p)
            except Exception:
                continue
            yield p, " ".join(page.get_text() for page in doc) + " " + " ".join(str(v) for v in doc.metadata.values())


def load(path):
    return [l.strip() for l in open(path) if l.strip()] if path else []


def sha1(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--terms", nargs="*", default=[])
    ap.add_argument("--names")
    ap.add_argument("--ids")
    ap.add_argument("--image-dir")
    a = ap.parse_args()
    terms = [t for f in a.terms for t in load(f)]
    term_re = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(re.escape(t) for t in terms) + r")(?![A-Za-z0-9])", re.I) if terms else None
    names = {" ".join(n.upper().split()) for n in load(a.names) if len(n.split()) >= 2}
    ids = set(load(a.ids))
    hits, files = Counter(), Counter()
    for d in a.dirs:
        for p, text in texts(d):
            if term_re:
                for m in term_re.finditer(text):
                    hits["term:" + m.group(1).upper()] += 1
                    files[str(p)] += 1
            if names:
                norm = " ".join(re.sub(r"[^A-Za-z ]", " ", text).upper().split())
                padded = f" {norm} "
                n = sum(1 for name in names if f" {name} " in padded)
                if n:
                    hits["full_name_match"] += n
                    files[str(p)] += n
            if ids:
                n = sum(1 for run in re.findall(r"\d{16}", text) if run in ids)
                if n:
                    hits["id_match"] += n
                    files[str(p)] += n
    if a.image_dir:
        ref = {sha1(p) for p in Path(a.image_dir).rglob("*") if p.suffix.lower() in IMAGES}
        for d in a.dirs:
            for p in Path(d).rglob("*"):
                if p.suffix.lower() in IMAGES and sha1(p) in ref:
                    hits["image_match"] += 1
                    files[str(p)] += 1
    for k, v in sorted(hits.items()):
        print(f"{v:6d}  {k}")
    for f, v in files.most_common(20):
        print(f"{v:6d}  {f}")
    print("clean" if not hits else "FOUND", file=sys.stderr)
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
