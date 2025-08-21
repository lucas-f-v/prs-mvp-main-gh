#!/bin/sh
set -eu
npx --yes jscpd --min-lines 5 --reporters console --threshold 1 "$@"
