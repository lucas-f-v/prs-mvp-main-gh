#!/bin/sh
set -eu

REPORT="jscpd-report/jscpd-report.json"

# Skip if report or required env vars are missing
if [ ! -f "$REPORT" ]; then
  echo "No jscpd report found, skipping comment"
  exit 0
fi

: "${CI_PROJECT_ID:=}"
: "${CI_MERGE_REQUEST_IID:=}"
: "${CI_API_V4_URL:=}"
: "${GITLAB_PERSONAL_TOKEN:=}"

if [ -z "$CI_PROJECT_ID" ] || [ -z "$CI_MERGE_REQUEST_IID" ] || \
   [ -z "$CI_API_V4_URL" ] || [ -z "$GITLAB_PERSONAL_TOKEN" ]; then
  echo "Missing GitLab environment variables, skipping comment"
  exit 0
fi

dup_lines=$(jq '.statistics.total.duplicatedLines' "$REPORT")
clones=$(jq '.statistics.total.clones' "$REPORT")
lines=$(jq '.statistics.total.lines' "$REPORT")
percent=$(jq '.statistics.total.percentage' "$REPORT")

comment=$(printf '🧬 **jscpd Report**\n\n- Clones: %s\n- Duplicated lines: %s / %s (%.2f%%)' "$clones" "$dup_lines" "$lines" "$percent")

duplicates_count=$(jq '.duplicates | length' "$REPORT")
if [ "$duplicates_count" -gt 0 ]; then
  table_rows=$(jq -r '.duplicates[] | "| \(.lines) | \(.firstFile.name):\(.firstFile.start)-\(.firstFile.end) | \(.secondFile.name):\(.secondFile.start)-\(.secondFile.end) |"' "$REPORT")
  comment="$comment\n\n| Lines | First File | Second File |\n|---|---|---|\n$table_rows"
else
  comment="$comment\n\n_No duplicates found_"
fi

# Report which files pass or are blocked by diff_filter.json
diff_data=$(git ls-files | python - <<'PY'
import sys, json
sys.path.append('scripts')
from gitlab_ci_summarizer import should_include

files=[line.strip() for line in sys.stdin if line.strip()]
passed=[f for f in files if should_include(f)]
blocked=[f for f in files if f not in passed]
print(json.dumps({'passed': passed, 'blocked': blocked}))
PY
)
passed_list=$(echo "$diff_data" | jq -r '.passed[]?' 2>/dev/null | sed 's/^/- /')
blocked_list=$(echo "$diff_data" | jq -r '.blocked[]?' 2>/dev/null | sed 's/^/- /')
[ -z "$passed_list" ] && passed_list="- (none)"
[ -z "$blocked_list" ] && blocked_list="- (none)"
comment="$comment\n\n**Diff Filter Results**\n\n_Passed files:_\n$passed_list\n\n_Blocked files:_\n$blocked_list"

curl --silent --show-error --fail \
  --header "PRIVATE-TOKEN: $GITLAB_PERSONAL_TOKEN" \
  --data-urlencode "body=$(printf '%b' "$comment")" \
  "$CI_API_V4_URL/projects/$CI_PROJECT_ID/merge_requests/$CI_MERGE_REQUEST_IID/notes"
