#!/bin/sh
set -eu

# EXIT_CODE=0
# ./scripts/run-jscpd-merge.sh || EXIT_CODE=$?
./scripts/run-jscpd-merge.sh || true
./scripts/post-jscpd-merge-comment.sh || true
rm -rf jscpd-report jscpd-base.json jscpd-merged.json
# exit $EXIT_CODE
