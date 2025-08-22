#!/usr/bin/env bash
set -euo pipefail

BASE_FILE="jscpd-base.json"
MERGED_FILE="jscpd-merged.json"

if [[ ! -f "$BASE_FILE" || ! -f "$MERGED_FILE" ]]; then
  echo "Missing jscpd JSON files" >&2
  exit 1
fi

FORMATS=$(jq -r '.statistics.formats | keys[]' "$BASE_FILE" "$MERGED_FILE" | sort -u)
TABLE="| Format | Base Duplicated Lines | Base % | Merged Duplicated Lines | Merged % |\n|---|---|---|---|---|"
for fmt in $FORMATS; do
  base_dup=$(jq -r --arg f "$fmt" '.statistics.formats[$f].total.duplicatedLines // 0' "$BASE_FILE")
  base_pct=$(jq -r --arg f "$fmt" '.statistics.formats[$f].total.percentage // 0' "$BASE_FILE")
  merged_dup=$(jq -r --arg f "$fmt" '.statistics.formats[$f].total.duplicatedLines // 0' "$MERGED_FILE")
  merged_pct=$(jq -r --arg f "$fmt" '.statistics.formats[$f].total.percentage // 0' "$MERGED_FILE")
  TABLE="$TABLE\n| $fmt | $base_dup | ${base_pct}% | $merged_dup | ${merged_pct}% |"
done

COMMENT="### jscpd duplicate code report\n\n$TABLE"

: "${CI_API_V4_URL?CI_API_V4_URL not set}"
: "${CI_PROJECT_ID?CI_PROJECT_ID not set}"
: "${CI_MERGE_REQUEST_IID?CI_MERGE_REQUEST_IID not set}"
: "${GITLAB_PERSONAL_TOKEN?GITLAB_PERSONAL_TOKEN not set}"

curl --header "PRIVATE-TOKEN: $GITLAB_PERSONAL_TOKEN" \
     --data-urlencode "body=$(printf '%s' "$COMMENT")" \
     "$CI_API_V4_URL/projects/$CI_PROJECT_ID/merge_requests/$CI_MERGE_REQUEST_IID/notes"
