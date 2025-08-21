#!/bin/sh
set -eu

EXIT_CODE=0
./scripts/run-jscpd.sh || EXIT_CODE=$?
./scripts/post-jscpd-comment.sh || true
exit $EXIT_CODE
