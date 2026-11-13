---
name: vc-pr
description: Open a pull request the right way - title equals the future squash commit, body from the repo template, then watch the checks. Use when the user says "open a PR", "make a PR", "push this up", "send for review", or when the vc router reaches a PR step.
---

# vc-pr

On this setup the PR title becomes the one commit on `main`, and a merge publishes a release. A wrong title means a wrong version, so the title is the most important line you write.

## Steps

1. Confirm the branch is not the default branch and the working tree is committed. Rebase if behind: `git fetch origin && git rebase origin/<default>`; push afterwards with `--force-with-lease` only.
2. Read what the branch does: `git log <default>..HEAD --format=%s` and `git diff <default>...HEAD --stat`.
3. Write the title: `type(scope): description`, 72 characters or fewer, no period. One branch with several commits still gets one title that describes the whole change. Compute the bump from the type table in `vc/references/conventions.md` and state it.
4. Fill the PR body from `.github/PULL_REQUEST_TEMPLATE.md`: what changed and why, how it was tested (real commands you ran, or "not tested"), release impact, risk and rollback. Keep it short and true. Write it to a temp file.
5. Show the title and body to the user. This is the publish step, so wait for the plan to be accepted or edited.
6. Push and open: `git push -u origin HEAD` then `gh pr create --title "<title>" --body-file <file>`. If `gh` is missing or not logged in, print the title and body and the compare URL instead, and say what is missing.
7. Watch: `gh pr checks --watch --interval 30`. Report the result. On failure show the failing lines and propose a fix; do not push one unasked.

## Rules

- Never push to the default branch. Never plain `--force`.
- Do not merge from this skill. Merging is vc-merge.
- Do not claim tests passed unless you ran them or saw them pass.
