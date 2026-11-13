# Conventions

Read this when you name a branch, choose a commit type, write a PR title, or compute a version bump.

## Branches
`type/short-slug` from the default branch. Lowercase, hyphens, 2 to 5 words.
`feat/cart-coupon-reuse`, `fix/login-redirect-loop`, `docs/install-steps`.
One branch, one purpose. Delete it after the squash-merge. Never commit on `main`.

## Commit and PR titles
`type(scope): description`. 72 characters or fewer. Imperative. No trailing period. No body.
The scope is the area changed. Copy scopes already used in `git log --format=%s -50`; do not invent new ones.

| Type | Use for | Release bump |
|---|---|---|
| feat | new behavior for users | minor |
| fix | a bug fix | patch |
| perf | faster, same behavior | patch |
| revert | undo an earlier change | patch |
| refactor | no behavior change | none |
| docs, style, test, build, ci, chore | the rest | none |
| any type with `!` (feat!: ...) | breaking change | major |

Good: `feat(auth): add refresh token rotation` and `fix(cart): stop double discount on coupon reuse`.
Poor: `update stuff`, `fix`, `WIP`, `feat: add search and fix bug and update docs.`
Two changes in one title means two commits (or two PRs).

Breaking change: put `!` after the type. The squash commit has no body, so a `BREAKING CHANGE:` footer is lost.

## History
- Squash-merge only. The PR title is the commit on `main`. No merge commits, no WIP on `main`.
- Update a feature branch with `git rebase origin/main`, then push with `--force-with-lease`. Never plain `--force`.
- Never amend or rebase commits that others have pulled.
- Stage files by name. Never `git add -A`. Skip `.env`, keys, build output.
- Parallel agents: one git worktree per agent (`git worktree add ../repo-task -b type/slug`). One agent merges.

## Releases
semantic-release runs on every push to `main`. It reads the squash commits since the last tag, picks the bump,
tags `vX.Y.Z`, and writes GitHub release notes. A merge is a release. A merge with a `docs:` or `chore:` title publishes nothing.
With no earlier tag, the first release is 1.0.0. For a pre-1.0 project, create a baseline tag first (ask the user).
