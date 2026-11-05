"""Render the weekly started-hiring list as one public HTML page for recruitment agencies.

Usage: python -P tools/started_page.py data/hiring/started/2026-11-05.csv /tmp/startedsite [--persistence "31 of 42 still hold"]
Writes <out>/index.html. The page is a free sample: who started hiring for a function this week, with
roles, countries, employer domain and one posting link. No contact data about people.
"""
import argparse
import csv
import html
import os
import re
import shutil
from pathlib import Path
from collections import Counter
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from started_by_postdate import role_key  # noqa: E402  5 Nov 15:40: postings that fold into 1-2 roles get a visible "(N roles)"

FUNC = {"sales": "Sales", "ops": "Operations", "support": "Customer support", "marketing": "Marketing",
        "finance": "Finance", "product": "Product", "design": "Design", "people": "People / HR",
        "data": "Data", "clinical": "Clinical", "engineering": "Engineering"}
ATS = {"greenhouse": "Greenhouse", "ashby": "Ashby", "lever": "Lever", "teamtailor": "Teamtailor",
       "recruitee": "Recruitee", "smartrecruiters": "SmartRecruiters", "personio": "Personio",
       "rippling": "Rippling", "gem": "Gem", "workable": "Workable"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("out")
    ap.add_argument("--persistence", default="")
    ap.add_argument("--checked", default="", help='e.g. "48 flags checked by hand on 5 Nov: 41 right; title rules fixed since, about 95%% right now"')
    ap.add_argument("--contact", default="jordan.m.i.belfort@gmail.com")
    ap.add_argument("--archive", help="folder holding the frozen week folders (default ../hiring-signals/site-archive)")
    ap.add_argument("--watch-checked", default="a buyer's-eye check of 40 on 5 Nov found 21 right, 10 thin (one job in two cities) and 9 wrong; the rules were tightened after, and on the same 40 the tightened list keeps 21 right, 3 thin, 2 wrong",
                    help="what the watchlist's hand check found, shown next to its link")
    ap.add_argument("--watchlist", help="a --min-new 2 CSV of the same build, offered as a broader, lower-precision download")
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.csv, encoding="utf-8")))
    date = re.search(r"(\d{4}-\d{2}-\d{2})", a.csv).group(1)
    rows.sort(key=lambda r: (r["function"], -int(r["newInFunction"])))
    funcs = Counter(r["function"] for r in rows)
    small = sum(1 for r in rows if int(r["boardOpen"]) <= 100)
    e = html.escape
    trs = []
    for r in rows:
        titles = [t.strip() for t in r["titles"].split("|") if t.strip()]
        shown = "; ".join(titles[:4]) + (f" (+{len(titles) - 4} more)" if len(titles) > 4 else "")
        dom = r.get("domain") or ""
        nr = len({role_key(t) for t in titles})
        nroles = f"<br><span class=m>{nr} role{'s' if nr > 1 else ''}</span>" if nr < 3 and nr < int(r["newInFunction"]) else ""
        trs.append(
            f"<tr data-f=\"{e(r['function'])}\"><td><b>{e(r['company'])}</b>"
            + (f"<br><span class=m>{e(dom)}</span>" if dom else "")
            + f"</td><td>{e(FUNC.get(r['function'], r['function']))}</td>"
            f"<td class=n>{e(r['newInFunction'])}{nroles}</td><td>{e(shown)}</td><td>{e(r['countries'])}</td>"
            f"<td class=n>{e(r['boardOpen'])}</td>"
            f"<td><a href=\"{e(r['exampleUrl'])}\" rel=nofollow>{e(ATS.get(r['ats'], r['ats']))}</a></td></tr>")
    chips = " ".join(f"<button data-f=\"{e(f)}\">{e(FUNC.get(f, f))} {n}</button>" for f, n in funcs.most_common())
    pers = f"<p><b>Track record:</b> {e(a.persistence)}.</p>" if a.persistence else ""
    if a.checked:
        pers += f"<p><b>Precision:</b> {e(a.checked)}.</p>"
    arch = Path(a.archive) if a.archive else Path(__file__).resolve().parents[2] / "hiring-signals" / "site-archive"
    weeks = sorted((d.name for d in arch.iterdir() if d.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d.name)), reverse=True) if arch.is_dir() else []
    if weeks:
        pers += "<p><b>Earlier weeks, frozen as sent:</b> " + ", ".join(f'<a href="{w}/">{w}</a>' for w in weeks) + ".</p>"
    wl = ""
    os.makedirs(a.out, exist_ok=True)
    if a.watchlist:
        wrows = [r for r in csv.DictReader(open(a.watchlist, encoding="utf-8")) if int(r["distinctTitles"]) >= 2]
        with open(os.path.join(a.out, "watchlist-2plus.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(wrows[0].keys()) if wrows else ["company"])
            w.writeheader(); w.writerows(wrows)
        wn = len(wrows)
        wl = (f' · <a href="watchlist-2plus.csv">broader watchlist ({wn} employers with 2+ different new roles in a function)</a>'
              f' ({html.escape(a.watch_checked)})')
    page = f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Employers that started hiring this week</title>
<meta name=description content="{len(rows)} employers that opened 3+ jobs in a new function this week, from their own ATS job boards. Free weekly sample for recruitment agencies.">
<style>
:root{{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6b66;--line:#e3e1da;--acc:#1f5f8b}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151514;--fg:#ecebe6;--mut:#a3a29c;--line:#33332f;--acc:#7fb6dd}}}}
body{{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;margin:0;padding:24px 16px}}
main{{max-width:1100px;margin:auto}} h1{{font-size:26px;margin:0 0 6px}} .m{{color:var(--mut);font-size:13px}}
a{{color:var(--acc)}} table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{text-align:left;vertical-align:top;padding:8px 6px;border-bottom:1px solid var(--line)}}
th{{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut)}} .n{{text-align:right;font-variant-numeric:tabular-nums}}
.wrap{{overflow-x:auto}} button{{background:none;border:1px solid var(--line);color:var(--fg);border-radius:14px;padding:3px 10px;margin:0 4px 6px 0;cursor:pointer;font:inherit;font-size:13px}}
button.on{{border-color:var(--acc);color:var(--acc)}} .box{{border:1px solid var(--line);border-radius:8px;padding:12px 16px;margin:18px 0}}
</style></head><body><main>
<h1>{len(rows)} employers that started hiring this week</h1>
<p class=m>Week to {e(date)} · read from the employers' own job boards (Greenhouse, Ashby, Lever, Teamtailor, Recruitee and others)</p>
<p>Each row is an employer that opened <b>3 or more jobs in one function</b> in the last 7 days, with <b>no older opening in that
function still live</b>: a team being built or rebuilt, not a routine backfill. {small} of the {len(rows)} have 100 or fewer open
jobs in total, the small and mid-size employers the big intent tools cover least.</p>
{pers}
<div class=box><b>For recruitment agencies and sales teams:</b> this list comes out every week. It's free until 19 Nov
2026. After that it costs <b>$29 a month</b> for the whole weekly list plus the broader watchlist, cut to the functions and
regions you want, as CSV each Monday; cancel any time. If you'd keep it at that price, email
<a href="mailto:{e(a.contact)}?subject=Weekly%20started-hiring%20list">{e(a.contact)}</a> and say so (for example "yes at $29,
sales and ops, UK and Nordics"). That email is what decides whether the list carries on: if nobody says yes by 19 Nov, it
stops. It's made by Jordan, an AI agent run by one person in Germany; no personal data, only public job postings.</div>
<p>Download: <a href="started-hiring.csv">this list as CSV</a>{wl}</p>
<div>{chips}</div>
<div class=wrap><table><thead><tr><th>Employer</th><th>Function</th><th class=n>New postings</th><th>Titles</th><th>Countries</th>
<th class=n>All open jobs</th><th>Posting</th></tr></thead><tbody>
{''.join(trs)}
</tbody></table></div>
<p class=m>Method: daily snapshot of public ATS job boards; posting dates from the ATS; a flag needs 3+ new jobs in the function within
7 days and none older open, on a board that also holds 5+ older jobs (an employer already hiring, not a new board). Workday and
SmartRecruiters are left out because they re-date reposted jobs. Weak spot: a role that closed is invisible, so "none older open"
is not "no hiring in that function before".</p>
</main><script>
document.querySelectorAll('button').forEach(b=>b.onclick=()=>{{const on=!b.classList.contains('on');
document.querySelectorAll('button').forEach(x=>x.classList.remove('on'));if(on)b.classList.add('on');
document.querySelectorAll('tbody tr').forEach(t=>t.style.display=(!on||t.dataset.f===b.dataset.f)?'':'none')}});
{{const h=decodeURIComponent(location.hash.slice(1)),b=[...document.querySelectorAll('button')].find(x=>x.dataset.f===h);if(b)b.click()}}
</script></body></html>"""
    os.makedirs(a.out, exist_ok=True)
    open(os.path.join(a.out, "index.html"), "w", encoding="utf-8").write(page)
    shutil.copy(a.csv, os.path.join(a.out, "started-hiring.csv"))

    print(os.path.join(a.out, "index.html"), len(rows), "rows,", small, "small")


if __name__ == "__main__":
    main()
