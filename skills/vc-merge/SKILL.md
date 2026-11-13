---
name: vc-merge
description: Squash-merge an approved pull request, clean up, and confirm the release. Use when the user says "merge it", "squash and merge", "ship it", "update the repo", or when the vc router reaches a merge step. A merge to the default branch publishes a release, so this skill asks first unless autopilot is on.
---

# vc-merge

Merging is a release here: semantic-release runs on every push to the default branch. Without autopilot, ask every time, even if an earlier plan was accepted. Under autopilot (see `vc`), or when the user named the merge ("merge it", "ship it", "update the repo"), do not ask: show the line from step 2 and run it. Autopilot never adds `--admin`, never force-pushes, never bypasses rules.

## Preconditions (check, do not assume)

1. `gh pr view --json state,isDraft,mergeable,title` shows an open, non-draft, mergeable PR.
2. `gh pr checks` shows every required check passing. If any is pending, wait with `gh pr checks --watch --interval 30`. If any failed, stop and report (under autopilot, fix the cause in a new commit if it is clear, push, and wait again).
3. `gh pr view --json headRefOid` equals `git rev-parse HEAD`, and `git status -sb` shows no `ahead`. Otherwise the checks are for an older commit: push and wait.
4. The PR title is a valid Conventional Commit (the pr-title check should say so).

## Steps

1. Work out the release: last tag from `git describe --tags --abbrev=0` (or none), the type in the title, and the bump from `vc/references/conventions.md`. With no earlier tag the first release is 1.0.0; mention it and offer a baseline tag for pre-1.0 projects.
2. Ask, showing the exact command and the result: "Squash-merge #12 `fix(cart): stop double discount` - publishes v1.4.3 (patch). Command: `gh pr merge 12 --squash --delete-branch`. Go?" Wait for a clear yes (skip the wait only under the exception above).
3. Run it. Never add `--admin` or `--auto` without being asked; never bypass branch rules.
4. Sync: `git switch <default> && git pull --ff-only origin <default>` (local default may have no upstream; `git branch -u origin/<default>` fixes that once), then delete the local branch with `git branch -d <name>` (lowercase `-d`).
5. Confirm the release: find the run with `gh run list --workflow release.yml --limit 1`; if it is `in_progress` or `queued`, `gh run watch <id> --exit-status` before reporting. Then `git fetch --tags` and report the new tag, or say that the title type publishes nothing (docs, chore, refactor).
6. Offer cleanup of other local branches already merged into the default branch (`git branch --merged <default>`); delete only after a yes. Under autopilot, skip the offer and end with a one-line report.

## If something fails

Report the error as it is. Do not retry with other flags and do not loosen rules to get the merge through.
