"""Employers that started hiring for a job function, read from posting dates in one index build (5 Nov, cloud).

The snapshot-based list (tools/function_movers.py) needs 7 days of per-function history (12 Nov). This is the
early version: in one build, a board "started" a function when 3+ of its open jobs in that function were posted in
the last --days days and none of its open jobs in that function is older, while the board holds --min-older+ older
jobs in other functions (an employer already hiring, not a new board). Only ATSs whose posting dates are first-publish
dates (Workday and SmartRecruiters re-date reposts, so they're left out), and boards whose recent share is over
--max-recent-share are skipped (a whole board re-posted or new to the ATS). Weak spot: a closed role is invisible,
so "no older open job in the function" is not "no hiring in that function for 90 days".

    python -P tools/started_by_postdate.py [ROWS.json.gz] [--days 7] [--min-new 3] [--csv out.csv] [--sample 50]
ROWS: {"builtAt", "rows": [[ats, board, company, title, publishedAt, url], ...]} (an index download). Without ROWS it
reads the live index from the store (~1 min) and, with --daily, writes data/hiring/started/<build date>.csv against the
snapshot of two days before: the post-build routine (since 5 Nov), so each flag can later be checked for whether the
employer kept hiring in that function (the number a buyer of the trigger would ask for first).
"""
import argparse, csv, gzip, json, random, re, sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "actors" / "ats-jobs"))
sys.path.insert(1, str(Path(__file__).resolve().parent))  # the GitHub repo copy keeps src/ next to the script
from src.functions import FUNC_RE, matches  # noqa: E402
from src.geo import country_codes  # noqa: E402
from collections import Counter

_dp = Path(__file__).resolve().parent.parent / "actors" / "ats-jobs" / "src" / "company_domains.json"
if not _dp.exists():  # the GitHub repo copy keeps src/ next to the script
    _dp = Path(__file__).resolve().parent / "src" / "company_domains.json"
DOMAINS = json.loads(_dp.read_text()) if _dp.exists() else {}
# 5 Nov 14:00: Trading212's and Jumia's graduate cohorts were flagged as new ops teams. Early-career titles don't count
# toward the 3 (or 2) new roles; they still count as older openings.
EARLY = re.compile(r"\b(graduate|graduates|intern|interns|internship|apprentice|apprenticeship|trainee|trainees|werkstudent|"
                   r"working student|praktikum|praktikant|praktikantin|stagiaire|stage|summer analyst|co-op)\b", re.I)
# 5 Nov 15:00 watchlist check: founder roles at a studio are not a team, and one job posted in two cities, levels or
# genders is one role. role_key() collapses those so --min-distinct counts roles, not postings.
FOUNDER = re.compile(r"\b(?:co-?founder|cofounder)\b", re.I)
_LEVEL = re.compile(r"\b(?:senior|sr|junior|jr|associate|principal|staff|i|ii|iii|iv|all genders|m/w/d|w/m/d|f/m/d|h/f|f/h|"
                    r"german speaking|french speaking|english speaking|remote|hybrid|dach|emea|apac|latam|nordics|uk|us|usa|eu)\b", re.I)


def role_key(title):
    t = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", title.lower())
    t = re.split(r"\s[-–—|]\s", t)[0]  # "Customer Success Director - London"
    return frozenset(w for w in re.findall(r"[a-z&+]+", _LEVEL.sub(" ", t)) if w not in {"and", "&", "the", "of", "for"})


DATED = {"greenhouse", "lever", "ashby", "recruitee", "teamtailor", "personio", "rippling", "gem"}


ATS_HOSTS = ("greenhouse.io", "lever.co", "ashbyhq.com", "teamtailor.com", "recruitee.com", "personio.de", "personio.com",
             "rippling.com", "gem.com", "myworkdayjobs.com")


def own_host(jobs):
    """An employer that serves its board on its own site (codeandtheory.com/careers?gh_jid=) gives its domain in the job URL."""
    from urllib.parse import urlparse
    for j in jobs:
        h = urlparse(j[3] or "").hostname or ""
        if h and not any(h == a or h.endswith("." + a) for a in ATS_HOSTS):
            return h.removeprefix("www.").removeprefix("jobs.").removeprefix("careers.")
    return ""


def flags(rows, built, days=7, min_new=3, min_older=5, max_recent_share=0.6, prev_boards=None, min_distinct=1):
    cut = (built - timedelta(days=days)).isoformat()
    boards = defaultdict(list)
    for r in rows:
        ats, slug, company, title, pub, url = r[:6]
        cc, dom = (r[6], r[7]) if len(r) > 7 else ([], "")
        if ats in DATED and pub and title:
            boards[(ats, slug)].append((company, title, pub, url, cc or [], dom or ""))
    out = []
    for (ats, slug), jobs in boards.items():
        if prev_boards is not None and f"{ats}:{slug}" not in prev_boards:
            continue
        recent = [j for j in jobs if j[2] >= cut]
        older = len(jobs) - len(recent)
        if older < min_older or len(recent) / len(jobs) > max_recent_share:
            continue
        for fn, rx in FUNC_RE.items():
            fr = [j for j in recent if matches(fn, j[1]) and not EARLY.search(j[1]) and not FOUNDER.search(j[1])]  # a graduate/intern cohort is not a new team
            if len(fr) >= min_new and len({role_key(j[1]) for j in fr}) >= min_distinct and not any(matches(fn, j[1]) for j in jobs if j[2] < cut):
                out.append({"ats": ats, "board": slug, "company": jobs[0][0] or slug, "function": fn,
                            "newInFunction": len(fr), "distinctTitles": len({j[1].strip().lower() for j in fr}), "boardOpen": len(jobs), "boardNewTotal": len(recent),
                            "titles": " | ".join(sorted({j[1] for j in fr}))[:400], "exampleUrl": fr[0][3],
                            "countries": " ".join(c for c, _ in Counter(c for j in fr for c in j[4]).most_common(5)),
                            "domain": next((j[5] for j in jobs if j[5]), "") or DOMAINS.get(ats, {}).get(slug, "") or own_host(fr)})
    return sorted(out, key=lambda r: (-r["newInFunction"], r["company"]))


def from_store():
    import concurrent.futures as cf, urllib.request
    store = "https://api.apify.com/v2/key-value-stores/VFEsrfmHwQiuxShwN/records/"
    m = json.loads(urllib.request.urlopen(store + "MANIFEST", timeout=60).read())

    def one(k):
        b = urllib.request.urlopen(store + k, timeout=180).read()
        rows = json.loads(gzip.decompress(b) if b[:2] == b"\x1f\x8b" else b)
        return [[r.get("ats"), r.get("boardSlug"), r.get("company"), r.get("title"), r.get("publishedAt"), r.get("url"),
                 country_codes(r), (r.get("companyDomain") or "").lower().removeprefix("www.")]
                for r in rows if r.get("ats") in DATED]
    rows = []
    with cf.ThreadPoolExecutor(8) as ex:
        for rs in ex.map(one, m["chunks"]):
            rows += rs
    return {"builtAt": m["builtAt"], "rows": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rows", nargs="?")
    ap.add_argument("--daily", action="store_true")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--min-new", type=int, default=3)
    ap.add_argument("--min-distinct", type=int, default=1, help="distinct roles (role_key) needed; the watchlist uses 2. Not on the strict list: on 5 Nov it dropped 3 of 14 right flags (one title in 3+ countries) and kept 12 of 19 thin ones")
    ap.add_argument("--csv")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--dump", help="save the downloaded rows (gz JSON) here, to pass as `rows` to a second run: one index download, not two (~68 MB each, billed to our Apify account)")
    ap.add_argument("--prev-boards", help="text file of ats:board lines from the previous build (the GitHub Action's state)")
    ap.add_argument("--write-boards", help="write this build's ats:board lines here, for the next --prev-boards")
    ap.add_argument("--prev", help="an earlier data/hiring/<date>.csv.gz: only boards present in it")
    a = ap.parse_args()
    d = json.load(gzip.open(a.rows, "rt")) if a.rows else from_store()
    if a.dump:
        with gzip.open(a.dump, "wt", encoding="utf8") as f:
            json.dump(d, f)
    built = datetime.fromisoformat(d["builtAt"])
    hist = Path(__file__).resolve().parent.parent / "data" / "hiring"
    if a.daily:
        out = hist / "started" / f"{built.date()}.csv"
        if out.exists():
            print(f"{out.name} exists; nothing to do")
            return
        out.parent.mkdir(parents=True, exist_ok=True)
        a.csv = a.csv or str(out)
        if not a.prev:
            older = sorted(p for p in hist.glob("*.csv.gz") if p.name < f"{(built - timedelta(days=1)).date()}")
            a.prev = str(older[-1]) if older else None
    prev = None
    if a.prev:
        with gzip.open(a.prev, "rt") as f:
            prev = {f"{r['ats']}:{r['board']}" for r in csv.DictReader(f)}
    if a.prev_boards and Path(a.prev_boards).exists():
        prev = set(Path(a.prev_boards).read_text(encoding="utf8").split())
    if a.write_boards:
        Path(a.write_boards).write_text("\n".join(sorted({f"{r[0]}:{r[1]}" for r in d["rows"]})) + "\n", encoding="utf8")
    fl = flags(d["rows"], built, a.days, a.min_new, prev_boards=prev, min_distinct=a.min_distinct)
    by = defaultdict(int)
    for r in fl:
        by[r["function"]] += 1
    print(f"{len(fl)} flags at {len({(r['ats'], r['board']) for r in fl})} employers; by function: {dict(sorted(by.items(), key=lambda x: -x[1]))}")
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf8") as f:
            w = csv.DictWriter(f, fieldnames=list(fl[0]))
            w.writeheader()
            w.writerows(fl)
    if a.sample:
        random.seed(5)
        for r in random.sample(fl, min(a.sample, len(fl))):
            print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
