"""Put the Impressum line (and the privacy notice under it) on every page of a built started-hiring site (root + frozen weeks), in the build folder only.

    python -P tools/add_impressum.py <site dir> [--src <impressum.txt>]

--src: the Started-Hiring-Weekly repo carries its own copy (scripts/add_impressum.py + impressum.txt at its root), so its
daily Action (scripts/update.sh) puts the same lines on the github.io root it re-renders (7 Nov, ask a15 "page yes").

Reads ../hiring-signals/impressum.txt (one or more lines, plain text, e.g. "Impressum (§5 DDG): Oskar ..., <street>,
<postcode> <town>, Germany. Contact: jordan.m.i.belfort@gmail.com"; for an Austrian address "Impressum (§5 ECG, §25 MedienG)"). No file = does nothing and says so. The file exists only
once Oskar has said "page yes" to ask a14 (6 Nov): the page shows a $29 offer, and the charter puts a German seller's name and
address on a selling page only with his yes. Frozen weeks in site-archive/ stay as sent; only the deployed copy gets the line,
inserted before </main>.
"""
import html
import pathlib
import sys

SRC = pathlib.Path(__file__).resolve().parents[2] / "hiring-signals" / "impressum.txt"
# GDPR Art. 13 notice for people who write to the page's address (compliance audit 6 Nov, row 8). It names no one itself:
# the controller is the person in the Impressum, so it ships only with that line. Checked 6 Nov 14:45: the page sets no
# cookies and loads no third-party script, font or image (only links out to job postings). Keep it true if that changes.
PRIVACY = ("Privacy: the person named above is the controller. This page sets no cookies and loads nothing from other sites; "
           "its hosts (Surge, GitHub Pages) keep their own server logs. If you email me, I keep your address, your mail and "
           "my replies to answer you and, if you take the list, to send it (GDPR Art. 6(1)(b) and (f)), and delete them by "
           "31 Dec 2026 unless you subscribe. Reply to any mail to get a copy, a correction or deletion, or to object (after a "
           "\"stop\" I keep only your address on a do-not-mail list); you "
           "can also complain to your data protection authority.")


def main():
    site = pathlib.Path(sys.argv[1])
    src = pathlib.Path(sys.argv[sys.argv.index("--src") + 1]) if "--src" in sys.argv else SRC
    if not src.exists() or not src.read_text(encoding="utf-8").strip():
        print(f"impressum: none ({src} missing; ask a15 'page yes' answered 7 Nov)")
        return
    lines = [l.strip() for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
    block = ('<p class=m id=impressum>' + "<br>".join(html.escape(l) for l in lines) + "</p>\n"
             + '<p class=m id=privacy>' + html.escape(PRIVACY) + "</p>\n")
    n = 0
    for page in sorted(site.rglob("index.html")):
        t = page.read_text(encoding="utf-8")
        if 'id=impressum' in t:
            continue
        if "</main>" not in t:
            sys.exit(f"impressum: {page} has no </main>; not deploying a page without it")
        page.write_text(t.replace("</main>", block + "</main>", 1), encoding="utf-8")
        n += 1
    print(f"impressum: added to {n} pages")


if __name__ == "__main__":
    main()
