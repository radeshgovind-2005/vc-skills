# vc skills

Version control for AI agents. Say "version control" and the agent reads the repo, shows a plan, and waits.

## Install (all your repos)

    cp -r skills/* ~/.claude/skills/          # Claude Code, personal skills

Other agents that read the Agent Skills format use their own folder. Check that agent's docs.
Publish this folder to GitHub, then `npx skills add <owner>/<repo>` installs into the agents it finds.

## Use

| You say | What happens |
|---|---|
| "version control" | Router reads state, shows a numbered plan, waits for ok / edits / questions |
| "set up the repo" | vc-setup shows a plan, then installs hooks, .github files, release flow, agent guard |
| "commit" | vc-commit: stage by name, one title-only Conventional Commit |

Start in a new repo with: "set up the repo".

## What is in here

| Skill | Job |
|---|---|
| vc | Router. Reads state, plans, runs the others, watches PR checks |
| vc-setup | Installer. Hooks, CI, PR template, semantic-release, agent guard, GitHub rules |
| vc-commit | Clean commits |
| vc-pr | PR title = squash commit; body from template; watch checks |
| vc-merge | Squash-merge, with a second ask because a merge publishes a release |

## Verify

    pip install pyyaml
    bash tests/run_all.sh

## Limits

- The guard is a text guard. CI and the GitHub ruleset are the real gate.
- Not tested: real GitHub (no `gh` login here), skill auto-triggering, other agents.
- Pin the actions in `.github/workflows/` to commit SHAs before you rely on them.
