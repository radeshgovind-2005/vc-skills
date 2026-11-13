#!/bin/sh
# Set GitHub repo rules: squash-only, PR title as the commit, branch ruleset, delete branch on merge.
# Usage: repo-settings.sh          (print the commands only)
#        repo-settings.sh --apply  (run them; needs `gh auth login` and admin rights)
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
apply=0; [ "$1" = "--apply" ] && apply=1
command -v gh >/dev/null 2>&1 || { echo "gh CLI not found. Install it from https://cli.github.com" >&2; exit 1; }
run() { echo "+ $*"; [ "$apply" = 1 ] && "$@"; return 0; }
run gh repo edit --enable-squash-merge --disable-merge-commit --disable-rebase-merge --delete-branch-on-merge
run gh api -X PATCH "repos/{owner}/{repo}" -f squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=BLANK
run gh api -X POST "repos/{owner}/{repo}/rulesets" --input "$here/../assets/ruleset-main.json"
[ "$apply" = 1 ] || echo "(dry run: nothing changed. Add --apply to run these.)"
