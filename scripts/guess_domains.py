"""Fill blank employer domains in started-hiring CSVs by guessing and checking (5 Nov, venture hiring-signals).

Buyers drop the domain into Apollo, Clay or a CRM (replies.md promises it), and 38 of 184 watchlist rows on 5 Nov had none,
mostly Greenhouse boards whose job URLs sit on greenhouse.io. For each blank row: candidates from the board slug and the
company name (.com, .io, .ai, .co, then the countries' TLDs), keep the first whose home page answers and whose <title> or
og:site_name carries the company name. Name-guarded like company_domains.py; a miss stays blank, never a guess.

    python -P tools/guess_domains.py data/hiring/started/2026-11-05.csv data/hiring/started/2026-11-05-watch2.csv [--save] [--dry-run]

Rewrites the CSVs in place (unless --dry-run) and, with --save, adds the finds to actors/ats-jobs/src/company_domains.json
so the next build and started_by_postdate.py carry them.
"""
import csv, html, json, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "actors" / "ats-jobs" / "src" / "company_domains.json"
if not SRC.parent.is_dir():  # the GitHub repo copy keeps src/ next to the script
    SRC = Path(__file__).resolve().parent / "src" / "company_domains.json"
UA = {"User-Agent": "Mozilla/5.0 (compatible; jordan-belfort-ats-jobs/1.0)"}
LEGAL = r"\b(inc|llc|ltd|limited|gmbh|ag|sa|sas|bv|plc|corp|corporation|co|company|group|holdings|technologies|europe|labs?)\b\.?"
CC_TLD = {"GB": "co.uk", "DE": "de", "FR": "fr", "NL": "nl", "SE": "se", "DK": "dk", "NO": "no", "FI": "fi", "ES": "es",
          "IT": "it", "PL": "pl", "LT": "lt", "IE": "ie", "CH": "ch", "AT": "at", "BE": "be", "PT": "pt", "IN": "in",
          "AU": "com.au", "CA": "ca", "BR": "com.br", "NG": "ng", "KE": "co.ke", "EG": "com.eg"}


def tokens(name):
    n = re.sub(LEGAL, " ", name.lower())
    return [t for t in re.findall(r"[a-z0-9]+", n.replace("ü", "u").replace("ö", "o").replace("ä", "a")) if len(t) > 1]


def candidates(slug, name, countries):
    t = tokens(name)
    stems = []
    for s in ("".join(t), slug.lower().removesuffix("careers").removesuffix("jobs"), "-".join(t), t[0] if t else ""):
        s = re.sub(r"[^a-z0-9-]", "", s)
        if len(s) > 2 and s not in stems:
            stems.append(s)
    tlds = ["com", "io", "ai", "co"] + [CC_TLD[c] for c in countries.split() if c in CC_TLD]
    return [f"{s}.{tld}" for s in stems for tld in tlds]


def check(dom, name):
    try:
        with urllib.request.urlopen(urllib.request.Request(f"https://{dom}/", headers=UA), timeout=8) as r:
            final = r.geturl()
            page = r.read(200_000).decode("utf8", "replace")
    except Exception:
        return None
    host = re.sub(r"^www\.", "", urllib.request.urlparse(final).hostname or "")
    if any(p in host for p in ("godaddy", "sedo", "dan.com", "afternic", "hugedomains", "parking")):
        return None
    title = " ".join(re.findall(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)[:1]
                     + re.findall(r'og:site_name"\s+content="([^"]+)"', page, re.I)[:1])
    title = html.unescape(title).lower()
    t = tokens(name)
    if not t or not all(x in re.sub(r"[^a-z0-9]", "", title.replace("ü", "u").replace("ö", "o")) for x in t[:2]):
        return None
    if re.search(r"for sale|domain is|parked|coming soon|under construction", page[:5000], re.I):
        return None
    return host if host.split(".")[0] in dom or dom.split(".")[0] in host else dom


def posting_text(row):
    """The board's own words: Greenhouse/Lever descriptions via their APIs, else the example posting's page."""
    urls = {"greenhouse": f"https://boards-api.greenhouse.io/v1/boards/{row['board']}/jobs?content=true",
            "lever": f"https://api.lever.co/v0/postings/{row['board']}?mode=json"}
    for u in filter(None, [urls.get(row["ats"]), row.get("exampleUrl")]):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=15) as r:
                return html.unescape(html.unescape(r.read(3_000_000).decode("utf8", "replace"))).lower()
        except Exception:
            continue
    return ""


def find(row):
    """A candidate counts if its home page carries the name AND either the board's own postings mention the domain, or
    the name is distinctive (2+ words, or 10+ letters) and is the domain's stem. 5 Nov: title-only matching took
    air.com for Air and momentous.com, a different company, for Momentous; both fail this."""
    text = None
    for d in candidates(row["board"], row["company"], row.get("countries", "")):
        got = check(d, row["company"])
        if not got:
            continue
        text = posting_text(row) if text is None else text
        if got in text or d in text:
            return got
        t = tokens(row["company"])  # no mention: only a distinctive name whose stem is the domain
        if (len(t) >= 2 or len("".join(t)) >= 10) and d.split(".")[0].replace("-", "") == "".join(t):
            return got
    return ""


def main():
    files = [a for a in sys.argv[1:] if not a.startswith("--")]
    blanks = {}
    for f in files:
        for r in csv.DictReader(open(f, encoding="utf8")):
            if not r["domain"]:
                blanks[(r["ats"], r["board"])] = r
    with ThreadPoolExecutor(12) as ex:
        found = dict(zip(blanks, ex.map(find, blanks.values())))
    hits = {k: v for k, v in found.items() if v}
    for (ats, board), d in sorted(found.items()):
        print(f"{ats}:{board:30} {blanks[(ats, board)]['company'][:30]:30} -> {d or '-'}")
    print(f"{len(hits)} of {len(blanks)} blank employers found")
    if "--dry-run" in sys.argv:
        return
    for f in files:
        rows = list(csv.DictReader(open(f, encoding="utf8")))
        for r in rows:
            r["domain"] = r["domain"] or hits.get((r["ats"], r["board"]), "")
        with open(f, "w", newline="", encoding="utf8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    if "--save" in sys.argv:
        db = json.loads(SRC.read_text())
        for (ats, board), d in hits.items():
            db.setdefault(ats, {}).setdefault(board, d)
        SRC.write_text(json.dumps(db, ensure_ascii=False, sort_keys=True, indent=0))


if __name__ == "__main__":
    main()
