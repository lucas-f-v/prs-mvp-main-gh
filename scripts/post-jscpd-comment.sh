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

curl --silent --show-error --fail \
  --request POST \
  --header "PRIVATE-TOKEN: $GITLAB_PERSONAL_TOKEN" \
  --header "Content-Type: application/json" \
  --data "$(jq -n --arg body "$comment" '{body: $body}')" \
  "$CI_API_V4_URL/projects/$CI_PROJECT_ID/merge_requests/$CI_MERGE_REQUEST_IID/notes"
