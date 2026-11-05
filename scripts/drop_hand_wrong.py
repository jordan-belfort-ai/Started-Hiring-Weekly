"""Drop flags a hand check found wrong (ventures/hiring-signals/hand-wrong.csv) from a started-hiring CSV before the page
renders, and print the "Removed by hand" sentence for started_page.py --removed. The daily record CSV is not touched.
Rows expire on their `until` date, so a re-opened team can come back. (5 Nov 22:00 UTC: the 19:45 hand removals were done
by editing the page's CSV, and the next render would have brought them back.)

    python -P tools/drop_hand_wrong.py IN.csv OUT.csv [--asof YYYY-MM-DD]   # prints the sentence, or nothing
"""
import argparse, csv, sys
from datetime import datetime, timezone
from pathlib import Path

HAND = Path(__file__).resolve().parents[2] / "hiring-signals" / "hand-wrong.csv"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--hand", default=str(HAND), help="the hand-wrong CSV (the Started-Hiring-Weekly repo keeps its own copy)")
    ap.add_argument("--asof", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    a = ap.parse_args()
    bad = {(r["ats"], r["board"], r["function"]): r for r in csv.DictReader(open(a.hand, encoding="utf-8")) if r["until"] >= a.asof}
    with open(a.inp, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f); rows = list(rd); fields = rd.fieldnames
    keep, gone = [], []
    for r in rows:
        h = bad.get((r["ats"], r["board"], r["function"]))
        (gone if h else keep).append(h or r)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(keep)
    if gone:
        n = len(gone)
        print(f"{n} row{'s' if n > 1 else ''} a hand check found wrong that the rules still flag ("
              + "; ".join(f"{g['company']}: {g['reason']} (checked {datetime.strptime(g['checked'], '%Y-%m-%d').strftime('%-d %b')})" for g in gone) + ")")


if __name__ == "__main__":
    main()
