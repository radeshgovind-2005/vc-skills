---
name: vc-commit
description: Make clean git commits - stage by intent, write one Conventional Commit title, run the hooks, never bypass them. Use when the user says "commit", "commit this", "save my work", or when the vc router reaches a commit step. Handles mixed unrelated changes by splitting them into separate commits.
---

# vc-commit

A commit is a note to four future readers: someone scanning `git log`, someone running `git blame`, someone bisecting, and an agent. One logical change, one title.

## Steps

1. Read `git status` and `git diff` (staged and unstaged). Group the changes by purpose. Two purposes mean two commits.
2. Check the branch. On `main` or `master`, stop and create a `type/slug` branch first (the pre-commit hook blocks commits there anyway).
3. Stage by name: `git add path/a path/b`. Never `git add -A` or `git add .`. Leave out `.env`, keys, build output, editor files. If a file looks like a secret, stop and tell the user.
4. Write the title: `type(scope): description`. 72 characters or fewer, imperative, no trailing period, no body, no trailer. Choose the type and scope from `vc/references/conventions.md`, and copy scopes already used in `git log --format=%s -50`.
5. Commit: `git commit -m "<title>"`.

## If a hook fails

The hook is telling you something true. Read the message, fix the cause, re-stage, and make a new commit. Do not use `--no-verify`, `-n`, `HUSKY=0`, `LEFTHOOK=0`, or edit hooks or CI to get past it. If you cannot fix it, stop and report what failed and why.

## Rules

- Never amend a commit that was pushed.
- Never commit on the default branch.
- A title that needs "and" is two commits.

## Examples

Input: changed the coupon code in `cart/discount.py` plus a typo in the README.
Output: two commits - `fix(cart): stop double discount on coupon reuse` and `docs(readme): fix install typo`.
