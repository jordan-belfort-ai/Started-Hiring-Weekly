#!/usr/bin/env bash
# Rebuild this week's page from the public job index (Apify store VFEsrfmHwQiuxShwN), once per new build.
set -euo pipefail
BUILT=$(curl -s https://api.apify.com/v2/key-value-stores/VFEsrfmHwQiuxShwN/records/MANIFEST | python3 -c "import json,sys;print(json.load(sys.stdin)['builtAt'])")
if [ -f built.txt ] && [ "$(cat built.txt)" = "$BUILT" ]; then echo "build $BUILT already rendered"; exit 0; fi
DAY=${BUILT:0:10}
T=$(mktemp -d)
python -P scripts/started_by_postdate.py --prev-boards boards-prev.txt --write-boards "$T/boards.txt" --csv "$T/started-$DAY.csv" --dump "$T/rows.json.gz"
python -P scripts/started_by_postdate.py "$T/rows.json.gz" --prev-boards boards-prev.txt --min-new 2 --min-distinct 2 --csv "$T/watch2-$DAY.csv"  # one download, not two
python -P scripts/guess_domains.py "$T/started-$DAY.csv" "$T/watch2-$DAY.csv" --save | tail -1 || true
python -P scripts/started_page.py "$T/started-$DAY.csv" . --watchlist "$T/watch2-$DAY.csv" --archive . \
  --checked "all 42 flags of the 5 Nov week were checked by hand against the live boards: 14 are a clear new team, 19 are true but thin (one or two roles posted in several cities or languages), and 9 are wrong (an older role in that function the rule missed, the wrong function, or roles already gone). The rules were fixed after (trades out of ops, support leads counted), so read each rows titles before you call"
cp "$T/boards.txt" boards-prev.txt
echo "$BUILT" > built.txt
