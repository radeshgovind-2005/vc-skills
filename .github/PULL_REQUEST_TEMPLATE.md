<!--
The PR title becomes the commit on main, and a merge publishes a release.
Format:  type(scope): description     (72 characters or fewer, no period)
  Good:  feat(auth): add refresh token rotation
  Good:  fix(cart): stop double discount on coupon reuse
  Poor:  update stuff   |   fix   |   WIP   |   feat: add search and fix bug and update docs.
Release bump: feat = minor, fix/perf = patch, "!" after the type = major, others = none.
-->

## What changed and why

<!-- One short paragraph. Say why, not only what. -->

## How I tested it

<!-- Commands run, or screenshots. "Not tested" is allowed, but say it. -->

## Release impact

- [ ] Bump matches the title: `patch` / `minor` / `major` / `none`
- [ ] Breaking change? The title has `!` (the commit body is not kept on squash)

## Risk and rollback

<!-- What could break? How do we undo it? Delete this section for trivial changes. -->
