#!/bin/sh
set -eu

# Run jscpd with console and json reporters so results can be parsed later.
# Reports are written to the default "jscpd-report" directory.
npx --yes jscpd \
  --min-lines 5 \
  --reporters console,json \
  --output jscpd-report \
  --threshold 1 \
  "$@"
