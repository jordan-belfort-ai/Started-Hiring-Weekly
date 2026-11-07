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
# rows a hand check found wrong (hand-wrong.csv, a copy of jordan's ventures/hiring-signals/hand-wrong.csv) stay off until their until-date
mkdir -p "$T/page"; REMOVED=$(python -P scripts/drop_hand_wrong.py "$T/started-$DAY.csv" "$T/page/started-$DAY.csv" --hand hand-wrong.csv)
python -P scripts/drop_hand_wrong.py "$T/watch2-$DAY.csv" "$T/page/watch2-$DAY.csv" --hand hand-wrong.csv >/dev/null
python -P scripts/started_page.py "$T/page/started-$DAY.csv" . --watchlist "$T/page/watch2-$DAY.csv" --archive . --removed "$REMOVED" \
  --checked "rows were checked by hand against the live boards. On a week the rules had not been tuned on (to 22 Oct), 11 of 46 were a clear new team, 20 true but thin (one or two roles posted in several cities or languages) and 15 wrong (mostly a title keyword read as the wrong function). The rules were fixed after that without losing any row checked right. On a second unseen week (to 15 Oct), checked against the fixed rules, 18 of 48 were a clear new team, 15 thin and 15 wrong: still about a third wrong, mostly an older role in the function whose title the rules don't recognise. Rows with 3 or more different roles, listed first, were right 59% of the time across the earlier checks. Read each row's titles before you call"
# Impressum + privacy notice (impressum.txt) on the root and the frozen weeks; skips a page that has it already (7 Nov)
python -P scripts/add_impressum.py . --src impressum.txt
cp "$T/boards.txt" boards-prev.txt
echo "$BUILT" > built.txt
