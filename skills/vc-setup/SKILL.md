---
name: vc-setup
description: Set up version-control guardrails in a repo - git hooks (.githooks), commit-title check, secret scan, lint and test gates, PR template, CI, PR-title check, semantic-release, GitHub merge rules, and an agent guard hook. Use when the user says "set up the repo", "add hooks", "set up .github", "enforce commit conventions", "add releases", or when the vc router finds missing setup. Shows a plan first and never overwrites existing files.
---

# vc-setup

Layers, because each one covers the weakness of the one before: instructions (AGENTS.md) can be ignored; the agent guard only covers agent sessions; local hooks can be skipped; CI and branch rules cannot. The same checks run in hooks and CI through `.githooks/run-checks.sh`.

## Steps

1. Plan (writes nothing): `python3 <this-skill-dir>/scripts/install.py plan` from the repo root. Show the output. It lists CREATE, MERGE, SKIP, CONFLICT, and the detected stack with its lint and test commands.
2. Wait for the user to accept or comment. Check the detected lint and test commands with them; wrong commands make every commit fail or pass for no reason.
3. Apply: `python3 <this-skill-dir>/scripts/install.py apply`. It never overwrites a file; for a CONFLICT it writes `<file>.vc-new`. Show the diff for each and let the user decide. Use the Edit tool to merge, not shell redirects.
4. Verify, and show the results: `sh .githooks/run-checks.sh all`; then prove the title hook rejects a bad title (`printf 'update stuff\n' > /tmp/m && .githooks/commit-msg /tmp/m` must exit 1).
5. GitHub rules (level 3): run `sh <this-skill-dir>/scripts/repo-settings.sh` with no flag to print the commands, show them, and ask. Only on a clear yes run it with `--apply` (needs `gh auth login` and admin rights). It sets squash-only, PR title as the commit, delete branch on merge, and a branch ruleset that needs the `checks` and `pr-title` jobs.
6. Report what is left for the user: commit the new files on a branch and open a PR through vc; each new clone needs `git config core.hooksPath .githooks`; consider pinning the actions in `.github/workflows/` to commit SHAs; with no earlier tag the first release is 1.0.0.

## Notes

- Node is needed only in CI, for semantic-release. Nothing local needs it.
- The release flow does not commit a changelog back to `main`, so protected branches keep working. Release notes live in GitHub Releases.
- The guard in `.claude/hooks/vc-guard.py` is a text guard. It stops lazy and accidental bypass, not code that builds commands at run time. CI is the real gate.
- Repo-specific gates (README rules, link checks) go in `.githooks/checks.d/*.sh`. `run-checks.sh all` runs each one, so hooks and CI share them.
- Re-run `plan` any time; a second run reports SKIP for everything that is current.
