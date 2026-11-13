---
name: vc-pr
description: Open a pull request the right way - title equals the future squash commit, body from the repo template, then watch the checks. Use when the user says "open a PR", "make a PR", "push this up", "send for review", or when the vc router reaches a PR step.
---

# vc-pr

On this setup the PR title becomes the one commit on `main`, and a merge publishes a release. A wrong title means a wrong version, so the title is the most important line you write.

## Steps

0. Find an existing PR: `gh pr list --head <branch> --state open --json number,title,url`. If one exists, you update it (steps 3 to 5, then `gh pr edit <n> --title ... --body-file ...`) instead of creating a new one. Its title may be stale from an earlier commit.
1. Confirm the branch is not the default branch and the working tree is committed. Run `git status -sb`; if it says `ahead`, push before you open or update the PR so the PR and its checks match local HEAD. Rebase if behind: `git fetch origin && git rebase origin/<default>`; push afterwards with `--force-with-lease` only.
2. Read what the branch does: `git log <default>..HEAD --format=%s` and `git diff <default>...HEAD --stat`.
3. Write the title: `type(scope): description`, 72 characters or fewer, no period. One branch with several commits still gets one title that describes the whole change. Compute the bump from the type table in `vc/references/conventions.md` and state it.
4. Fill the PR body from `.github/PULL_REQUEST_TEMPLATE.md`: what changed and why, how it was tested (real commands you ran, or "not tested"), release impact, risk and rollback. Keep it short and true. Write it to a temp file.
5. Show the title and body to the user. This is the publish step, so wait for the plan to be accepted or edited. Under autopilot (see `vc`), show them and continue without waiting.
6. Push, then open or update: `git push -u origin HEAD` then (new PR) `gh pr create --title "<title>" --body-file <file>` or (existing PR) `gh pr edit <n> --title "<title>" --body-file <file>`. If `gh` is missing or not logged in, print the title and body and the compare URL instead, and say what is missing.
7. Before trusting checks, confirm `gh pr view --json headRefOid --jq .headRefOid` equals `git rev-parse HEAD`. Green checks for an older head say nothing about your commits. Then watch: `gh pr checks --watch --interval 30`. Report the result. On failure show the failing lines and propose a fix; do not push one unasked.

## Rules

- Never push to the default branch. Never plain `--force`.
- Do not merge from this skill. Merging is vc-merge.
- If the title type publishes nothing (docs, chore, ...), say so in the PR summary. Do not change the type to force a release.
- Do not claim tests passed unless you ran them or saw them pass.
