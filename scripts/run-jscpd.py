#!/usr/bin/env python3
"""Run jscpd scans and post GitLab comments.

This script replaces previous shell helpers and can:

* run a jscpd scan on the current repository (``scan``)
* compare duplicate code between base and merged branches (``merge``)
* optionally post the results back to the merge request when GitLab
  environment variables are available.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from fnmatch import fnmatch
from pathlib import Path

# ---------------------------------------------------------------------------
# Diff filter helpers (simplified copy of gitlab_ci_summarizer.should_include)
# ---------------------------------------------------------------------------

def load_diff_filter(path: str = "diff_filter.json") -> tuple[list[str], list[str]]:
    try:
        data = json.loads(Path(path).read_text())
        allow = data.get("allow", [])
        deny = data.get("deny", [])
        if not isinstance(allow, list) or not isinstance(deny, list):
            return [], []
        return allow, deny
    except Exception:
        return [], []


ALLOW_PATTERNS, DENY_PATTERNS = load_diff_filter()


def should_include(path: str) -> bool:
    for pattern in DENY_PATTERNS:
        if fnmatch(path, pattern):
            return False
    if not ALLOW_PATTERNS:
        return True
    for pattern in ALLOW_PATTERNS:
        if fnmatch(path, pattern):
            return True
    return False


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def run_cmd(cmd: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a subprocess command."""
    return subprocess.run(cmd, cwd=cwd, check=check)


def run_jscpd(target: str = ".", reporters: str = "console,json", extra: list[str] | None = None) -> int:
    """Execute jscpd via ``npx`` in *target* directory."""
    cmd = [
        "npx",
        "--yes",
        "jscpd",
        "--min-lines",
        "5",
        "--reporters",
        reporters,
        "--output",
        "jscpd-report",
    ]
    if extra:
        cmd.extend(extra)
    proc = subprocess.run(cmd, cwd=target)
    return proc.returncode


def post_comment(body: str) -> None:
    """Post *body* as a merge request comment if env vars are present."""
    env = os.environ
    required = [
        "CI_PROJECT_ID",
        "CI_MERGE_REQUEST_IID",
        "CI_API_V4_URL",
        "GITLAB_PERSONAL_TOKEN",
    ]
    if not all(env.get(k) for k in required):
        print("Missing GitLab environment variables, skipping comment")
        return

    url = (
        f"{env['CI_API_V4_URL']}/projects/{env['CI_PROJECT_ID']}/"
        f"merge_requests/{env['CI_MERGE_REQUEST_IID']}/notes"
    )
    data = json.dumps({"body": body}).encode()
    headers = {
        "PRIVATE-TOKEN": env["GITLAB_PERSONAL_TOKEN"],
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req):
        pass


# ---------------------------------------------------------------------------
# Comment builders
# ---------------------------------------------------------------------------

def build_scan_comment(report_path: Path) -> str:
    data = json.loads(report_path.read_text())
    total = data["statistics"]["total"]
    comment = (
        "🧬 **jscpd Report**\n\n"
        f"- Clones: {total['clones']}\n"
        f"- Duplicated lines: {total['duplicatedLines']} / {total['lines']} ({total['percentage']:.2f}%)"
    )

    duplicates = data.get("duplicates", [])
    if duplicates:
        rows = [
            "| Lines | First File | Second File |",
            "|---|---|---|",
        ]
        for dup in duplicates:
            rows.append(
                f"| {dup['lines']} | {dup['firstFile']['name']}:{dup['firstFile']['start']}-{dup['firstFile']['end']} "
                f"| {dup['secondFile']['name']}:{dup['secondFile']['start']}-{dup['secondFile']['end']} |"
            )
        comment += "\n\n" + "\n".join(rows)
    else:
        comment += "\n\n_No duplicates found_"

    files = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
    passed = [f for f in files if should_include(f)]
    blocked = [f for f in files if f not in passed]

    def fmt(items: list[str]) -> str:
        return "\n".join(f"- {i}" for i in items) if items else "- (none)"

    comment += (
        "\n\n**Diff Filter Results**\n\n"
        f"_Passed files:_\n{fmt(passed)}\n\n"
        f"_Blocked files:_\n{fmt(blocked)}"
    )
    return comment


def build_merge_comment(base_file: Path, merged_file: Path) -> str:
    base = json.loads(base_file.read_text())
    merged = json.loads(merged_file.read_text())
    formats = sorted(
        set(base.get("statistics", {}).get("formats", {}).keys())
        | set(merged.get("statistics", {}).get("formats", {}).keys())
    )

    rows = [
        "| Format | Base Duplicated Lines | Base % | Merged Duplicated Lines | Merged % |",
        "|---|---|---|---|---|",
    ]
    for fmt in formats:
        b = base["statistics"].get("formats", {}).get(fmt, {}).get("total", {})
        m = merged["statistics"].get("formats", {}).get(fmt, {}).get("total", {})
        rows.append(
            f"| {fmt} | {b.get('duplicatedLines', 0)} | {b.get('percentage', 0)}% | "
            f"{m.get('duplicatedLines', 0)} | {m.get('percentage', 0)}% |"
        )

    table = "\n".join(rows)
    return f"### jscpd duplicate code report\n\n{table}"


# ---------------------------------------------------------------------------
# Mode implementations
# ---------------------------------------------------------------------------

def scan_mode(args: argparse.Namespace) -> int:
    rc = run_jscpd(extra=args.extra)
    if args.comment:
        report = Path("jscpd-report/jscpd-report.json")
        if report.exists():
            post_comment(build_scan_comment(report))
        else:
            print("No jscpd report found, skipping comment")
    return rc


def merge_mode(args: argparse.Namespace) -> int:
    env = os.environ
    target_branch = env.get("CI_MERGE_REQUEST_TARGET_BRANCH_NAME", "main")
    base_wt = Path("jscpd-base-worktree")
    merged_wt = Path("jscpd-merged-worktree")
    base_json = Path("jscpd-base.json")
    merged_json = Path("jscpd-merged.json")

    # fetch target branch when possible
    if run_cmd(["git", "remote", "get-url", "origin"], check=False).returncode == 0:
        run_cmd(["git", "fetch", "origin", target_branch], check=False)
    else:
        print("No remote named 'origin'; skipping fetch", file=sys.stderr)

    if run_cmd(["git", "show-ref", "--verify", "--quiet", f"refs/remotes/origin/{target_branch}"], check=False).returncode == 0:
        target_ref = f"origin/{target_branch}"
    elif run_cmd(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{target_branch}"], check=False).returncode == 0:
        target_ref = target_branch
    else:
        print(f"Target branch {target_branch} not found", file=sys.stderr)
        return 1

    def cleanup() -> None:
        for wt in [base_wt, merged_wt]:
            run_cmd(["git", "worktree", "remove", str(wt), "--force"], check=False)
        for path in [Path("jscpd-report"), base_json, merged_json]:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass

    try:
        run_cmd(["git", "worktree", "add", str(base_wt), target_ref])
        run_jscpd(str(base_wt), reporters="json")
        shutil.move(str(base_wt / "jscpd-report" / "jscpd-report.json"), base_json)

        run_cmd(["git", "worktree", "add", "--detach", str(merged_wt), "HEAD"])
        run_cmd(["git", "merge", "--no-commit", "--no-ff", target_ref], cwd=str(merged_wt))
        run_jscpd(str(merged_wt), reporters="json")
        shutil.move(str(merged_wt / "jscpd-report" / "jscpd-report.json"), merged_json)

        if args.comment:
            post_comment(build_merge_comment(base_json, merged_json))
    finally:
        cleanup()
    return 0


# ---------------------------------------------------------------------------
# Argument parsing and entry point
# ---------------------------------------------------------------------------

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run jscpd and optionally comment on MR")
    sub = parser.add_subparsers(dest="command")

    scan = sub.add_parser("scan", help="scan current repository (default)")
    scan.add_argument("extra", nargs=argparse.REMAINDER, help="extra arguments for jscpd")
    scan.add_argument("--comment", action="store_true", help="post results as MR comment")

    merge = sub.add_parser("merge", help="compare base and merged code")
    merge.add_argument("--comment", action="store_true", help="post merge report as MR comment")

    if not argv:
        argv = ["scan"]
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.command == "merge":
        return merge_mode(args)
    return scan_mode(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
