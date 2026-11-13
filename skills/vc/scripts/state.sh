#!/bin/sh
# Read-only. Prints the git facts the vc router needs, as key=value lines.
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "repo=false"; exit 0; }
echo "repo=true"
branch=$(git symbolic-ref --short -q HEAD || echo "(detached)")
echo "branch=$branch"

default=$(git symbolic-ref --short -q refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##')
[ -n "$default" ] || { for b in main master; do git show-ref --verify -q "refs/heads/$b" && default=$b && break; done; }
echo "default_branch=${default:-unknown}"
[ "$branch" = "$default" ] && echo "on_default=true" || echo "on_default=false"

echo "staged=$(git diff --cached --name-only | wc -l | tr -d ' ')"
echo "unstaged=$(git diff --name-only | wc -l | tr -d ' ')"
echo "untracked=$(git ls-files --others --exclude-standard | wc -l | tr -d ' ')"

if git rev-parse --verify -q HEAD >/dev/null 2>&1; then
  echo "has_commits=true"
  if up=$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null); then
    echo "upstream=$up"
    echo "ahead=$(git rev-list --count '@{u}..HEAD')"
    echo "behind=$(git rev-list --count 'HEAD..@{u}')"
  else
    echo "upstream=none"
  fi
  # Local default branch without upstream makes a bare `git pull` print a hint; pull with `origin <default>`.
  [ -n "$default" ] && ! git rev-parse --verify -q "$default@{u}" >/dev/null 2>&1 && echo "default_has_upstream=false"
  if [ -n "$default" ] && [ "$branch" != "$default" ] && git rev-parse --verify -q "$default" >/dev/null 2>&1; then
    echo "commits_ahead_of_default=$(git rev-list --count "$default..HEAD")"
  fi
  tag=$(git describe --tags --abbrev=0 2>/dev/null) && {
    echo "last_tag=$tag"; echo "commits_since_tag=$(git rev-list --count "$tag..HEAD")"; } || echo "last_tag=none"
else
  echo "has_commits=false"
fi

[ "$(git config --local --get core.hooksPath)" = ".githooks" ] && echo "hooks_installed=true" || echo "hooks_installed=false"
for f in .releaserc.json .github/workflows/release.yml .github/workflows/pr-title.yml .github/PULL_REQUEST_TEMPLATE.md .claude/hooks/vc-guard.py; do
  [ -f "$f" ] || echo "missing=$f"
done
echo "remote=$(git remote get-url origin 2>/dev/null || echo none)"

if command -v gh >/dev/null 2>&1; then
  echo "gh=installed"
  if gh auth status >/dev/null 2>&1; then
    echo "gh_auth=true"
    gh pr view --json number,title,state,isDraft,url,reviewDecision,statusCheckRollup,headRefOid \
      --jq '"open_pr=#\(.number) \(.state) draft=\(.isDraft) \(.url)\npr_title=\(.title)\npr_head=\(.headRefOid)\npr_checks=" + ([.statusCheckRollup[]? | (.conclusion // .status)] | group_by(.) | map("\(.[0]):\(length)") | join(","))' 2>/dev/null || echo "open_pr=none"
  else echo "gh_auth=false"; fi
else
  echo "gh=not_installed"
fi

if [ -n "$default" ]; then
  merged=$(git branch --merged "$default" --format='%(refname:short)' 2>/dev/null | grep -vxF -e "$default" -e "$branch" | tr '\n' ' ')
  [ -n "$merged" ] && echo "merged_local_branches=$merged"
fi
echo "head=$(git rev-parse HEAD 2>/dev/null)"

echo "--- changed files (max 30)"
git status --porcelain | head -30
echo "--- recent subjects"
git log --format='%s' -8 2>/dev/null
