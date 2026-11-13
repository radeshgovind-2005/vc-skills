## Version control rules

- Never commit on `main`. Work on a `type/short-slug` branch.
- Commit titles only: `type(scope): description`. 72 characters or fewer, imperative, no period.
- Never skip a check. No `--no-verify`, `HUSKY=0`, `LEFTHOOK=0`. Do not edit `.githooks/`, CI files,
  or `core.hooksPath` to make a change pass. Fix the cause, or stop and report the blocker.
- PRs are squash-merged. The PR title becomes the commit on `main`. A merge to `main` publishes a release.
- Say "version control" to start the `vc` skill. It shows a plan and waits for your answer.
