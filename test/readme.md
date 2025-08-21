# Duplicate Code Check

This repository uses [jscpd](https://github.com/kucherenko/jscpd) to detect duplicated code.

## Run locally

Make sure you have Node.js installed. Then run:

```sh
./scripts/run-jscpd.sh
```

The script uses `npx` to download jscpd if necessary and scans the repository. The command exits with a non‑zero status when duplicates are found.

## CI integration

The `.gitlab-ci.yml` includes a `code-duplication` job in the `test` stage that runs the same script to prevent duplicated code from entering the repository.
