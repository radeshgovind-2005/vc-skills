---
name: vc
description: Version control for any git repo - commit, branch, PR, squash-merge, release. Use whenever the user says "version control", "vc", "commit this", "ship this", "wrap this up", "branch and PR", "clean up my git", "what should I do with these changes", or asks about uncommitted changes, a messy branch, an open PR, a merge, or a release, even if they never say git. Reads the repo, shows a numbered plan, and waits for the user to accept or comment before changing anything.
---

# vc - version control router

The user wants version control done properly without re-explaining the rules each time. Read the repo, propose a plan, wait, then run the plan through the other vc skills. The user's conventions live in `references/conventions.md` (read it when you name a branch, pick a commit type, or compute a bump).

## Step 1 - Read state (always free)

Run `sh <this-skill-dir>/scripts/state.sh`. It is read-only. Also skim the diff (`git diff`, `git diff --cached`) so you understand what the changes are for. Do not ask the user things the repo can tell you.

If `repo=false`, offer `git init` and stop. If `hooks_installed=false` or any `missing=` line appears, put "run vc-setup" in the plan; the checks and release flow depend on it.

## Autopilot

If the user says "autopilot", "just ship it", or "merge it without asking" (or names the merge outright, like "merge it"), skip the plan wait, the PR-text wait in vc-pr, and the merge ask in vc-merge for that request. Say what you will do in one line, then run it. Autopilot lifts the asks only. It never lifts the Never list below: no `--admin`, no force push, no push to the default branch, no skipped hooks. It also does not extend to later requests. If a precondition fails (checks red, wrong head, not mergeable), stop and report.

Autopilot and releases: say up front what the title type will publish. `docs`, `chore`, `refactor`, `style`, `test`, `build`, `ci` publish nothing. Do not change the type to force a bump. If the change is user-facing and the user wants a release, ask once whether it should be `feat` or `fix`.

## Step 2 - Build the plan

Pick steps from the state. Unrelated changes become separate commits (see vc-commit).

| State | Plan |
|---|---|
| On default branch, changes present | new branch from the changes, commit(s), push + PR |
| On default branch, clean | say there is nothing to do; check for a merged-PR cleanup |
| Feature branch, changes present | commit(s); then push + PR if no PR exists |
| Feature branch, clean, unpushed commits | push + PR |
| Feature branch, pushed, no PR | open PR |
| Feature branch, PR already open | update that PR's title and body (do not create another) |
| Feature branch, `ahead` > 0 | push first; checks on the PR describe the old head until you do |
| PR open, checks pending | watch checks and report |
| PR open, checks failed | show the failure; propose a fix commit |
| PR open, checks green | propose squash-merge, with the version it will release |
| PR merged | sync default branch, delete the local branch, report the release tag |
| `merged_local_branches=` present | offer to delete those local branches (and their remotes) with `git branch -d`; ask first |
| Behind default branch | rebase on origin/<default> before the PR |

Mark each step with who decides: `auto` (local and reversible), `asks` (publishes or hard to undo).

## Step 3 - Show the plan and wait

Use this shape. Keep it short.

```
State: on main, 4 files changed, nothing pushed.
1. [auto]  Create branch  fix/cart-coupon-reuse
2. [auto]  Commit         fix(cart): stop double discount on coupon reuse
3. [asks]  Push + open PR (title = the squash commit, bump: patch)
4. [auto]  Watch checks, then report
Merge is not in this plan. A merge publishes a release, so I ask again.
```

Then handle the reply in plain language: "ok" runs every step; "ok, skip 3" or "change 2: use feat" edits the plan and shows it again; a question gets an answer with the plan kept open; "no" stops with nothing changed.
If the user only wants advice ("just tell me", "don't change anything"), print the state and your recommendation and stop.

## Step 4 - Run the plan

Load the matching skill for each step: `vc-commit`, `vc-pr`, `vc-merge`, `vc-setup`. An accepted plan covers exactly the steps shown. If anything surprising appears (a hook fails, the state changed, a conflict), stop and report instead of improvising.

Approval levels, because the cost of a wrong move rises with each one:

| Level | Examples | Rule |
|---|---|---|
| 0 read | status, diff, log, `gh pr view` | free |
| 1 local, reversible | branch, commit, stash | run, then report |
| 2 publishes | push, open PR | covered by an accepted plan; show the PR text first |
| 3 hard to undo | merge, tag, release, delete, force-with-lease | ask again at that moment, show the exact command |

Never: commit on the default branch, force push, push to the default branch, skip a hook (`--no-verify`, `HUSKY=0`), edit `.githooks/` or CI to make a check pass, merge with `--admin`. If a check fails, fix the cause or stop and report. The vc-guard hook enforces this, but do not rely on it; the rule is yours too.

## Step 5 - Monitor

After a PR opens, watch it: `gh pr checks --watch --interval 30` (or poll `gh pr checks` every 30 to 60 seconds if you cannot run long commands). Report when checks finish. Before trusting `gh pr checks`, confirm they are for the current commit: `gh pr view --json headRefOid` must equal `git rev-parse HEAD` (state.sh prints `pr_head=` and `head=`). If not, push and wait for the new run. On failure, show the failing log lines and propose a fix; do not push fixes unasked. Never merge on your own; green checks lead to the Step 2 proposal.
