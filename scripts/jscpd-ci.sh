#!/bin/sh
set -eu

# EXIT_CODE=0
# ./scripts/run-jscpd.sh || EXIT_CODE=$?
./scripts/run-jscpd.sh || true
./scripts/post-jscpd-comment.sh || true
rm -rf jscpd-report jscpd-base.json jscpd-merged.json
# exit $EXIT_CODE
