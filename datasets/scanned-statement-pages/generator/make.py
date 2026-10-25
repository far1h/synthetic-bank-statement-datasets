"""Write synthetic statement page images, clean and degraded, with a labels CSV.

Usage: python make.py <out dir> [--pages 10] [--seed 0]
Degradations: Gaussian blur (sigma 1-3 px), low resolution (50/33/25 % then
upscaled back) and horizontal motion blur (6-20 px). Pages are A4 at 150 dpi.
"""

import argparse
import csv
from pathlib import Path

import synth

DEGRADATIONS = [("clean", 0, lambda p: p)] + \
    [("gaussian", s, lambda p, s=s: synth.gaussian(p, s)) for s in (1, 2, 3)] + \
    [("lowres", f, lambda p, f=f: synth.lowres(p, f / 100)) for f in (50, 33, 25)] + \
    [("motion", n, lambda p, n=n: synth.motion(p, n)) for n in (6, 12, 20)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--pages", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    out = Path(a.out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(a.pages):
        seed = a.seed + i
        page = synth.statement_page(lines=20 + seed % 17, seed=seed)
        for kind, param, fn in DEGRADATIONS:
            name = f"page{seed:04d}_{kind}{param}.png"
            fn(page).save(out / "images" / name, optimize=True)
            rows.append({"file": f"images/{name}", "page_seed": seed, "degradation": kind, "parameter": param})
    with open(out / "labels.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "images")


if __name__ == "__main__":
    main()
