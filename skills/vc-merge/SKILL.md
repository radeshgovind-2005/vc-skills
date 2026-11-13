---
name: vc-merge
description: Squash-merge an approved pull request, clean up, and confirm the release. Use when the user says "merge it", "squash and merge", "ship it", or when the vc router reaches a merge step. A merge to the default branch publishes a release, so this skill always asks first.
---

# vc-merge

Merging is a release here: semantic-release runs on every push to the default branch. That makes this a level-3 action. Ask every time, even if an earlier plan was accepted.

## Preconditions (check, do not assume)

1. `gh pr view --json state,isDraft,mergeable,title` shows an open, non-draft, mergeable PR.
2. `gh pr checks` shows every required check passing. If any is pending or failed, stop and report.
3. The PR title is a valid Conventional Commit (the pr-title check should say so).

## Steps

1. Work out the release: last tag from `git describe --tags --abbrev=0` (or none), the type in the title, and the bump from `vc/references/conventions.md`. With no earlier tag the first release is 1.0.0; mention it and offer a baseline tag for pre-1.0 projects.
2. Ask, showing the exact command and the result: "Squash-merge #12 `fix(cart): stop double discount` - publishes v1.4.3 (patch). Command: `gh pr merge 12 --squash --delete-branch`. Go?" Wait for a clear yes.
3. Run it. Never add `--admin` or `--auto` without being asked; never bypass branch rules.
4. Sync: `git switch <default> && git pull --ff-only`, then delete the local branch with `git branch -d <name>` (lowercase `-d`).
5. Confirm the release: `git fetch --tags`, then `gh run list --workflow release.yml --limit 1`. Report the new tag, or say that the title type publishes nothing (docs, chore, refactor).

## If something fails

Report the error as it is. Do not retry with other flags and do not loosen rules to get the merge through.
