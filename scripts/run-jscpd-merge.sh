#!/usr/bin/env bash
set -euo pipefail

TARGET_BRANCH="${CI_MERGE_REQUEST_TARGET_BRANCH_NAME:-main}"
BASE_WORKTREE="jscpd-base-worktree"
MERGED_WORKTREE="jscpd-merged-worktree"

# Determine reference for target branch
if git show-ref --verify --quiet "refs/remotes/origin/$TARGET_BRANCH"; then
  TARGET_REF="origin/$TARGET_BRANCH"
elif git show-ref --verify --quiet "refs/heads/$TARGET_BRANCH"; then
  TARGET_REF="$TARGET_BRANCH"
else
  echo "Target branch $TARGET_BRANCH not found" >&2
  exit 1
fi

cleanup() {
  git worktree remove "$BASE_WORKTREE" --force 2>/dev/null || true
  git worktree remove "$MERGED_WORKTREE" --force 2>/dev/null || true
}
trap cleanup EXIT

# Ensure we have the latest target branch when a remote is available
if git remote get-url origin >/dev/null 2>&1; then
  git fetch origin "$TARGET_BRANCH" >/dev/null
else
  echo "No remote named 'origin'; skipping fetch" >&2
fi

# Run jscpd on the base branch
git worktree add "$BASE_WORKTREE" "$TARGET_REF"
(
  cd "$BASE_WORKTREE"
  npx --yes jscpd --reporters json --output jscpd-report . >/dev/null
  mv jscpd-report/jscpd-report.json ../jscpd-base.json
)

# Run jscpd on the merged code (current HEAD merged with target branch)
git worktree add --detach "$MERGED_WORKTREE" HEAD
(
  cd "$MERGED_WORKTREE"
  git merge --no-commit --no-ff "$TARGET_REF" >/dev/null
  npx --yes jscpd --reporters json --output jscpd-report . >/dev/null
  mv jscpd-report/jscpd-report.json ../jscpd-merged.json
)
